"""Pipeline registry and request planner.

The orchestrator can trigger more than one inner Step Functions pipeline:

    esg_report     -> ESGReportGenerationStateMachine (parallel section generation, validation, DOCX assembly)
    ghg_inventory  -> GHG inventory state machine      (Glue ETL, aggregation, inventory build)

``plan_request`` is a deterministic intent classifier. The LLM agent calls it as a tool so that routing is
reproducible and unit-tested, and so a missing parameter is asked for explicitly instead of guessed.
"""

from __future__ import annotations

import re
from typing import Any

from .config import Settings

FRAMEWORKS = ("GRI_305", "IFRS_S2", "CSRD_ESRS_E1", "OJK_PSPK", "MULTI_FRAMEWORK")

SECTION_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "GRI_305": [{"template_id": t, "framework": "NONE" if t == "summary" else "GRI_305"} for t in
                ("summary", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social")],
    "IFRS_S2": [{"template_id": t, "framework": "IFRS_S2"} for t in
                ("summary", "governance", "scope1", "scope2", "scope3_pcaf", "intensity", "targets", "social")],
    "CSRD_ESRS_E1": [{"template_id": t, "framework": "CSRD_ESRS_E1"} for t in
                     ("summary", "governance", "targets", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social")],
    "OJK_PSPK": [{"template_id": t, "framework": "OJK_PSPK"} for t in
                 ("summary", "governance", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social")],
    "MULTI_FRAMEWORK": [
        *[{"template_id": f"{t}_unified", "framework": "MULTI_FRAMEWORK"} for t in
          ("scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social", "governance", "targets", "scenario")],
        {"template_id": "summary", "framework": "NONE"},
    ],
}

PIPELINES: dict[str, dict[str, Any]] = {
    "esg_report": {
        "title": "ESG report generation",
        "description": "Generates a validated DOCX sustainability report for one framework or all four (multi-framework).",
        "eta_minutes": {"single": "10-20", "multi": "20-40"},
        "params": ["reporting_year", "framework", "revenue_idr_billion"],
    },
    "ghg_inventory": {
        "title": "GHG inventory (GHG Protocol template)",
        "description": "Runs Scope 1/2/3 ETL and builds the inventory structured as GHG Protocol Parts 1-6.",
        "eta_minutes": {"single": "5-10", "multi": "5-10"},
        "params": ["reporting_year"],
    },
}


def section_name_to_id(framework_of_template: str, template_id: str, year: int) -> str:
    """Full section id as written by SectionGenFn: ``{framework}_{TEMPLATE_ID}_{year}``."""
    return f"{framework_of_template}_{template_id.upper()}_{year}"


# ── Planner ─────────────────────────────────────────────────────────────────────────────────────
_FW_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("MULTI_FRAMEWORK", re.compile(r"\b(semua|all|multi|seluruh|unified|gabungan)\b.*\b(frameworks?|kerangka|standar|standards?)\b|\bmulti[-_ ]?framework\b", re.I)),
    ("GRI_305", re.compile(r"\bgri\b", re.I)),
    ("IFRS_S2", re.compile(r"\bifrs\b|\bissb\b", re.I)),
    ("CSRD_ESRS_E1", re.compile(r"\bcsrd\b|\besrs\b", re.I)),
    ("OJK_PSPK", re.compile(r"\bojk\b|\bpspk\b", re.I)),
]
_GHG_RE = re.compile(r"\binventory\b|\binventaris\b|\binventori\b|\bghg protocol\b|\bscope ?3 template\b", re.I)
_REPORT_RE = re.compile(r"\b(report|laporan|generate|buat|bikin|susun|docx|dokumen)\b", re.I)
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_REVENUE_RE = re.compile(r"(?:revenue|pendapatan)[^\d]{0,20}([\d][\d.,]*)", re.I)


def plan_request(text: str, settings: Settings) -> dict[str, Any]:
    """Classify a user request into a pipeline plus the parameters still missing."""
    t = text or ""
    year_m = _YEAR_RE.search(t)
    year = int(year_m.group(1)) if year_m else None

    frameworks = [fw for fw, rx in _FW_PATTERNS if rx.search(t)]
    framework = None
    if "MULTI_FRAMEWORK" in frameworks or len(set(frameworks)) > 1:
        framework = "MULTI_FRAMEWORK"
    elif frameworks:
        framework = frameworks[0]

    # An explicit framework (or "report") means a full report; inventory wording alone means the GHG inventory pipeline.
    if framework:
        pipeline = "esg_report"
    elif _GHG_RE.search(t):
        pipeline = "ghg_inventory"
    elif _REPORT_RE.search(t):
        pipeline = "esg_report"
    else:
        pipeline = None

    revenue = None
    rm = _REVENUE_RE.search(t)
    if rm:
        try:
            revenue = float(rm.group(1).replace(",", ""))
        except ValueError:
            revenue = None

    params: dict[str, Any] = {}
    if year:
        params["reporting_year"] = year
    if pipeline == "esg_report":
        if framework:
            params["framework"] = framework
        if revenue:
            params["revenue_idr_billion"] = revenue

    missing: list[str] = []
    problems: list[str] = []
    if pipeline:
        required = PIPELINES[pipeline]["params"]
        for p in required:
            if p == "revenue_idr_billion":
                continue  # has a default; we only confirm it
            if p not in params:
                missing.append(p)
        if year and year not in settings.available_years:
            problems.append(f"Data is only available for {', '.join(map(str, settings.available_years))}.")
            missing = [m for m in missing if m != "reporting_year"] + ["reporting_year"]
            params.pop("reporting_year", None)
    return {
        "pipeline": pipeline,
        "parameters": params,
        "missing": missing,
        "problems": problems,
        "defaults": {"revenue_idr_billion": 92000.0} if pipeline == "esg_report" else {},
        "ready": bool(pipeline) and not missing and not problems,
    }


def build_input(pipeline: str, params: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """Validate parameters and build the Step Functions input for the chosen pipeline."""
    year = int(params["reporting_year"])
    if year not in settings.available_years:
        raise ValueError(f"Data not available for {year}. Available: {settings.available_years}")
    if pipeline == "esg_report":
        fw = params.get("framework", "GRI_305")
        if fw not in SECTION_TEMPLATES:
            raise ValueError(f"Unknown framework {fw!r}. Choose one of {FRAMEWORKS}.")
        revenue = float(params.get("revenue_idr_billion") or 92000.0)
        if revenue <= 0:
            raise ValueError("Revenue must be positive (IDR billion).")
        return {
            "reporting_year": year, "framework": fw, "bank_id": settings.bank_id,
            "output_bucket": settings.output_bucket, "revenue_idr_billion": revenue,
            "kb_id": settings.kb_id, "section_templates": SECTION_TEMPLATES[fw],
        }
    if pipeline == "ghg_inventory":
        return {"reporting_year": year, "bank_id": settings.bank_id}
    raise ValueError(f"Unknown pipeline {pipeline!r}")


def state_machine_for(pipeline: str, settings: Settings) -> str:
    arn = settings.report_state_machine_arn if pipeline == "esg_report" else settings.ghg_state_machine_arn
    if not arn:
        raise RuntimeError(f"State machine for pipeline {pipeline!r} is not configured (set GHG_STATE_MACHINE_ARN).")
    return arn
