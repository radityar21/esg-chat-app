from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agentcore"))
sys.path.insert(0, str(ROOT / "lambda" / "_shared"))
sys.path.insert(0, str(Path(__file__).parent))

from fakes import FakeAws  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.pipelines import build_input, plan_request  # noqa: E402
from orchestrator.rules import classify  # noqa: E402
from orchestrator.service import ToolService  # noqa: E402

B = "bucket"


def S(**kw):
    base = dict(output_bucket=B, report_state_machine_arn="arn:aws:states:us-east-1:1:stateMachine:Report",
                ghg_state_machine_arn="arn:aws:states:us-east-1:1:stateMachine:Ghg")
    base.update(kw)
    return Settings(**base)


class Immediate:
    """Runs background work inline so tests are deterministic."""

    def __init__(self):
        self.names = []

    def submit(self, name, fn):
        self.names.append(name)
        return True


# ── planner ───────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text,pipeline,fw,ready", [
    ("Tolong buat laporan GRI untuk 2024", "esg_report", "GRI_305", True),
    ("generate all frameworks report 2023", "esg_report", "MULTI_FRAMEWORK", True),
    ("laporan IFRS dan CSRD 2024", "esg_report", "MULTI_FRAMEWORK", True),
    ("bikin ghg inventory 2024", "ghg_inventory", None, True),
    ("buat laporan OJK", "esg_report", "OJK_PSPK", False),
    ("halo apa kabar", None, None, False),
])
def test_planner_routes_requests(text, pipeline, fw, ready):
    p = plan_request(text, S())
    assert p["pipeline"] == pipeline
    assert p["parameters"].get("framework") == fw
    assert p["ready"] is ready


def test_planner_rejects_years_without_data_and_asks_again():
    p = plan_request("report 2019 OJK", S())
    assert not p["ready"] and "reporting_year" in p["missing"] and p["problems"]


def test_build_input_validates_and_defaults():
    inp = build_input("esg_report", {"reporting_year": 2024, "framework": "MULTI_FRAMEWORK"}, S())
    ids = [t["template_id"] for t in inp["section_templates"]]
    assert "scenario_unified" in ids and inp["revenue_idr_billion"] == 92000.0
    with pytest.raises(ValueError):
        build_input("esg_report", {"reporting_year": 2019, "framework": "GRI_305"}, S())
    with pytest.raises(ValueError):
        build_input("esg_report", {"reporting_year": 2024, "framework": "NOPE"}, S())
    with pytest.raises(ValueError):
        build_input("esg_report", {"reporting_year": 2024, "framework": "GRI_305", "revenue_idr_billion": -1}, S())


# ── rules ─────────────────────────────────────────────────────────────────────────────────────────
def test_rule_classification_splits_fixable_from_data_issues():
    c = classify({"validation_outcome": "FAIL", "errors": [{"rule": "VAL-PRH-04", "detail": "x"}, {"rule": "VAL-NUM-06", "detail": "y"}]})
    assert c["needs_repair"] and [e["rule"] for e in c["data_issues"]] == ["VAL-NUM-06"]
    only_data = classify({"validation_outcome": "FAIL_NO_RETRY", "errors": [{"rule": "VAL-NUM-06"}]})
    assert not only_data["needs_repair"] and only_data["data_issues"]
    warn = classify({"validation_outcome": "WARN", "errors": [], "warnings": [{"rule": "VAL-STR-10"}]})
    assert not warn["needs_repair"]


# ── service ───────────────────────────────────────────────────────────────────────────────────────
def test_start_returns_execution_id_text_and_launches_supervision():
    aws, runner = FakeAws(), Immediate()
    svc = ToolService(aws, S(), runner=runner)
    r = svc.start("esg_report", 2024, "GRI_305", subsidiary="syariah")
    assert r["started"] and f"Execution ID: {r['execution_id']}" in r["message"] and "10-20" in r["eta_minutes"]
    assert runner.names == [f"supervise-{r['execution_id']}"]
    meta = aws.s3_get_json(B, f"executions/{r['execution_id']}/meta.json")
    assert meta["subsidiary"] == "syariah" and meta["pipeline"] == "esg_report"


def test_start_with_bad_parameters_returns_error_not_exception():
    r = ToolService(FakeAws(), S(), runner=Immediate()).start("esg_report", 2019, "GRI_305")
    assert r["started"] is False and "2019" in r["error"]


def test_multi_framework_eta_is_longer():
    r = ToolService(FakeAws(), S(), runner=Immediate()).start("esg_report", 2024, "MULTI_FRAMEWORK")
    assert r["eta_minutes"] == "20-40"


def test_explain_reports_failure_and_unresolved_sections():
    aws = FakeAws()
    svc = ToolService(aws, S(), runner=Immediate())
    r = svc.start("esg_report", 2024, "GRI_305", auto_heal=False)
    arn = r["execution_arn"]
    aws.finish(arn, "FAILED", error="ExecutionError", cause="boom")
    aws.history[arn] = [{"id": 1, "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "QueryAthena"}},
                        {"id": 2, "type": "TaskFailed", "taskFailedEventDetails": {"error": "States.TaskFailed", "cause": "HIVE_PARTITION_SCHEMA_MISMATCH"}}]
    out = svc.explain(r["execution_id"])
    assert out["diagnosis"]["category"] == "athena" and out["diagnosis"]["advice"]


def test_download_falls_back_to_engine_output_when_no_heal_result():
    aws = FakeAws()
    svc = ToolService(aws, S(), runner=Immediate())
    r = svc.start("esg_report", 2024, "GRI_305", auto_heal=False)
    aws.finish(r["execution_arn"], "SUCCEEDED", {"assembly_result": {"s3_path": f"s3://{B}/reports/a.docx"}})
    d = svc.download(r["execution_id"])
    assert d["ready"] and d["download_url"].endswith("a.docx")
    assert "error" in svc.download("does-not-exist-yet")
    assert "error" in svc.explain("does-not-exist-yet")


def test_platform_errors_are_returned_not_raised():
    aws = FakeAws()
    aws.lambdas["esg-platform-api"] = lambda p: (_ for _ in ()).throw(RuntimeError("boom"))
    assert "error" in ToolService(aws, S(), runner=Immediate()).platform("compliance_readiness", year=2024)


# ── strands wiring ────────────────────────────────────────────────────────────────────────────────
def test_strands_agent_builds_with_all_tools():
    pytest.importorskip("strands")
    from orchestrator.agent import build_agent

    agent = build_agent(ToolService(FakeAws(), S(), runner=Immediate()), model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0")
    names = set(agent.tool_names)
    assert {"plan_pipeline", "start_pipeline", "get_run_status", "explain_run", "get_download_link", "run_climate_scenarios"} <= names
