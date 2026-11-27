"""esg-agent-trigger: EventBridge (Step Functions Execution Status Change) -> AgentCore Runtime ``supervise``.

The runtime holds a per-execution lock in S3, so duplicate events are harmless. Only executions of the report
state machine are forwarded (the rule filters too; this is a second guard).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

import boto3

log = logging.getLogger()
log.setLevel(logging.INFO)

RUNTIME_ARN = os.environ.get("AGENTCORE_RUNTIME_ARN", "")
REPORT_SM = os.environ.get("REPORT_STATE_MACHINE_ARN", "")
TERMINAL = {"SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"}
_client = None


def _session_id(execution_id: str) -> str:
    # AgentCore needs >= 33 characters; a stable id means one microVM per execution
    return "sup-" + hashlib.sha256(execution_id.encode()).hexdigest()[:40]


def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    global _client
    d = event.get("detail") or {}
    arn, status, sm = d.get("executionArn", ""), d.get("status", ""), d.get("stateMachineArn", "")
    if status not in TERMINAL or not arn:
        return {"skipped": "not a terminal state"}
    if REPORT_SM and sm != REPORT_SM:
        return {"skipped": "different state machine"}
    if not RUNTIME_ARN:
        raise RuntimeError("AGENTCORE_RUNTIME_ARN is not configured")
    eid = arn.split(":")[-1]
    _client = _client or boto3.client("bedrock-agentcore")
    resp = _client.invoke_agent_runtime(agentRuntimeArn=RUNTIME_ARN, runtimeSessionId=_session_id(eid),
                                        payload=json.dumps({"mode": "supervise", "execution_id": eid}).encode(),
                                        contentType="application/json", accept="application/json")
    body = resp["response"].read().decode("utf-8", "replace")
    log.info("supervise %s (%s) -> %s", eid, status, body[:300])
    return {"execution_id": eid, "sfn_status": status, "runtime_response": body[:500]}
