"""Data sync supervision: the agent decides what happens after the extract from the source database.

For every table the Step Functions run reports OK or FAILED. The orchestrator then
  * reads the data-contract report the Glue job wrote (warnings travel with a successful load),
  * triages each failure: contract violation (needs a data owner), infrastructure hiccup (retry once),
    access problem, or unknown,
  * retries only the transient failures, once,
  * starts the downstream ETL (GHG inventory pipeline: Glue scope jobs and aggregation) only when EVERY table loaded,
    so reports never mix fresh and stale tables,
  * writes plain-language notes for the people who own the data.
A blocking contract violation stops the Glue job before it writes, so the raw zone keeps the last good data.
"""

from __future__ import annotations

from typing import Any

TRANSIENT_HINTS = ("timed out", "timeout", "connection refused", "could not connect", "connection reset", "communications link failure",
                   "throttl", "too many connections", "service unavailable", "unable to execute http request", "internal error")
ACCESS_HINTS = ("access denied", "accessdenied", "permission denied", "authentication failed", "password authentication", "not authorized")

SUGGESTIONS = {
    "MISSING_COLUMN": "A column was renamed or removed in the source database. Restore it, or update the data contract if the change is intended.",
    "TYPE": "A column changed type in the source database. Fix the column type or update the data contract.",
    "ROWS": "The source has no rows for this year. Check that the upstream load finished before syncing.",
    "NULL_KEY": "Rows without a required key value exist. The data owner should correct or remove them.",
    "DUPLICATE_KEYS": "Duplicated keys exist. The data owner should de-duplicate the source rows.",
}


def triage(error: str | None, cause: str | None, report: dict[str, Any] | None) -> dict[str, Any]:
    text = f"{error or ''} {cause or ''}".lower()
    blocking = [v for v in (report or {}).get("violations", []) if v.get("level") == "blocking"]
    if "data_contract_failed" in text or blocking:
        detail = " ".join(v["detail"] for v in blocking[:3]) or "The data contract was violated."
        tips = []
        for v in blocking:
            tip = SUGGESTIONS.get(v["rule"])
            if tip and tip not in tips:
                tips.append(tip)
        return {"kind": "contract", "transient": False, "explanation": f"The source data does not meet its contract. {detail}",
                "suggestion": " ".join(tips) or "Ask the data owner to correct the source data, then sync again. Nothing was written to the raw zone."}
    if any(h in text for h in ACCESS_HINTS):
        return {"kind": "access", "transient": False, "explanation": "The extract job could not authenticate or was not allowed to read the source.",
                "suggestion": "Check the read-only database user and its secret, and the job role permissions."}
    if any(h in text for h in TRANSIENT_HINTS):
        return {"kind": "infrastructure", "transient": True, "explanation": "The extract failed because of a connection or capacity problem that is usually temporary.",
                "suggestion": "The orchestrator retries once automatically. If it fails again, check the database and network."}
    short = (cause or error or "no details")[:200]
    return {"kind": "unknown", "transient": False, "explanation": f"The extract failed for a reason the orchestrator does not recognise: {short}",
            "suggestion": "Open the Glue job run log for details."}


class DataSyncMixin:
    """Mixed into SelfHealingSupervisor (needs self.aws, self.s, self.ledger, self._wait, self.start, self.supervise)."""

    def _report(self, table: str, year: int) -> dict[str, Any] | None:
        try:
            r = self.aws.lambda_invoke(self.s.data_tools_function, {"action": "etl_report", "table": table, "year": year})
            return r.get("report") if r.get("found") else None
        except Exception:  # noqa: BLE001 - a missing report must not stop the triage
            return None

    def _handle_sync(self, arn: str, doc: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        from .aws import short_id

        inp = d["input"]
        year = int(inp["reporting_year"])
        results = {r["table"]: r for r in (d.get("output") or {}).get("results", [])}
        retried: list[str] = []

        failing = [t for t, r in results.items() if r.get("status") != "OK"]
        transient = [t for t in failing if triage(results[t].get("error"), results[t].get("cause"), self._report(t, year))["transient"]]
        if transient:
            self.ledger.event(arn, doc, "sync_retry", f"{', '.join(transient)}: temporary failure, retrying once.", tables=transient)
            retry_arn = self.aws.sfn_start(self.s.sync_state_machine_arn, {"reporting_year": year, "tables": transient})
            rd = self._wait(retry_arn, doc)
            if rd["status"] == "SUCCEEDED":
                for r in (rd.get("output") or {}).get("results", []):
                    results[r["table"]] = r
            retried = transient

        tables: dict[str, Any] = {}
        notes: list[dict[str, Any]] = []
        for table, r in sorted(results.items()):
            report = self._report(table, year)
            if r.get("status") == "OK":
                warns = [v for v in (report or {}).get("violations", []) if v.get("level") == "warning"]
                tables[table] = {"status": "ok", "rows": (report or {}).get("rows"), "warnings": len(warns)}
                if warns:
                    notes.append({"section": table, "level": "review", "label": "Loaded with warnings", "text": f"Loaded {(report or {}).get('rows', '?')} rows with {len(warns)} warning(s): "
                                  + " ".join(v["detail"] for v in warns[:3]) + " The data was loaded; ask the data owner to confirm."})
                else:
                    notes.append({"section": table, "level": "ok", "label": "Loaded", "text": f"Loaded {(report or {}).get('rows', '?')} rows. The data contract was met."
                                  + (" Loaded on the automatic retry." if table in retried else "")})
            else:
                t = triage(r.get("error"), r.get("cause"), report)
                tables[table] = {"status": "failed", "kind": t["kind"], "retried": table in retried}
                notes.append({"section": table, "level": "action", "label": "Not loaded", "text": f"{t['explanation']} {t['suggestion']}"
                              + (" It was retried once." if table in retried else "")})
                self.ledger.event(arn, doc, "sync_table_failed", f"{table}: {t['kind']} problem. {t['explanation']}", table=table, kind=t["kind"])

        failed = [t for t, v in tables.items() if v["status"] != "ok"]
        result: dict[str, Any] = {"pipeline": "data_sync", "reporting_year": year, "tables": tables, "notes": notes, "retried": retried}
        if failed:
            doc["status"] = "escalated"
            self.ledger.event(arn, doc, "escalated", f"Sync finished with problems in: {', '.join(failed)}. The raw zone still holds the last good data; the downstream ETL was not started.")
            notes.append({"section": "pipeline", "level": "action", "label": "ETL not started", "text": "The downstream ETL was not started because not every table loaded. Fix the tables above and sync again."})
        else:
            doc["status"] = "completed"
            self.ledger.event(arn, doc, "sync_loaded", f"All {len(tables)} tables loaded.")
            if inp.get("run_etl", True):
                started = self.start("ghg_inventory", {"reporting_year": year}, subsidiary=doc.get("subsidiary", "bank"), requested_by="data_sync", parent=arn)
                result["etl_execution_id"] = started["execution_id"]
                self.ledger.event(arn, doc, "etl_started", "Started the downstream ETL (Scope 1/2/3 Glue jobs and aggregation) because every table loaded.", etl_execution_id=started["execution_id"])
                etl = self.supervise(started["execution_arn"])
                result["etl_state"] = etl.get("state")
                if etl.get("state") != "completed":
                    doc["status"] = "escalated"
                    notes.append({"section": "etl", "level": "action", "label": "ETL problem", "text": "The tables loaded, but the downstream ETL did not finish cleanly. Open its run for the explanation."})
                    self.ledger.event(arn, doc, "escalated", f"The downstream ETL ended as '{etl.get('state')}'.")
                else:
                    notes.append({"section": "etl", "level": "ok", "label": "ETL finished", "text": "Scope 1, 2 and 3 calculations and the aggregation finished; curated and aggregated data are up to date."})
                    self.ledger.event(arn, doc, "etl_finished", "The downstream ETL finished: curated and aggregated zones are up to date.")
        doc["sections"] = {t: {"status": "ok" if v["status"] == "ok" else "unresolved", "explanations": []} for t, v in tables.items()}
        doc["result"] = result
        self.ledger.save(arn, doc)
        return {"state": doc["status"], "execution_id": short_id(arn), "result": result}
