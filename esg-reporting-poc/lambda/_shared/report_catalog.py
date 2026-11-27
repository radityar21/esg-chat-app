"""Single source of truth for report structure: which sections each framework has, which template file each section
uses, and what the user sees about it in the Report Builder.

Used by the section generator (template file), the AgentCore planner (sections per framework) and the platform API
(Report Builder). Template files live in the repository under templates/ and are uploaded to
s3://esg-kb-documents-<account>/prompts/templates/ (scripts/upload_kb_documents.py). Versions edited in the Report
Builder are published to the same key.
"""

from __future__ import annotations

from typing import Any

LANGUAGES = {"en": "English", "id": "Bahasa Indonesia"}
DEFAULT_LANGUAGE = "en"

# template key -> file under prompts/templates/, label, description
SECTIONS: dict[str, dict[str, str]] = {
    "summary": {"file": "section_summary.txt", "label": "Executive summary", "desc": "Headline GHG figures and the year's key messages."},
    "governance": {"file": "section_governance.txt", "label": "Climate governance", "desc": "Board and management oversight of climate risks."},
    "targets": {"file": "section_targets.txt", "label": "Strategy and targets", "desc": "Targets, transition plan and progress."},
    "scope1": {"file": "section_scope1.txt", "label": "Scope 1 emissions", "desc": "Direct emissions from fuel use (natural gas, diesel)."},
    "scope2": {"file": "section_scope2.txt", "label": "Scope 2 emissions", "desc": "Purchased electricity, location- and market-based."},
    "scope3_pcaf": {"file": "section_scope3_pcaf.txt", "label": "Scope 3 financed emissions (PCAF)", "desc": "Category 15 by sector with PCAF data quality."},
    "intensity": {"file": "section_intensity.txt", "label": "Emission intensity", "desc": "Emissions per revenue and per employee."},
    "reduction": {"file": "section_reduction.txt", "label": "Emission reduction", "desc": "Change versus prior and base year, initiatives."},
    "social": {"file": "section_social.txt", "label": "Workforce (social)", "desc": "Headcount, diversity, training, turnover."},
    "double_materiality": {"file": "section_double_materiality.txt", "label": "Double materiality", "desc": "Impact and financial materiality (CSRD)."},
    "scope1_unified": {"file": "section_unified_scope1.txt", "label": "Scope 1 emissions", "desc": "Direct emissions, all four frameworks in one section."},
    "scope2_unified": {"file": "section_unified_scope2.txt", "label": "Scope 2 emissions", "desc": "Purchased electricity, all frameworks."},
    "scope3_pcaf_unified": {"file": "section_unified_scope3_pcaf.txt", "label": "Scope 3 financed emissions (PCAF)", "desc": "Category 15, all frameworks."},
    "intensity_unified": {"file": "section_unified_intensity.txt", "label": "Emission intensity", "desc": "Intensity ratios, all frameworks."},
    "reduction_unified": {"file": "section_unified_reduction.txt", "label": "Emission reduction", "desc": "Reduction versus prior and base year."},
    "social_unified": {"file": "section_unified_social.txt", "label": "Workforce (social)", "desc": "Workforce metrics, all frameworks."},
    "governance_unified": {"file": "section_unified_governance.txt", "label": "Climate governance", "desc": "Governance, all frameworks."},
    "targets_unified": {"file": "section_unified_targets.txt", "label": "Strategy and targets", "desc": "Targets and transition plan."},
    "scenario_unified": {"file": "section_unified_scenario.txt", "label": "Climate scenario analysis", "desc": "1.5°C / 2°C / 3°C+ financial effects."},
}

FRAMEWORKS: dict[str, dict[str, Any]] = {
    "GRI_305": {"label": "GRI 305 Emissions", "sections": ["summary", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social"]},
    "IFRS_S2": {"label": "IFRS S2 Climate-related Disclosures", "sections": ["summary", "governance", "scope1", "scope2", "scope3_pcaf", "intensity", "targets", "social"]},
    "CSRD_ESRS_E1": {"label": "CSRD · ESRS E1 Climate Change", "sections": ["summary", "governance", "targets", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social"]},
    "OJK_PSPK": {"label": "OJK PSPK (POJK 51/2017)", "sections": ["summary", "governance", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social"]},
    "MULTI_FRAMEWORK": {"label": "All four frameworks (unified)", "sections": [
        "scope1_unified", "scope2_unified", "scope3_pcaf_unified", "intensity_unified", "reduction_unified", "social_unified",
        "governance_unified", "targets_unified", "scenario_unified", "summary"]},
}


def template_framework(framework: str, template_id: str) -> str:
    """Framework tag the section generator expects for a template (the summary is framework-neutral)."""
    return "NONE" if template_id == "summary" and framework in ("GRI_305", "MULTI_FRAMEWORK") else framework


def section_templates(framework: str, sections: list[str] | None = None, language: str = DEFAULT_LANGUAGE) -> list[dict[str, str]]:
    """Step Functions section list for a framework, optionally restricted to a subset. Raises ValueError on bad input."""
    if framework not in FRAMEWORKS:
        raise ValueError(f"Unknown framework {framework!r}. Choose one of {list(FRAMEWORKS)}.")
    if language not in LANGUAGES:
        raise ValueError(f"Unknown language {language!r}. Choose one of {list(LANGUAGES)}.")
    allowed = FRAMEWORKS[framework]["sections"]
    chosen = allowed if not sections else [s for s in allowed if s in set(sections)]  # the document order is fixed by the framework
    unknown = [s for s in (sections or []) if s not in allowed]
    if unknown:
        raise ValueError(f"Section(s) {unknown} are not part of {framework}. Available: {allowed}")
    if not chosen:
        raise ValueError("Choose at least one section.")
    return [{"template_id": t, "framework": template_framework(framework, t), "language": language} for t in chosen]


def template_file(template_key: str) -> str:
    return SECTIONS[template_key]["file"]
