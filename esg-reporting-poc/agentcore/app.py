"""AgentCore Runtime entrypoint (container, ARM64).

Payload contract (JSON):
    {"mode": "chat",      "prompt": "...", "subsidiary": "bank"}      conversational turn
    {"mode": "supervise", "execution_id": "..."}                      start self-correction for a run (fire and forget)
    {"mode": "status",    "execution_id": "..."}                      status + ledger summary
    {"mode": "ledger",    "execution_id": "..."}                      full agent timeline

Each AgentCore session is its own microVM, so a module-level agent keeps the conversation for that session.
The runtime is kept alive (HealthyBusy) while a background supervision task is running.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
for p in (HERE / "_shared", HERE.parent / "lambda" / "_shared"):  # container layout, then repo layout
    if p.exists():
        sys.path.insert(0, str(p))

from bedrock_agentcore.runtime import BedrockAgentCoreApp, PingStatus  # noqa: E402

from orchestrator import config  # noqa: E402
from orchestrator.aws import RealAws  # noqa: E402
from orchestrator.service import BackgroundRunner, ToolService  # noqa: E402
from pii_guard import mask_text  # noqa: E402
from usage_meter import record as record_usage  # noqa: E402

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("esg-orchestrator")

app = BedrockAgentCoreApp()
settings = config.load()
service = ToolService(RealAws(settings.region), settings, runner=BackgroundRunner(app))
_agents: dict[str, Any] = {}


def _agent_for(session_id: str) -> Any:
    if session_id not in _agents:
        from orchestrator.agent import build_agent  # imported on first chat so supervise-only calls start fast

        _agents[session_id] = build_agent(service)
    return _agents[session_id]


def _meter(agent: Any, result: Any, user: str, latency_ms: int) -> None:
    """Record the tokens of this turn (all model calls the agent made for it) in the FinOps usage table."""
    try:
        inv = result.metrics.latest_agent_invocation
        usage = inv.usage if inv else result.metrics.accumulated_usage
        record_usage("agent_chat", getattr(agent, "esg_model_id", ""), int(usage.get("inputTokens", 0)), int(usage.get("outputTokens", 0)),
                     cached_in=int(usage.get("cacheReadInputTokens", 0) or 0), source="agent", latency_ms=latency_ms, user=user)
    except Exception as exc:  # noqa: BLE001 - metering must never break a chat turn
        log.warning("usage metering failed: %s", exc)


@app.ping
def health() -> PingStatus:
    busy = app.get_async_task_info().get("active_count", 0) > 0
    return PingStatus.HEALTHY_BUSY if busy else PingStatus.HEALTHY


@app.entrypoint
def invoke(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
    mode = payload.get("mode", "chat")
    session_id = getattr(context, "session_id", None) or payload.get("session_id") or "local"

    if mode == "supervise":
        return service.supervise(payload["execution_id"])
    if mode == "status":
        return service.status(payload["execution_id"])
    if mode == "ledger":
        return service.ledger.load(service.supervisor._arn(payload["execution_id"]))
    if mode != "chat":
        return {"error": f"unknown mode {mode!r}"}

    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        return {"error": "prompt is required"}
    masked, findings = mask_text(prompt)  # UU PDP: personal data never reaches the model
    if findings:
        log.warning("masked %d personal-data item(s) in a user message", len(findings))
        masked += "\n\n(Personal data in this message was replaced by tokens before processing.)"
    agent = _agent_for(session_id)
    t0 = time.time()
    result = agent(masked)
    _meter(agent, result, str(payload.get("user") or ""), int((time.time() - t0) * 1000))
    text = result.message["content"][0]["text"] if getattr(result, "message", None) else str(result)
    return {"response": text, "session_id": session_id, "pii_masked": len(findings)}


if __name__ == "__main__":
    app.run()
