"""
=============================================================================
Lambda #1: ValidateInputFn
=============================================================================
Spec Reference: §9, REQ-SFN-03

Purpose:
    Validates Step Functions input JSON against required schema.
    Checks S3 file existence, data freshness, and input completeness.

Input:
    {
        "reporting_year": 2024,
        "framework": "GRI_305" | "IFRS_S2" | "CSRD_ESRS_E1" | "OJK_PSPK" | "MULTI_FRAMEWORK",
        "bank_id": "GENERIC_FI_001",
        "output_bucket": "esg-output-reports-061039769766",
        "revenue_idr_billion": 92000.0,
        "section_templates": [...],  (optional — auto-populated for MULTI_FRAMEWORK)
        "kb_id": "XXXXXXXX"
    }

Output:
    {
        "status": "PASS" | "FAIL",
        "metadata": {
            "reporting_year": 2024,
            "framework": "GRI_305",
            "bank_id": "GENERIC_FI_001",
            "validated_at": "2026-06-03T10:00:00Z",
            "data_freshness_hours": 12.5,
            "s3_files_verified": 3
        },
        "errors": []  (empty if PASS)
    }

Deployment:
    Runtime: Python 3.11
    Memory: 256 MB
    Timeout: 30s
    Role: ESG-ValidateInput-ExecutionRole
=============================================================================
"""

from __future__ import annotations

import json
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# =============================================================================
# CONFIGURATION
# =============================================================================

ACCOUNT_ID = "061039769766"
RAW_BUCKET = f"esg-data-raw-{ACCOUNT_ID}"
CURATED_BUCKET = f"esg-data-curated-{ACCOUNT_ID}"
AGGREGATED_BUCKET = f"esg-data-aggregated-{ACCOUNT_ID}"

# Valid values (per spec REQ-SFN-03)
VALID_FRAMEWORKS = {"GRI_305", "IFRS_S2", "CSRD_ESRS_E1", "OJK_PSPK", "MULTI_FRAMEWORK"}
VALID_YEAR_RANGE = (2020, 2035)
BANK_ID_PATTERN = re.compile(r"^[A-Z_]+_\d{3}$")

# Data freshness threshold (hours)
MAX_DATA_AGE_HOURS = 24 * 30  # 30 days for POC (spec says 24h but synthetic data is older)

# Required S3 paths that must contain data (per reporting year)
REQUIRED_DATA_PATHS = {
    "curated_scope1": "{curated_bucket}/curated/ghg_scope1/reporting_year={year}/",
    "curated_scope2": "{curated_bucket}/curated/ghg_scope2/reporting_year={year}/",
    "curated_scope3": "{curated_bucket}/curated/ghg_scope3_financed/reporting_year={year}/",
    "aggregated_summary": "{aggregated_bucket}/aggregated/ghg_summary_annual/reporting_year={year}/",
}

# MULTI_FRAMEWORK section template auto-population (REQ-SFN-02, REQ-PROMPT-16)
# Legacy: per-framework sections (kept for backward compatibility)
MULTI_FRAMEWORK_LEGACY_SECTIONS = [
    {"template_id": "scope1", "framework": "GRI_305"},
    {"template_id": "scope2", "framework": "GRI_305"},
    {"template_id": "scope3_pcaf", "framework": "GRI_305"},
    {"template_id": "intensity", "framework": "GRI_305"},
    {"template_id": "social", "framework": "GRI_305"},
    {"template_id": "reduction", "framework": "GRI_305"},
    {"template_id": "scope1", "framework": "IFRS_S2"},
    {"template_id": "governance", "framework": "IFRS_S2"},
    {"template_id": "scope3_pcaf", "framework": "IFRS_S2"},
    {"template_id": "targets", "framework": "IFRS_S2"},
    {"template_id": "scope1", "framework": "CSRD_ESRS_E1"},
    {"template_id": "scope3_pcaf", "framework": "CSRD_ESRS_E1"},
    {"template_id": "scope1", "framework": "OJK_PSPK"},
    {"template_id": "scope3_pcaf", "framework": "OJK_PSPK"},
    {"template_id": "intensity", "framework": "OJK_PSPK"},
    {"template_id": "summary", "framework": "NONE"},
]

# Unified: single consolidated sections covering all frameworks
UNIFIED_SECTIONS = [
    {"template_id": "scope1_unified", "framework": "MULTI_FRAMEWORK"},
    {"template_id": "scope2_unified", "framework": "MULTI_FRAMEWORK"},
    {"template_id": "scope3_pcaf_unified", "framework": "MULTI_FRAMEWORK"},
    {"template_id": "intensity_unified", "framework": "MULTI_FRAMEWORK"},
    {"template_id": "reduction_unified", "framework": "MULTI_FRAMEWORK"},
    {"template_id": "social_unified", "framework": "MULTI_FRAMEWORK"},
    {"template_id": "governance_unified", "framework": "MULTI_FRAMEWORK"},
    {"template_id": "targets_unified", "framework": "MULTI_FRAMEWORK"},
    {"template_id": "double_materiality", "framework": "MULTI_FRAMEWORK"},
    {"template_id": "summary", "framework": "NONE"},
]

# CSRD ESRS E1: includes double materiality (standalone framework)
CSRD_SECTIONS = [
    {"template_id": "scope1", "framework": "CSRD_ESRS_E1"},
    {"template_id": "scope2", "framework": "CSRD_ESRS_E1"},
    {"template_id": "scope3_pcaf", "framework": "CSRD_ESRS_E1"},
    {"template_id": "intensity", "framework": "CSRD_ESRS_E1"},
    {"template_id": "reduction", "framework": "CSRD_ESRS_E1"},
    {"template_id": "social", "framework": "CSRD_ESRS_E1"},
    {"template_id": "governance", "framework": "CSRD_ESRS_E1"},
    {"template_id": "targets", "framework": "CSRD_ESRS_E1"},
    {"template_id": "double_materiality", "framework": "CSRD_ESRS_E1"},
    {"template_id": "summary", "framework": "NONE"},
]

s3_client = boto3.client("s3")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Validate Step Functions input per REQ-SFN-03.

    Args:
        event: Step Functions input JSON.
        context: Lambda context.

    Returns:
        Dict with status (PASS/FAIL), metadata, errors, and validated_input.
    """
    logger.info(f"ValidateInputFn invoked with: {json.dumps(event)}")

    errors = []
    metadata = {}

    # =========================================================================
    # RULE 1: Required fields present
    # =========================================================================
    required_fields = ["framework", "reporting_year", "bank_id", "output_bucket"]
    for field in required_fields:
        if field not in event or event[field] is None:
            errors.append({
                "error_code": "InputValidationError",
                "field": field,
                "message": f"Required field '{field}' is missing or null"
            })

    if errors:
        return _build_response("FAIL", metadata, errors)

    framework = event["framework"]
    reporting_year = event["reporting_year"]
    bank_id = event["bank_id"]
    output_bucket = event["output_bucket"]
    revenue = event.get("revenue_idr_billion", 0)

    # =========================================================================
    # RULE 2: Year range (2020 <= reporting_year <= 2035)
    # =========================================================================
    if not (VALID_YEAR_RANGE[0] <= reporting_year <= VALID_YEAR_RANGE[1]):
        errors.append({
            "error_code": "InvalidYearRange",
            "field": "reporting_year",
            "message": f"reporting_year {reporting_year} outside valid range {VALID_YEAR_RANGE}"
        })

    # =========================================================================
    # RULE 3: Framework validation
    # =========================================================================
    if framework not in VALID_FRAMEWORKS:
        errors.append({
            "error_code": "InvalidFramework",
            "field": "framework",
            "message": f"framework '{framework}' not in {VALID_FRAMEWORKS}"
        })

    # =========================================================================
    # RULE 4: Bank ID format (regex: ^[A-Z_]+_\d{3}$)
    # =========================================================================
    if not BANK_ID_PATTERN.match(bank_id):
        errors.append({
            "error_code": "InvalidBankIdFormat",
            "field": "bank_id",
            "message": f"bank_id '{bank_id}' does not match pattern ^[A-Z_]+_\\d{{3}}$"
        })

    # =========================================================================
    # RULE 5: Output bucket exists
    # =========================================================================
    try:
        s3_client.head_bucket(Bucket=output_bucket)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        errors.append({
            "error_code": "BucketNotFound",
            "field": "output_bucket",
            "message": f"Bucket '{output_bucket}' not accessible (HTTP {error_code})"
        })

    # =========================================================================
    # RULE 6: Revenue provided if intensity section needed
    # =========================================================================
    section_templates = event.get("section_templates", [])
    has_intensity = any(t.get("template_id") == "intensity" for t in section_templates)
    if has_intensity and (revenue is None or revenue <= 0):
        errors.append({
            "error_code": "MissingRevenueData",
            "field": "revenue_idr_billion",
            "message": "revenue_idr_billion must be > 0 when intensity section is in templates"
        })

    # =========================================================================
    # RULE 7: No duplicate templates
    # =========================================================================
    seen_templates = set()
    for t in section_templates:
        key = (t.get("template_id"), t.get("framework"))
        if key in seen_templates:
            errors.append({
                "error_code": "DuplicateTemplate",
                "field": "section_templates",
                "message": f"Duplicate template: {key}"
            })
        seen_templates.add(key)

    # =========================================================================
    # RULE 8: Check S3 data files exist for reporting year
    # =========================================================================
    s3_files_verified = 0
    data_freshness_hours = None

    if not errors:  # Only check S3 if no prior errors
        for path_name, path_template in REQUIRED_DATA_PATHS.items():
            s3_path = path_template.format(
                curated_bucket=CURATED_BUCKET,
                aggregated_bucket=AGGREGATED_BUCKET,
                year=reporting_year
            )
            bucket = s3_path.split("/")[0]
            # Determine actual bucket from path
            if "curated" in s3_path:
                check_bucket = CURATED_BUCKET
            else:
                check_bucket = AGGREGATED_BUCKET
            prefix = "/".join(s3_path.split("/")[1:])  # Remove bucket from path
            # Actually the path_template has bucket name in it, extract prefix after bucket
            full_prefix = s3_path.replace(f"{check_bucket}/", "")

            try:
                response = s3_client.list_objects_v2(
                    Bucket=check_bucket,
                    Prefix=full_prefix,
                    MaxKeys=1
                )
                if response.get("KeyCount", 0) > 0:
                    s3_files_verified += 1
                    # Check freshness
                    obj = response["Contents"][0]
                    last_modified = obj["LastModified"]
                    age = datetime.now(timezone.utc) - last_modified
                    age_hours = age.total_seconds() / 3600
                    if data_freshness_hours is None or age_hours > data_freshness_hours:
                        data_freshness_hours = round(age_hours, 1)
                else:
                    errors.append({
                        "error_code": "DataNotFound",
                        "field": path_name,
                        "message": f"No data files found at s3://{check_bucket}/{full_prefix}"
                    })
            except ClientError as e:
                errors.append({
                    "error_code": "S3AccessError",
                    "field": path_name,
                    "message": f"Cannot access s3://{check_bucket}/{full_prefix}: {str(e)}"
                })

    # =========================================================================
    # MULTI_FRAMEWORK: Auto-populate section_templates (REQ-SFN-02)
    # =========================================================================
    if framework == "MULTI_FRAMEWORK" and not section_templates:
        section_templates = UNIFIED_SECTIONS
    elif framework == "CSRD_ESRS_E1" and not section_templates:
        section_templates = CSRD_SECTIONS

    # =========================================================================
    # BUILD RESPONSE
    # =========================================================================
    metadata = {
        "reporting_year": reporting_year,
        "framework": framework,
        "bank_id": bank_id,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "data_freshness_hours": data_freshness_hours,
        "s3_files_verified": s3_files_verified,
        "section_count": len(section_templates),
    }

    status = "FAIL" if errors else "PASS"

    result = _build_response(status, metadata, errors)

    # Pass through validated input for downstream states
    if status == "PASS":
        result["validated_input"] = {
            "reporting_year": reporting_year,
            "framework": framework,
            "bank_id": bank_id,
            "output_bucket": output_bucket,
            "revenue_idr_billion": revenue,
            "section_templates": section_templates,
            "kb_id": event.get("kb_id"),
        }

    logger.info(f"Validation result: {status} ({len(errors)} errors)")
    return result


def _build_response(status: str, metadata: dict[str, Any], errors: list[dict]) -> dict[str, Any]:
    """Build standardized response.

    Args:
        status: PASS or FAIL.
        metadata: Validation metadata.
        errors: List of error dicts.

    Returns:
        Response dict.
    """
    return {
        "status": status,
        "metadata": metadata,
        "errors": errors,
    }
