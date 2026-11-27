"""Thin AWS gateway. The orchestrator only talks to AWS through this interface, which makes the
self-correction loop fully testable with an in-memory fake (see tests/agentcore/fakes.py)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Protocol


class AwsGateway(Protocol):
    # Step Functions
    def sfn_start(self, state_machine_arn: str, payload: dict[str, Any], name: str | None = None) -> str: ...
    def sfn_describe(self, execution_arn: str) -> dict[str, Any]: ...
    def sfn_history(self, execution_arn: str, max_events: int = 400) -> list[dict[str, Any]]: ...
    # Lambda
    def lambda_invoke(self, function_name: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    # S3
    def s3_get_json(self, bucket: str, key: str) -> dict[str, Any] | None: ...
    def s3_put_json(self, bucket: str, key: str, body: dict[str, Any]) -> None: ...
    def s3_copy(self, bucket: str, src_key: str, dst_key: str) -> None: ...
    def s3_put_if_absent(self, bucket: str, key: str, body: dict[str, Any]) -> bool: ...
    def s3_delete(self, bucket: str, key: str) -> None: ...
    def s3_presign(self, bucket: str, key: str, expires: int = 3600) -> str: ...
    def now(self) -> float: ...


def short_id(execution_arn_or_id: str) -> str:
    return execution_arn_or_id.split(":")[-1]


class RealAws:
    """boto3-backed implementation. Clients are created lazily so importing this module is free."""

    def __init__(self, region: str = "us-east-1") -> None:
        import boto3
        from botocore.config import Config

        cfg = Config(read_timeout=900, connect_timeout=10, retries={"max_attempts": 3, "mode": "standard"})
        self._sfn = boto3.client("stepfunctions", region_name=region, config=cfg)
        self._lambda = boto3.client("lambda", region_name=region, config=cfg)
        self._s3 = boto3.client("s3", region_name=region, config=Config(signature_version="s3v4"))

    # --- Step Functions ---------------------------------------------------------------------------
    def sfn_start(self, state_machine_arn: str, payload: dict[str, Any], name: str | None = None) -> str:
        kwargs: dict[str, Any] = {"stateMachineArn": state_machine_arn, "input": json.dumps(payload)}
        if name:
            kwargs["name"] = name
        return self._sfn.start_execution(**kwargs)["executionArn"]

    def sfn_describe(self, execution_arn: str) -> dict[str, Any]:
        d = self._sfn.describe_execution(executionArn=execution_arn)
        return {
            "status": d["status"],
            "startDate": d["startDate"].timestamp() if d.get("startDate") else None,
            "stopDate": d["stopDate"].timestamp() if d.get("stopDate") else None,
            "input": json.loads(d.get("input") or "{}"),
            "output": json.loads(d["output"]) if d.get("output") else None,
            "error": d.get("error"),
            "cause": d.get("cause"),
            "stateMachineArn": d.get("stateMachineArn"),
        }

    def sfn_history(self, execution_arn: str, max_events: int = 400) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {"executionArn": execution_arn, "reverseOrder": True, "includeExecutionData": False, "maxResults": 100}
        while len(events) < max_events:
            resp = self._sfn.get_execution_history(**kwargs)
            events.extend(resp.get("events", []))
            token = resp.get("nextToken")
            if not token:
                break
            kwargs["nextToken"] = token
        return events

    # --- Lambda -----------------------------------------------------------------------------------
    def lambda_invoke(self, function_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        resp = self._lambda.invoke(FunctionName=function_name, InvocationType="RequestResponse", Payload=json.dumps(payload).encode())
        body = resp["Payload"].read().decode() or "{}"
        if resp.get("FunctionError"):
            raise RuntimeError(f"{function_name} failed: {body[:500]}")
        return json.loads(body)

    # --- S3 ---------------------------------------------------------------------------------------
    def s3_get_json(self, bucket: str, key: str) -> dict[str, Any] | None:
        try:
            return json.loads(self._s3.get_object(Bucket=bucket, Key=key)["Body"].read())
        except self._s3.exceptions.NoSuchKey:
            return None

    def s3_put_json(self, bucket: str, key: str, body: dict[str, Any]) -> None:
        self._s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(body, ensure_ascii=False, default=str).encode(), ContentType="application/json")

    def s3_copy(self, bucket: str, src_key: str, dst_key: str) -> None:
        self._s3.copy_object(Bucket=bucket, Key=dst_key, CopySource={"Bucket": bucket, "Key": src_key})

    def s3_put_if_absent(self, bucket: str, key: str, body: dict[str, Any]) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(body).encode(), IfNoneMatch="*")
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("PreconditionFailed", "ConditionalRequestConflict", "412"):
                return False
            raise

    def s3_delete(self, bucket: str, key: str) -> None:
        self._s3.delete_object(Bucket=bucket, Key=key)

    def s3_presign(self, bucket: str, key: str, expires: int = 3600) -> str:
        return self._s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires)

    def now(self) -> float:
        return time.time()


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
