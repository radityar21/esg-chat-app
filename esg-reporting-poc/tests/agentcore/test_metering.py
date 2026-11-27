"""Every chat turn of the agent is metered for FinOps (tokens of that turn, the model, the user)."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "agentcore"), str(ROOT / "lambda" / "_shared")]
pytest.importorskip("bedrock_agentcore")
import app  # noqa: E402


def test_meter_records_the_latest_invocation(monkeypatch):
    seen = {}
    monkeypatch.setattr(app, "record_usage", lambda *a, **k: seen.update(args=a, kw=k))
    result = SimpleNamespace(metrics=SimpleNamespace(latest_agent_invocation=SimpleNamespace(usage={"inputTokens": 1200, "outputTokens": 300, "cacheReadInputTokens": 100}),
                                                     accumulated_usage={"inputTokens": 99999, "outputTokens": 99999}))
    app._meter(SimpleNamespace(esg_model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0"), result, "user-1", 850)
    assert seen["args"] == ("agent_chat", "us.anthropic.claude-haiku-4-5-20251001-v1:0", 1200, 300)
    assert seen["kw"]["user"] == "user-1" and seen["kw"]["cached_in"] == 100 and seen["kw"]["source"] == "agent"


def test_meter_never_raises(monkeypatch):
    monkeypatch.setattr(app, "record_usage", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ddb down")))
    app._meter(SimpleNamespace(), SimpleNamespace(metrics=None), "", 0)  # must not raise


def test_start_mode_passes_the_report_builder_options(monkeypatch):
    seen = {}
    monkeypatch.setattr(app.service, "start", lambda *a, **k: seen.update(a=a, k=k) or {"started": True})
    out = app.invoke({"mode": "start", "pipeline": "esg_report", "reporting_year": 2024, "framework": "OJK_PSPK", "language": "id", "sections": ["scope1"]})
    assert out == {"started": True} and seen["a"][:3] == ("esg_report", 2024, "OJK_PSPK")
    assert seen["k"] == {"language": "id", "sections": ["scope1"]}


def test_agents_are_separate_per_user_and_memory_is_optional(monkeypatch):
    built = []
    import orchestrator.agent as agent_mod
    monkeypatch.setattr(agent_mod, "build_agent", lambda service, session_manager=None: built.append(session_manager) or object())
    monkeypatch.setattr(app, "MEMORY_ID", "")
    a1 = app._agent_for("s" * 40, "user-a")
    a2 = app._agent_for("s" * 40, "user-b")
    assert a1 is not a2 and app._agent_for("s" * 40, "user-a") is a1 and built == [None, None]
