"""Report run history and the reference-document list (replaces the old REST endpoints /history and /history?type=documents)."""

from __future__ import annotations

import json
from typing import Any

from . import common

REPORT_SM = "ESGReportGenerationStateMachine"
STATUSES = ("SUCCEEDED", "FAILED", "RUNNING")
KB_PREFIX = "documents/"


def _sm_arn() -> str:
    return f"arn:aws:states:{common.REGION}:{common.ACCOUNT_ID}:stateMachine:{REPORT_SM}"


def _presign(path: str) -> str | None:
    if not path or not path.startswith("s3://"):
        return None
    bucket, _, key = path[5:].partition("/")
    return common.client("s3").generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)


def history(params: dict[str, Any], sfn: Any = None, presign: Any = None) -> dict[str, Any]:
    try:
        limit = max(1, min(int(params.get("limit", 10)), 20))
    except (TypeError, ValueError):
        raise ValueError("limit must be a number") from None
    sfn = sfn or common.client("stepfunctions")
    presign = presign or _presign
    rows: list[dict[str, Any]] = []
    for status in STATUSES:
        for ex in sfn.list_executions(stateMachineArn=_sm_arn(), statusFilter=status, maxResults=limit).get("executions", []):
            row: dict[str, Any] = {"execution_id": ex["name"], "status": status, "start_time": ex["startDate"].isoformat(), "framework": "", "reporting_year": 0}
            if ex.get("stopDate"):
                row["duration_seconds"] = int((ex["stopDate"] - ex["startDate"]).total_seconds())
            try:
                d = sfn.describe_execution(executionArn=ex["executionArn"])
                inp = json.loads(d.get("input") or "{}")
                row["framework"], row["reporting_year"] = inp.get("framework", ""), inp.get("reporting_year", 0)
                if status == "SUCCEEDED":
                    asm = (json.loads(d.get("output") or "{}")).get("assembly_result", {})
                    row["download_url"] = presign(asm.get("s3_path", ""))
                    row["download_url_pptx"] = presign(asm.get("s3_path_pptx", ""))
                    row["sections_assembled"] = asm.get("sections_assembled", 0)
            except Exception:  # noqa: BLE001 - one unreadable execution must not hide the others
                pass
            rows.append(row)
    rows.sort(key=lambda r: r["start_time"], reverse=True)
    return {"executions": rows[:limit], "total_succeeded": sum(r["status"] == "SUCCEEDED" for r in rows),
            "total_failed": sum(r["status"] == "FAILED" for r in rows), "total_running": sum(r["status"] == "RUNNING" for r in rows)}


def documents(params: dict[str, Any], s3: Any = None) -> dict[str, Any]:
    s3 = s3 or common.client("s3")
    bucket = f"esg-kb-documents-{common.ACCOUNT_ID}"
    out = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=KB_PREFIX):
        for o in page.get("Contents", []):
            key = o["Key"]
            if key.endswith(".metadata.json") or key.endswith("/"):
                continue
            rest = key[len(KB_PREFIX):]
            category, _, name = rest.partition("/")
            out.append({"filename": name or rest, "category": category if name else "other", "size_kb": round(o["Size"] / 1024), "key": key})
    out.sort(key=lambda d: (d["category"], d["filename"]))
    return {"documents": out, "total_count": len(out)}
