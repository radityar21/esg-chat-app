"""
Lambda: esg-history
Purpose: Return list of recent Step Functions executions + document listing.
Called by frontend via API Gateway GET /history and GET /history?type=documents

Input (query params):
    type: "executions" (default) | "documents"
    limit: number (default 10, max 20)

Output:
    For executions: {executions: [...], total_succeeded, total_failed, total_running}
    For documents: {documents: [...], total_count}
"""

import json
import boto3
from botocore.config import Config as BotoConfig
from datetime import datetime, timezone

sfn_client = boto3.client("stepfunctions", region_name="us-east-1")
s3_client = boto3.client("s3", region_name="us-east-1", config=BotoConfig(signature_version='s3v4'))

STATE_MACHINE_ARN = "arn:aws:states:us-east-1:061039769766:stateMachine:ESGReportGenerationStateMachine"
OUTPUT_BUCKET = "esg-output-reports-061039769766"
KB_BUCKET = "esg-kb-documents-061039769766"

HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Content-Type": "application/json",
}


def lambda_handler(event, context):
    http_method = event.get("httpMethod", "GET")
    if http_method == "OPTIONS":
        return {"statusCode": 200, "headers": HEADERS, "body": ""}

    params = event.get("queryStringParameters") or {}
    query_type = params.get("type", "executions")
    limit = min(int(params.get("limit", "10")), 20)

    if query_type == "documents":
        return _list_documents()
    else:
        return _list_executions(limit)


def _list_executions(limit: int) -> dict:
    """List recent Step Functions executions with download URLs."""
    try:
        # Get all statuses
        executions = []
        counts = {"SUCCEEDED": 0, "FAILED": 0, "RUNNING": 0}

        for status in ["SUCCEEDED", "FAILED", "RUNNING"]:
            try:
                resp = sfn_client.list_executions(
                    stateMachineArn=STATE_MACHINE_ARN,
                    maxResults=limit,
                    statusFilter=status
                )
                for ex in resp.get("executions", []):
                    counts[status] += 1
                    entry = {
                        "execution_id": ex["name"],
                        "status": status,
                        "start_time": ex["startDate"].isoformat(),
                        "framework": "",
                        "reporting_year": 0,
                    }
                    if ex.get("stopDate"):
                        entry["end_time"] = ex["stopDate"].isoformat()
                        entry["duration_seconds"] = int((ex["stopDate"] - ex["startDate"]).total_seconds())

                    # Get details for succeeded executions
                    if status == "SUCCEEDED":
                        try:
                            desc = sfn_client.describe_execution(executionArn=ex["executionArn"])
                            output = json.loads(desc.get("output", "{}"))
                            inp = json.loads(desc.get("input", "{}"))
                            entry["framework"] = inp.get("framework", "")
                            entry["reporting_year"] = inp.get("reporting_year", 0)

                            assembly = output.get("assembly_result", {})
                            s3_path = assembly.get("s3_path", "")
                            pptx_path = assembly.get("s3_path_pptx", "")

                            if s3_path.startswith("s3://"):
                                bucket = s3_path.replace("s3://", "").split("/")[0]
                                key = "/".join(s3_path.replace("s3://", "").split("/")[1:])
                                entry["download_url"] = s3_client.generate_presigned_url(
                                    "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)

                            if pptx_path and pptx_path.startswith("s3://"):
                                pptx_bucket = pptx_path.replace("s3://", "").split("/")[0]
                                pptx_key = "/".join(pptx_path.replace("s3://", "").split("/")[1:])
                                entry["download_url_pptx"] = s3_client.generate_presigned_url(
                                    "get_object", Params={"Bucket": pptx_bucket, "Key": pptx_key}, ExpiresIn=3600)

                            entry["file_size_kb"] = assembly.get("file_size_kb", 0)
                            entry["sections_assembled"] = assembly.get("sections_assembled", 0)
                        except Exception:
                            pass
                    elif status == "RUNNING":
                        try:
                            desc = sfn_client.describe_execution(executionArn=ex["executionArn"])
                            inp = json.loads(desc.get("input", "{}"))
                            entry["framework"] = inp.get("framework", "")
                            entry["reporting_year"] = inp.get("reporting_year", 0)
                        except Exception:
                            pass

                    executions.append(entry)
            except Exception:
                pass

        # Sort by start_time descending
        executions.sort(key=lambda x: x.get("start_time", ""), reverse=True)

        return {
            "statusCode": 200,
            "headers": HEADERS,
            "body": json.dumps({
                "executions": executions[:limit],
                "total_succeeded": counts["SUCCEEDED"],
                "total_failed": counts["FAILED"],
                "total_running": counts["RUNNING"],
            }),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": HEADERS,
            "body": json.dumps({"error": str(e)}),
        }


def _list_documents() -> dict:
    """List reference documents in KB bucket."""
    try:
        documents = []
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=KB_BUCKET):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.startswith("prompts/"):
                    continue
                if key.endswith(".metadata.json"):
                    continue
                if obj["Size"] < 100:
                    continue
                documents.append({
                    "key": key,
                    "category": key.split("/")[0] if "/" in key else "other",
                    "filename": key.split("/")[-1],
                    "size_kb": round(obj["Size"] / 1024, 1),
                    "last_modified": obj["LastModified"].isoformat(),
                })

        return {
            "statusCode": 200,
            "headers": HEADERS,
            "body": json.dumps({
                "documents": documents,
                "total_count": len(documents),
            }),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": HEADERS,
            "body": json.dumps({"error": str(e)}),
        }
