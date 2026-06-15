"""
Chat API Lambda — Proxy between frontend and Bedrock Agent.
Handles POST /chat with message body, invokes Bedrock Agent, returns response.
"""

import json
import uuid
import boto3

bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

AGENT_ID = "MBERNIQMBG"
AGENT_ALIAS_ID = "QIXEJW2TN6"


def lambda_handler(event, context):
    """Handle chat request from frontend."""
    # CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return _cors_response(200, "")

    try:
        body = json.loads(event.get("body", "{}"))
    except:
        return _cors_response(400, json.dumps({"error": "Invalid JSON body"}))

    message = body.get("message", "")
    session_id = body.get("session_id", str(uuid.uuid4()))

    if not message:
        return _cors_response(400, json.dumps({"error": "message is required"}))

    # Invoke Bedrock Agent
    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=message,
        )

        # Collect streaming response
        completion = ""
        for event_stream in response["completion"]:
            if "chunk" in event_stream:
                chunk = event_stream["chunk"]
                completion += chunk["bytes"].decode("utf-8")

        return _cors_response(200, json.dumps({
            "response": completion,
            "session_id": session_id,
        }))

    except Exception as e:
        return _cors_response(500, json.dumps({
            "error": str(e),
            "session_id": session_id,
        }))


def _cors_response(status_code, body):
    """Return response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
        },
        "body": body,
    }
