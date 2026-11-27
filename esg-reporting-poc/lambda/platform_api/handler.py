"""esg-platform-api Lambda (handler: platform_api.handler.lambda_handler): one entry point for the HTTP API, direct
invocations (AgentCore tools, Step Functions, its own async worker) and EventBridge schedules.

HTTP routes (API Gateway HTTP API, payload v2, Cognito JWT authorizer on every route except /health):
    GET  /compliance/readiness?year=         GET  /compliance/alerts
    POST /compliance/attest   [admin]        POST /compliance/scan [admin]      GET  /ghg/inventory?year=
    GET  /portfolio?year=                    POST /scenario                     POST /governance/pii-mask
    GET  /governance/finops?days=            POST /agent/chat                   GET  /agent/chat/{job_id}
    GET  /agent/runs                         GET  /agent/runs/{id}              GET  /health
    GET  /reports/history?limit=             GET  /reference/documents
Roles come from the ``cognito:groups`` claim: ``admin`` and ``viewer``. A user in neither group is rejected.
Direct invocations are protected by IAM only.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Callable

from platform_api import agent_api, common, compliance, ghg, governance, portfolio, reports

log = logging.getLogger()
log.setLevel(logging.INFO)

ACTIONS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "compliance_readiness": lambda p: compliance.readiness(common.year_param(p)),
    "regulatory_alerts": lambda p: compliance.alerts(),
    "regulatory_scan": lambda p: compliance.scan(),
    # HTTP callers cannot wait for a scan (API Gateway cuts at 30 s): start it asynchronously, the UI polls /compliance/alerts
    "regulatory_scan_start": lambda p: (agent_api._invoke_self({"action": "regulatory_scan"}), {"started": True})[1],
    "compliance_attest": compliance.attest,
    "ghg_inventory": ghg.handle,
    "ghg_inventory_build": ghg.build_and_store,
    "portfolio": portfolio.overview,
    "scenario": portfolio.scenario,
    "pii_mask": governance.pii_mask,
    "finops_summary": governance.finops_summary,
    "agent_chat": agent_api.chat_submit,
    "agent_chat_worker": agent_api.chat_worker,
    "agent_runs": agent_api.runs,
    "reports_history": reports.history,
    "reference_documents": reports.documents,
}

ROUTES: dict[tuple[str, str], str] = {
    ("GET", "/compliance/readiness"): "compliance_readiness", ("GET", "/compliance/alerts"): "regulatory_alerts",
    ("POST", "/compliance/attest"): "compliance_attest", ("POST", "/compliance/scan"): "regulatory_scan_start",
    ("GET", "/ghg/inventory"): "ghg_inventory", ("GET", "/portfolio"): "portfolio", ("POST", "/scenario"): "scenario",
    ("POST", "/governance/pii-mask"): "pii_mask", ("GET", "/governance/finops"): "finops_summary",
    ("POST", "/agent/chat"): "agent_chat", ("GET", "/agent/runs"): "agent_runs",
    ("GET", "/reports/history"): "reports_history", ("GET", "/reference/documents"): "reference_documents",
}
ADMIN_ONLY = {"compliance_attest", "regulatory_scan_start"}


def _claims(event: dict[str, Any]) -> dict[str, Any]:
    return ((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt", {}).get("claims", {}) or {}


def _roles(claims: dict[str, Any]) -> set[str]:
    raw = claims.get("cognito:groups", "")
    if isinstance(raw, list):
        return {str(x) for x in raw}
    return {g for g in str(raw).strip("[]").replace(",", " ").split() if g}


def _http(event: dict[str, Any]) -> dict[str, Any]:
    ctx = event["requestContext"]["http"]
    method, path = ctx["method"].upper(), ctx["path"].rstrip("/") or "/"
    if method == "OPTIONS":
        return common.response(204, {})
    if path == "/health":
        return common.response(200, {"ok": True})
    claims = _claims(event)
    roles = _roles(claims) & {"admin", "viewer"}
    if not claims.get("sub"):
        return common.response(401, {"error": "authentication required"})
    if not roles:
        return common.response(403, {"error": "your account has no role; ask an administrator to add you to the viewer or admin group"})
    user, is_admin = str(claims["sub"]), "admin" in roles
    try:
        params: dict[str, Any] = dict(event.get("queryStringParameters") or {})
        if event.get("body"):
            body = event["body"]
            if event.get("isBase64Encoded"):
                body = base64.b64decode(body).decode()
            parsed = json.loads(body)
            if not isinstance(parsed, dict):
                raise ValueError("body must be a JSON object")
            params.update(parsed)
        params = {k: v for k, v in params.items() if not str(k).startswith("_")}  # never trust client-supplied internal fields
        if method == "GET" and path.startswith("/agent/runs/"):
            return common.response(200, agent_api.run_detail(path.rsplit("/", 1)[1]))
        if method == "GET" and path.startswith("/agent/chat/"):
            return common.response(200, agent_api.chat_status(path.rsplit("/", 1)[1], user, is_admin))
        action = ROUTES.get((method, path))
        if not action:
            return common.response(404, {"error": f"no route for {method} {path}"})
        if action in ADMIN_ONLY and not is_admin:
            return common.response(403, {"error": "administrator role required"})
        if action == "agent_chat":
            params["_user"] = user
        return common.response(200, ACTIONS[action](params))
    except (ValueError, KeyError) as exc:
        return common.response(400, {"error": str(exc)})
    except common.AthenaError as exc:
        log.warning("athena error: %s", exc)
        return common.response(502, {"error": "data query failed"})
    except LookupError as exc:
        return common.response(404, {"error": str(exc)})
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
