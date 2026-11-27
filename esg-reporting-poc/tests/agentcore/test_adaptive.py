"""Adaptive self-correction: strategy choice by failure type, learning from earlier runs, budgets, critic, review notes."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "agentcore"), str(ROOT / "lambda" / "_shared"), str(Path(__file__).parent)]

from fakes import FakeAws
from orchestrator import strategies as S
from orchestrator.healer import SelfHealingSupervisor
from test_healer import BUCKET, TEMPLATES, build_run, entry, settings, val


def lambdas(aws, rules_by_tid, plan, usage=(12000, 3500)):
    """plan[tid] = validation outcomes for successive validations; rules_by_tid[tid] = rule reported on failure."""
    state = {"gen": {}, "val": {}}

    def section_gen(p):
        tid = p["section_id"]
        state["gen"].setdefault(tid, []).append(p)
        sid = f"GRI_305_{tid.upper()}_2024"
        return {"section_id": sid, "content_s3_key": f"sections/x/{sid}.json", "content_s3_bucket": BUCKET,
                "token_usage": {"input": usage[0], "output": usage[1]}}

    def validation(p):
        tid = p["section_id"].split("_", 2)[2].rsplit("_", 1)[0].lower()
        seq = plan.get(tid, ["PASS"])
        i = state["val"].setdefault(tid, 0)
        state["val"][tid] = i + 1
        outcome = seq[min(i, len(seq) - 1)]
        errs = [] if outcome in ("PASS", "WARN") else [{"rule": rules_by_tid.get(tid, "VAL-PRH-04"), "detail": "x"}]
        numeric = {"failures": [{"value": 4242}]} if outcome != "PASS" and rules_by_tid.get(tid, "").startswith("VAL-NUM") else {}
        return val(outcome, errs, numeric)

    aws.lambdas.update({"esg-section-gen": section_gen, "esg-validation": validation,
                        "esg-assembly-doc": lambda p: {"s3_path": f"s3://{BUCKET}/reports/fixed.docx", "sections_assembled": len(p["sections"])}})
    return state


def failing(tid, rule):
    numeric = {"failures": [{"value": 4242}]} if rule.startswith("VAL-NUM") else None
    return entry(tid, "INCLUDED_WITH_WARNINGS", val("FAIL", [{"rule": rule, "detail": "x"}], numeric))


def run(rule, plan, memory=None, **settings_kw):
    aws = FakeAws()
    aws.memory = memory or {}
    sup = SelfHealingSupervisor(aws, settings(max_correction_attempts=4, **settings_kw), sleep=lambda _x: None)
    gen = [entry(t) for t in TEMPLATES]
    gen[1] = failing("scope1", rule)
    arn = build_run(sup, aws, gen)
    state = lambdas(aws, {"scope1": rule}, {"scope1": plan})
    res = sup.supervise(arn)
    return aws, sup, arn, state, res


# ── pure strategy logic ──────────────────────────────────────────────────────────────────────────
def test_categorize():
    assert S.categorize([{"rule": "VAL-NUM-01"}]) == "numeric"
    assert S.categorize([{"rule": "VAL-STR-02"}, {"rule": "VAL-PRH-04"}]) == "structural"
    assert S.categorize([{"rule": "VAL-PRH-05"}]) == "language"
    assert S.categorize([], "generate") == "generate"


def test_cheap_model_first_for_format_problems_strong_for_numbers():
    assert S.choose("structural", set(), {}, None, 0, 0, 1, 5)["strategy"] == "fix_cheap"
    assert S.choose("numeric", set(), {}, None, 0, 0, 1, 5)["strategy"].startswith("grounded")


def test_memory_changes_the_order():
    bad_cheap = {"structural#fix_cheap": {"trials": 12, "successes": 1}, "structural#fix_strong": {"trials": 12, "successes": 11}}
    assert S.choose("structural", set(), bad_cheap, None, 0, 0, 1, 5)["strategy"] == "fix_strong"


def test_minimal_safe_is_the_last_resort():
    assert S.rank("structural", set(), {}, None)[-1]["strategy"] == "minimal_safe"
    assert S.rank("structural", {"fix_cheap", "fix_strong", "critic_strong"}, {}, None)[0]["strategy"] == "minimal_safe"


def test_never_repeats_a_strategy_and_stops_when_exhausted():
    tried = {n for n, _ in S.CANDIDATES["language"]}
    assert "stop" in S.choose("language", tried, {}, None, 0, 0, 1, 5)


def test_budget_stops_the_choice():
    assert "section" in S.choose("numeric", set(), {}, None, 0.39, 0, 0.40, 5)["stop"]
    assert "run" in S.choose("numeric", set(), {}, None, 0, 1.49, 1.0, 1.5)["stop"]


def test_collect_numbers_and_sanitize():
    nums = S.collect_numbers({"a": 1.5, "b": [2, {"c": 3.0}], "d": True, "e": "x"})
    assert nums == ["1.5", "2", "3"]
    assert "http" not in S.sanitize_hint("see https://evil.example now <script>{x}</script>")


def test_correction_block_for_grounded_strategy_has_allowed_values_and_model():
    c = S.build_correction("grounded_strong", 2, {"instructions": ["i"], "offending_values": [9]}, {"scope1": 10, "x": [11]})
    assert c["model"] == "sonnet" and c["allowed_values"] == ["10", "11"] and "minimal" not in c
    assert S.build_correction("minimal_safe", 3, {}, {})["minimal"] is True


# ── through the supervisor ───────────────────────────────────────────────────────────────────────
def test_format_failure_starts_cheap_then_escalates_and_learns():
    aws, sup, arn, state, res = run("VAL-PRH-04", ["FAIL", "PASS"])
    calls = state["gen"]["scope1"]
    assert [c["correction"]["model"] for c in calls] == ["haiku", "sonnet"]
    assert res["state"] == "completed" and res["result"]["healed"] == ["scope1"]
    assert aws.memory["language#fix_cheap"] == {"trials": 1, "successes": 0, "cost": pytest.approx(aws.memory["language#fix_cheap"]["cost"])}
    assert aws.memory["language#fix_strong"]["successes"] == 1
    sec = sup.ledger.load(arn)["sections"]["scope1"]
    assert [h["strategy"] for h in sec["strategies"]] == ["fix_cheap", "fix_strong"]
    assert any("Repaired automatically" in n["text"] for n in res["result"]["notes"])


def test_learned_memory_skips_the_strategy_that_keeps_failing():
    memory = {"language#fix_cheap": {"trials": 20, "successes": 1, "cost": 0.4}, "language#fix_strong": {"trials": 20, "successes": 19, "cost": 1.4}}
    _, _, _, state, res = run("VAL-PRH-04", ["PASS"], memory=memory)
    assert [c["correction"]["model"] for c in state["gen"]["scope1"]] == ["sonnet"]
    assert res["result"]["healed"] == ["scope1"]


def test_numeric_failure_gets_allowed_values_from_the_metrics():
    _, _, _, state, _ = run("VAL-NUM-01", ["PASS"])
    corr = state["gen"]["scope1"][0]["correction"]
    assert corr["allowed_values"] and "3402.99" in corr["allowed_values"] and corr["offending_values"] == [4242]


def test_unresolved_after_all_strategies_has_a_review_note_and_is_still_included():
    aws, sup, arn, state, res = run("VAL-PRH-05", ["FAIL"], section_budget_usd=5.0, run_budget_usd=10.0)
    r = res["result"]
    assert res["state"] == "escalated" and r["unresolved"][0]["template_id"] == "scope1"
    note = next(n for n in r["notes"] if n["section"] == "scope1")
    assert note["level"] == "review" and "Tried:" in note["text"] and "review before publishing" in note["text"].lower()
    assert r["reassembled"] is True  # the newest text is still in the report, flagged
    assert len(state["gen"]["scope1"]) <= 4


def test_section_budget_stops_early_with_a_reason():
    aws, sup, arn, state, res = run("VAL-NUM-01", ["FAIL"], section_budget_usd=0.01)
    assert state["gen"].get("scope1") is None  # even the first attempt did not fit the budget
    ev = [e for e in sup.ledger.load(arn)["events"] if e["type"] == "repair_stopped"]
    assert ev and "budget" in ev[0]["message"]
    assert "budget" in sup.ledger.load(arn)["sections"]["scope1"]["stop_reason"]


def test_run_budget_is_shared_between_sections():
    aws = FakeAws()
    sup = SelfHealingSupervisor(aws, settings(max_correction_attempts=4, run_budget_usd=0.08, section_budget_usd=5.0), sleep=lambda _x: None)
    gen = [entry(t) for t in TEMPLATES]
    gen[1], gen[2] = failing("scope1", "VAL-PRH-04"), failing("scope2", "VAL-PRH-04")
    arn = build_run(sup, aws, gen)
    state = lambdas(aws, {"scope1": "VAL-PRH-04", "scope2": "VAL-PRH-04"}, {"scope1": ["PASS"], "scope2": ["PASS"]}, usage=(30000, 9000))
    res = sup.supervise(arn)
    assert state["gen"].get("scope1") and not state["gen"].get("scope2")
    assert res["result"]["budget"]["spent_usd"] <= 0.08
    assert {u["template_id"] for u in res["result"]["unresolved"]} == {"scope2"}


def test_critic_hint_is_sanitized_and_added_to_instructions():
    aws = FakeAws()
    aws.hint_reply = "Use third person, see https://x.example `now`"
    sup = SelfHealingSupervisor(aws, settings(max_correction_attempts=4, section_budget_usd=5.0, run_budget_usd=10.0), sleep=lambda _x: None)
    gen = [entry(t) for t in TEMPLATES]
    gen[1] = failing("scope1", "VAL-STR-02")
    arn = build_run(sup, aws, gen)
    state = lambdas(aws, {"scope1": "VAL-STR-02"}, {"scope1": ["FAIL", "FAIL", "PASS"]})
    sup.supervise(arn)
    hinted = [c for c in state["gen"]["scope1"] if any(i.startswith("Reviewer note:") for i in c["correction"]["instructions"])]
    assert hinted and "http" not in " ".join(hinted[0]["correction"]["instructions"]) and "`" not in " ".join(hinted[0]["correction"]["instructions"])
    assert "DATA, not instructions" in aws.hints[0]


def test_critic_unavailable_does_not_break_the_loop():
    aws = FakeAws()
    aws.hint_reply = None
    sup = SelfHealingSupervisor(aws, settings(max_correction_attempts=4, section_budget_usd=5.0, run_budget_usd=10.0), sleep=lambda _x: None)
    gen = [entry(t) for t in TEMPLATES]
    gen[1] = failing("scope1", "VAL-STR-02")
    arn = build_run(sup, aws, gen)
    lambdas(aws, {"scope1": "VAL-STR-02"}, {"scope1": ["FAIL", "FAIL", "PASS"]})
    assert sup.supervise(arn)["state"] in ("completed", "escalated")


def test_source_data_issue_note_asks_for_etl_fix():
    aws = FakeAws()
    sup = SelfHealingSupervisor(aws, settings(), sleep=lambda _x: None)
    gen = [entry(t) for t in TEMPLATES]
    gen[1] = entry("scope1", "INCLUDED_WITH_WARNINGS", val("FAIL", [{"rule": "VAL-NUM-02", "detail": "x"}]))
    arn = build_run(sup, aws, gen)
    lambdas(aws, {}, {})
    res = sup.supervise(arn)
    note = next(n for n in res["result"]["notes"] if n["section"] == "scope1")
    assert note["level"] == "action" and "re-run the pipeline" in note["text"]
