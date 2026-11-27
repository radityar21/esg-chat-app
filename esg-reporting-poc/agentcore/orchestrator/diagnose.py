"""Explain why a Step Functions execution failed, in structured form the agent can turn into plain language."""

from __future__ import annotations

from typing import Any

_FAILURE_EVENTS = {
    "TaskFailed", "LambdaFunctionFailed", "ExecutionFailed", "MapStateFailed", "ParallelStateFailed",
    "ActivityFailed", "TaskTimedOut", "LambdaFunctionTimedOut", "ExecutionTimedOut", "ExecutionAborted",
}
_DETAIL_KEYS = ("taskFailedEventDetails", "lambdaFunctionFailedEventDetails", "executionFailedEventDetails",
                "mapStateFailedEventDetails", "executionTimedOutEventDetails", "executionAbortedEventDetails",
                "taskTimedOutEventDetails")

_CATEGORY_BY_STATE = [
    ("validateinput", "input_validation"), ("glue", "etl"), ("aggregation", "etl"), ("scope1", "etl"), ("scope2", "etl"),
    ("scope3", "etl"), ("runetl", "etl"), ("queryathena", "athena"), ("sectiongen", "generation"),
    ("generatesections", "generation"), ("validation", "generation"), ("assembl", "assembly"),
    ("buildinventory", "inventory_build"), ("notify", "notification"),
]

_TRANSIENT = ("throttl", "rate exceeded", "toomanyrequests", "serviceexception", "service unavailable", "timeout", "timed out",
              "concurrent runs exceeded", "resourcenumberlimitexceeded", "internal server error", "modelnotready")
_PERMANENT = ("accessdenied", "not authorized", "validationexception", "no such key", "does not exist", "invalid", "schema")

ADVICE = {
    "input_validation": ["Check the requested year and framework. Only 2023 and 2024 have source data."],
    "etl": ["Open the Glue job run for the failed job and read its error log.",
            "Check that the raw data for the reporting year exists in the raw S3 zone and matches the expected schema."],
    "athena": ["Check that the aggregated tables have a partition for the reporting year (re-run the aggregation job).",
               "Check the Athena workgroup and that the query result location is writable."],
    "generation": ["Check Bedrock model access and quotas in the region.", "Re-run the report; the orchestrator already retried transient errors."],
    "assembly": ["Check the output bucket permissions and that the python-docx Lambda layer is attached."],
    "inventory_build": ["Check that the curated and aggregated Athena tables exist for the year."],
    "notification": ["The report was generated; only the SNS notification failed."],
}


def _category(state_name: str) -> str:
    n = (state_name or "").lower()
    for needle, cat in _CATEGORY_BY_STATE:
        if needle in n:
            return cat
    return "unknown"


def diagnose(execution: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    """Return {category, failed_state, error, cause, retryable, advice}."""
    events = sorted(history, key=lambda e: e.get("id", 0))
    last_state = ""
    found: dict[str, Any] | None = None
    for ev in events:
        et = ev.get("type", "")
        if et.endswith("StateEntered"):
            last_state = (ev.get("stateEnteredEventDetails") or {}).get("name", last_state)
        if et in _FAILURE_EVENTS:
            for k in _DETAIL_KEYS:
                if ev.get(k):
                    found = {"state": last_state, "error": ev[k].get("error", et), "cause": ev[k].get("cause", "")}
                    break
            found = found or {"state": last_state, "error": et, "cause": ""}
            if et != "ExecutionFailed":  # prefer the most specific (inner) failure over the final ExecutionFailed
                break
    error = (found or {}).get("error") or execution.get("error") or "Unknown"
    cause = (found or {}).get("cause") or execution.get("cause") or ""
    state = (found or {}).get("state") or ""
    category = _category(state)
    if category == "unknown" and error == "ExecutionError":
        category = "pipeline"  # raised by an explicit Fail state; the real cause is earlier in history
    text = f"{error} {cause}".lower()
    retryable = any(t in text for t in _TRANSIENT) and not any(p in text for p in _PERMANENT)
    return {
        "category": category, "failed_state": state, "error": error, "cause": str(cause)[:600], "retryable": retryable,
        "advice": ADVICE.get(category, ["Open the execution in the Step Functions console and inspect the failed state."]),
    }
