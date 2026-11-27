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
