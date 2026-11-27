"""esg-platform-api Lambda (handler: platform_api.handler.lambda_handler): one entry point for the HTTP API, direct
invocations (AgentCore tools, Step Functions, its own async worker) and EventBridge schedules.

HTTP routes (API Gateway HTTP API, payload v2, Cognito JWT authorizer on every route except /health):
    GET  /compliance/readiness?year=         GET  /compliance/alerts
    POST /compliance/attest   [admin]        POST /compliance/scan [admin]      GET  /ghg/inventory?year=
    GET  /portfolio?year=                    POST /scenario                     POST /governance/pii-mask
    GET  /governance/finops?days=            POST /agent/chat                   GET  /agent/chat/{job_id}
    GET  /agent/runs                         GET  /agent/runs/{id}              GET  /health
    GET  /reports/history?limit=             GET  /reference/documents          GET  /agent/runs/{id}/progress
    GET  /reports/catalog                    GET  /reports/configs              POST /reports/configs [admin]
    POST /reports/configs/{id}/delete [admin] POST /reports/generate
    GET  /reports/templates/{key}            POST /reports/templates/{key}/draft [admin]   POST /reports/templates/{key}/publish [admin]
    POST /compliance/alerts/status [admin]   GET  /agent/conversations          GET  /agent/conversations/{id}
    POST /agent/conversations/{id}/delete
    GET  /data/overview?year=&approach=&ef_set=        GET  /data/ledger?year=&approach=control|equity&ef_set=&entity=
    GET  /data/facilities?year=&entity=                GET  /data/facility?year=&facility_id=&ef_set=
    GET  /data/metrics?year=   GET  /data/alerts?year=   GET  /data/factors?year=
Roles come from the ``cognito:groups`` claim: ``admin`` and ``viewer``. A user in neither group is rejected.
Direct invocations are protected by IAM only.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Callable

from platform_api import agent_api, common, compliance, conversations, datahub, ghg, governance, portfolio, progress, report_builder, reports

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
    "report_catalog": report_builder.get_catalog,
    "report_configs": report_builder.list_configs,
    "report_generate": agent_api.start_submit,
    # direct invocations used by the AgentCore agent
    "report_config_get": lambda p: report_builder.get_config(str(p.get("config_id", ""))),
    "template_get": lambda p: report_builder.get_template(str(p.get("template_key", ""))),
    "template_propose": lambda p: report_builder.save_draft(str(p.get("template_key", "")), str(p.get("text", "")),
                                                            f"AI proposal: {str(p.get('reason', ''))[:400]}", "agent"),
    "alert_context": lambda p: compliance.alert_context(str(p.get("alert_id", "")), int(p.get("year") or 2024)),
    "data_query": datahub.agent_query,
    # ESG Data Hub and GHG accounting
    "data_overview": datahub.overview,
    "data_ledger": datahub.ledger,
    "data_facilities": datahub.facilities,
    "data_facility": datahub.facility_detail,
    "data_metrics": datahub.metrics,
    "data_alerts": datahub.alerts,
    "data_factors": datahub.factors,
}

ROUTES: dict[tuple[str, str], str] = {
    ("GET", "/compliance/readiness"): "compliance_readiness", ("GET", "/compliance/alerts"): "regulatory_alerts",
    ("POST", "/compliance/attest"): "compliance_attest", ("POST", "/compliance/scan"): "regulatory_scan_start",
    ("GET", "/ghg/inventory"): "ghg_inventory", ("GET", "/portfolio"): "portfolio", ("POST", "/scenario"): "scenario",
    ("POST", "/governance/pii-mask"): "pii_mask", ("GET", "/governance/finops"): "finops_summary",
    ("POST", "/agent/chat"): "agent_chat", ("GET", "/agent/runs"): "agent_runs",
    ("GET", "/reports/history"): "reports_history", ("GET", "/reference/documents"): "reference_documents",
    ("GET", "/reports/catalog"): "report_catalog", ("GET", "/reports/configs"): "report_configs", ("POST", "/reports/generate"): "report_generate",
    ("GET", "/data/overview"): "data_overview", ("GET", "/data/ledger"): "data_ledger", ("GET", "/data/facilities"): "data_facilities",
    ("GET", "/data/facility"): "data_facility", ("GET", "/data/metrics"): "data_metrics", ("GET", "/data/alerts"): "data_alerts",
    ("GET", "/data/factors"): "data_factors",
}
AGENT_ONLY = {"report_config_get", "template_get", "template_propose", "alert_context", "data_query"}  # agent-only actions are not routed
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
        dyn = _dynamic(method, path, params, user, is_admin)
        if dyn is not None:
            return dyn
        if method == "GET" and path.startswith("/agent/runs/") and path.endswith("/progress"):
            return common.response(200, progress.progress(path.split("/")[3]))
        if method == "GET" and path.startswith("/agent/runs/"):
            return common.response(200, agent_api.run_detail(path.rsplit("/", 1)[1]))
        if method == "GET" and path.startswith("/agent/chat/"):
            return common.response(200, agent_api.chat_status(path.rsplit("/", 1)[1], user, is_admin))
        action = ROUTES.get((method, path))
        if action in AGENT_ONLY:
            action = None
        if not action:
            return common.response(404, {"error": f"no route for {method} {path}"})
        if action in ADMIN_ONLY and not is_admin:
            return common.response(403, {"error": "administrator role required"})
        if action in ("agent_chat", "report_generate"):
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


def _dynamic(method: str, path: str, params: dict[str, Any], user: str, is_admin: bool) -> dict[str, Any] | None:
    """Routes with an id in the path. Returns None when the path is not one of them."""
    parts = path.strip("/").split("/")

    def admin_only() -> dict[str, Any] | None:
        return None if is_admin else common.response(403, {"error": "administrator role required"})

    if parts[:2] == ["reports", "templates"] and len(parts) >= 3:
        key = parts[2]
        if method == "GET" and len(parts) == 3:
            return common.response(200, report_builder.get_template(key))
        if method == "POST" and len(parts) == 4 and parts[3] in ("draft", "publish"):
            denied = admin_only()
            if denied:
                return denied
            if parts[3] == "draft":
                return common.response(200, report_builder.save_draft(key, params.get("text", ""), params.get("note", ""), user))
            return common.response(200, report_builder.publish(key, str(params.get("version", "")), user))
    if parts[:2] == ["reports", "configs"]:
        if method == "POST" and len(parts) == 2:
            return admin_only() or common.response(200, report_builder.save_config(params, user))
        if method == "POST" and len(parts) == 4 and parts[3] == "delete":
            return admin_only() or common.response(200, report_builder.delete_config(parts[2]))
    if parts[:3] == ["compliance", "alerts", "status"] and method == "POST":
        return admin_only() or common.response(200, compliance.set_alert_status(params, user))
    if parts[:2] == ["agent", "conversations"]:
        if method == "GET" and len(parts) == 2:
            return common.response(200, conversations.list_conversations(user))
        if method == "GET" and len(parts) == 3:
            return common.response(200, conversations.get_conversation(user, parts[2]))
        if method == "POST" and len(parts) == 4 and parts[3] == "delete":
            return common.response(200, conversations.delete_conversation(user, parts[2]))
    return None


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
