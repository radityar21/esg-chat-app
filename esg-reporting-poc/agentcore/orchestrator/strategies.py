"""Adaptive choice of the next correction strategy for a section that failed validation.

Why a policy and not a fixed retry count:
  * each failure type (structure, numbers, language) is fixed best by a different approach;
  * a cheap model fixes format problems at a fraction of the cost, a strong model is needed for numeric grounding;
  * what worked in earlier runs is remembered (success counts per failure type and strategy) and shifts the order;
  * the loop stops on a money budget or when nothing untried is left, not after a magic number of attempts.

The validator stays the judge. A strategy only changes HOW the next regeneration is asked for. Everything here is
deterministic given the same memory, so it is unit-testable. The only LLM use is the optional ``critic`` hint.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path
from typing import Any

for _p in (Path(__file__).resolve().parents[1] / "_shared", Path(__file__).resolve().parents[2] / "lambda" / "_shared"):
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
try:
    from model_routing import MODELS, cost_usd
except ImportError:  # pragma: no cover
    MODELS = {"sonnet": {"in": 3.0, "out": 15.0}, "haiku": {"in": 1.0, "out": 5.0}}

    def cost_usd(alias: str, tokens_in: int, tokens_out: int, cached_in: int = 0) -> float:
        m = MODELS[alias]
        return (tokens_in * m["in"] + tokens_out * m["out"]) / 1_000_000

# name -> how the regeneration is asked for
STRATEGIES: dict[str, dict[str, Any]] = {
    "fix_cheap": {"model": "haiku", "grounded": False, "minimal": False, "critic": False,
                  "label": "Corrected prompt, fast model"},
    "fix_strong": {"model": "sonnet", "grounded": False, "minimal": False, "critic": False,
                   "label": "Corrected prompt, stronger model"},
    "grounded_cheap": {"model": "haiku", "grounded": True, "minimal": False, "critic": False,
                       "label": "Only source numbers allowed, fast model"},
    "grounded_strong": {"model": "sonnet", "grounded": True, "minimal": False, "critic": False,
                        "label": "Only source numbers allowed, stronger model"},
    "critic_strong": {"model": "sonnet", "grounded": True, "minimal": False, "critic": True,
                      "label": "AI-written correction hint, stronger model"},
    "minimal_safe": {"model": "sonnet", "grounded": True, "minimal": True,
                     "critic": False, "label": "Short safe text, figures only in tables"},
}

# Candidate strategies per failure category with a prior success probability (used until memory has data).
CANDIDATES: dict[str, list[tuple[str, float]]] = {
    "structural": [("fix_cheap", 0.60), ("fix_strong", 0.75), ("critic_strong", 0.55), ("minimal_safe", 0.80)],
    "language": [("fix_cheap", 0.65), ("fix_strong", 0.80), ("critic_strong", 0.55), ("minimal_safe", 0.80)],
    "numeric": [("grounded_cheap", 0.40), ("grounded_strong", 0.65), ("critic_strong", 0.55), ("minimal_safe", 0.80)],
    "generate": [("fix_strong", 0.70), ("fix_cheap", 0.45), ("minimal_safe", 0.75)],
}
PRIOR_WEIGHT = 2.0       # the prior counts as this many observations
EXPLORATION = 0.15       # optimism bonus for strategies with few observations
DEFAULT_TOKENS = (12000, 3500)  # (in, out) when the previous generation did not report usage


def categorize(fixable_errors: list[dict[str, Any]], action: str = "repair") -> str:
    if action == "generate":
        return "generate"
    rules = [str(e.get("rule", "")) for e in fixable_errors]
    if any(r.startswith("VAL-NUM") for r in rules):
        return "numeric"
    if any(r.startswith("VAL-STR") for r in rules):
        return "structural"
    if any(r.startswith("VAL-PRH") for r in rules):
        return "language"
    return "numeric" if rules else "structural"


def memory_key(category: str, strategy: str) -> str:
    return f"{category}#{strategy}"


def estimate_cost(strategy: str, usage: dict[str, int] | None) -> float:
    tin, tout = (usage or {}).get("input") or DEFAULT_TOKENS[0], (usage or {}).get("output") or DEFAULT_TOKENS[1]
    est = cost_usd(STRATEGIES[strategy]["model"], int(tin), int(tout))
    return est + (cost_usd("haiku", 1500, 300) if STRATEGIES[strategy].get("critic") else 0.0)


def rank(category: str, tried: set[str], memory: dict[str, dict[str, float]], usage: dict[str, int] | None) -> list[dict[str, Any]]:
    """Untried candidates ordered best first. score = estimated success probability per dollar, with a small exploration bonus."""
    total_obs = sum(int(memory.get(memory_key(category, s), {}).get("trials", 0)) for s, _ in CANDIDATES[category])
    out = []
    for name, prior in CANDIDATES[category]:
        if name in tried:
            continue
        m = memory.get(memory_key(category, name), {})
        n, s = float(m.get("trials", 0)), float(m.get("successes", 0))
        p = (s + prior * PRIOR_WEIGHT) / (n + PRIOR_WEIGHT)
        p = min(0.98, p + EXPLORATION * math.sqrt(math.log(total_obs + 2) / (n + 1)) * 0.5)
        cost = estimate_cost(name, usage)
        out.append({"strategy": name, "p": round(p, 3), "cost": round(cost, 4), "score": p / max(cost, 1e-4), "learned": n > 0})
    # a strategy that is very unlikely to work is not worth the money even if it is cheap
    out = [o for o in out if o["p"] >= 0.15]
    out.sort(key=lambda o: (-o["score"], o["cost"]))
    # "minimal_safe" shortens the text, so it is the last resort: it never jumps ahead of a strategy that keeps the full content
    return [o for o in out if o["strategy"] != "minimal_safe"] + [o for o in out if o["strategy"] == "minimal_safe"]


def choose(category: str, tried: set[str], memory: dict[str, dict[str, float]], usage: dict[str, int] | None,
           spent_section: float, spent_run: float, section_budget: float, run_budget: float) -> dict[str, Any]:
    """Pick the next strategy or explain why to stop. Returns {'strategy': name, ...} or {'stop': reason}."""
    ranked = rank(category, tried, memory, usage)
    if not ranked:
        return {"stop": "every applicable strategy has been tried"}
    for cand in ranked:  # the best affordable one (the minimal fallback is often the cheapest strong option)
        if spent_section + cand["cost"] <= section_budget and spent_run + cand["cost"] <= run_budget:
            return {**cand, "ranked": [r["strategy"] for r in ranked]}
    if spent_run + ranked[0]["cost"] > run_budget:
        return {"stop": "the repair budget for this run is used up"}
    return {"stop": "the repair budget for this section is used up"}


_NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def collect_numbers(obj: Any, out: list[str] | None = None, limit: int = 120) -> list[str]:
    """Every distinct numeric value in the source metrics, as short strings, in document order."""
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        v = f"{obj:.4f}".rstrip("0").rstrip(".") if isinstance(obj, float) else str(obj)
        if v not in out:
            out.append(v)
    elif isinstance(obj, dict):
        for v in obj.values():
            collect_numbers(v, out, limit)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            collect_numbers(v, out, limit)
    return out


def sanitize_hint(text: str, limit: int = 600) -> str:
    """The critic's hint goes into a prompt: keep it short, plain text, without links or markup."""
    text = re.sub(r"https?://\S+", "", text or "")
    text = re.sub(r"[`<>{}]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def build_correction(strategy: str, attempt: int, cls: dict[str, Any], metrics: dict[str, Any], hint: str | None = None) -> dict[str, Any]:
    spec = STRATEGIES[strategy]
    instructions = list(cls.get("instructions") or [])
    if hint:
        instructions.append(f"Reviewer note: {hint}")
    corr: dict[str, Any] = {"attempt": attempt, "strategy": strategy, "model": spec["model"], "instructions": instructions,
                            "offending_values": cls.get("offending_values") or []}
    if spec["grounded"]:
        corr["allowed_values"] = collect_numbers(metrics)
    if spec["minimal"]:
        corr["minimal"] = True
    return corr
