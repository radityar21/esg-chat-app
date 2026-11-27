"""Smart model routing + cost model (shared by section_gen, platform_api and the AgentCore orchestrator).

Profiles:
    quality   (default) section narratives use Sonnet, exactly as before this module existed.
    balanced  simple, table-heavy sections go to Haiku; narrative-heavy ones stay on Sonnet.
    economy   everything except the corrector and the executive summary goes to Haiku.

The profile is read from the env var ``MODEL_ROUTING_PROFILE``. Unknown values fall back to ``quality``.
Prices are USD per 1M tokens (list price, used for estimates only; verify before external quoting).
"""

from __future__ import annotations

import os
from typing import Any

MODELS: dict[str, dict[str, Any]] = {
    "sonnet": {
        "id": os.environ.get("SONNET_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
        "label": "Claude Sonnet 4.5",
        "in": 3.0,
        "out": 15.0,
    },
    "haiku": {
        "id": os.environ.get("HAIKU_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),
        "label": "Claude Haiku 4.5",
        "in": 1.0,
        "out": 5.0,
    },
}

CACHE_READ_DISCOUNT = 0.10  # cached input tokens are billed at 10% of the input price

# task -> alias, per profile
PROFILES: dict[str, dict[str, str]] = {
    "quality": {
        "section_complex": "sonnet", "section_simple": "sonnet", "executive_summary": "sonnet",
        "corrector": "sonnet", "agent_planner": "haiku", "agent_explainer": "sonnet",
        "reg_classifier": "haiku", "chat_qa": "haiku",
    },
    "balanced": {
        "section_complex": "sonnet", "section_simple": "haiku", "executive_summary": "sonnet",
        "corrector": "sonnet", "agent_planner": "haiku", "agent_explainer": "haiku",
        "reg_classifier": "haiku", "chat_qa": "haiku",
    },
    "economy": {
        "section_complex": "haiku", "section_simple": "haiku", "executive_summary": "sonnet",
        "corrector": "sonnet", "agent_planner": "haiku", "agent_explainer": "haiku",
        "reg_classifier": "haiku", "chat_qa": "haiku",
    },
}

# section template key -> task class
SECTION_TASK: dict[str, str] = {
    "summary": "executive_summary",
    "scope1": "section_simple", "scope2": "section_simple", "intensity": "section_simple", "social": "section_simple",
    "scope3_pcaf": "section_complex", "reduction": "section_complex", "governance": "section_complex",
    "targets": "section_complex", "double_materiality": "section_complex", "scenario": "section_complex",
}


def active_profile() -> str:
    p = os.environ.get("MODEL_ROUTING_PROFILE", "quality").lower()
    return p if p in PROFILES else "quality"


def task_for_section(template_key: str) -> str:
    base = template_key[:-8] if template_key.endswith("_unified") else template_key
    return SECTION_TASK.get(base, "section_complex")


def resolve(task: str, profile: str | None = None) -> tuple[str, str]:
    """Return (alias, bedrock_model_id) for a task."""
    prof = PROFILES.get(profile or active_profile(), PROFILES["quality"])
    alias = prof.get(task, "sonnet")
    return alias, MODELS[alias]["id"]


def alias_for_model_id(model_id: str) -> str:
    for alias, m in MODELS.items():
        if m["id"] == model_id:
            return alias
    return "haiku" if "haiku" in model_id else "sonnet"


def cost_usd(alias: str, tokens_in: int, tokens_out: int, cached_in: int = 0) -> float:
    m = MODELS[alias]
    fresh_in = max(0, tokens_in - cached_in)
    return (fresh_in * m["in"] + cached_in * m["in"] * CACHE_READ_DISCOUNT + tokens_out * m["out"]) / 1_000_000
