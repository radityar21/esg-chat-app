"""
=============================================================================
Lambda #2: AthenaQueryFn
=============================================================================
Spec Reference: §4.4 (REQ-DDL-11, REQ-DDL-13), §9, REQ-TRACE-01

Purpose:
    Executes a SINGLE Athena query to fetch ALL aggregated data for the
    reporting year. Returns complete DATA INPUT for all section templates.
    Called ONCE per Step Functions execution (not per section).

Architecture (§9.1):
    Step Functions calls AthenaQueryFn ONCE → result cached in $.athena_query_result
    → Map state passes same data to each SectionGenFn iteration.

Input:
    {
        "reporting_year": 2024,
        "bank_id": "GENERIC_FI_001",
        "execution_id": "arn:aws:states:us-east-1:061039769766:execution:..."
    }

Output:
    {
        "ghg_summary": {...},
        "pcaf_sectors": [...],
        "prior_year_summary": {...},
        "query_execution_id": "...",
        "data_scanned_bytes": 12345
    }

Deployment:
    Runtime: Python 3.11
    Memory: 512 MB
    Timeout: 60s
    Role: ESG-AthenaQuery-ExecutionRole

Raises:
    QueryTimeoutError: If Athena query exceeds 50s poll window.
    QueryFailedError: If Athena returns FAILED/CANCELLED state.
=============================================================================
"""

from __future__ import annotations

import json
import time
import logging
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# =============================================================================
# CONFIGURATION (Config Externalization standard)
# =============================================================================

ACCOUNT_ID: str = "061039769766"
ATHENA_WORKGROUP: str = "esg-reporting-workgroup"
ATHENA_DATABASE: str = "esg_aggregated"
ATHENA_CATALOG: str = "AwsDataCatalog"
RESULT_BUCKET: str = f"esg-data-aggregated-{ACCOUNT_ID}"
RESULT_PREFIX: str = "athena-results"

# REQ-TRACE-01: Result reuse (cache queries for 60 min)
RESULT_REUSE_ENABLED: bool = True
RESULT_REUSE_MAX_AGE_MINUTES: int = 60

# Lambda timeout = 60s, so poll max = 50s (leave 10s buffer)
POLL_MAX_SECONDS: int = 50
POLL_INTERVAL_SECONDS: int = 2

athena_client = boto3.client("athena")

# =============================================================================
# QUERIES (REQ-DDL-11 — parameterized via PREPARE/EXECUTE)
# =============================================================================

# REQ-DDL-11 Query 1: GHG Summary (all aggregated metrics for reporting year)
QUERY_GHG_SUMMARY: str = """
SELECT
    metric_key,
    scope1_tco2e,
    scope1_natgas_tco2e,
    scope1_diesel_tco2e,
    scope2_location_tco2e,
    scope2_market_tco2e,
    scope3_cat15_gross_tco2e,
    scope3_cat15_weighted_tco2e,
    intensity_tco2e_per_idr_bn,
    intensity_tco2e_per_fte,
    yoy_change_pct,
    vs_base_year_change_pct,
    avg_pcaf_data_quality,
    assurance_level
FROM esg_aggregated.ghg_summary_annual
WHERE reporting_year = ?
  AND metric_key LIKE ?
"""

# REQ-DDL-11 Query 2: PCAF Sector Breakdown (top emitters)
QUERY_PCAF_SECTORS: str = """
SELECT
    sector_nace,
    sector_display_name,
    loan_count,
    borrower_count,
    total_outstanding_idr_trillion,
    financed_emissions_gross_tco2e,
    financed_emissions_weighted_tco2e,
    emission_intensity_per_idr_bn,
    avg_pcaf_score,
    pct_of_total_portfolio,
    pct_of_total_financed_emissions,
    yoy_change_emissions_pct
FROM esg_aggregated.pcaf_by_sector
WHERE reporting_year = ?
ORDER BY financed_emissions_gross_tco2e DESC
LIMIT 10
"""

# REQ-DDL-11 Query 3: Prior year (for YoY context in narrative)
QUERY_PRIOR_YEAR: str = """
SELECT
    metric_key,
    scope1_tco2e,
    scope1_natgas_tco2e,
    scope1_diesel_tco2e,
    scope2_location_tco2e,
    scope2_market_tco2e,
    scope3_cat15_gross_tco2e,
    scope3_cat15_weighted_tco2e,
    intensity_tco2e_per_idr_bn,
    intensity_tco2e_per_fte
FROM esg_aggregated.ghg_summary_annual
WHERE reporting_year = ?
  AND metric_key LIKE ?
"""

# Query 4: Scope 1 facility breakdown (top 10 emitters)
QUERY_SCOPE1_FACILITIES: str = """
SELECT
    facility_id,
    scope1_tco2e,
    scope1_natgas_tco2e,
    scope1_diesel_tco2e,
    total_natgas_gj,
    total_diesel_liters,
    data_quality_score
FROM esg_aggregated.scope1_by_facility
WHERE reporting_year = ?
ORDER BY scope1_tco2e DESC
LIMIT 10
"""

# Query 5: HR Metrics for Social (S) section — current + prior year
# Source: esg_raw.hr_metrics (not aggregated — raw table, no Glue ETL needed)
# Pre-computes: hiring_rate_pct, female_headcount, male_headcount
QUERY_HR_METRICS: str = """
SELECT
    reporting_year,
    fte_total,
    fte_female_pct,
    fte_management_female_pct,
    new_hire_count,
    voluntary_turnover_pct,
    training_hours_per_fte,
    discrimination_cases,
    ROUND(CAST(new_hire_count AS DOUBLE) / CAST(fte_total AS DOUBLE) * 100, 2) AS hiring_rate_pct,
    CAST(ROUND(CAST(fte_total AS DOUBLE) * (fte_female_pct / 100.0)) AS INTEGER) AS female_headcount,
    CAST(ROUND(CAST(fte_total AS DOUBLE) * (1.0 - fte_female_pct / 100.0)) AS INTEGER) AS male_headcount
FROM esg_raw.hr_metrics
WHERE reporting_year IN (?, ?)
ORDER BY reporting_year DESC
"""


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Execute all required Athena queries and return complete DATA INPUT.

    Args:
        event: Input containing reporting_year, bank_id, execution_id.
        context: Lambda context object.

    Returns:
        Dict with ghg_summary, pcaf_sectors, prior_year_summary, and metadata.

    Raises:
        ValueError: If required input fields are missing.
        RuntimeError: If Athena query fails or times out.
    """
    logger.info(f"AthenaQueryFn invoked: {json.dumps(event)}")

    # REQ-SFN-03: Validate input
    reporting_year: int = event["reporting_year"]
    bank_id: str = event.get("bank_id", "GENERIC_FI_001")
    execution_id: str = event.get("execution_id", "local-test")
    bank_id_pattern: str = f"{bank_id}_%"

    # REQ-DDL-13: Query tags — Athena doesn't support tags in start_query_execution,
    # so we encode traceability in the OutputLocation path (execution_id segmentation)
    # and workgroup-level tags. Path includes execution_id for audit trail.
    execution_id_short = execution_id.split(":")[-1] if ":" in execution_id else execution_id

    # =========================================================================
    # Execute Query 1: GHG Summary (REQ-DDL-11)
    # =========================================================================
    ghg_result = _execute_prepared_query(
        query_name="ghg_summary_query",
        sql=QUERY_GHG_SUMMARY,
        parameters=[str(reporting_year), bank_id_pattern],
        execution_id_short=execution_id_short,
    )

    # =========================================================================
    # Execute Query 2: PCAF Sectors (REQ-DDL-11)
    # =========================================================================
    pcaf_result = _execute_prepared_query(
        query_name="pcaf_sector_query",
        sql=QUERY_PCAF_SECTORS,
        parameters=[str(reporting_year)],
        execution_id_short=execution_id_short,
    )

    # =========================================================================
    # Execute Query 3: Prior Year (for YoY narrative context)
    # =========================================================================
    prior_year_result = _execute_prepared_query(
        query_name="prior_year_query",
        sql=QUERY_PRIOR_YEAR,
        parameters=[str(reporting_year - 1), bank_id_pattern],
        execution_id_short=execution_id_short,
    )

    # =========================================================================
    # Execute Query 4: Scope 1 Facility Breakdown (top 10)
    # =========================================================================
    facility_result = _execute_prepared_query(
        query_name="scope1_facility_query",
        sql=QUERY_SCOPE1_FACILITIES,
        parameters=[str(reporting_year)],
        execution_id_short=execution_id_short,
    )

    # =========================================================================
    # Execute Query 5: HR Metrics for Social section (current + prior year)
    # =========================================================================
    hr_result = _execute_prepared_query(
        query_name="hr_metrics_query",
        sql=QUERY_HR_METRICS,
        parameters=[str(reporting_year), str(reporting_year - 1)],
        execution_id_short=execution_id_short,
    )

    # =========================================================================
    # Build unified response
    # =========================================================================
    ghg_summary = _parse_single_row(ghg_result["rows"])
    pcaf_sectors = _parse_multi_rows(pcaf_result["rows"])
    prior_year_summary = _parse_single_row(prior_year_result["rows"])
    scope1_facilities = _parse_multi_rows(facility_result["rows"])
    hr_metrics_raw = _parse_multi_rows(hr_result["rows"])
    hr_metrics = _build_hr_metrics(hr_metrics_raw, reporting_year)

    total_scanned = (
        ghg_result["data_scanned_bytes"]
        + pcaf_result["data_scanned_bytes"]
        + prior_year_result["data_scanned_bytes"]
        + facility_result["data_scanned_bytes"]
        + hr_result["data_scanned_bytes"]
    )

    response = {
        "ghg_summary": ghg_summary,
        "pcaf_sectors": pcaf_sectors,
        "prior_year_summary": prior_year_summary,
        "scope1_facilities": scope1_facilities,
        "hr_metrics": hr_metrics,
        "reporting_year": reporting_year,
        "bank_id": bank_id,
        "query_execution_ids": [
            ghg_result["execution_id"],
            pcaf_result["execution_id"],
            prior_year_result["execution_id"],
            facility_result["execution_id"],
            hr_result["execution_id"],
        ],
        "total_data_scanned_bytes": total_scanned,
    }

    logger.info(
        f"AthenaQueryFn complete: {len(pcaf_sectors)} sectors, "
        f"{total_scanned} bytes scanned"
    )
    return response


def _execute_prepared_query(
    query_name: str,
    sql: str,
    parameters: list[str],
    execution_id_short: str,
) -> dict[str, Any]:
    """Execute a parameterized Athena query using execution parameters.

    Args:
        query_name: Descriptive name for logging.
        sql: SQL with ? placeholders.
        parameters: Values for ? placeholders (in order).
        execution_id_short: Short execution ID for output path segmentation.

    Returns:
        Dict with rows (parsed), execution_id, data_scanned_bytes.

    Raises:
        RuntimeError: If query fails or times out.
    """
    logger.info(f"Executing query: {query_name} with params={parameters}")

    # REQ-DDL-11: Use ExecutionParameters for parameterized queries (not string format)
    # REQ-DDL-13: Traceability via OutputLocation path (execution_id segmentation)
    result_config = {
        "OutputLocation": f"s3://{RESULT_BUCKET}/{RESULT_PREFIX}/{execution_id_short}/{query_name}/",
    }

    start_kwargs: dict[str, Any] = {
        "QueryString": sql,
        "QueryExecutionContext": {
            "Database": ATHENA_DATABASE,
            "Catalog": ATHENA_CATALOG,
        },
        "WorkGroup": ATHENA_WORKGROUP,
        "ResultConfiguration": result_config,
        "ExecutionParameters": parameters,
    }

    # REQ-TRACE-01: Result reuse
    if RESULT_REUSE_ENABLED:
        start_kwargs["ResultReuseConfiguration"] = {
            "ResultReuseByAgeConfiguration": {
                "Enabled": True,
                "MaxAgeInMinutes": RESULT_REUSE_MAX_AGE_MINUTES,
            }
        }

    response = athena_client.start_query_execution(**start_kwargs)
    execution_id = response["QueryExecutionId"]

    # Poll for completion (within Lambda timeout budget)
    result = _poll_query(execution_id)

    if result["status"] != "SUCCEEDED":
        raise RuntimeError(
            f"Athena query '{query_name}' {result['status']}: {result.get('reason', 'unknown')}"
        )

    # Fetch results
    results_response = athena_client.get_query_results(QueryExecutionId=execution_id)
    rows = results_response["ResultSet"]["Rows"]

    return {
        "rows": rows,
        "execution_id": execution_id,
        "data_scanned_bytes": result.get("data_scanned_bytes", 0),
    }


def _poll_query(execution_id: str) -> dict[str, Any]:
    """Poll Athena query status until completion or timeout.

    Args:
        execution_id: Athena query execution ID.

    Returns:
        Dict with status, data_scanned_bytes, and optional reason.
    """
    elapsed = 0
    while elapsed < POLL_MAX_SECONDS:
        response = athena_client.get_query_execution(QueryExecutionId=execution_id)
        state = response["QueryExecution"]["Status"]["State"]

        if state == "SUCCEEDED":
            stats = response["QueryExecution"].get("Statistics", {})
            return {
                "status": "SUCCEEDED",
                "data_scanned_bytes": stats.get("DataScannedInBytes", 0),
            }
        elif state in ("FAILED", "CANCELLED"):
            reason = response["QueryExecution"]["Status"].get("StateChangeReason", "")
            return {"status": state, "reason": reason}

        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS

    return {"status": "TIMEOUT", "reason": f"Exceeded {POLL_MAX_SECONDS}s poll window"}


def _parse_single_row(rows: list[dict]) -> dict[str, Any]:
    """Parse Athena result with single data row into flat dict.

    Args:
        rows: Athena ResultSet rows (first row = headers).

    Returns:
        Dict mapping column names to typed values. Empty dict if no data.
    """
    if len(rows) < 2:
        return {}

    headers = [col.get("VarCharValue", "") for col in rows[0]["Data"]]
    values = [_parse_value(col.get("VarCharValue")) for col in rows[1]["Data"]]
    return dict(zip(headers, values))


def _parse_multi_rows(rows: list[dict]) -> list[dict[str, Any]]:
    """Parse Athena result with multiple data rows into list of dicts.

    Args:
        rows: Athena ResultSet rows (first row = headers).

    Returns:
        List of dicts, one per data row.
    """
    if len(rows) < 2:
        return []

    headers = [col.get("VarCharValue", "") for col in rows[0]["Data"]]
    result = []
    for row in rows[1:]:
        values = [_parse_value(col.get("VarCharValue")) for col in row["Data"]]
        result.append(dict(zip(headers, values)))
    return result


def _parse_value(val: str | None) -> int | float | str | None:
    """Parse string value to appropriate Python type.

    Args:
        val: String value from Athena result.

    Returns:
        Typed value (int, float, str, or None).
    """
    if val is None or val == "":
        return None
    try:
        if "." in val:
            return float(val)
        return int(val)
    except (ValueError, TypeError):
        return val


def _build_hr_metrics(hr_rows: list[dict[str, Any]], reporting_year: int) -> dict[str, Any]:
    """Build structured HR metrics with YoY changes for the Social section.

    Pre-computes all year-over-year changes so the LLM does NOT need to calculate.

    Args:
        hr_rows: Parsed HR metrics rows (ordered DESC by reporting_year).
        reporting_year: Current reporting year.

    Returns:
        Dict with current year metrics, prior year metrics, and all YoY values.
    """
    if not hr_rows:
        logger.warning("No HR metrics data returned from Athena")
        return {}

    # Find current and prior year rows
    current: dict[str, Any] = {}
    prior: dict[str, Any] = {}

    for row in hr_rows:
        yr = row.get("reporting_year")
        if yr == reporting_year:
            current = row
        elif yr == reporting_year - 1:
            prior = row

    if not current:
        logger.warning(f"No HR metrics for reporting_year={reporting_year}")
        return {}

    # Build result with pre-computed YoY changes
    result: dict[str, Any] = {
        "reporting_year": reporting_year,
        "fte_total": current.get("fte_total"),
        "fte_female_pct": current.get("fte_female_pct"),
        "fte_management_female_pct": current.get("fte_management_female_pct"),
        "new_hire_count": current.get("new_hire_count"),
        "voluntary_turnover_pct": current.get("voluntary_turnover_pct"),
        "training_hours_per_fte": current.get("training_hours_per_fte"),
        "discrimination_cases": current.get("discrimination_cases"),
        "hiring_rate_pct": current.get("hiring_rate_pct"),
        "female_headcount": current.get("female_headcount"),
        "male_headcount": current.get("male_headcount"),
    }

    # Prior year metrics
    if prior:
        result["prior_year"] = {
            "reporting_year": reporting_year - 1,
            "fte_total": prior.get("fte_total"),
            "fte_female_pct": prior.get("fte_female_pct"),
            "fte_management_female_pct": prior.get("fte_management_female_pct"),
            "new_hire_count": prior.get("new_hire_count"),
            "voluntary_turnover_pct": prior.get("voluntary_turnover_pct"),
            "training_hours_per_fte": prior.get("training_hours_per_fte"),
            "discrimination_cases": prior.get("discrimination_cases"),
            "hiring_rate_pct": prior.get("hiring_rate_pct"),
            "female_headcount": prior.get("female_headcount"),
            "male_headcount": prior.get("male_headcount"),
        }

        # Pre-compute YoY changes (model MUST NOT recalculate these)
        result["yoy_changes"] = _compute_yoy(current, prior)
    else:
        result["prior_year"] = None
        result["yoy_changes"] = None

    return result


def _compute_yoy(current: dict[str, Any], prior: dict[str, Any]) -> dict[str, Any]:
    """Compute all year-over-year changes for HR metrics.

    Args:
        current: Current year metrics dict.
        prior: Prior year metrics dict.

    Returns:
        Dict with all YoY percentage changes and percentage-point changes.
    """
    def pct_change(curr_val, prior_val) -> float | None:
        """Calculate percentage change: (current - prior) / prior * 100."""
        if curr_val is None or prior_val is None or prior_val == 0:
            return None
        return round((curr_val - prior_val) / prior_val * 100, 2)

    def pp_change(curr_val, prior_val) -> float | None:
        """Calculate percentage-point change: current - prior."""
        if curr_val is None or prior_val is None:
            return None
        return round(curr_val - prior_val, 2)

    return {
        "yoy_headcount_change_pct": pct_change(
            current.get("fte_total"), prior.get("fte_total")
        ),
        "yoy_turnover_change_pct": pct_change(
            current.get("voluntary_turnover_pct"), prior.get("voluntary_turnover_pct")
        ),
        "yoy_training_change_pct": pct_change(
            current.get("training_hours_per_fte"), prior.get("training_hours_per_fte")
        ),
        "female_pct_change_pp": pp_change(
            current.get("fte_female_pct"), prior.get("fte_female_pct")
        ),
        "mgmt_female_pct_change_pp": pp_change(
            current.get("fte_management_female_pct"), prior.get("fte_management_female_pct")
        ),
    }
