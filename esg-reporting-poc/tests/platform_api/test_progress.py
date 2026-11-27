"""Run checkpoints, run summaries and readiness scoring with unknown probes."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lambda"))
from platform_api import agent_api, compliance, progress as P  # noqa: E402

T0 = datetime(2026, 11, 27, 9, tzinfo=timezone.utc)


def ev(i, typ, name=None, **extra):
    e = {"id": i, "type": typ, "timestamp": T0 + timedelta(seconds=i)}
    if typ.endswith("StateEntered"):
        e["stateEnteredEventDetails"] = {"name": name}
    elif typ.endswith("StateExited"):
        e["stateExitedEventDetails"] = {"name": name}
    e.update(extra)
    return e


def report_history(sections_done=2, total=3, finished=False):
    h = [ev(1, "TaskStateEntered", "ValidateInput"), ev(2, "TaskStateExited", "ValidateInput"),
         ev(3, "ChoiceStateEntered", "CheckValidation"), ev(4, "ChoiceStateExited", "CheckValidation"),
         ev(5, "ParallelStateEntered", "WaitForGlueJobs"), ev(6, "ParallelStateExited", "WaitForGlueJobs"),
         ev(7, "TaskStateEntered", "TriggerAggregation"), ev(8, "TaskStateExited", "TriggerAggregation"),
         ev(9, "TaskStateEntered", "QueryAthena"), ev(10, "TaskStateExited", "QueryAthena"),
         ev(11, "MapStateEntered", "GenerateSections"), ev(12, "MapStateStarted", mapStateStartedEventDetails={"length": total})]
    h += [ev(20 + k, "MapIterationSucceeded", mapIterationEventDetails={"name": "GenerateSections", "index": k}) for k in range(sections_done)]
    if finished:
        h += [ev(40, "MapStateExited", "GenerateSections"), ev(41, "TaskStateEntered", "FilterSections"), ev(42, "TaskStateExited", "FilterSections"),
              ev(43, "TaskStateEntered", "AssembleDocument"), ev(44, "TaskStateExited", "AssembleDocument"),
              ev(45, "TaskStateEntered", "NotifyCompletion"), ev(46, "TaskStateExited", "NotifyCompletion")]
    return h


def test_report_steps_while_generating():
    steps = {s["key"]: s for s in P.sfn_steps("esg_report", report_history(), "RUNNING")}
    assert steps["validate"]["status"] == "done" and steps["etl"]["status"] == "done"
    assert steps["generate"]["status"] == "running" and steps["generate"]["detail"] == "2/3 sections"
    assert steps["assemble"]["status"] == "pending"


def test_report_steps_finished_and_agent_repair():
    sfn = P.sfn_steps("esg_report", report_history(3, 3, True), "SUCCEEDED")
    assert all(s["status"] == "done" for s in sfn)
    doc = {"status": "completed", "result": {"download_url": "x"}, "sections": {"scope1": {"status": "healed", "attempts": 2}},
           "events": [{"type": "validation_review", "ts": "t", "message": "Reviewed 8", "detail": {"to_repair": ["scope1"]}},
                      {"type": "regenerating", "ts": "t2", "message": "a"}, {"type": "regenerating", "ts": "t3", "message": "b"},
                      {"type": "reassembled", "ts": "t4", "message": "c"}]}
    ag = {s["key"]: s for s in P.agent_steps("esg_report", doc, "SUCCEEDED")}
    assert ag["repair"]["status"] == "done" and ag["repair"]["detail"].startswith("1 repaired") and "2 attempt" in ag["repair"]["detail"]
    assert ag["reassemble"]["status"] == "done" and ag["ready"]["status"] == "done"


def test_report_nothing_to_repair_is_skipped_not_pending():
    doc = {"status": "completed", "result": {}, "sections": {}, "events": [{"type": "validation_review", "ts": "t", "message": "ok", "detail": {"to_repair": []}}]}
    ag = {s["key"]: s for s in P.agent_steps("esg_report", doc, "SUCCEEDED")}
    assert ag["repair"]["status"] == "skipped" and ag["reassemble"]["status"] == "skipped"


def test_sync_steps_count_ok_and_failed_tables():
    h = [ev(1, "MapStateEntered", "SyncTables"), ev(2, "MapStateStarted", mapStateStartedEventDetails={"length": 4}),
         ev(3, "PassStateEntered", "Ok"), ev(4, "PassStateEntered", "Ok"), ev(5, "PassStateEntered", "Failed"), ev(6, "PassStateEntered", "Ok"),
         ev(7, "MapStateExited", "SyncTables")]
    s = P.sfn_steps("data_sync", h, "SUCCEEDED")[0]
    assert s["detail"] == "4/4 tables processed · 1 failed" and s["status"] == "warning"


def test_sync_agent_steps_with_child_etl():
    doc = {"status": "completed", "result": {"tables": {t: {"status": "ok"} for t in "abcd"}},
           "events": [{"type": "etl_started", "ts": "t", "detail": {"etl_execution_id": "c1"}}]}
    child = {"status": "completed", "steps": [{"label": "Calculate", "status": "done"}]}
    ag = {s["key"]: s for s in P.agent_steps("data_sync", doc, "SUCCEEDED", child)}
    assert ag["triage"]["detail"] == "4/4 tables loaded" and ag["etl"]["status"] == "done" and ag["done"]["status"] == "done"
    doc2 = {"status": "escalated", "result": {"tables": {"a": {"status": "ok"}, "b": {"status": "failed"}}}, "events": []}
    ag2 = {s["key"]: s for s in P.agent_steps("data_sync", doc2, "SUCCEEDED")}
    assert ag2["etl"]["status"] == "skipped" and "not every table" in ag2["etl"]["detail"] and ag2["done"]["status"] == "warning"


def test_progress_end_to_end_with_fakes():
    class Sfn:
        def describe_execution(self, executionArn):
            return {"status": "SUCCEEDED", "input": '{"reporting_year": 2024, "section_templates": [1]}', "startDate": T0, "stopDate": T0}

        def get_execution_history(self, **kw):
            if kw["executionArn"].endswith(":c1"):
                return {"events": [ev(1, "ParallelStateEntered", "RunEtl"), ev(2, "ParallelStateExited", "RunEtl")]}
            return {"events": [ev(1, "MapStateEntered", "SyncTables"), ev(2, "MapStateStarted", mapStateStartedEventDetails={"length": 1}),
                               ev(3, "PassStateEntered", "Ok"), ev(4, "MapStateExited", "SyncTables")]}

    store = {"executions/s1/meta.json": {"pipeline": "data_sync", "execution_arn": "arn:x:s1"},
             "agent-ledger/s1.json": {"status": "completed", "result": {"tables": {"a": {"status": "ok"}}},
                                      "events": [{"type": "etl_started", "ts": "t", "detail": {"etl_execution_id": "c1"}}]},
             "executions/c1/meta.json": {"pipeline": "ghg_inventory", "execution_arn": "arn:x:c1"},
             "agent-ledger/c1.json": {"status": "completed", "events": []}}
    out = P.progress("s1", sfn=Sfn(), get=store.get)
    assert out["status"] == "completed" and out["params"] == {"reporting_year": 2024}
    assert [s["key"] for s in out["steps"]] == ["extract", "triage", "etl", "done"]
    assert out["child"]["pipeline"] == "ghg_inventory" and out["steps"][2]["status"] == "done"
    with pytest.raises(ValueError):
        P.progress("../x", sfn=Sfn(), get=store.get)


def test_run_summaries_speak_the_pipeline_language():
    assert agent_api.summarize({"pipeline": "data_sync", "status": "completed",
                                "result": {"tables": {"a": {"status": "ok"}, "b": {"status": "ok", "warnings": 2}}, "retried": ["b"], "etl_state": "completed"}}) \
        == "2/2 tables loaded · 1 retried · 2 warning(s) · ETL finished"
    assert agent_api.summarize({"pipeline": "esg_report", "status": "escalated", "result": {"healed": ["a"], "unresolved": [{}]}}) == "1 section(s) repaired · 1 need review"
    assert agent_api.summarize({"pipeline": "esg_report", "status": "completed", "result": {}}) == "all sections passed"
    assert agent_api.summarize({"pipeline": "ghg_inventory", "status": "completed"}) == "inventory built"
    assert agent_api.summarize({"pipeline": "data_sync", "status": "running"}) == "in progress"


def test_unknown_probe_is_excluded_from_the_score():
    items = [{"w": 3, "status": "ready"}, {"w": 3, "status": "unknown"}, {"w": 1, "status": "gap"}]
    assert compliance.score(items) == 75.0
    assert compliance.score([{"w": 1, "status": "unknown"}]) is None


def test_readiness_marks_failed_checks_unknown(monkeypatch):
    monkeypatch.setattr(compliance.common, "s3_get", lambda *a, **k: None)

    def q(sql, db="x", *a, **k):
        raise RuntimeError("AccessDenied on athena results")
    r = compliance.readiness(2024, q=q)
    athena_items = [i for i in r["items"] if i["id"] in {it["id"] for it in compliance.CONFIG["items"] if it["probe"]["type"] in ("athena_rows", "pcaf_quality", "assurance")}]
    assert athena_items and all(i["status"] == "unknown" and i["rec"] == "" for i in athena_items)
    assert r["counts"]["unknown"] == len(athena_items) and r["summary_error"]
