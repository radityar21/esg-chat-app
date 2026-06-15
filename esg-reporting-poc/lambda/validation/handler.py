"""
=============================================================================
Lambda #4: ValidationFn
=============================================================================
Spec Reference: §7 (VAL-NUM-01 to VAL-NUM-07, VAL-STR-01 to VAL-STR-09,
                     VAL-PRH-01 to VAL-PRH-05), REQ-VAL-01 to REQ-VAL-07

Purpose:
    Validates generated section JSON against 21 validation rules.
    Runs AFTER SectionGenFn, BEFORE assembly.

Input:
    {
        "section_content": {...},
        "source_metrics": {...},
        "framework": "GRI_305",
        "section_id": "GRI_305_S1_2024",
        "execution_id": "arn:...",
        "retry_count": 0
    }

Output (REQ-VAL-07 contract):
    {
        "section_id": "GRI_305_S1_2024",
        "validation_outcome": "PASS" | "WARN" | "RETRY" | "FAIL",
        "structural_results": {...},
        "numeric_results": {...},
        "prohibited_content_results": {...},
        "warnings": [],
        "errors": [],
        "retry_count": 0,
        "timestamp": "...",
        "execution_id": "..."
    }

Deployment:
    Runtime: Python 3.11, Memory: 512 MB, Timeout: 60s
    Role: ESG-Validation-ExecutionRole
=============================================================================
"""

from __future__ import annotations

import json
import re
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# =============================================================================
# TOLERANCES (§7.1)
# =============================================================================

TOLERANCE_TCO2E: float = 0.001        # VAL-NUM-01, VAL-NUM-02, VAL-NUM-07
TOLERANCE_PCT: float = 0.05           # VAL-NUM-03
TOLERANCE_YOY: float = 0.1            # VAL-NUM-04
TOLERANCE_INTENSITY: float = 0.000001 # VAL-NUM-05

# =============================================================================
# REQ-VAL-05: Whitelisted values (years, GWP constants, PCAF scores)
# These may appear in narrative without being in DATA INPUT
# =============================================================================

WHITELISTED_VALUES: set[float] = {
    # Years
    2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030, 2035, 2050, 2060,
    # GWP constants
    29.8, 273.0,
    # PCAF scores
    1.0, 1.5, 2.0, 3.0, 4.0, 5.0,
    # PCAF confidence factors
    0.45, 0.60, 0.75, 0.90, 1.00,
    # Common percentages
    100.0, 0.0,
    # Grid EF
    0.7886,
}

# =============================================================================
# PROHIBITED PATTERNS (§7.3)
# =============================================================================

CALCULATION_PHRASES = re.compile(
    r"\b(calculated as|computed by|we estimate|approximately|roughly|"
    r"we calculate|divided by|multiplied by)\b",
    re.IGNORECASE
)

# VAL-PRH-04: Including "I" — case-sensitive standalone only (not in "Scope I")
FIRST_PERSON = re.compile(r"\b(we|our|us|my|ourselves)\b", re.IGNORECASE)
FIRST_PERSON_I = re.compile(r"(?<![A-Z])\bI\b(?!\w)")  # Standalone "I" not after uppercase (avoids "Scope I")

MARKETING_LANGUAGE = re.compile(
    r"\b(industry.leading|best.in.class|world.class|cutting.edge|"
    r"pioneering|unparalleled|groundbreaking|revolutionary)\b",
    re.IGNORECASE
)

URL_PATTERN = re.compile(r"https?://\S+")

# VAL-PRH-03: "according to [source]" check
ACCORDING_TO_PATTERN = re.compile(r"according to\s+([^,.]+)", re.IGNORECASE)

# Numeric extraction (REQ-VAL-01)
NUMERIC_PATTERN = re.compile(
    r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(tCO2e|%|IDR|MWh|GJ|tCO2e/IDR|per FTE|per employee|per IDR billion)"
)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Validate section content against 21 rules per §7.

    Args:
        event: Input with section_content, source_metrics, framework.
        context: Lambda context.

    Returns:
        REQ-VAL-07 compliant response dict.
    """
    logger.info("ValidationFn invoked")

    section_content: dict = event.get("section_content")
    content_s3_key: str = event.get("content_s3_key", "")
    content_s3_bucket: str = event.get("content_s3_bucket", "")

    # Fetch from S3 if content not inline (payload offloading)
    if not section_content and content_s3_key:
        try:
            import boto3 as _boto3
            _s3 = _boto3.client("s3")
            resp = _s3.get_object(Bucket=content_s3_bucket, Key=content_s3_key)
            section_content = json.loads(resp["Body"].read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to fetch section from S3: {content_s3_key} - {str(e)}")
            section_content = {}

    if not section_content:
        section_content = {}

    source_metrics: dict = event["source_metrics"]
    framework: str = event["framework"]
    section_id: str = event.get("section_id", "unknown")
    execution_id: str = event.get("execution_id", "local-test")
    retry_count: int = event.get("retry_count", 0)

    structural_results: dict[str, Any] = {}
    numeric_results: dict[str, Any] = {"total_claims_checked": 0, "passed": 0, "failed": 0, "failures": []}
    prohibited_results: dict[str, Any] = {"fabricated_numbers": [], "calculation_phrases": [], "first_person": [], "urls": [], "marketing": []}
    warnings: list[dict] = []
    errors: list[dict] = []

    # =========================================================================
    # PHASE 1: STRUCTURAL VALIDATION (REQ-VAL-03: runs FIRST)
    # =========================================================================

    # VAL-STR-01: Valid JSON
    if not isinstance(section_content, dict):
        structural_results["json_valid"] = False
        return _build_response(section_id, "RETRY", structural_results, numeric_results, prohibited_results, warnings,
                               [{"rule": "VAL-STR-01", "detail": "Not a valid JSON object"}], retry_count, execution_id)
    structural_results["json_valid"] = True

    # VAL-STR-02: Required keys
    required_keys = {"section_id", "title", "paragraphs", "tables", "key_metrics", "footnotes", "framework_references"}
    present_keys = set(section_content.keys())
    missing_keys = required_keys - present_keys
    structural_results["required_keys_present"] = len(missing_keys) == 0
    if missing_keys:
        errors.append({"rule": "VAL-STR-02", "detail": f"Missing: {sorted(missing_keys)}"})

    # VAL-STR-03: section_id format
    sid = section_content.get("section_id", "")
    sid_valid = bool(re.match(r"^[A-Z0-9_]+_[A-Z0-9]+_\d{4}$", sid))
    structural_results["section_id_format_valid"] = sid_valid
    if not sid_valid:
        warnings.append({"rule": "VAL-STR-03", "detail": f"section_id format: {sid}"})

    # VAL-STR-04: Paragraph count
    paragraphs = section_content.get("paragraphs", [])
    structural_results["paragraph_count"] = len(paragraphs) if isinstance(paragraphs, list) else 0
    if not isinstance(paragraphs, list) or len(paragraphs) == 0:
        warnings.append({"rule": "VAL-STR-04", "detail": "Empty or invalid paragraphs"})

    # VAL-STR-05: Paragraph type enum
    valid_types = {"narrative", "methodology", "footnote", "forward_looking"}
    invalid_types = []
    for i, p in enumerate(paragraphs if isinstance(paragraphs, list) else []):
        ptype = p.get("paragraph_type", "")
        if ptype not in valid_types:
            invalid_types.append((i, ptype))
    structural_results["all_paragraph_types_valid"] = len(invalid_types) == 0
    if invalid_types:
        errors.append({"rule": "VAL-STR-05", "detail": f"Invalid types: {invalid_types[:3]}"})

    # VAL-STR-06: Tables for quantitative sections
    tables = section_content.get("tables", [])
    quant_sections = {"scope1", "scope2", "scope3_pcaf", "intensity", "summary"}
    sec_type = _extract_section_type(sid)
    has_tables = isinstance(tables, list) and len(tables) > 0
    structural_results["tables_present"] = has_tables
    if sec_type in quant_sections and not has_tables:
        errors.append({"rule": "VAL-STR-06", "detail": "No tables for quantitative section"})

    # VAL-STR-07: Table column consistency
    table_consistent = True
    for i, table in enumerate(tables if isinstance(tables, list) else []):
        headers = table.get("headers", [])
        for j, row in enumerate(table.get("rows", [])):
            if len(row) != len(headers):
                table_consistent = False
                errors.append({"rule": "VAL-STR-07", "detail": f"Table {i} row {j}: {len(row)} cols vs {len(headers)}"})
                break
    structural_results["table_columns_consistent"] = table_consistent

    # VAL-STR-08: key_metrics
    key_metrics = section_content.get("key_metrics", [])
    structural_results["key_metrics_present"] = isinstance(key_metrics, list) and len(key_metrics) > 0
    if sec_type in quant_sections and not structural_results["key_metrics_present"]:
        errors.append({"rule": "VAL-STR-08", "detail": "No key_metrics for quantitative section"})

    # VAL-STR-09: data_sources_used
    data_sources = section_content.get("data_sources_used", [])
    structural_results["data_sources_present"] = len(data_sources) > 0
    if not structural_results["data_sources_present"]:
        warnings.append({"rule": "VAL-STR-09", "detail": "data_sources_used is empty"})

    # VAL-STR-10: advisory_recommendations (WARN only — non-blocking)
    advisory = section_content.get("advisory_recommendations", [])
    structural_results["advisory_present"] = isinstance(advisory, list) and len(advisory) >= 2
    if not structural_results["advisory_present"]:
        warnings.append({"rule": "VAL-STR-10", "detail": "advisory_recommendations missing or < 2 entries"})

    # If structural FAIL, stop
    if errors:
        return _build_response(section_id, "FAIL", structural_results, numeric_results, prohibited_results, warnings, errors, retry_count, execution_id)

    # =========================================================================
    # PHASE 2: NUMERIC VALIDATION (REQ-VAL-01)
    # =========================================================================
    all_text = _extract_all_text(section_content)
    numeric_claims = NUMERIC_PATTERN.findall(all_text)
    allowed_values = _build_allowed_values(source_metrics)

    total_checked = 0
    passed = 0
    failures = []

    for value_str, unit in numeric_claims:
        value = _parse_numeric(value_str)
        if value is None:
            continue
        total_checked += 1

        # REQ-VAL-05: Skip whitelisted values
        if value in WHITELISTED_VALUES:
            passed += 1
            continue

        if _value_in_allowed(value, allowed_values, TOLERANCE_TCO2E):
            passed += 1
        else:
            failures.append({"value": value, "unit": unit, "rule": "VAL-NUM-01"})

    numeric_results["total_claims_checked"] = total_checked
    numeric_results["passed"] = passed
    numeric_results["failed"] = len(failures)
    numeric_results["failures"] = failures[:10]  # Cap at 10

    if failures:
        # Single mismatch → RETRY; multiple → FAIL
        if len(failures) <= 1 and retry_count == 0:
            return _build_response(section_id, "RETRY", structural_results, numeric_results, prohibited_results, warnings, errors, retry_count, execution_id)
        else:
            errors.append({"rule": "VAL-NUM-01", "detail": f"{len(failures)} fabricated/mismatched values"})

    # VAL-NUM-02: Scope 1 component sum
    s1 = source_metrics.get("scope1_tco2e")
    s1_n = source_metrics.get("scope1_natgas_tco2e")
    s1_d = source_metrics.get("scope1_diesel_tco2e")
    if all(v is not None for v in [s1, s1_n, s1_d]):
        if abs(s1 - (s1_n + s1_d)) > TOLERANCE_TCO2E:
            errors.append({"rule": "VAL-NUM-02", "detail": "Source data: natgas + diesel != scope1_tco2e"})

    # VAL-NUM-03: Percentage tolerance
    pct_claims = re.findall(r"(\d+\.\d+)\s*%", all_text)
    for pct_str in pct_claims:
        pct_val = float(pct_str)
        if pct_val in WHITELISTED_VALUES:
            continue
        if not _value_in_allowed(pct_val, allowed_values, TOLERANCE_PCT):
            if pct_val not in (0.0, 100.0):
                warnings.append({"rule": "VAL-NUM-03", "detail": f"Percentage {pct_val}% not in source (±{TOLERANCE_PCT})"})

    # VAL-NUM-04: YoY consistency
    yoy = source_metrics.get("yoy_change_pct")
    if yoy is not None:
        yoy_in_text = re.findall(r"(-?\d+\.\d+)\s*%.*(?:year.over.year|YoY|change)", all_text, re.IGNORECASE)
        for yoy_str in yoy_in_text:
            yoy_val = float(yoy_str)
            if abs(yoy_val - yoy) > TOLERANCE_YOY:
                errors.append({"rule": "VAL-NUM-04", "detail": f"YoY in text={yoy_val}, source={yoy}"})

    # VAL-NUM-05: Intensity values
    intensity_rev = source_metrics.get("intensity_tco2e_per_idr_bn")
    intensity_fte = source_metrics.get("intensity_tco2e_per_fte")
    intensity_pattern = re.findall(r"(\d+\.\d{4,})\s*(?:tCO2e/IDR|per IDR|per FTE|tCO2e/FTE)", all_text)
    for int_str in intensity_pattern:
        int_val = float(int_str)
        match_found = False
        if intensity_rev and abs(int_val - intensity_rev) <= TOLERANCE_INTENSITY:
            match_found = True
        if intensity_fte and abs(int_val - intensity_fte) <= TOLERANCE_INTENSITY:
            match_found = True
        if not match_found and int_val not in WHITELISTED_VALUES:
            errors.append({"rule": "VAL-NUM-05", "detail": f"Intensity {int_str} not matching source"})

    # VAL-NUM-06: PCAF gross vs weighted (ZERO TOLERANCE — no retry, direct to HumanReview)
    gross = source_metrics.get("scope3_cat15_gross_tco2e")
    weighted = source_metrics.get("scope3_cat15_weighted_tco2e")
    if gross is not None and weighted is not None:
        if weighted > gross:
            errors.append({
                "rule": "VAL-NUM-06",
                "detail": f"weighted ({weighted}) > gross ({gross})",
                "no_retry": True,  # Signal: HALT → HumanReviewState, no retry
            })

    # VAL-NUM-07: Table↔Paragraph consistency
    table_values = _extract_table_values(section_content)
    para_values = set(_parse_numeric(v) for v, _ in NUMERIC_PATTERN.findall(all_text) if _parse_numeric(v) is not None)
    for tv in table_values:
        if tv not in WHITELISTED_VALUES and tv not in para_values:
            if not _value_in_allowed(tv, para_values, TOLERANCE_TCO2E):
                warnings.append({"rule": "VAL-NUM-07", "detail": f"Table value {tv} not found in paragraphs"})

    # =========================================================================
    # PHASE 3: PROHIBITED CONTENT (§7.3)
    # =========================================================================

    # VAL-PRH-02: Calculation phrases
    calc_matches = CALCULATION_PHRASES.findall(all_text)
    if calc_matches:
        prohibited_results["calculation_phrases"] = calc_matches[:5]
        errors.append({"rule": "VAL-PRH-02", "detail": f"Calc language: {calc_matches[:3]}"})

    # VAL-PRH-03: External sources + URLs
    url_matches = URL_PATTERN.findall(all_text)
    if url_matches:
        prohibited_results["urls"] = url_matches[:3]
        errors.append({"rule": "VAL-PRH-03", "detail": f"External URLs: {url_matches[:3]}"})

    acc_matches = ACCORDING_TO_PATTERN.findall(all_text)
    if acc_matches:
        # Check if cited source is in RAG context (simplified: just flag)
        prohibited_results["unverified_citations"] = acc_matches[:3]
        warnings.append({"rule": "VAL-PRH-03", "detail": f"'According to' citations: {acc_matches[:3]}"})

    # VAL-PRH-04: First person (includes standalone "I")
    fp_matches = FIRST_PERSON.findall(all_text)
    fp_i_matches = FIRST_PERSON_I.findall(all_text)
    all_fp = fp_matches + fp_i_matches
    if all_fp:
        prohibited_results["first_person"] = all_fp[:5]
        errors.append({"rule": "VAL-PRH-04", "detail": f"First person: {all_fp[:5]}"})

    # VAL-PRH-05: Marketing language
    mkt_matches = MARKETING_LANGUAGE.findall(all_text)
    if mkt_matches:
        prohibited_results["marketing"] = mkt_matches[:3]
        errors.append({"rule": "VAL-PRH-05", "detail": f"Marketing: {mkt_matches[:3]}"})

    # =========================================================================
    # BUILD RESPONSE (REQ-VAL-07 contract)
    # =========================================================================
    outcome = _determine_outcome(errors, warnings)
    return _build_response(section_id, outcome, structural_results, numeric_results, prohibited_results, warnings, errors, retry_count, execution_id)


# =============================================================================
# RESPONSE BUILDER (REQ-VAL-07)
# =============================================================================

def _build_response(
    section_id: str,
    outcome: str,
    structural: dict,
    numeric: dict,
    prohibited: dict,
    warnings: list,
    errors: list,
    retry_count: int,
    execution_id: str,
) -> dict[str, Any]:
    """Build REQ-VAL-07 compliant response.

    Args:
        section_id: Section being validated.
        outcome: PASS, WARN, RETRY, or FAIL.
        structural: Structural validation results.
        numeric: Numeric validation results.
        prohibited: Prohibited content results.
        warnings: Warning list.
        errors: Error list.
        retry_count: Current retry count.
        execution_id: Step Functions execution ARN.

    Returns:
        Spec-compliant validation response dict.
    """
    return {
        "section_id": section_id,
        "validation_outcome": outcome,
        "structural_results": structural,
        "numeric_results": numeric,
        "prohibited_content_results": prohibited,
        "warnings": warnings,
        "errors": errors,
        "retry_count": retry_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "execution_id": execution_id,
    }


def _determine_outcome(errors: list, warnings: list) -> str:
    """Determine validation outcome.

    Args:
        errors: List of error dicts.
        warnings: List of warning dicts.

    Returns:
        One of PASS, WARN, FAIL, FAIL_NO_RETRY.
    """
    # Check for no-retry errors first (e.g., VAL-NUM-06 weighted > gross)
    if any(e.get("no_retry") for e in errors):
        return "FAIL_NO_RETRY"  # Step Functions → HumanReviewState immediately
    if errors:
        return "FAIL"
    if warnings:
        return "WARN"
    return "PASS"


# =============================================================================
# HELPERS
# =============================================================================

def _extract_all_text(section: dict) -> str:
    """Extract all text from section paragraphs and tables.

    Args:
        section: Section JSON dict.

    Returns:
        Concatenated text string.
    """
    parts = []
    for p in section.get("paragraphs", []):
        parts.append(p.get("text", ""))
    for table in section.get("tables", []):
        for row in table.get("rows", []):
            parts.extend(str(cell) for cell in row)
    return " ".join(parts)


def _extract_table_values(section: dict) -> set[float]:
    """Extract all numeric values from tables.

    Args:
        section: Section JSON dict.

    Returns:
        Set of float values found in table cells.
    """
    values = set()
    for table in section.get("tables", []):
        for row in table.get("rows", []):
            for cell in row:
                v = _parse_numeric(str(cell).replace(",", ""))
                if v is not None:
                    values.add(v)
    return values


def _build_allowed_values(source_metrics: dict) -> set[float]:
    """Build set of allowed numeric values from source metrics (REQ-VAL-04).

    Args:
        source_metrics: DATA INPUT dict from Athena.

    Returns:
        Set of allowed float values (including derived variants).
    """
    allowed: set[float] = set(WHITELISTED_VALUES)
    for key, val in source_metrics.items():
        if isinstance(val, (int, float)) and val is not None:
            allowed.add(float(val))
            allowed.add(abs(float(val)))
            allowed.add(val * 1000)
            allowed.add(val / 1000)
            allowed.add(val * 100)
            allowed.add(round(val, 1))
            allowed.add(round(val, 2))
            allowed.add(round(val, 3))
            allowed.add(round(val, 4))
            allowed.add(round(val, 6))
    return allowed


def _value_in_allowed(value: float, allowed: set[float], tolerance: float) -> bool:
    """Check if value exists in allowed set within tolerance.

    Args:
        value: Value to check.
        allowed: Set of allowed values.
        tolerance: Acceptable difference.

    Returns:
        True if value matches any allowed value within tolerance.
    """
    for av in allowed:
        if abs(value - av) <= tolerance:
            return True
    return False


def _parse_numeric(value_str: str) -> float | None:
    """Parse numeric string to float.

    Args:
        value_str: String potentially containing a number.

    Returns:
        Float value or None if not parseable.
    """
    try:
        return float(value_str.replace(",", "").replace("%", ""))
    except (ValueError, TypeError, AttributeError):
        return None


def _extract_section_type(section_id: str) -> str:
    """Extract section type from section_id.

    Args:
        section_id: Full section ID string.

    Returns:
        Section type string (scope1, scope2, etc.).
    """
    sid = section_id.lower()
    if "scope1" in sid or "_s1_" in sid:
        return "scope1"
    if "scope2" in sid or "_s2_" in sid:
        return "scope2"
    if "pcaf" in sid or "scope3" in sid:
        return "scope3_pcaf"
    if "intensity" in sid:
        return "intensity"
    if "summary" in sid:
        return "summary"
    return "unknown"
