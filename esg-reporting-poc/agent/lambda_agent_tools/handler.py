"""
Lambda for Bedrock Agent Action Group: ESGReportActions
Handles all 4 tools: generate_report, check_status, download_report, list_available_data
"""

import json
import boto3
from botocore.config import Config as BotoConfig
from datetime import datetime, timezone

sfn_client = boto3.client("stepfunctions", region_name="us-east-1")
s3_client = boto3.client("s3", region_name="us-east-1", config=BotoConfig(signature_version='s3v4'))

# Config
STATE_MACHINE_ARN = "arn:aws:states:us-east-1:061039769766:stateMachine:ESGReportGenerationStateMachine"
OUTPUT_BUCKET = "esg-output-reports-061039769766"
KB_ID = "WVREXI1LEI"
BANK_ID = "GENERIC_FI_001"

# Section templates per framework
SECTION_TEMPLATES = {
    "GRI_305": [
        {"template_id": "summary", "framework": "NONE"},
        {"template_id": "scope1", "framework": "GRI_305"},
        {"template_id": "scope2", "framework": "GRI_305"},
        {"template_id": "scope3_pcaf", "framework": "GRI_305"},
        {"template_id": "intensity", "framework": "GRI_305"},
        {"template_id": "reduction", "framework": "GRI_305"},
        {"template_id": "social", "framework": "GRI_305"},
    ],
    "IFRS_S2": [
        {"template_id": "summary", "framework": "IFRS_S2"},
        {"template_id": "governance", "framework": "IFRS_S2"},
        {"template_id": "scope1", "framework": "IFRS_S2"},
        {"template_id": "scope2", "framework": "IFRS_S2"},
        {"template_id": "scope3_pcaf", "framework": "IFRS_S2"},
        {"template_id": "intensity", "framework": "IFRS_S2"},
        {"template_id": "targets", "framework": "IFRS_S2"},
        {"template_id": "social", "framework": "IFRS_S2"},
    ],
    "CSRD_ESRS_E1": [
        {"template_id": "summary", "framework": "CSRD_ESRS_E1"},
        {"template_id": "governance", "framework": "CSRD_ESRS_E1"},
        {"template_id": "targets", "framework": "CSRD_ESRS_E1"},
        {"template_id": "scope1", "framework": "CSRD_ESRS_E1"},
        {"template_id": "scope2", "framework": "CSRD_ESRS_E1"},
        {"template_id": "scope3_pcaf", "framework": "CSRD_ESRS_E1"},
        {"template_id": "intensity", "framework": "CSRD_ESRS_E1"},
        {"template_id": "reduction", "framework": "CSRD_ESRS_E1"},
        {"template_id": "social", "framework": "CSRD_ESRS_E1"},
    ],
    "OJK_PSPK": [
        {"template_id": "summary", "framework": "OJK_PSPK"},
        {"template_id": "governance", "framework": "OJK_PSPK"},
        {"template_id": "scope1", "framework": "OJK_PSPK"},
        {"template_id": "scope2", "framework": "OJK_PSPK"},
        {"template_id": "scope3_pcaf", "framework": "OJK_PSPK"},
        {"template_id": "intensity", "framework": "OJK_PSPK"},
        {"template_id": "reduction", "framework": "OJK_PSPK"},
        {"template_id": "social", "framework": "OJK_PSPK"},
    ],
    "MULTI_FRAMEWORK": [
        {"template_id": "scope1_unified", "framework": "MULTI_FRAMEWORK"},
        {"template_id": "scope2_unified", "framework": "MULTI_FRAMEWORK"},
        {"template_id": "scope3_pcaf_unified", "framework": "MULTI_FRAMEWORK"},
        {"template_id": "intensity_unified", "framework": "MULTI_FRAMEWORK"},
        {"template_id": "reduction_unified", "framework": "MULTI_FRAMEWORK"},
        {"template_id": "social_unified", "framework": "MULTI_FRAMEWORK"},
        {"template_id": "governance_unified", "framework": "MULTI_FRAMEWORK"},
        {"template_id": "targets_unified", "framework": "MULTI_FRAMEWORK"},
        {"template_id": "summary", "framework": "NONE"},
    ],
}


def lambda_handler(event, context):
    """Bedrock Agent Action Group handler."""

    # Store event for _response() to echo back actionGroup
    global _current_event
    _current_event = event

    # Extract tool name and parameters from agent event
    action_group = event.get("actionGroup", "")
    api_path = event.get("apiPath", "")
    parameters = {}

    # Parse parameters from agent request
    if "parameters" in event:
        for param in event["parameters"]:
            parameters[param["name"]] = param["value"]

    # Also check requestBody for POST-style
    if "requestBody" in event and event["requestBody"]:
        body_content = event["requestBody"].get("content", {})
        if "application/json" in body_content:
            props = body_content["application/json"].get("properties", [])
            for prop in props:
                parameters[prop["name"]] = prop["value"]

    # Route to tool
    if api_path == "/generate_report":
        return _generate_report(parameters)
    elif api_path == "/check_status":
        return _check_status(parameters)
    elif api_path == "/download_report":
        return _download_report(parameters)
    elif api_path == "/list_available_data":
        return _list_available_data()
    else:
        return _response(f"Unknown tool: {api_path}")


def _generate_report(params):
    """Trigger Step Functions execution."""
    year = int(params.get("reporting_year", 2024))
    framework = params.get("framework", "GRI_305")
    revenue = float(params.get("revenue_idr_billion", 92000.0))

    # Validate
    if year not in (2023, 2024):
        return _response(f"Data not available for year {year}. Only 2023 and 2024 have data.")

    if framework not in SECTION_TEMPLATES:
        return _response(f"Framework '{framework}' not available. Choose: GRI_305, IFRS_S2, CSRD_ESRS_E1, OJK_PSPK, MULTI_FRAMEWORK")

    if revenue <= 0:
        return _response("Revenue must be positive. Please provide revenue in IDR billions (e.g., 92000 = IDR 92 Trillion).")

    # Build Step Functions input
    sfn_input = {
        "reporting_year": year,
        "framework": framework,
        "bank_id": BANK_ID,
        "output_bucket": OUTPUT_BUCKET,
        "revenue_idr_billion": revenue,
        "kb_id": KB_ID,
        "section_templates": SECTION_TEMPLATES[framework],
    }

    # Start execution
    response = sfn_client.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps(sfn_input),
    )

    execution_arn = response["executionArn"]
    section_count = len(SECTION_TEMPLATES[framework])

    if framework == "MULTI_FRAMEWORK":
        est_time = "8-12 minutes (14 sections across all frameworks)"
    else:
        est_time = f"3-5 minutes ({section_count} sections)"

    return _response(
        f"Report generation started!\n\n"
        f"- Year: {year}\n"
        f"- Framework: {framework}\n"
        f"- Revenue: IDR {revenue:,.0f} billion\n"
        f"- Sections: {section_count}\n"
        f"- Estimated time: {est_time}\n"
        f"- Execution ID: {execution_arn.split(':')[-1]}\n\n"
        f"Use 'check status' to monitor progress."
    )


def _check_status(params):
    """Check Step Functions execution status."""
    execution_arn = params.get("execution_arn", "")

    # If short ID provided, construct full ARN
    if not execution_arn.startswith("arn:"):
        execution_arn = f"{STATE_MACHINE_ARN.replace(':stateMachine:', ':execution:')}:{execution_arn}"

    try:
        response = sfn_client.describe_execution(executionArn=execution_arn)
    except Exception as e:
        return _response(f"Could not find execution. Error: {str(e)}")

    status = response["status"]
    start_time = response["startDate"]
    elapsed = (datetime.now(timezone.utc) - start_time.replace(tzinfo=timezone.utc)).total_seconds()

    result = f"Status: {status}\nElapsed: {int(elapsed)}s ({elapsed/60:.1f} min)\n"

    if status == "SUCCEEDED":
        output = json.loads(response.get("output", "{}"))
        assembly = output.get("assembly_result", {})
        s3_path = assembly.get("s3_path", "N/A")
        result += f"\n✅ Report complete!\nS3 Path: {s3_path}\nSize: {assembly.get('file_size_kb', '?')} KB\nSections: {assembly.get('sections_assembled', '?')}"
        result += "\n\nUse 'download report' to get the download link."
    elif status == "FAILED":
        error = response.get("error", "Unknown")
        cause = response.get("cause", "Unknown")
        result += f"\n❌ Failed: {error}\nCause: {cause}"
    elif status == "RUNNING":
        result += "\n⏳ Still running... check again in 1-2 minutes."

    return _response(result)


def _download_report(params):
    """Generate presigned URL for completed report."""
    execution_arn = params.get("execution_arn", "")

    if not execution_arn.startswith("arn:"):
        execution_arn = f"{STATE_MACHINE_ARN.replace(':stateMachine:', ':execution:')}:{execution_arn}"

    try:
        response = sfn_client.describe_execution(executionArn=execution_arn)
    except Exception as e:
        return _response(f"Could not find execution: {str(e)}")

    if response["status"] != "SUCCEEDED":
        return _response(f"Report not ready yet. Status: {response['status']}")

    output = json.loads(response.get("output", "{}"))
    s3_path = output.get("assembly_result", {}).get("s3_path", "")

    if not s3_path:
        return _response("No output file found in execution results.")

    # Parse s3://bucket/key
    bucket = s3_path.replace("s3://", "").split("/")[0]
    key = "/".join(s3_path.replace("s3://", "").split("/")[1:])

    # Generate presigned URL (1 hour)
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600,
    )

    return _response(f"Download link (valid 1 hour):\n\n{url}\n\nCopy-paste link di atas ke browser untuk download.")


def _list_available_data():
    """List years with available data."""
    return _response(
        "Available reporting data:\n\n"
        "- **2023**: Full data (energy, loans, HR metrics)\n"
        "- **2024**: Full data (energy, loans, HR metrics)\n\n"
        "Frameworks available: GRI 305, IFRS S2, CSRD/ESRS E1, OJK PSPK, All Frameworks"
    )


_current_event = {}

def _response(body, event=None):
    """Format response for Bedrock Agent."""
    evt = event or _current_event
    action_group = evt.get("actionGroup", "ESGReportActions")
    api_path = evt.get("apiPath", "/")
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "apiPath": api_path,
            "httpMethod": evt.get("httpMethod", "POST"),
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": body
                }
            }
        }
    }
