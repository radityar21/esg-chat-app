"""Endpoints that front the AgentCore Runtime orchestrator: chat, run list and run detail (ledger + SFN status)."""

from __future__ import annotations

import json
import os
import re
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


def chat(body: dict[str, Any]) -> dict[str, Any]:
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("prompt is required")
    if len(prompt) > MAX_PROMPT:
        raise ValueError(f"prompt longer than {MAX_PROMPT} characters")
    sid = str(body.get("session_id") or "")
    if len(sid) < 33:  # AgentCore requires a session id of at least 33 characters
        sid = f"esg-{uuid.uuid4().hex}"
    out = _runtime({"mode": "chat", "prompt": prompt}, sid)
    out.setdefault("session_id", sid)
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
                    "updated_at": doc.get("updated_at"), "created_at": doc.get("created_at"),
                    "sections": len(sections), "healed": sum(1 for s in sections.values() if (s or {}).get("status") == "healed"),
                    "escalated": sum(1 for s in sections.values() if (s or {}).get("status") in ("source_data", "unresolved", "escalate_data"))})
    return {"runs": out}


def run_detail(execution_id: str) -> dict[str, Any]:
    if not EXEC_ID_RE.match(execution_id or ""):
        raise ValueError("invalid execution id")
    short = execution_id.split(":")[-1]
    doc = common.s3_get(f"agent-ledger/{short}.json")
    if doc is None:
        return {"found": False, "execution_id": short}
    return {"found": True, "ledger": doc}
