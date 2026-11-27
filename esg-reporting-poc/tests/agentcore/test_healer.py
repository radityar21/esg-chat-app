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
from orchestrator.healer import SelfHealingSupervisor  # noqa: E402

BUCKET = "esg-output-reports-test"


def settings(**kw) -> Settings:
    base = dict(output_bucket=BUCKET, report_state_machine_arn="arn:aws:states:us-east-1:1:stateMachine:Report",
                ghg_state_machine_arn="arn:aws:states:us-east-1:1:stateMachine:Ghg", max_correction_attempts=2, max_wait_seconds=60, poll_seconds=1)
    base.update(kw)
    return Settings(**base)


def val(outcome, errors=None, numeric=None):
    return {"validation_outcome": outcome, "errors": errors or [], "warnings": [], "numeric_results": numeric or {}}


def entry(tid, status="INCLUDED", validation=None, fw="GRI_305", year=2024):
    sid = f"{fw}_{tid.upper()}_{year}"
    e = {"section_id": sid, "template_id": tid, "framework": fw, "status": status,
         "section_result": {"section_id": sid, "content_s3_key": f"sections/x/{sid}.json", "content_s3_bucket": BUCKET}}
    if validation is not None:
        e["validation_result"] = validation
    return e


TEMPLATES = ["summary", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social"]


def build_run(sup: SelfHealingSupervisor, aws: FakeAws, generated: list[dict], year=2024):
    started = sup.start("esg_report", {"reporting_year": year, "framework": "GRI_305"})
    arn = started["execution_arn"]
    inp = aws.executions[arn]["input"]
    included = [e for e in generated if e["status"] in ("INCLUDED", "INCLUDED_WITH_WARNINGS")]
    aws.finish(arn, "SUCCEEDED", {"assembly_result": {"s3_path": f"s3://{BUCKET}/reports/orig.docx", "sections_assembled": len(included)},
                                  "generated_sections": generated, "filtered_sections": {"included": included},
                                  "athena_query_result": {"ghg_summary": {"scope1_tco2e": 3402.99}}})
    assert inp["section_templates"][0]["template_id"] == "summary"
    return arn


def install_lambdas(aws: FakeAws, gen_plan: dict[str, list[str]]):
    """gen_plan: template -> list of validation outcomes returned for successive validations after regeneration."""
    state = {"gen": {}, "val": {}}

    def section_gen(p):
        tid = p["section_id"]
        state["gen"].setdefault(tid, []).append(p)
        sid = f"GRI_305_{tid.upper()}_2024"
        return {"section_id": sid, "content_s3_key": f"sections/x/{sid}.json", "content_s3_bucket": BUCKET}

    def validation(p):
        tid = p["section_id"].split("_", 2)[2].rsplit("_", 1)[0].lower()
        plan = gen_plan.get(tid, ["PASS"])
        i = state["val"].setdefault(tid, 0)
        state["val"][tid] = i + 1
        outcome = plan[min(i, len(plan) - 1)]
        errs = [] if outcome in ("PASS", "WARN") else [{"rule": "VAL-PRH-04", "detail": "First person: ['we']"}]
        return val(outcome, errs)

    def assembly(p):
        return {"s3_path": f"s3://{BUCKET}/reports/fixed.docx", "sections_assembled": len(p["sections"]), "file_size_kb": 100}

    aws.lambdas.update({"esg-section-gen": section_gen, "esg-validation": validation, "esg-assembly-doc": assembly})
    return state


@pytest.fixture
def env():
    aws = FakeAws()
    s = settings()
    return aws, s, SelfHealingSupervisor(aws, s, sleep=lambda _x: None)


def test_repairs_failed_section_with_corrective_prompt_and_reassembles(env):
    aws, s, sup = env
    gen = [entry(t) for t in TEMPLATES]
    gen[1] = entry("scope1", "INCLUDED_WITH_WARNINGS", val("FAIL", [{"rule": "VAL-PRH-04", "detail": "First person: ['we']"}]))
    arn = build_run(sup, aws, gen)
    state = install_lambdas(aws, {"scope1": ["FAIL", "PASS"]})

    res = sup.supervise(arn)

    assert res["state"] == "completed"
    assert res["result"]["healed"] == ["scope1"]
    calls = state["gen"]["scope1"]
    assert len(calls) == 2  # attempt 1 failed re-validation, attempt 2 passed
    assert calls[0]["correction"]["attempt"] == 1
    assert any("third person" in i.lower() for i in calls[0]["correction"]["instructions"])
    assert "scope2" not in state["gen"]  # healthy sections are never touched
    asm = [c for c in aws.calls if c[1] == "esg-assembly-doc"]
    assert len(asm) == 1 and len(asm[0][2]["sections"]) == len(TEMPLATES)
    assert res["result"]["download_url"].endswith("reports/fixed.docx")
    types = [e["type"] for e in sup.ledger.load(arn)["events"]]
    assert "regenerating" in types and "reassembled" in types and types[-1] == "completed"


def test_source_data_problem_is_escalated_not_regenerated(env):
    aws, s, sup = env
    gen = [entry(t) for t in TEMPLATES]
    gen[3] = entry("scope3_pcaf", "INCLUDED_WITH_WARNINGS", val("FAIL_NO_RETRY", [{"rule": "VAL-NUM-06", "detail": "weighted > gross", "no_retry": True}]))
    arn = build_run(sup, aws, gen)
    state = install_lambdas(aws, {})

    res = sup.supervise(arn)

    assert res["state"] == "escalated"
    assert "scope3_pcaf" not in state["gen"]
    assert res["result"]["unresolved"][0]["reason"] == "source_data"
    assert not res["result"]["reassembled"]
    assert res["result"]["assembly_result"]["s3_path"].endswith("orig.docx")


def test_missing_section_is_generated_and_added(env):
    aws, s, sup = env
    gen = [entry(t) for t in TEMPLATES if t != "intensity"]
    gen.append({"section_id": "intensity", "template_id": "intensity", "framework": "GRI_305", "status": "ERROR", "error": "boom"})
    arn = build_run(sup, aws, gen)
    state = install_lambdas(aws, {"intensity": ["PASS"]})

    res = sup.supervise(arn)

    assert res["result"]["healed"] == ["intensity"]
    asm = [c for c in aws.calls if c[1] == "esg-assembly-doc"][0][2]
    assert len(asm["sections"]) == len(TEMPLATES)
    assert state["gen"]["intensity"][0]["correction"]["attempt"] == 1


def test_stops_after_max_attempts(env):
    aws, s, sup = env
    gen = [entry(t) for t in TEMPLATES]
    gen[1] = entry("scope1", "INCLUDED_WITH_WARNINGS", val("FAIL", [{"rule": "VAL-PRH-05", "detail": "Marketing"}]))
    arn = build_run(sup, aws, gen)
    state = install_lambdas(aws, {"scope1": ["FAIL"]})

    res = sup.supervise(arn)

    assert len(state["gen"]["scope1"]) == s.max_correction_attempts == 2
    assert res["state"] == "escalated"
    assert res["result"]["unresolved"][0]["template_id"] == "scope1"
    assert res["result"]["reassembled"]  # newest content is still included


def test_warn_only_sections_are_left_alone(env):
    aws, s, sup = env
    gen = [entry(t) for t in TEMPLATES]
    gen[2] = entry("scope2", "INCLUDED_WITH_WARNINGS", val("WARN"))
    arn = build_run(sup, aws, gen)
    install_lambdas(aws, {})

    res = sup.supervise(arn)

    assert res["state"] == "completed"
    assert [c for c in aws.calls if c[0] == "lambda"] == []
    assert res["result"]["healed"] == [] and not res["result"]["reassembled"]


def test_numeric_retry_outcome_passes_offending_values_into_correction(env):
    aws, s, sup = env
    gen = [entry(t) for t in TEMPLATES]
    gen[1] = entry("scope1", "INCLUDED_WITH_WARNINGS", val("RETRY", [], {"failures": [{"value": 777.7, "unit": "tCO2e", "rule": "VAL-NUM-01"}]}))
    arn = build_run(sup, aws, gen)
    state = install_lambdas(aws, {"scope1": ["PASS"]})

    sup.supervise(arn)

    corr = state["gen"]["scope1"][0]["correction"]
    assert 777.7 in corr["offending_values"]
    assert any("ONLY numbers" in i for i in corr["instructions"])


def test_transient_failure_restarts_once_then_explains(env):
    aws, s, sup = env
    started = sup.start("esg_report", {"reporting_year": 2024, "framework": "GRI_305"})
    arn = started["execution_arn"]
    aws.finish(arn, "FAILED", error="Lambda.TooManyRequestsException", cause="Rate exceeded")
    aws.history[arn] = [
        {"id": 1, "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "InvokeSectionGen"}},
        {"id": 2, "type": "TaskFailed", "taskFailedEventDetails": {"error": "ThrottlingException", "cause": "Rate exceeded"}},
        {"id": 3, "type": "ExecutionFailed", "executionFailedEventDetails": {"error": "ThrottlingException", "cause": "Rate exceeded"}},
    ]
    res = sup.supervise(arn)
    assert res["state"] == "restarted" and res["diagnosis"]["category"] == "generation" and res["diagnosis"]["retryable"]
    assert len(aws.started) == 2

    # the restarted execution fails too: no second restart
    new_arn = [a for a in aws.executions if a != arn][0]
    aws.finish(new_arn, "FAILED", error="ThrottlingException", cause="Rate exceeded")
    aws.history[new_arn] = aws.history[arn]
    res2 = sup.supervise(new_arn)
    assert res2["state"] == "failed" and len(aws.started) == 2


def test_permanent_failure_is_not_restarted_and_is_explained(env):
    aws, s, sup = env
    arn = sup.start("esg_report", {"reporting_year": 2024, "framework": "GRI_305"})["execution_arn"]
    aws.finish(arn, "FAILED", error="ExecutionError", cause="x")
    aws.history[arn] = [
        {"id": 1, "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "TriggerGlueScope1"}},
        {"id": 2, "type": "TaskFailed", "taskFailedEventDetails": {"error": "Glue.AccessDeniedException", "cause": "not authorized to start job"}},
    ]
    res = sup.supervise(arn)
    assert res["state"] == "failed" and len(aws.started) == 1
    d = res["diagnosis"]
    assert d["category"] == "etl" and not d["retryable"] and d["advice"]


def test_concurrent_supervisors_cannot_double_run(env):
    aws, s, sup = env
    arn = sup.start("esg_report", {"reporting_year": 2024, "framework": "GRI_305"})["execution_arn"]
    assert sup.ledger.claim(arn) is True
    assert sup.supervise(arn)["state"] == "already_supervised"
    sup.ledger.release(arn)


def test_completed_run_is_idempotent(env):
    aws, s, sup = env
    arn = build_run(sup, aws, [entry(t) for t in TEMPLATES])
    install_lambdas(aws, {})
    first = sup.supervise(arn)
    second = sup.supervise(arn)
    assert first["state"] == "completed" and second["already_done"] is True


def test_still_running_does_not_block_and_releases_lock(env):
    aws, s, sup = env
    sup2 = SelfHealingSupervisor(aws, settings(max_wait_seconds=3, poll_seconds=1), sleep=lambda _x: None)
    arn = sup2.start("esg_report", {"reporting_year": 2024, "framework": "GRI_305"})["execution_arn"]
    assert sup2.supervise(arn)["state"] == "running"
    assert sup2.ledger.claim(arn) is True  # lock was released


def test_ghg_pipeline_is_supervised_without_report_healing(env):
    aws, s, sup = env
    started = sup.start("ghg_inventory", {"reporting_year": 2024})
    arn = started["execution_arn"]
    aws.finish(arn, "SUCCEEDED", {"inventory_result": {"inventory": {"s3_key": "ghg/2024/inventory.json"}}})
    res = sup.supervise(started["execution_id"])  # short id resolves through the stored metadata
    assert res["state"] == "completed" and res["result"]["pipeline"] == "ghg_inventory"
