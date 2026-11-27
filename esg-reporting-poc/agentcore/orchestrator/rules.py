"""Catalogue of the validation rules (VAL-STR / VAL-NUM / VAL-PRH) and what to do when one fails.

For every rule we record:
  * ``kind``: ``generation`` (the model output can be fixed by regenerating) or ``data`` (the source data is
    inconsistent, regenerating cannot help and the right action is to fix the ETL and re-run the pipeline).
  * ``instruction``: the corrective sentence injected into the regeneration prompt.
  * ``explain``: plain-language explanation for the end user.

Regeneration is only attempted for ``generation`` rules, so the agent never burns tokens on something an LLM
cannot repair.
"""

from __future__ import annotations

from typing import Any

RULES: dict[str, dict[str, str]] = {
    "VAL-STR-01": {"kind": "generation", "instruction": "Return one valid JSON object that matches the output contract exactly. No text outside the JSON.",
                   "explain": "The model did not return valid JSON."},
    "VAL-STR-02": {"kind": "generation", "instruction": "Include ALL required keys: section_id, title, paragraphs, tables, key_metrics, footnotes, framework_references.",
                   "explain": "Required fields were missing from the generated section."},
    "VAL-STR-05": {"kind": "generation", "instruction": "Every paragraph_type must be exactly one of: narrative, methodology, footnote, forward_looking.",
                   "explain": "A paragraph used an unsupported type."},
    "VAL-STR-06": {"kind": "generation", "instruction": "This is a quantitative section: include at least one table with the figures from DATA INPUT.",
                   "explain": "A quantitative section had no table."},
    "VAL-STR-07": {"kind": "generation", "instruction": "Every table row must have exactly as many cells as the table has headers.",
                   "explain": "A table had rows whose cell count did not match the header."},
    "VAL-STR-08": {"kind": "generation", "instruction": "Include a non-empty key_metrics list for this quantitative section, using exact values from DATA INPUT.",
                   "explain": "The key metrics list was empty."},
    "VAL-NUM-01": {"kind": "generation", "instruction": "Use ONLY numbers that appear in DATA INPUT. Do not calculate, round or estimate. If a figure is not available, say it is not yet captured instead of inventing it.",
                   "explain": "The narrative contained numbers that cannot be traced to the source data."},
    "VAL-NUM-02": {"kind": "data", "instruction": "", "explain": "In the source data, natural-gas plus diesel emissions do not equal the Scope 1 total. This is an ETL data problem."},
    "VAL-NUM-04": {"kind": "generation", "instruction": "Quote the year-over-year change exactly as given in DATA INPUT (yoy_change_pct).",
                   "explain": "The year-over-year change in the text differs from the source value."},
    "VAL-NUM-05": {"kind": "generation", "instruction": "Quote intensity ratios exactly as given in DATA INPUT, with all decimals.",
                   "explain": "An intensity value in the text does not match the source value."},
    "VAL-NUM-06": {"kind": "data", "instruction": "", "explain": "Weighted financed emissions exceed gross financed emissions in the source data. This is an ETL data problem (PCAF aggregation) and needs a human."},
    "VAL-PRH-02": {"kind": "generation", "instruction": "Do not describe calculations (avoid 'calculated as', 'computed by', 'we estimate', 'approximately', 'roughly', 'divided by', 'multiplied by'). State the pre-computed value directly.",
                   "explain": "The text described a calculation or used estimating language."},
    "VAL-PRH-03": {"kind": "generation", "instruction": "Do not include URLs or cite sources that are not in RAG CONTEXT.",
                   "explain": "The text included a URL or an unverified external source."},
    "VAL-PRH-04": {"kind": "generation", "instruction": "Write in third person only. Never use 'we', 'our', 'us', 'my' or 'I'. Use 'the institution' or 'the bank'.",
                   "explain": "The text used first-person wording."},
    "VAL-PRH-05": {"kind": "generation", "instruction": "Remove marketing language (industry-leading, best-in-class, world-class, cutting-edge, pioneering, unparalleled, groundbreaking, revolutionary).",
                   "explain": "The text used marketing language."},
}

NON_BLOCKING = {"VAL-STR-03", "VAL-STR-04", "VAL-STR-09", "VAL-STR-10", "VAL-NUM-03", "VAL-NUM-07"}
BAD_OUTCOMES = {"FAIL", "RETRY", "FAIL_NO_RETRY"}


def classify(validation: dict[str, Any] | None) -> dict[str, Any]:
    """Split a validation result into fixable-by-regeneration items and source-data issues."""
    if not validation:
        return {"needs_repair": False, "unknown": True, "fixable": [], "data_issues": [], "instructions": [], "offending_values": [], "explanations": []}
    errors = validation.get("errors") or []
    fixable, data_issues, instructions, explanations = [], [], [], []
    for err in errors:
        rule = err.get("rule", "")
        meta = RULES.get(rule)
        if meta and meta["kind"] == "data":
            data_issues.append(err)
        else:
            fixable.append(err)
        if meta:
            if meta["instruction"] and meta["instruction"] not in instructions:
                instructions.append(meta["instruction"])
            if meta["explain"] not in explanations:
                explanations.append(meta["explain"])
        elif rule:
            instructions.append(f"Fix the violation of rule {rule}: {err.get('detail', '')}")
            explanations.append(f"Rule {rule} failed: {err.get('detail', '')}")

    numeric = validation.get("numeric_results") or {}
    offending = [f.get("value") for f in (numeric.get("failures") or []) if f.get("value") is not None]
    outcome = validation.get("validation_outcome")
    if outcome == "RETRY" and not errors:
        # numeric RETRY (single mismatch): the failure details live in numeric_results
        if offending:
            fixable.append({"rule": "VAL-NUM-01", "detail": f"{len(offending)} value(s) not found in source data"})
            instructions.append(RULES["VAL-NUM-01"]["instruction"])
            explanations.append(RULES["VAL-NUM-01"]["explain"])
    needs = outcome in BAD_OUTCOMES and bool(fixable)
    return {
        "needs_repair": needs,
        "unknown": False,
        "fixable": fixable,
        "data_issues": data_issues,
        "instructions": instructions,
        "offending_values": offending,
        "explanations": explanations,
    }
