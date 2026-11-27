"""Logic tests for lambda/platform_api with fake Athena / S3 / DynamoDB (no AWS access)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

LAMBDA = Path(__file__).resolve().parents[2] / "lambda"
sys.path.insert(0, str(LAMBDA))

from platform_api import common, compliance, ghg, governance, portfolio  # noqa: E402
from platform_api import handler  # noqa: E402


class FakeS3:
    def __init__(self):
        self.d: dict[str, object] = {}

    def get(self, key, bucket=None):
        return self.d.get(key)

    def put(self, key, body, bucket=None):
        self.d[key] = json.loads(common.dumps(body))


@pytest.fixture()
def s3(monkeypatch):
    f = FakeS3()
    monkeypatch.setattr(common, "s3_get", f.get)
    monkeypatch.setattr(common, "s3_put", f.put)
    return f


# ── GHG ───────────────────────────────────────────────────────────────────────────────────────────
def test_gas_breakdown_reconciles():
    r = ghg.gas_breakdown(1000.0, 500.0, 70.0)
    assert r["available"] and len(r["vals"]) == 6
    assert r["computed_total"] == pytest.approx(sum(r["vals"]), abs=0.01)
    assert r["delta_pct"] is not None


def test_gas_breakdown_missing_data():
    assert ghg.gas_breakdown(None, None, 10) == {"available": False}


def _fake_q(operational: bool):
    def q(sql, db="esg_aggregated", *a, **k):
        if "ghg_summary_annual" in sql:
            return [{"scope1_tco2e": 100.0, "scope2_location_tco2e": 200.0, "scope2_market_tco2e": 180.0, "scope3_cat15_gross_tco2e": 1000.0,
                     "scope3_cat15_weighted_tco2e": 900.0, "avg_pcaf_data_quality": 3.2, "assurance_level": "limited"}]
        if "ghg_scope1" in sql:
            return [{"gj": 1000, "l": 500, "dq": 3.0, "n": 4}]
        if "ghg_scope2" in sql:
            return [{"mwh": 5000, "rec": 100, "dq": 3.5}]
        if "ghg_scope3_financed" in sql:
            return [{"pcaf": 3.2, "hq": 20.0, "loans": 100}]
        if "scope3_operational_activity" in sql:
            if not operational:
                raise RuntimeError("TABLE_NOT_FOUND")
            return [{"category": "c1", "t": 50.0, "dq": 3.0, "method": "spend", "src": "EXIOBASE", "acts": "purchases"}]
        return []
    return q


def test_inventory_marks_missing_operational_as_not_measured_not_zero():
    inv = ghg.build_inventory(2024, q=_fake_q(operational=False))
    c1 = next(r for r in inv["part2"] if r["k"] == "c1")
    assert c1["v"] is None and c1["inc"] is False
    assert inv["totals"]["total"] == 100 + 200 + 1000


def test_inventory_includes_operational_when_present():
    inv = ghg.build_inventory(2024, q=_fake_q(operational=True))
    c1 = next(r for r in inv["part2"] if r["k"] == "c1")
    assert c1["v"] == 50.0 and inv["totals"]["total"] == 1350.0


def test_inventory_without_summary_raises():
    with pytest.raises(LookupError):
        ghg.build_inventory(2024, q=lambda *a, **k: [])


# ── Compliance ────────────────────────────────────────────────────────────────────────────────────
def test_score_weights():
    items = [{"w": 3, "status": "ready"}, {"w": 1, "status": "gap"}]
    assert compliance.score(items) == 75.0
    assert compliance.score([{"w": 2, "status": "partial"}]) == 50.0


def test_readiness_structure_and_probe_failure_degrades(s3):
    def q(sql, db="x", *a, **k):
        raise RuntimeError("athena down")
    r = compliance.readiness(2024, q=q)
    assert r["items"] and 0 <= r["score"] <= 100
    assert sum(r["counts"].values()) == len(r["items"])


def test_attest_validates_and_is_used(s3):
    with pytest.raises(ValueError):
        compliance.attest({"item_id": "NOPE", "status": "ready"})
    iid = compliance.CONFIG["items"][0]["id"]
    compliance.attest({"item_id": iid, "status": "gap", "note": "x"})
    r = compliance.readiness(2024, q=lambda *a, **k: [])
    assert next(i for i in r["items"] if i["id"] == iid)["status"] == "gap"


def test_scan_extracts_dedupes_and_survives_source_failure(s3):
    kw = compliance.CONFIG["keywords"][0]
    html = f'<a href="/a">Regulation on {kw} reporting for banks</a><a href="/b">Contact us today please</a>'
    calls = {"n": 0}

    def fetch(url):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("boom")
        return html

    clf = lambda t, s: {"severity": "high", "impact": ["Governance"], "action": "x", "classified": True}  # noqa: E731
    r1 = compliance.scan(fetch, clf)
    assert r1["errors"] and r1["new"] >= 1
    r2 = compliance.scan(lambda u: html, clf)
    assert r2["new"] >= 1  # the source that failed in the first scan is picked up now
    r3 = compliance.scan(lambda u: html, clf)
    assert r3["new"] == 0  # everything already seen
    assert compliance.alerts()["alerts"]


# ── Portfolio / scenario ──────────────────────────────────────────────────────────────────────────
ROWS = [
    {"sector_nace": "energy_oil_gas", "loan_type": "term_loan", "score": 4, "outstanding": 2e12, "financed": 1e6, "n": 10},
    {"sector_nace": "real_estate_residential", "loan_type": "mortgage", "score": 5, "outstanding": 3e12, "financed": 2e5, "n": 30},
    {"sector_nace": "real_estate_commercial", "loan_type": "term_loan", "score": 3, "outstanding": 1e12, "financed": 2e5, "n": 3},
]


def test_pcaf_distribution_sums_to_100():
    r = portfolio.pcaf(2024, rows=ROWS)
    assert sum(r["dist_pct"]) == pytest.approx(100, abs=0.2)
    assert {c["id"] for c in r["classes"]} == {"corp", "mort", "cre"}
    assert r["total_outstanding_tn"] == 6.0


def test_tkbi_parts_sum_to_total():
    r = portfolio.tkbi(2024, rows=ROWS)
    assert r["green_tn"] + r["transition_tn"] + r["brown_tn"] == pytest.approx(r["total_tn"], abs=0.01)


def test_green_trend_projects_to_target(monkeypatch):
    monkeypatch.setattr(portfolio, "_book", lambda y, q: ROWS)
    t = portfolio.green_trend([2023, 2024], q=None, target=40.0)
    assert t["points"][-1]["year"] == 2030 and t["points"][-1]["green_ratio_pct"] == 40.0


def test_benchmark_ranks_and_flags_illustrative():
    b = portfolio.benchmark()
    assert b["illustrative"] and [r["rank"] for r in b["rows"]] == list(range(1, len(b["rows"]) + 1))
    assert all("bank" not in r["name"].lower() or r.get("us") for r in b["rows"])


def test_scenario_orders_by_severity_and_records_baseline_run(s3, monkeypatch):
    monkeypatch.setattr(portfolio, "_book", lambda y, q: ROWS)
    r = portfolio.scenario({"year": 2024})
    ids = [s["scenario_id"] for s in r["scenarios"]]
    assert ids == ["s15", "s2", "s3"]
    assert r["scenarios"][0]["transition_delta_ecl_tn"] > r["scenarios"][2]["transition_delta_ecl_tn"]
    assert compliance.SCENARIO_RUN_KEY in s3.d
    s3.d.clear()
    portfolio.scenario({"year": 2024, "whatif": {"carbon_override": 200}})
    assert compliance.SCENARIO_RUN_KEY not in s3.d  # what-if runs are not evidence


# ── Governance ────────────────────────────────────────────────────────────────────────────────────
def test_pii_mask_records_and_text():
    r = governance.pii_mask({"records": [{"name": "Budi Santoso", "nik": "3171234567890001", "salary": 12_000_000, "dept": "Ops"}]})
    m = r["masked"][0]
    assert "Budi" not in json.dumps(m) and "3171234567890001" not in json.dumps(m) and m["dept"] == "Ops"
    assert r["total_findings"] == 3
    t = governance.pii_mask({"text": "NIK 3171234567890001"})
    assert "3171234567890001" not in t["masked"]
    with pytest.raises(ValueError):
        governance.pii_mask({})
    with pytest.raises(ValueError):
        governance.pii_mask({"text": "x", "mode": "bad"})


def test_finops_summary_attribution_and_projection():
    items = [
        {"day": "2026-11-27", "task": "section_complex", "model": "sonnet", "tokens_in": 10000, "tokens_out": 2000, "cached_in": 0,
         "cost_usd": 0.06, "baseline_cost_usd": 0.06, "execution_id": "e1"},
        {"day": "2026-11-26", "task": "section_simple", "model": "haiku", "tokens_in": 10000, "tokens_out": 2000, "cached_in": 5000,
         "cost_usd": 0.015, "baseline_cost_usd": 0.06, "execution_id": ""},
    ]
    s = governance.summarize(items, 3, meta_get=lambda k: {"subsidiary": "BNS Finance"}, today=datetime(2026, 11, 27, tzinfo=timezone.utc))
    assert s["totals"]["calls"] == 2 and s["totals"]["saved_vs_baseline_usd"] == pytest.approx(0.045)
    assert {r["key"] for r in s["by_subsidiary"]} == {"BNS Finance", "Unattributed"}
    assert len(s["daily"]) == 3 and s["daily"][-1]["day"] == "2026-11-27"
    assert s["projection_by_profile_usd"]["economy"] <= s["projection_by_profile_usd"]["quality"]


def test_finops_without_table_is_explicit(monkeypatch):
    monkeypatch.delenv("USAGE_TABLE", raising=False)
    r = governance.finops_summary({"days": 7})
    assert r["has_data"] is False and "warning" in r
    with pytest.raises(ValueError):
        governance.finops_summary({"days": "abc"})


# ── Handler ───────────────────────────────────────────────────────────────────────────────────────
def _http(method, path, body=None, qs=None, groups="[viewer]", sub="user-1", authed=True):
    claims = {"sub": sub, "cognito:groups": groups} if authed else {}
    return {"requestContext": {"http": {"method": method, "path": path}, "authorizer": {"jwt": {"claims": claims}} if authed else {}},
            "queryStringParameters": qs, "body": json.dumps(body) if body is not None else None}


def test_handler_routes_and_errors():
    assert handler.lambda_handler(_http("GET", "/health", authed=False))["statusCode"] == 200
    assert handler.lambda_handler(_http("GET", "/nope"))["statusCode"] == 404
    r = handler.lambda_handler(_http("POST", "/governance/pii-mask", {}))
    assert r["statusCode"] == 400 and "error" in json.loads(r["body"])
    assert handler.lambda_handler(_http("OPTIONS", "/anything", authed=False))["statusCode"] == 204


def test_handler_requires_login_and_role():
    assert handler.lambda_handler(_http("GET", "/portfolio", authed=False))["statusCode"] == 401
    assert handler.lambda_handler(_http("GET", "/portfolio", groups=""))["statusCode"] == 403
    assert handler.lambda_handler(_http("POST", "/governance/pii-mask", {"text": "hi"}))["statusCode"] == 200


def test_admin_only_routes(monkeypatch):
    monkeypatch.setattr(handler.agent_api, "_invoke_self", lambda p: None)
    assert handler.lambda_handler(_http("POST", "/compliance/scan", {}, groups="[viewer]"))["statusCode"] == 403
    assert handler.lambda_handler(_http("POST", "/compliance/attest", {}, groups="[viewer]"))["statusCode"] == 403
    r = handler.lambda_handler(_http("POST", "/compliance/scan", {}, groups="[viewer admin]"))
    assert r["statusCode"] == 200 and json.loads(r["body"]) == {"started": True}


def test_client_cannot_inject_internal_fields(monkeypatch):
    seen = {}
    monkeypatch.setitem(handler.ACTIONS, "agent_chat", lambda p: seen.update(p) or {})
    handler.lambda_handler(_http("POST", "/agent/chat", {"prompt": "x", "_user": "someone-else"}, sub="real-user"))
    assert seen["_user"] == "real-user"


def test_handler_direct_invocation_returns_error_object():
    r = handler.lambda_handler({"action": "pii_mask"})
    assert "error" in r
    assert "actions" in handler.lambda_handler({"action": "zzz"})


# ── Async chat ────────────────────────────────────────────────────────────────────────────────────
class FakeJobs:
    def __init__(self):
        self.items = {}

    def put_item(self, Item):
        self.items[Item["job_id"]] = dict(Item)

    def get_item(self, Key):
        i = self.items.get(Key["job_id"])
        return {"Item": dict(i)} if i else {}

    def update_item(self, Key, UpdateExpression, ExpressionAttributeValues, ExpressionAttributeNames=None):
        item = self.items[Key["job_id"]]
        names = ExpressionAttributeNames or {}
        for part in UpdateExpression[4:].split(","):
            k, v = [x.strip() for x in part.split("=")]
            item[names.get(k, k)] = ExpressionAttributeValues[v]


def test_chat_flow_and_ownership():
    from platform_api import agent_api
    jobs, calls = FakeJobs(), []
    r = agent_api.chat_submit({"prompt": "halo", "_user": "u1", "session_id": "short"}, jobs=jobs, invoke=calls.append)
    assert len(r["session_id"]) >= 33 and calls[0]["action"] == "agent_chat_worker" and "halo" == calls[0]["prompt"]
    assert "prompt" not in jobs.items[r["job_id"]]  # the prompt is never stored
    assert agent_api.chat_status(r["job_id"], "u1", jobs=jobs)["status"] == "queued"
    agent_api.chat_worker(calls[0], jobs=jobs, runtime=lambda p, s: {"response": "ok"})
    assert agent_api.chat_status(r["job_id"], "u1", jobs=jobs)["result"]["response"] == "ok"
    assert agent_api.chat_status(r["job_id"], "u2", jobs=jobs) == {"found": False}
    assert agent_api.chat_status(r["job_id"], "u2", is_admin=True, jobs=jobs)["found"]


def test_chat_worker_failure_is_reported_without_details():
    from platform_api import agent_api
    jobs = FakeJobs()
    r = agent_api.chat_submit({"prompt": "x", "_user": "u"}, jobs=jobs, invoke=lambda p: None)

    def boom(p, s):
        raise RuntimeError("secret internal detail")
    agent_api.chat_worker({"job_id": r["job_id"], "prompt": "x", "session_id": r["session_id"]}, jobs=jobs, runtime=boom)
    st = agent_api.chat_status(r["job_id"], "u", jobs=jobs)
    assert st["status"] == "failed" and "secret" not in json.dumps(st)


def test_chat_validation():
    from platform_api import agent_api
    with pytest.raises(ValueError):
        agent_api.chat_submit({"prompt": " "}, jobs=FakeJobs(), invoke=lambda p: None)
    with pytest.raises(ValueError):
        agent_api.chat_submit({"prompt": "x" * 5000}, jobs=FakeJobs(), invoke=lambda p: None)
    with pytest.raises(ValueError):
        agent_api.chat_status("not-a-job", "u", jobs=FakeJobs())
