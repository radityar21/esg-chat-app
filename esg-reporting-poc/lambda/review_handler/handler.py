"""
=============================================================================
Lambda: ReviewHandlerFn
=============================================================================
Purpose:
    Handles human review approve/reject via API Gateway URL click.
    Called when reviewer clicks link in SNS email notification.

    GET /review?action=approve&token={url_encoded_task_token}
    GET /review?action=reject&token={url_encoded_task_token}

Flow:
    SNS email contains clickable URLs → Reviewer clicks → API Gateway
    → This Lambda → send-task-success/failure → Step Functions continues

Deployment:
    Runtime: Python 3.11, Memory: 128 MB, Timeout: 10s
    Behind API Gateway (REST API or Function URL)
=============================================================================
"""

from __future__ import annotations

import json
import logging
import urllib.parse
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sfn_client = boto3.client("stepfunctions", region_name="us-east-1")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle review action from API Gateway or Lambda Function URL.

    Args:
        event: API Gateway event with queryStringParameters.
        context: Lambda context.

    Returns:
        API Gateway response with HTML body.
    """
    logger.info(f"ReviewHandler invoked")

    # Extract query parameters
    params = event.get("queryStringParameters") or {}
    action = params.get("action", "").lower()
    token = params.get("token", "")

    # URL decode token (it was encoded in the link)
    token = urllib.parse.unquote(token)

    if not token:
        return _html_response(400, "Error", "Missing task token parameter.")

    if action not in ("approve", "reject"):
        return _html_response(400, "Error", f"Invalid action: '{action}'. Must be 'approve' or 'reject'.")

    try:
        if action == "approve":
            sfn_client.send_task_success(
                taskToken=token,
                output=json.dumps({"review_decision": "APPROVED"})
            )
            return _html_response(200, "Approved ✅",
                "Section has been approved and will be included in the ESG report. "
                "You can close this page.")

        else:  # reject
            sfn_client.send_task_failure(
                taskToken=token,
                error="HumanRejected",
                cause="Section rejected by human reviewer via email link."
            )
            return _html_response(200, "Rejected ❌",
                "Section has been rejected and will be excluded from the ESG report. "
                "You can close this page.")

    except sfn_client.exceptions.TaskTimedOut:
        return _html_response(410, "Expired",
            "This review link has expired. The task has already timed out or been resolved.")

    except sfn_client.exceptions.TaskDoesNotExist:
        return _html_response(404, "Not Found",
            "This review task no longer exists. It may have already been approved/rejected.")

    except Exception as e:
        logger.error(f"Error processing review: {str(e)}")
        return _html_response(500, "Error", f"Failed to process review: {str(e)}")


def _html_response(status_code: int, title: str, message: str) -> dict[str, Any]:
    """Build API Gateway HTML response.

    Args:
        status_code: HTTP status code.
        title: Page title.
        message: Body message.

    Returns:
        API Gateway proxy response dict.
    """
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>ESG Review - {title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }}
        h1 {{ color: #1B3A6B; }}
        p {{ color: #333; font-size: 16px; line-height: 1.6; }}
        .success {{ color: #2e7d32; }}
        .error {{ color: #c62828; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>{message}</p>
    <hr>
    <p style="font-size: 12px; color: #999;">ESG Reporting System | Human Review Handler</p>
</body>
</html>"""

    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "text/html"},
        "body": html,
    }
