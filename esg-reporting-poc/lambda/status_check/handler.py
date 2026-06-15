"""
Lambda: esg-status-check
Purpose: Direct Step Functions status check — no LLM, deterministic response.
Called by frontend polling via API Gateway /status endpoint.

Input (via API Gateway query params or POST body):
    execution_id: short ID or full ARN

Output:
    {status: "RUNNING"|"SUCCEEDED"|"FAILED", elapsed_seconds: N, s3_path: "...", ...}
"""

import json
import boto3
from botocore.config import Config as BotoConfig
from datetime import datetime, timezone

sfn_client = boto3.client("stepfunctions", region_name="us-east-1")
s3_client = boto3.client("s3", region_name="us-east-1", config=BotoConfig(signature_version='s3v4'))

STATE_MACHINE_ARN = "arn:aws:states:us-east-1:061039769766:stateMachine:ESGReportGenerationStateMachine"


def lambda_handler(event, context):
    """Handle status check request from API Gateway."""

    # CORS headers
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Content-Type": "application/json",
    }

    # Handle OPTIONS preflight
    http_method = event.get("httpMethod", "GET")
    if http_method == "OPTIONS":
        return {"statusCode": 200, "headers": headers, "body": ""}

    # Extract execution_id from query params or body
    execution_id = None

    # Try query string params first (GET)
    params = event.get("queryStringParameters") or {}
    execution_id = params.get("execution_id")

    # Try body (POST)
    if not execution_id and event.get("body"):
        try:
            body = json.loads(event["body"])
            execution_id = body.get("execution_id")
        except (json.JSONDecodeError, TypeError):
            pass

    if not execution_id:
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps({"error": "execution_id required"}),
        }

    # Build full ARN if short ID provided
    if not execution_id.startswith("arn:"):
        execution_arn = f"{STATE_MACHINE_ARN.replace(':stateMachine:', ':execution:')}:{execution_id}"
    else:
        execution_arn = execution_id

    # Describe execution
    try:
        response = sfn_client.describe_execution(executionArn=execution_arn)
    except sfn_client.exceptions.ExecutionDoesNotExist:
        return {
            "statusCode": 404,
            "headers": headers,
            "body": json.dumps({"error": "Execution not found", "execution_id": execution_id}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": str(e)}),
        }

    status = response["status"]
    start_time = response["startDate"].replace(tzinfo=timezone.utc)
    elapsed = int((datetime.now(timezone.utc) - start_time).total_seconds())

    result = {
        "status": status,
        "elapsed_seconds": elapsed,
        "execution_id": execution_id,
    }

    if status == "SUCCEEDED":
        try:
            output = json.loads(response.get("output", "{}"))
            assembly = output.get("assembly_result", {})
            result["s3_path"] = assembly.get("s3_path", "")
            result["file_size_kb"] = assembly.get("file_size_kb", 0)
            result["sections_assembled"] = assembly.get("sections_assembled", 0)

            # Generate presigned URL for DOCX
            s3_path = result["s3_path"]
            if s3_path.startswith("s3://"):
                bucket = s3_path.replace("s3://", "").split("/")[0]
                key = "/".join(s3_path.replace("s3://", "").split("/")[1:])
                presigned_url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=3600,
                )
                result["download_url"] = presigned_url

            # Generate presigned URL for PPTX (if available)
            pptx_path = assembly.get("s3_path_pptx", "")
            if pptx_path and pptx_path.startswith("s3://"):
                pptx_bucket = pptx_path.replace("s3://", "").split("/")[0]
                pptx_key = "/".join(pptx_path.replace("s3://", "").split("/")[1:])
                pptx_url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": pptx_bucket, "Key": pptx_key},
                    ExpiresIn=3600,
                )
                result["download_url_pptx"] = pptx_url
        except Exception:
            pass

    elif status == "FAILED":
        result["error"] = response.get("error", "Unknown")
        result["cause"] = response.get("cause", "Unknown")[:500]

    return {
        "statusCode": 200,
        "headers": headers,
        "body": json.dumps(result),
    }
