"""Report Builder (versioned templates, configs, generate), regulatory finding workflow, conversation history."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lambda"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from platform_api import agent_api, common, compliance, conversations, handler, report_builder as RB  # noqa: E402
from test_platform_api import FakeJobs, FakeS3, _http  # noqa: E402

TEMPLATE = "# SECTION: SCOPE1\nSECTION_ID: {section_id}\nREPORTING_YEAR: {reporting_year}\n" + "Write the Scope 1 section. " * 20


class Store(RB.Store):
    def __init__(self):
        self.d = {}

    def get_text(self, bucket, key):
        return self.d.get((bucket, key))

    def put_text(self, bucket, key, text):
        self.d[(bucket, key)] = text

    def get_json(self, bucket, key):
        t = self.d.get((bucket, key))
        return json.loads(t) if t else None

    def put_json(self, bucket, key, body):
        self.d[(bucket, key)] = json.dumps(body)

    def list_keys(self, bucket, prefix):
        return [k for (b, k) in self.d if b == bucket and k.startswith(prefix)]

    def delete(self, bucket, key):
        self.d.pop((bucket, key), None)


@pytest.fixture()
def store(monkeypatch):
    st = Store()
    st.put_text(RB._kb_bucket(), "prompts/templates/section_scope1.txt", TEMPLATE)
    monkeypatch.setattr(RB, "STORE", st)
    return st


# ── templates ─────────────────────────────────────────────────────────────────────────────────────
def test_first_open_records_the_live_text_as_v1(store):
    t = RB.get_template("scope1")
    assert t["published"] == "v1" and t["versions"][0]["author"] == "repository" and t["placeholders"] == ["{reporting_year}", "{section_id}"]


def test_draft_validation_protects_the_generator(store):
    assert not RB.save_draft("scope1", "too short", "", "u")["saved"]
    r = RB.save_draft("scope1", TEMPLATE.replace("{reporting_year}", "2024"), "", "u")
    assert not r["saved"] and "{reporting_year}" in r["problems"][0]
    r = RB.save_draft("scope1", TEMPLATE + " {new_field}", "", "u")
    assert not r["saved"] and "new_field" in " ".join(r["problems"])
    with pytest.raises(ValueError):
        RB.save_draft("nope", TEMPLATE, "", "u")


def test_draft_then_publish_then_restore(store):
    v2 = RB.save_draft("scope1", TEMPLATE + " Mention the boiler replacement.", "add initiative", "admin@x")["version"]
    assert v2 == "v2" and store.get_text(RB._kb_bucket(), "prompts/templates/section_scope1.txt") == TEMPLATE  # drafts never go live
    RB.publish("scope1", "v2", "admin@x")
    assert store.get_text(RB._kb_bucket(), "prompts/templates/section_scope1.txt").endswith("boiler replacement.")
    t = RB.get_template("scope1")
    assert t["published"] == "v2" and {v["version"]: v["status"] for v in t["versions"]} == {"v2": "published", "v1": "archived"}
    RB.publish("scope1", "v1", "admin@x")
    assert store.get_text(RB._kb_bucket(), "prompts/templates/section_scope1.txt") == TEMPLATE


def test_agent_proposals_are_drafts(store):
    r = handler.lambda_handler({"action": "template_propose", "template_key": "scope1", "text": TEMPLATE + " New OJK rule.", "reason": "finding A-1"})
    assert r["saved"] and RB.get_template("scope1")["versions"][0]["author"] == "agent"


# ── configs and generate ──────────────────────────────────────────────────────────────────────────
def test_config_crud_and_validation(store):
    c = RB.save_config({"name": "IFRS short ID", "framework": "IFRS_S2", "sections": ["scope2", "scope1"], "language": "id"}, "admin")
    assert c["sections"] == ["scope1", "scope2"] and RB.get_config(c["id"])["language"] == "id"
    assert [x["id"] for x in RB.list_configs()["configs"]] == [c["id"]]
    with pytest.raises(ValueError):
        RB.save_config({"name": "x", "framework": "IFRS_S2", "sections": ["double_materiality"]}, "admin")
    RB.delete_config(c["id"])
    assert RB.list_configs()["configs"] == []


def test_generate_goes_through_the_agent_runtime(store, monkeypatch):
    jobs, calls = FakeJobs(), []
    r = agent_api.start_submit({"framework": "GRI_305", "reporting_year": 2024, "sections": ["scope1"], "language": "id", "_user": "u1"},
                               jobs=jobs, invoke=calls.append)
    p = calls[0]["runtime_payload"]
    assert p == {"mode": "start", "pipeline": "esg_report", "reporting_year": 2024, "framework": "GRI_305", "language": "id", "sections": ["scope1"], "user": "u1"}
    agent_api.chat_worker(calls[0], jobs=jobs, runtime=lambda payload, sid: {"started": True, "execution_id": "e-1"})
    assert agent_api.chat_status(r["job_id"], "u1", jobs=jobs)["result"]["execution_id"] == "e-1"
    with pytest.raises(ValueError):
        agent_api.start_submit({"framework": "GRI_305", "reporting_year": 2030}, jobs=jobs, invoke=calls.append)


def test_builder_routes_and_admin_rights(store, monkeypatch):
    assert handler.lambda_handler(_http("GET", "/reports/catalog"))["statusCode"] == 200
    assert handler.lambda_handler(_http("GET", "/reports/templates/scope1"))["statusCode"] == 200
    draft = _http("POST", "/reports/templates/scope1/draft", {"text": TEMPLATE + " x" * 5})
    assert handler.lambda_handler(draft)["statusCode"] == 403
    draft["requestContext"]["authorizer"]["jwt"]["claims"]["cognito:groups"] = "[admin]"
    assert json.loads(handler.lambda_handler(draft)["body"])["saved"] is True
    assert handler.lambda_handler(_http("POST", "/reports/configs", {"name": "a", "framework": "GRI_305"}))["statusCode"] == 403
    assert handler.lambda_handler(_http("GET", "/reports/templates/../../etc"))["statusCode"] in (400, 404)
    # agent-only actions are not reachable over HTTP
    assert handler.lambda_handler(_http("POST", "/template_propose", {}))["statusCode"] == 404


# ── regulatory findings ───────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def s3(monkeypatch):
    f = FakeS3()
    monkeypatch.setattr(common, "s3_get", f.get)
    monkeypatch.setattr(common, "s3_put", f.put)
    return f


def test_scan_records_history_relevance_and_status(s3):
    kw = compliance.CONFIG["keywords"][0]
    html = f'<a href="/a">Regulation on {kw} reporting for banks</a><a href="/b">Insurance {kw} rule for pension funds</a>'

    def clf(title, source):
        rel = "Insurance" not in title
        return {"severity": "high" if rel else "low", "impact": ["Governance"], "action": "x", "classified": True, "relevant": rel, "relevance": "r"}
    compliance.scan(lambda u: html, clf)
    a = compliance.alerts()
    assert a["scans"][0]["new"] == len(a["alerts"]) and a["scans"][0]["relevant"] < a["scans"][0]["new"]
    assert {x["status"] for x in a["alerts"]} == {"new", "not_relevant"}
    compliance.scan(lambda u: html, clf)
    assert len(compliance.alerts()["scans"]) == 2 and compliance.alerts()["scans"][0]["new"] == 0


def test_finding_status_and_validation(s3):
    s3.put(compliance.ALERTS_KEY, {"alerts": [{"id": "A-1", "title": "t", "impact": []}]})
    r = compliance.set_alert_status({"alert_id": "A-1", "status": "actioned", "note": "template updated"}, "admin@x")
    assert r["alert"]["status"] == "actioned" and r["alert"]["status_by"] == "admin@x"
    with pytest.raises(ValueError):
        compliance.set_alert_status({"alert_id": "A-1", "status": "done"}, "a")
    with pytest.raises(LookupError):
        compliance.set_alert_status({"alert_id": "A-9", "status": "reviewed"}, "a")
    assert handler.lambda_handler(_http("POST", "/compliance/alerts/status", {"alert_id": "A-1", "status": "reviewed"}))["statusCode"] == 403


def test_alert_context_maps_areas_to_templates_and_checklist(s3):
    s3.put(compliance.ALERTS_KEY, {"alerts": [{"id": "A-2", "title": "Assurance of sustainability reports", "impact": ["Governance", "Scope 3"]}]})
    seen = []
    ctx = compliance.alert_context("A-2", get_template=lambda k: seen.append(k) or {"label": k, "published": "v1", "placeholders": [],
                                                                                    "versions": [{"version": "v1", "text": "T" * 3000}]})
    keys = [t["template_key"] for t in ctx["affected_templates"]]
    assert "governance" in keys and "scope3_pcaf" in keys and len(ctx["affected_templates"][0]["excerpt"]) == 1800
    assert all(i["pillar"] in ("gov", "met") for i in ctx["related_checklist_items"])


# ── conversations ─────────────────────────────────────────────────────────────────────────────────
class Table:
    def __init__(self):
        self.items = {}

    def get_item(self, Key):
        i = self.items.get((Key["user"], Key["sk"]))
        return {"Item": dict(i)} if i else {}

    def put_item(self, Item):
        self.items[(Item["user"], Item["sk"])] = dict(Item)

    def delete_item(self, Key):
        self.items.pop((Key["user"], Key["sk"]), None)

    def query(self, KeyConditionExpression, **kw):
        # boto3 condition objects: read user and prefix from their values
        vals = [v for v in KeyConditionExpression.get_expression()["values"]]
        user = vals[0].get_expression()["values"][1]
        prefix = vals[1].get_expression()["values"][1]
        return {"Items": [dict(v) for (u, sk), v in self.items.items() if u == user and sk.startswith(prefix)]}


def test_conversation_history_is_per_user_masked_and_deletable():
    t = Table()
    cid = "esg-" + "a" * 32
    conversations.record_turn("u1", cid, "Hubungi Budi di 081234567890 soal scope 2", "Scope 2 is 38,950 tCO2e.", table=t)
    conversations.record_turn("u1", cid, "and scope 1?", "12,480 tCO2e.", table=t)
    lst = conversations.list_conversations("u1", table=t)["conversations"]
    assert len(lst) == 1 and "081234567890" not in lst[0]["title"]
    conv = conversations.get_conversation("u1", cid, table=t)
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant", "user", "assistant"]
    assert "081234567890" not in conv["messages"][0]["text"]
    assert conversations.get_conversation("u2", cid, table=t) == {"found": False}  # another user cannot read it
    assert conversations.list_conversations("u2", table=t)["conversations"] == []
    conversations.delete_conversation("u1", cid, table=t)
    assert conversations.get_conversation("u1", cid, table=t) == {"found": False} and t.items == {}
    with pytest.raises(ValueError):
        conversations.get_conversation("u1", "short", table=t)


def test_chat_worker_records_history(monkeypatch):
    jobs, calls, recorded = FakeJobs(), [], []
    monkeypatch.setattr(conversations, "TABLE", "t")
    monkeypatch.setattr(conversations, "record_turn", lambda *a, **k: recorded.append(a))
    r = agent_api.chat_submit({"prompt": "halo", "_user": "u1", "session_id": "esg-" + "b" * 32}, jobs=jobs, invoke=calls.append)
    agent_api.chat_worker(calls[0], jobs=jobs, runtime=lambda p, s: {"response": "hi"})
    assert recorded == [("u1", "esg-" + "b" * 32, "halo", "hi")] and agent_api.chat_status(r["job_id"], "u1", jobs=jobs)["status"] == "done"
