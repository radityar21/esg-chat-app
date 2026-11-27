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
    result = agent(masked)
    text = result.message["content"][0]["text"] if getattr(result, "message", None) else str(result)
    return {"response": text, "session_id": session_id, "pii_masked": len(findings)}


if __name__ == "__main__":
    app.run()
