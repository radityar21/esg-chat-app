"""
Lambda: esg-dashboard-data
Purpose: Serve ESG metrics data for frontend analytics dashboard.
         Reads from S3 cache (fast, free) or refreshes from Athena on demand.

Endpoints:
    GET /dashboard-data              → Read cached data from S3
    GET /dashboard-data?refresh=true → Query Athena, update S3 cache, return fresh data

Architecture:
    Normal: S3 cache read (0 cost, <200ms)
    Refresh: Athena query → save to S3 → return (Athena scan cost, ~5-15s)
"""

import json
import boto3
import time
from datetime import datetime, timezone
from decimal import Decimal
from botocore.config import Config as BotoConfig

ACCOUNT_ID = "061039769766"
CACHE_BUCKET = f"esg-data-aggregated-{ACCOUNT_ID}"
CACHE_KEY = "dashboard-cache/latest.json"
ATHENA_WORKGROUP = "esg-reporting-workgroup"
ATHENA_DATABASE = "esg_aggregated"
REPORTING_YEAR = 2024
BANK_ID = "GENERIC_FI_001"

s3_client = boto3.client("s3", config=BotoConfig(signature_version='s3v4'))
athena_client = boto3.client("athena", region_name="us-east-1")

HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Content-Type": "application/json",
}

# ─── SQL Queries ───────────────────────────────────────────────────────────────

QUERY_GHG_SUMMARY = """
SELECT
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
WHERE reporting_year = {year}
  AND metric_key LIKE '{bank_id}_%'
"""

QUERY_PRIOR_YEAR = """
SELECT
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
WHERE reporting_year = {prior_year}
  AND metric_key LIKE '{bank_id}_%'
"""

QUERY_PCAF_SECTORS = """
SELECT
    sector_display_name,
    total_outstanding_idr_trillion,
    financed_emissions_gross_tco2e,
    financed_emissions_weighted_tco2e,
    emission_intensity_per_idr_bn,
    avg_pcaf_score,
    pct_of_total_portfolio,
    pct_of_total_financed_emissions,
    yoy_change_emissions_pct
FROM esg_aggregated.pcaf_by_sector
WHERE reporting_year = {year}
ORDER BY financed_emissions_gross_tco2e DESC
LIMIT 10
"""

QUERY_SCOPE1_FACILITIES = """
SELECT
    facility_id,
    scope1_tco2e,
    scope1_natgas_tco2e,
    scope1_diesel_tco2e,
    data_quality_score
FROM esg_aggregated.scope1_by_facility
WHERE reporting_year = {year}
ORDER BY scope1_tco2e DESC
LIMIT 10
"""

QUERY_HR_METRICS = """
SELECT
    reporting_year,
    fte_total,
    fte_female_pct,
    fte_management_female_pct,
    new_hire_count,
    voluntary_turnover_pct,
    training_hours_per_fte,
    discrimination_cases
FROM esg_raw.hr_metrics
WHERE reporting_year IN ({year}, {prior_year})
ORDER BY reporting_year DESC
"""


def lambda_handler(event, context):
    http_method = event.get("httpMethod", "GET")
    if http_method == "OPTIONS":
        return {"statusCode": 200, "headers": HEADERS, "body": ""}

    params = event.get("queryStringParameters") or {}
    refresh = params.get("refresh", "false").lower() == "true"

    if refresh:
        # Query Athena fresh and update S3 cache
        try:
            data = _query_athena_all()
            _save_to_s3(data)
            return _success(data)
        except Exception as e:
            return _error(f"Athena refresh failed: {str(e)}")
    else:
        # Read from S3 cache
        try:
            data = _read_from_s3()
            if data:
                return _success(data)
            else:
                # No cache exists yet, try Athena
                data = _query_athena_all()
                _save_to_s3(data)
                return _success(data)
        except Exception as e:
            return _error(f"Failed to load dashboard data: {str(e)}")


def _query_athena_all():
    """Execute all Athena queries and build dashboard data structure."""
    year = REPORTING_YEAR
    prior_year = year - 1
    bank_id = BANK_ID

    ghg = _run_query(QUERY_GHG_SUMMARY.format(year=year, bank_id=bank_id))
    prior = _run_query(QUERY_PRIOR_YEAR.format(prior_year=prior_year, bank_id=bank_id))
    pcaf = _run_query(QUERY_PCAF_SECTORS.format(year=year))
    facilities = _run_query(QUERY_SCOPE1_FACILITIES.format(year=year))
    hr = _run_query(QUERY_HR_METRICS.format(year=year, prior_year=prior_year))

    ghg_row = _parse_single(ghg)
    prior_row = _parse_single(prior)
    pcaf_rows = _parse_multi(pcaf)
    facility_rows = _parse_multi(facilities)
    hr_rows = _parse_multi(hr)

    # Build structured response
    data = {
        "reporting_year": year,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "ghg_summary": ghg_row,
        "prior_year_summary": prior_row,
        "pcaf_sectors": pcaf_rows,
        "scope1_facilities": facility_rows,
        "hr_metrics": hr_rows,
    }
    return data


def _run_query(sql):
    """Execute Athena query and return raw results."""
    response = athena_client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": ATHENA_DATABASE, "Catalog": "AwsDataCatalog"},
        WorkGroup=ATHENA_WORKGROUP,
        ResultConfiguration={
            "OutputLocation": f"s3://{CACHE_BUCKET}/athena-results/dashboard/"
        },
    )
    execution_id = response["QueryExecutionId"]

    # Poll until complete
    for _ in range(30):
        time.sleep(2)
        status = athena_client.get_query_execution(QueryExecutionId=execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            break
        elif state in ("FAILED", "CANCELLED"):
            reason = status["QueryExecution"]["Status"].get("StateChangeReason", "unknown")
            raise RuntimeError(f"Query failed: {reason}")
    else:
        raise RuntimeError("Query timed out")

    results = athena_client.get_query_results(QueryExecutionId=execution_id)
    return results["ResultSet"]["Rows"]


def _parse_single(rows):
    """Parse single-row Athena result into dict."""
    if len(rows) < 2:
        return {}
    headers = [col["VarCharValue"] for col in rows[0]["Data"]]
    values = [col.get("VarCharValue", "") for col in rows[1]["Data"]]
    return {h: _cast(v) for h, v in zip(headers, values)}


def _parse_multi(rows):
    """Parse multi-row Athena result into list of dicts."""
    if len(rows) < 2:
        return []
    headers = [col["VarCharValue"] for col in rows[0]["Data"]]
    result = []
    for row in rows[1:]:
        values = [col.get("VarCharValue", "") for col in row["Data"]]
        result.append({h: _cast(v) for h, v in zip(headers, values)})
    return result


def _cast(val):
    """Cast Athena string value to appropriate type."""
    if val == "" or val is None:
        return None
    try:
        if "." in val:
            return float(val)
        return int(val)
    except (ValueError, TypeError):
        return val


def _save_to_s3(data):
    """Save dashboard data to S3 cache."""
    s3_client.put_object(
        Bucket=CACHE_BUCKET,
        Key=CACHE_KEY,
        Body=json.dumps(data, default=str),
        ContentType="application/json",
    )


def _read_from_s3():
    """Read cached dashboard data from S3."""
    try:
        response = s3_client.get_object(Bucket=CACHE_BUCKET, Key=CACHE_KEY)
        return json.loads(response["Body"].read().decode("utf-8"))
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception:
        return None


def _success(data):
    return {
        "statusCode": 200,
        "headers": HEADERS,
        "body": json.dumps(data, default=str),
    }


def _error(msg):
    return {
        "statusCode": 500,
        "headers": HEADERS,
        "body": json.dumps({"error": msg}),
    }
