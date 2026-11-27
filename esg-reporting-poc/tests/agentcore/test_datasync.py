"""Data sync supervision: triage, retry of temporary failures, escalation of contract violations, downstream ETL decision."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "agentcore"), str(ROOT / "lambda" / "_shared"), str(Path(__file__).parent)]

from fakes import FakeAws  # noqa: E402
from orchestrator import datasync as D  # noqa: E402
from orchestrator.healer import SelfHealingSupervisor  # noqa: E402
from orchestrator.pipelines import SYNC_TABLES, plan_request  # noqa: E402
from test_healer import settings  # noqa: E402

SYNC_SM = "arn:aws:states:us-east-1:1:stateMachine:Sync"
GHG_SM = "arn:aws:states:us-east-1:1:stateMachine:Ghg"


def make(reports=None, on_start=None):
    aws = FakeAws()
    s = settings(sync_state_machine_arn=SYNC_SM, ghg_state_machine_arn=GHG_SM)
    reports = reports or {}
    aws.lambdas["esg-data-tools"] = lambda p: ({"found": True, "report": reports[p["table"]]} if p["table"] in reports else {"found": False})
    aws.on_start = on_start
    return aws, SelfHealingSupervisor(aws, s, sleep=lambda _x: None)


def ok(t):
    return {"table": t, "status": "OK"}


def failed(t, error="States.TaskFailed", cause="boom"):
    return {"table": t, "status": "FAILED", "error": error, "cause": cause}


def report(rows=100, violations=None):
    v = violations or []
    return {"rows": rows, "violations": v, "blocking": sum(1 for x in v if x["level"] == "blocking")}


def run_sync(sup, aws, results, **params):
    started = sup.start("data_sync", {"reporting_year": 2024, **params})
    arn = started["execution_arn"]
    aws.finish(arn, "SUCCEEDED", {"reporting_year": 2024, "results": results})
    return arn


# ── triage ────────────────────────────────────────────────────────────────────────────────────────
def test_triage_kinds():
    assert D.triage("Glue.AWSGlueException", "DATA_CONTRACT_FAILED: loan_portfolio 2024: x", None)["kind"] == "contract"
    assert D.triage("X", "Communications link failure", None)["transient"] is True
    assert D.triage("X", "FATAL: password authentication failed for user", None)["kind"] == "access"
    t = D.triage("X", "weird", None)
    assert t["kind"] == "unknown" and not t["transient"]


def test_contract_triage_uses_the_report_and_gives_a_concrete_suggestion():
    rep = report(0, [{"level": "blocking", "rule": "MISSING_COLUMN", "detail": "Column 'fte_total' is not present in the source table."}])
    t = D.triage("E", "irrelevant", rep)
    assert "fte_total" in t["explanation"] and "renamed or removed" in t["suggestion"]


def test_planner_routes_sync_requests():
    s = settings()
    assert plan_request("sync data dari database untuk 2024", s)["pipeline"] == "data_sync"
    assert plan_request("tarik data dari rds 2023", s)["pipeline"] == "data_sync"
    assert plan_request("generate GRI 305 report 2024", s)["pipeline"] == "esg_report"


# ── supervisor ────────────────────────────────────────────────────────────────────────────────────
def test_all_tables_loaded_starts_the_downstream_etl_and_waits_for_it():
    def on_start(aws, arn, sm, payload):
        if sm == GHG_SM:
            aws.finish(arn, "SUCCEEDED", {"ok": True})
    aws, sup = make({t: report() for t in SYNC_TABLES}, on_start)
    arn = run_sync(sup, aws, [ok(t) for t in SYNC_TABLES])
    res = sup.supervise(arn)
    assert res["state"] == "completed"
    r = res["result"]
    assert r["etl_execution_id"] and r["etl_state"] == "completed"
    assert any(sm == GHG_SM for sm, _ in aws.started)
    types = [e["type"] for e in sup.ledger.load(arn)["events"]]
    assert "etl_started" in types and "etl_finished" in types


def test_run_etl_false_does_not_start_the_etl():
    aws, sup = make({t: report() for t in SYNC_TABLES})
    arn = run_sync(sup, aws, [ok(t) for t in SYNC_TABLES], run_etl=False)
    res = sup.supervise(arn)
    assert res["state"] == "completed" and "etl_execution_id" not in res["result"]
    assert not any(sm == GHG_SM for sm, _ in aws.started)


def test_contract_violation_escalates_with_note_and_blocks_the_etl():
    bad = report(0, [{"level": "blocking", "rule": "ROWS", "detail": "0 rows found; at least 1 expected for this year."}])
    aws, sup = make({**{t: report() for t in SYNC_TABLES}, "hr_metrics": bad})
    arn = run_sync(sup, aws, [ok(t) if t != "hr_metrics" else failed(t, cause="DATA_CONTRACT_FAILED: hr_metrics 2024") for t in SYNC_TABLES])
    res = sup.supervise(arn)
    assert res["state"] == "escalated"
    note = next(n for n in res["result"]["notes"] if n["section"] == "hr_metrics")
    assert note["level"] == "action" and "no rows" in note["text"]
    assert any(n["section"] == "pipeline" and "ETL was not started" in n["text"] for n in res["result"]["notes"])
    assert not any(sm == GHG_SM for sm, _ in aws.started)
    assert res["result"]["tables"]["hr_metrics"]["kind"] == "contract"


def test_transient_failure_is_retried_once_and_recovers():
    def on_start(aws, arn, sm, payload):
        if sm == SYNC_SM and payload.get("tables") == ["loan_portfolio"]:
            aws.finish(arn, "SUCCEEDED", {"results": [ok("loan_portfolio")]})
        if sm == GHG_SM:
            aws.finish(arn, "SUCCEEDED", {})
    aws, sup = make({t: report() for t in SYNC_TABLES}, None)
    arn = run_sync(sup, aws, [failed(t, cause="Connection timed out") if t == "loan_portfolio" else ok(t) for t in SYNC_TABLES])
    aws.on_start = on_start  # the retry execution is started during supervision
    res = sup.supervise(arn)
    assert res["state"] == "completed" and res["result"]["retried"] == ["loan_portfolio"]
    assert res["result"]["tables"]["loan_portfolio"]["status"] == "ok"
    retries = [p for sm, p in aws.started if sm == SYNC_SM and p.get("tables") == ["loan_portfolio"]]
    assert len(retries) == 1


def test_transient_failure_that_stays_failed_is_not_retried_twice():
    def on_start(aws, arn, sm, payload):
        if sm == SYNC_SM and payload.get("tables") == ["loan_portfolio"]:
            aws.finish(arn, "SUCCEEDED", {"results": [failed("loan_portfolio", cause="Connection timed out")]})
    aws, sup = make({t: report() for t in SYNC_TABLES}, None)
    arn = run_sync(sup, aws, [failed(t, cause="Connection timed out") if t == "loan_portfolio" else ok(t) for t in SYNC_TABLES])
    aws.on_start = on_start
    res = sup.supervise(arn)
    assert res["state"] == "escalated" and "retried once" in next(n["text"] for n in res["result"]["notes"] if n["section"] == "loan_portfolio")
    assert len([1 for sm, p in aws.started if sm == SYNC_SM and p.get("tables") == ["loan_portfolio"]]) == 1


def test_warnings_are_reported_but_do_not_block():
    warn = report(4400, [{"level": "warning", "rule": "RANGE", "detail": "Maximum of 'pcaf_data_quality_score' is 9, above the documented maximum 5."}])
    def on_start(aws, arn, sm, payload):
        if sm == GHG_SM:
            aws.finish(arn, "SUCCEEDED", {})
    aws, sup = make({**{t: report() for t in SYNC_TABLES}, "loan_portfolio": warn}, on_start)
    arn = run_sync(sup, aws, [ok(t) for t in SYNC_TABLES])
    res = sup.supervise(arn)
    assert res["state"] == "completed"
    n = next(n for n in res["result"]["notes"] if n["section"] == "loan_portfolio")
    assert n["level"] == "review" and "above the documented maximum" in n["text"]


def test_invalid_table_names_are_rejected_before_starting():
    aws, sup = make()
    with pytest.raises(ValueError):
        sup.start("data_sync", {"reporting_year": 2024, "tables": ["users; drop"]})


def test_sync_notes_are_labelled_loaded_not_repaired_and_child_links_parent():
    def on_start(aws, arn, sm, payload):
        if sm == GHG_SM:
            aws.finish(arn, "SUCCEEDED", {})
    aws, sup = make({t: report() for t in SYNC_TABLES}, on_start)
    arn = run_sync(sup, aws, [ok(t) for t in SYNC_TABLES])
    res = sup.supervise(arn)
    notes = {n["section"]: n for n in res["result"]["notes"]}
    assert all(notes[t]["level"] == "ok" and notes[t]["label"] == "Loaded" for t in SYNC_TABLES)
    assert notes["etl"]["label"] == "ETL finished"
    child = res["result"]["etl_execution_id"]
    assert sup.ledger.load(child)["parent_execution_id"] == arn.split(":")[-1]
