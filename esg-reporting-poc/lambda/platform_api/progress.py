"""Run checkpoints: one ordered list of steps per run, combining the Step Functions history (inner engine) with the
agent's ledger (outer orchestrator). Used by the UI to show a live stepper for reports, data syncs and GHG inventories.

Step status: pending | running | done | failed | skipped | warning
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Callable

from . import common

TERMINAL_AGENT = {"completed", "escalated", "failed"}
EXEC_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,80}$")

# key, label, Step Functions states that belong to the step (entered/exited), map state (counted per item)
SFN_STEPS: dict[str, list[dict[str, Any]]] = {
    "esg_report": [
        {"key": "validate", "label": "Validate the request", "states": ["ValidateInput", "CheckValidation"]},
        {"key": "etl", "label": "Refresh the GHG calculations (Scope 1, 2, 3 ETL)", "states": ["WaitForGlueJobs", "TriggerAggregation"]},
        {"key": "query", "label": "Read the metrics from the data lake", "states": ["QueryAthena"]},
        {"key": "generate", "label": "Write and validate each section", "states": ["GenerateSections"], "map": "GenerateSections", "unit": "sections"},
        {"key": "filter", "label": "Select the sections for the document", "states": ["FilterSections"]},
        {"key": "assemble", "label": "Assemble the document", "states": ["AssembleDocument", "NotifyCompletion"]},
    ],
    "data_sync": [
        {"key": "extract", "label": "Extract the tables from the source database and check their data contracts", "states": ["SyncTables"],
         "map": "SyncTables", "unit": "tables", "ok_state": "Ok", "failed_state": "Failed"},
    ],
    "ghg_inventory": [
        {"key": "etl", "label": "Calculate Scope 1, 2 and 3 emissions", "states": ["RunEtl"]},
        {"key": "aggregate", "label": "Aggregate the annual figures", "states": ["Aggregate"]},
        {"key": "inventory", "label": "Build the GHG Protocol inventory", "states": ["BuildInventory"]},
    ],
}


def _iso(t: Any) -> str | None:
    return t.isoformat() if isinstance(t, datetime) else (str(t) if t else None)


def _history(sfn: Any, arn: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    kw: dict[str, Any] = {"executionArn": arn, "maxResults": 1000, "includeExecutionData": False}
    while True:
        r = sfn.get_execution_history(**kw)
        events += r.get("events", [])
        if not r.get("nextToken") or len(events) > 5000:
            return events
        kw["nextToken"] = r["nextToken"]


def sfn_steps(pipeline: str, events: list[dict[str, Any]], sfn_status: str) -> list[dict[str, Any]]:
    """Turn the execution history into step statuses. Pure function (unit-tested)."""
    entered: dict[str, Any] = {}
    exited: dict[str, Any] = {}
    counts: dict[str, int] = {}
    map_len: dict[str, int] = {}
    map_done: dict[str, int] = {}
    map_failed: dict[str, int] = {}
    last_entered = ""
    for e in sorted(events, key=lambda x: x.get("id", 0)):
        t = e.get("type", "")
        if t.endswith("StateEntered"):
            name = e["stateEnteredEventDetails"]["name"]
            entered.setdefault(name, e.get("timestamp"))
            counts[name] = counts.get(name, 0) + 1
            last_entered = name
        elif t.endswith("StateExited"):
            exited[e["stateExitedEventDetails"]["name"]] = e.get("timestamp")
        elif t == "MapStateStarted":  # carries no state name: it belongs to the map state entered just before it
            n = (e.get("mapStateStartedEventDetails") or {}).get("length")
            if n is not None:
                map_len[last_entered] = int(n)
        elif t in ("MapIterationSucceeded", "MapIterationFailed", "MapIterationAborted"):
            name = (e.get("mapIterationEventDetails") or {}).get("name", "")
            bucket = map_done if t == "MapIterationSucceeded" else map_failed
            bucket[name] = bucket.get(name, 0) + 1

    terminal = sfn_status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED")
    out = []
    for spec in SFN_STEPS.get(pipeline, []):
        names = spec["states"]
        started = [entered[n] for n in names if n in entered]
        ended = [exited[n] for n in names if n in exited]
        if not started:
            status = ("skipped" if sfn_status == "SUCCEEDED" else "pending") if terminal else "pending"
        elif all(n in exited for n in names if n in entered) and len(ended) == len(started):
            status = "done"
        else:
            status = "failed" if terminal and sfn_status != "SUCCEEDED" else "running"
        step = {"key": spec["key"], "label": spec["label"], "status": status, "started_at": _iso(min(started) if started else None),
                "ended_at": _iso(max(ended) if ended and status == "done" else None)}
        m = spec.get("map")
        if m and m in entered:
            total = map_len.get(m)
            done = map_done.get(m, 0)
            if spec.get("ok_state"):  # per-item outcome is recorded by Pass states inside the iteration
                ok, bad = counts.get(spec["ok_state"], 0), counts.get(spec["failed_state"], 0)
                step["detail"] = f"{ok + bad}/{total or '?'} {spec['unit']} processed" + (f" · {bad} failed" if bad else "")
                if status == "done" and bad:
                    step["status"] = "warning"
            else:
                step["detail"] = f"{done}/{total or '?'} {spec['unit']}" + (f" · {map_failed[m]} failed" if map_failed.get(m) else "")
        out.append(step)
    return out


def _ev(doc: dict[str, Any], *types: str) -> list[dict[str, Any]]:
    return [e for e in doc.get("events", []) if e.get("type") in types]


def agent_steps(pipeline: str, doc: dict[str, Any], sfn_status: str, child: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Steps the AgentCore orchestrator performs after (or around) the inner pipeline. Pure function."""
    st = doc.get("status") or "pending"
    terminal_sfn = sfn_status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED")
    done_agent = st in TERMINAL_AGENT
    res = doc.get("result") or {}
    steps: list[dict[str, Any]] = []

    def step(key: str, label: str, status: str, detail: str | None = None, at: str | None = None) -> None:
        steps.append({"key": key, "label": label, "status": status, "detail": detail, "started_at": at, "ended_at": None})

    if sfn_status in ("FAILED", "TIMED_OUT", "ABORTED"):
        restarted = _ev(doc, "pipeline_restarted")
        step("diagnose", "Agent: diagnose the failure", "done" if done_agent or restarted else "running",
             "restarted once automatically" if restarted else (res.get("diagnosis") or {}).get("error") if isinstance(res.get("diagnosis"), dict) else None)
        return steps

    if pipeline == "esg_report":
        review = _ev(doc, "validation_review")
        regen = _ev(doc, "regenerating")
        sections = doc.get("sections") or {}
        healed = sum(1 for s in sections.values() if s.get("status") == "healed")
        unresolved = sum(1 for s in sections.values() if s.get("status") in ("unresolved", "source_data", "escalate_data"))
        todo = (review[-1].get("detail") or {}).get("to_repair", []) if review else []
        if not terminal_sfn:
            for k, label in (("review", "Agent: review the validation results"), ("repair", "Agent: repair failed sections"),
                             ("reassemble", "Agent: re-assemble the report"), ("ready", "Report ready")):
                step(k, label, "pending")
            return steps
        step("review", "Agent: review the validation results", "done" if review else ("running" if not done_agent else "skipped"),
             (review[-1]["message"] if review else None), review[-1]["ts"] if review else None)
        if review and not todo:
            step("repair", "Agent: repair failed sections", "skipped", "every section passed")
        elif regen or todo:
            detail = f"{healed} repaired" + (f" · {unresolved} need review" if unresolved else "") + f" · {len(regen)} attempt(s)"
            step("repair", "Agent: repair failed sections", ("warning" if unresolved else "done") if done_agent else "running", detail,
                 regen[0]["ts"] if regen else None)
        else:
            step("repair", "Agent: repair failed sections", "pending")
        reasm = _ev(doc, "reassembled", "reassembling")
        step("reassemble", "Agent: re-assemble the report", "done" if _ev(doc, "reassembled") else ("running" if reasm else ("skipped" if done_agent else "pending")))
        step("ready", "Report ready", ("warning" if st == "escalated" else "done") if done_agent else "pending",
             "download available" if res.get("download_url") else None)
        return steps

    if pipeline == "data_sync":
        tables = res.get("tables") or {}
        retried = _ev(doc, "sync_retry")
        if not terminal_sfn:
            step("triage", "Agent: check every table and retry temporary failures", "pending")
            step("etl", "Run the Scope 1, 2, 3 ETL", "pending")
            step("done", "Data up to date", "pending")
            return steps
        ok = sum(1 for t in tables.values() if t.get("status") == "ok")
        detail = (f"{ok}/{len(tables)} tables loaded" + (f" · retried {', '.join((retried[-1].get('detail') or {}).get('tables', []))}" if retried else "")) if tables else None
        step("triage", "Agent: check every table and retry temporary failures", ("done" if ok == len(tables) else "warning") if done_agent or tables else "running", detail)
        etl_started = _ev(doc, "etl_started")
        if child is not None:
            cs = child.get("status")
            status = {"completed": "done", "escalated": "warning", "failed": "failed"}.get(cs, "running")
            step("etl", "Run the Scope 1, 2, 3 ETL", status, " · ".join(f"{s['label']}: {s['status']}" for s in child.get("steps", [])[:3]),
                 etl_started[0]["ts"] if etl_started else None)
        elif etl_started:
            step("etl", "Run the Scope 1, 2, 3 ETL", "running", None, etl_started[0]["ts"])
        else:
            step("etl", "Run the Scope 1, 2, 3 ETL", "skipped" if done_agent else "pending",
                 "not started: not every table loaded" if done_agent and tables and ok < len(tables) else None)
        step("done", "Data up to date", ("warning" if st == "escalated" else "done") if done_agent else "pending")
        return steps

    if pipeline == "ghg_inventory":
        step("done", "Inventory ready", ("done" if st == "completed" else "warning") if done_agent else ("running" if terminal_sfn else "pending"))
    return steps


def overall(sfn_status: str, doc: dict[str, Any]) -> str:
    st = doc.get("status")
    if st in TERMINAL_AGENT:
        return st
    if sfn_status in ("FAILED", "TIMED_OUT", "ABORTED") and st not in ("running", "pending"):
        return "failed"
    return "running"


def progress(execution_id: str, sfn: Any = None, get: Callable[[str], Any] | None = None, depth: int = 0) -> dict[str, Any]:
    if not EXEC_ID_RE.match(execution_id or ""):
        raise ValueError("invalid execution id")
    get = get or common.s3_get
    sfn = sfn or common.client("stepfunctions")
    meta = get(f"executions/{execution_id}/meta.json") or {}
    doc = get(f"agent-ledger/{execution_id}.json") or {"events": [], "status": "pending"}
    pipeline = meta.get("pipeline") or doc.get("pipeline") or "esg_report"
    arn = meta.get("execution_arn") or doc.get("execution_arn") or (
        f"arn:aws:states:{common.REGION}:{common.ACCOUNT_ID}:execution:ESGReportGenerationStateMachine:{execution_id}")
    d = sfn.describe_execution(executionArn=arn)
    sfn_status = d["status"]
    steps = sfn_steps(pipeline, _history(sfn, arn), sfn_status)
    child = None
    if pipeline == "data_sync" and depth == 0:
        started = _ev(doc, "etl_started")
        cid = ((started[-1].get("detail") or {}).get("etl_execution_id")) if started else None
        if cid:
            try:
                child = progress(cid, sfn, get, depth + 1)
            except Exception:  # noqa: BLE001 - the parent progress must still render
                child = None
    steps += agent_steps(pipeline, doc, sfn_status, child)
    return {"execution_id": execution_id, "pipeline": pipeline, "sfn_status": sfn_status, "status": overall(sfn_status, doc),
            "params": {k: v for k, v in json.loads(d.get("input") or "{}").items() if k != "section_templates"} if depth == 0 else None, "started_at": _iso(d.get("startDate")),
            "stopped_at": _iso(d.get("stopDate")), "steps": steps, "child": child}
