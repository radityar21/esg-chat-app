"""ToolService: every action the orchestrator agent can take, as plain, JSON-in/JSON-out Python.

The Strands ``@tool`` wrappers in ``tools.py`` are one-liners over these methods, so behaviour is unit-testable
without an LLM or the Strands SDK.
"""

from __future__ import annotations

import functools
import logging
import threading
from typing import Any, Callable

from .aws import AwsGateway, short_id
from .config import Settings
from .diagnose import diagnose
from .healer import SelfHealingSupervisor
from .ledger import Ledger
from .pipelines import FRAMEWORKS, PIPELINES, plan_request
from .rules import classify


log = logging.getLogger(__name__)


def _safe(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    """Tools must never raise into the LLM loop: return a structured error it can explain instead."""

    @functools.wraps(fn)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return fn(self, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s failed: %s", fn.__name__, exc)
            return {"error": f"{fn.__name__} failed: {str(exc)[:300]}"}

    return wrapper


class BackgroundRunner:
    """Runs supervision off the request thread. Inside AgentCore Runtime the task is registered with the app so the
    session reports HealthyBusy (and is not reclaimed) until the work finishes."""

    def __init__(self, app: Any | None = None) -> None:
        self.app = app
        self.active: dict[str, threading.Thread] = {}

    def submit(self, name: str, fn: Callable[[], Any]) -> bool:
        if name in self.active and self.active[name].is_alive():
            return False
        task_id = self.app.add_async_task(name, {"name": name}) if self.app is not None else None

        def run() -> None:
            try:
                fn()
            finally:
                if self.app is not None and task_id is not None:
                    self.app.complete_async_task(task_id)

        t = threading.Thread(target=run, name=name, daemon=True)
        self.active[name] = t
        t.start()
        return True


class ToolService:
    def __init__(self, aws: AwsGateway, settings: Settings, runner: BackgroundRunner | None = None,
                 supervisor: SelfHealingSupervisor | None = None) -> None:
        self.aws = aws
        self.s = settings
        self.supervisor = supervisor or SelfHealingSupervisor(aws, settings)
        self.ledger = Ledger(aws, settings)
        self.runner = runner or BackgroundRunner()

    # ── discovery / planning ───────────────────────────────────────────────────────────────────
    def capabilities(self) -> dict[str, Any]:
        return {"pipelines": PIPELINES, "frameworks": list(FRAMEWORKS), "available_years": list(self.s.available_years),
                "self_correction": {"max_attempts_per_section": self.s.max_correction_attempts, "max_pipeline_restarts": self.s.max_restarts},
                "notes": "Reports are validated against 21 rules; failing sections are regenerated automatically with a corrective prompt."}

    def plan(self, request: str) -> dict[str, Any]:
        return plan_request(request, self.s)

    # ── run control ────────────────────────────────────────────────────────────────────────────
    def start(self, pipeline: str, reporting_year: int, framework: str | None = None, revenue_idr_billion: float | None = None,
              subsidiary: str = "bank", auto_heal: bool = True, tables: list[str] | None = None, run_etl: bool = True,
              language: str | None = None, sections: list[str] | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"reporting_year": reporting_year}
        if language:
            params["language"] = language
        if sections:
            params["sections"] = list(sections)
        if pipeline == "data_sync":
            params["tables"] = tables or None
            params["run_etl"] = run_etl
        if framework:
            params["framework"] = framework
        if revenue_idr_billion:
            params["revenue_idr_billion"] = revenue_idr_billion
        try:
            started = self.supervisor.start(pipeline, params, subsidiary=subsidiary, auto_heal=auto_heal)
        except (ValueError, RuntimeError) as exc:
            return {"started": False, "error": str(exc)}
        eta = PIPELINES[pipeline]["eta_minutes"]["multi" if framework == "MULTI_FRAMEWORK" else "single"]
        # begin supervising in the background immediately: it waits for the run, then repairs failed sections
        if auto_heal:
            self.runner.submit(f"supervise-{started['execution_id']}", lambda: self.supervisor.supervise(started["execution_arn"]))
        return {"started": True, **started, "eta_minutes": eta,
                "message": f"Execution ID: {started['execution_id']}. Estimated {eta} minutes. Self-correction is "
                           f"{'on' if auto_heal else 'off'}."}

    def status(self, execution_id: str) -> dict[str, Any]:
        try:
            return self.supervisor.status(execution_id)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Could not read execution {execution_id}: {exc}"}

    @_safe
    def supervise(self, execution_id: str, wait: bool = False) -> dict[str, Any]:
        arn = self.supervisor._arn(execution_id)
        if wait:
            return self.supervisor.supervise(arn)
        ok = self.runner.submit(f"supervise-{short_id(arn)}", lambda: self.supervisor.supervise(arn))
        return {"accepted": ok, "execution_id": short_id(arn), "message": "Supervision started in the background." if ok else "Already being supervised."}

    # ── explanation ────────────────────────────────────────────────────────────────────────────
    @_safe
    def explain(self, execution_id: str) -> dict[str, Any]:
        """Structured facts the agent turns into a plain-language explanation of what happened and why."""
        arn = self.supervisor._arn(execution_id)
        doc = self.ledger.load(arn)
        d = self.aws.sfn_describe(arn)
        out: dict[str, Any] = {"execution_id": short_id(arn), "sfn_status": d["status"], "agent_status": doc["status"],
                               "timeline": [{"ts": e["ts"], "message": e["message"]} for e in doc["events"][-25:]]}
        if d["status"] in ("FAILED", "TIMED_OUT", "ABORTED"):
            out["diagnosis"] = doc.get("diagnosis") or diagnose(d, self.aws.sfn_history(arn))
        sections = {}
        for tid, st in (doc.get("sections") or {}).items():
            if st.get("status") not in ("ok", None):
                sections[tid] = st
        if sections:
            out["sections"] = sections
        res = doc.get("result") or {}
        if res.get("unresolved"):
            out["needs_human"] = res["unresolved"]
        if res.get("healed"):
            out["auto_repaired"] = res["healed"]
        if res.get("notes"):
            out["review_notes"] = res["notes"]  # plain-language notes also shown in the UI
        if doc.get("budget"):
            out["repair_budget"] = doc["budget"]
        return out

    @_safe
    def download(self, execution_id: str) -> dict[str, Any]:
        doc = self.ledger.load(self.supervisor._arn(execution_id))
        res = doc.get("result") or {}
        if res.get("download_url"):
            return {"ready": True, "download_url": res["download_url"], "download_url_pptx": res.get("download_url_pptx"),
                    "healed_sections": res.get("healed", []), "note": "Link is valid for 1 hour."}
        d = self.aws.sfn_describe(self.supervisor._arn(execution_id))
        if d["status"] == "SUCCEEDED":  # auto-heal was off or has not finished yet: fall back to the engine's own output
            info = self.supervisor._download_info((d.get("output") or {}).get("assembly_result"))
            if info:
                return {"ready": True, **info, "note": "Report as generated by Step Functions (self-correction not applied)."}
        return {"ready": False, "sfn_status": d["status"], "agent_status": doc["status"]}

    # ── source database tools (read-only Lambda in the VPC) ─────────────────────────────────────
    def data_tool(self, action: str, **params: Any) -> dict[str, Any]:
        try:
            return self.aws.lambda_invoke(self.s.data_tools_function, {"action": action, **params})
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Data tool {action!r} failed: {str(exc)[:300]}"}

    # ── platform capabilities (Lambda) ─────────────────────────────────────────────────────────
    def platform(self, action: str, **params: Any) -> dict[str, Any]:
        try:
            return self.aws.lambda_invoke(self.s.platform_function, {"action": action, **params})
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Platform action {action!r} failed: {str(exc)[:300]}"}

    @staticmethod
    def validation_digest(validation: dict[str, Any] | None) -> dict[str, Any]:
        """Used by the API layer to render a per-section validation summary."""
        c = classify(validation)
        return {"needs_repair": c["needs_repair"], "data_issues": [e.get("rule") for e in c["data_issues"]],
                "fixable": [e.get("rule") for e in c["fixable"]], "explanations": c["explanations"]}
