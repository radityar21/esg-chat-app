"""esg-platform-api Lambda (handler: platform_api.handler.lambda_handler): one entry point for the HTTP API, direct invocations (AgentCore tools, Step Functions)
and EventBridge schedules.

HTTP routes (API Gateway HTTP API, payload v2):
    GET  /compliance/readiness?year=         GET  /compliance/alerts       POST /compliance/attest
    POST /compliance/scan                    GET  /ghg/inventory?year=     GET  /portfolio?year=
    POST /scenario                           POST /governance/pii-mask     GET  /governance/finops?days=
    POST /agent/chat                         GET  /agent/runs              GET  /agent/runs/{id}
    GET  /health
Direct invocation: {"action": "<name>", ...params}. Optional shared secret: env API_KEY checked against x-api-key
for HTTP calls only (direct invocations are already protected by IAM).
"""

from __future__ import annotations

import hmac
import json
import logging
import os
from typing import Any, Callable

from platform_api import agent_api, common, compliance, ghg, governance, portfolio

log = logging.getLogger()
log.setLevel(logging.INFO)

ACTIONS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "compliance_readiness": lambda p: compliance.readiness(common.year_param(p)),
    "regulatory_alerts": lambda p: compliance.alerts(),
    "regulatory_scan": lambda p: compliance.scan(),
    "compliance_attest": compliance.attest,
    "ghg_inventory": ghg.handle,
    "ghg_inventory_build": ghg.build_and_store,
    "portfolio": portfolio.overview,
    "scenario": portfolio.scenario,
    "pii_mask": governance.pii_mask,
    "finops_summary": governance.finops_summary,
    "agent_chat": agent_api.chat,
    "agent_runs": agent_api.runs,
}

ROUTES: dict[tuple[str, str], str] = {
    ("GET", "/compliance/readiness"): "compliance_readiness", ("GET", "/compliance/alerts"): "regulatory_alerts",
    ("POST", "/compliance/attest"): "compliance_attest", ("POST", "/compliance/scan"): "regulatory_scan",
    ("GET", "/ghg/inventory"): "ghg_inventory", ("GET", "/portfolio"): "portfolio", ("POST", "/scenario"): "scenario",
    ("POST", "/governance/pii-mask"): "pii_mask", ("GET", "/governance/finops"): "finops_summary",
    ("POST", "/agent/chat"): "agent_chat", ("GET", "/agent/runs"): "agent_runs",
}


def _authorized(headers: dict[str, str]) -> bool:
    key = os.environ.get("API_KEY", "")
    if not key:
        return True
    given = {k.lower(): v for k, v in (headers or {}).items()}.get("x-api-key", "")
    return hmac.compare_digest(given.encode(), key.encode())


def _http(event: dict[str, Any]) -> dict[str, Any]:
    ctx = event["requestContext"]["http"]
    method, path = ctx["method"].upper(), ctx["path"].rstrip("/") or "/"
    if method == "OPTIONS":
        return common.response(204, {})
    if path == "/health":
        return common.response(200, {"ok": True})
    if not _authorized(event.get("headers")):
        return common.response(401, {"error": "invalid or missing x-api-key"})
    try:
        params: dict[str, Any] = dict(event.get("queryStringParameters") or {})
        if event.get("body"):
            body = event["body"]
            if event.get("isBase64Encoded"):
                import base64

                body = base64.b64decode(body).decode()
            params.update(json.loads(body))
        if method == "GET" and path.startswith("/agent/runs/"):
            return common.response(200, agent_api.run_detail(path.rsplit("/", 1)[1]))
        action = ROUTES.get((method, path))
        if not action:
            return common.response(404, {"error": f"no route for {method} {path}"})
        return common.response(200, ACTIONS[action](params))
    except (ValueError, KeyError) as exc:
        return common.response(400, {"error": str(exc)})
    except common.AthenaError as exc:
        log.warning("athena error: %s", exc)
        return common.response(502, {"error": f"data query failed: {exc}"})
    except Exception:  # noqa: BLE001
        log.exception("unhandled error")
        return common.response(500, {"error": "internal error"})


def lambda_handler(event: dict[str, Any], context: Any = None) -> Any:
    if "requestContext" in event and "http" in event.get("requestContext", {}):
        return _http(event)
    if event.get("source") == "aws.events" and event.get("detail-type") == "Scheduled Event":
        return ACTIONS["regulatory_scan"]({})
    action = event.get("action")
    if action not in ACTIONS:
        return {"error": f"unknown action {action!r}", "actions": sorted(ACTIONS)}
    try:
        return ACTIONS[action]({k: v for k, v in event.items() if k != "action"})
    except Exception as exc:  # noqa: BLE001 - the AgentCore tool layer expects an error object, not a Lambda failure
        if event.get("_raise"):
            raise
        log.exception("action %s failed", action)
        return {"error": f"{action} failed: {str(exc)[:300]}"}
