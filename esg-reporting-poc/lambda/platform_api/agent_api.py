"""Endpoints that front the AgentCore Runtime orchestrator: chat, run list and run detail (ledger + SFN status)."""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from typing import Any

from . import common

RUNTIME_ARN = os.environ.get("AGENTCORE_RUNTIME_ARN", "")
EXEC_ID_RE = re.compile(r"^[A-Za-z0-9_\-:.]{1,120}$")
MAX_PROMPT = 4000


def _runtime(payload: dict[str, Any], session_id: str, timeout_note: str = "") -> dict[str, Any]:
    if not RUNTIME_ARN:
        raise RuntimeError("AGENTCORE_RUNTIME_ARN is not configured")
    resp = common.client("bedrock-agentcore").invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN, runtimeSessionId=session_id, payload=json.dumps(payload).encode(), contentType="application/json", accept="application/json")
    raw = resp["response"].read()
    try:
        return json.loads(raw)
    except ValueError:
        return {"response": raw.decode("utf-8", "replace")}


JOBS_TABLE = os.environ.get("CHAT_JOBS_TABLE", "")
JOB_TTL_DAYS = int(os.environ.get("JOB_TTL_DAYS", "14"))
SESSION_RE = re.compile(r"^[A-Za-z0-9_\-]{33,100}$")


def _jobs():
    import boto3

    return boto3.resource("dynamodb", region_name=common.REGION).Table(JOBS_TABLE)


def _invoke_self(payload: dict[str, Any]) -> None:
    common.client("lambda").invoke(FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"], InvocationType="Event", Payload=json.dumps(payload).encode())


def chat_submit(body: dict[str, Any], jobs: Any = None, invoke: Any = None) -> dict[str, Any]:
    """Queue a chat turn. The HTTP API cuts requests at 30 s, so the turn runs in a second (asynchronous) invocation
    and the UI polls ``chat_status``. The prompt is NOT stored: only the answer, for 14 days."""
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("prompt is required")
    if len(prompt) > MAX_PROMPT:
        raise ValueError(f"prompt longer than {MAX_PROMPT} characters")
    sid = str(body.get("session_id") or "")
    if not SESSION_RE.match(sid):  # AgentCore needs >= 33 characters; never accept arbitrary client strings
        sid = f"esg-{uuid.uuid4().hex}"
    user = str(body.get("_user") or "anonymous")
    job_id = uuid.uuid4().hex
    (jobs or _jobs()).put_item(Item={"job_id": job_id, "user": user, "status": "queued", "session_id": sid, "created_at": int(time.time()),
                                     "ttl": int(time.time()) + JOB_TTL_DAYS * 86400})
    (invoke or _invoke_self)({"action": "agent_chat_worker", "job_id": job_id, "prompt": prompt, "session_id": sid, "user": user})
    return {"job_id": job_id, "session_id": sid, "status": "queued"}


def chat_worker(event: dict[str, Any], jobs: Any = None, runtime: Any = None) -> dict[str, Any]:
    table = jobs or _jobs()
    job_id = event["job_id"]
    table.update_item(Key={"job_id": job_id}, UpdateExpression="SET #s = :s", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":s": "running"})
    try:
        out = (runtime or _runtime)({"mode": "chat", "prompt": event["prompt"], "user": event.get("user", "")}, event["session_id"])
        table.update_item(Key={"job_id": job_id}, UpdateExpression="SET #s = :s, #r = :r", ExpressionAttributeNames={"#s": "status", "#r": "result"},
                          ExpressionAttributeValues={":s": "done", ":r": json.dumps(out)[:300000]})
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001 - the UI shows a short, safe message; details stay in the Lambda log
        import logging

        logging.getLogger().exception("chat worker failed")
        table.update_item(Key={"job_id": job_id}, UpdateExpression="SET #s = :s, #e = :e", ExpressionAttributeNames={"#s": "status", "#e": "error"},
                          ExpressionAttributeValues={":s": "failed", ":e": f"{type(exc).__name__}"})
        return {"ok": False}


def chat_status(job_id: str, user: str, is_admin: bool = False, jobs: Any = None) -> dict[str, Any]:
    if not re.match(r"^[0-9a-f]{32}$", job_id or ""):
        raise ValueError("invalid job id")
    item = (jobs or _jobs()).get_item(Key={"job_id": job_id}).get("Item")
    if not item or (item["user"] != user and not is_admin):
        return {"found": False}
    out: dict[str, Any] = {"found": True, "status": item["status"]}
    if item["status"] == "done":
        out["result"] = json.loads(item["result"])
    if item["status"] == "failed":
        out["error"] = item.get("error", "failed")
    return out


def runs(params: dict[str, Any]) -> dict[str, Any]:
    """List agent ledgers, newest first (S3 listing is enough for the demo volume)."""
    s3 = common.client("s3")
    items: list[dict[str, Any]] = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=common.OUTPUT_BUCKET, Prefix="agent-ledger/"):
        items += [o for o in page.get("Contents", []) if o["Key"].endswith(".json")]
    items.sort(key=lambda o: o["LastModified"], reverse=True)
    limit = max(1, min(50, int(params.get("limit", 15))))
    out = []
    for o in items[:limit]:
        doc = common.s3_get(o["Key"]) or {}
        sections = doc.get("sections", {})
        out.append({"execution_id": doc.get("execution_id"), "status": doc.get("status"), "pipeline": doc.get("pipeline"),
                    "updated_at": doc.get("updated_at"), "created_at": doc.get("created_at"), "parent_execution_id": doc.get("parent_execution_id"),
                    "year": (doc.get("params") or {}).get("reporting_year"), "framework": (doc.get("params") or {}).get("framework"),
                    "sections": len(sections), "healed": sum(1 for s in sections.values() if (s or {}).get("status") == "healed"),
                    "escalated": sum(1 for s in sections.values() if (s or {}).get("status") in ("source_data", "unresolved", "escalate_data")),
                    "summary": summarize(doc)})
    return {"runs": out}


def summarize(doc: dict[str, Any]) -> str:
    """One line per run, in the words of its pipeline (a data sync has no 'repaired sections')."""
    pipeline, status, res = doc.get("pipeline"), doc.get("status"), doc.get("result") or {}
    if status in ("pending", "running", None):
        return "in progress"
    if pipeline == "data_sync":
        tables = res.get("tables") or {}
        ok = sum(1 for t in tables.values() if t.get("status") == "ok")
        parts = [f"{ok}/{len(tables)} tables loaded"]
        if res.get("retried"):
            parts.append(f"{len(res['retried'])} retried")
        warns = sum(int(t.get("warnings") or 0) for t in tables.values())
        if warns:
            parts.append(f"{warns} warning(s)")
        if res.get("etl_state"):
            parts.append("ETL finished" if res["etl_state"] == "completed" else f"ETL {res['etl_state']}")
        elif tables and ok < len(tables):
            parts.append("ETL not started")
        return " · ".join(parts)
    if pipeline == "ghg_inventory":
        return "inventory built" if status == "completed" else f"inventory {status}"
    if pipeline == "esg_report":
        healed, unresolved = len(res.get("healed") or []), len(res.get("unresolved") or [])
        if status == "failed":
            return "pipeline failed"
        parts = [f"{healed} section(s) repaired" if healed else "all sections passed"]
        if unresolved:
            parts.append(f"{unresolved} need review")
        return " · ".join(parts)
    return status or ""


def run_detail(execution_id: str) -> dict[str, Any]:
    if not EXEC_ID_RE.match(execution_id or ""):
        raise ValueError("invalid execution id")
    short = execution_id.split(":")[-1]
    doc = common.s3_get(f"agent-ledger/{short}.json")
    if doc is None:
        return {"found": False, "execution_id": short}
    return {"found": True, "ledger": doc}
