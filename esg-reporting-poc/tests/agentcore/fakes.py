"""In-memory AWS fake for orchestrator tests. No network, no boto3."""

from __future__ import annotations

import json
from typing import Any, Callable


class FakeAws:
    def __init__(self) -> None:
        self.t = 1_800_000_000.0
        self.s3: dict[tuple[str, str], Any] = {}
        self.executions: dict[str, dict[str, Any]] = {}
        self.history: dict[str, list[dict[str, Any]]] = {}
        self.lambdas: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.started: list[tuple[str, dict[str, Any]]] = []
        self._n = 0

    # time
    def now(self) -> float:
        self.t += 1
        return self.t

    # sfn
    def sfn_start(self, state_machine_arn: str, payload: dict[str, Any], name: str | None = None) -> str:
        self._n += 1
        arn = f"{state_machine_arn.replace(':stateMachine:', ':execution:')}:exec-{self._n}"
        self.executions[arn] = {"status": "RUNNING", "startDate": self.t, "stopDate": None, "input": payload, "output": None,
                                "error": None, "cause": None, "stateMachineArn": state_machine_arn}
        self.started.append((state_machine_arn, payload))
        return arn

    def sfn_describe(self, execution_arn: str) -> dict[str, Any]:
        return json.loads(json.dumps(self.executions[execution_arn]))

    def sfn_history(self, execution_arn: str, max_events: int = 400) -> list[dict[str, Any]]:
        return self.history.get(execution_arn, [])

    def finish(self, arn: str, status: str, output: dict[str, Any] | None = None, error: str | None = None, cause: str | None = None) -> None:
        self.executions[arn].update({"status": status, "output": output, "error": error, "cause": cause, "stopDate": self.t + 5})

    # lambda
    def lambda_invoke(self, function_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("lambda", function_name, payload))
        return self.lambdas[function_name](payload)

    # s3
    def s3_get_json(self, bucket: str, key: str) -> dict[str, Any] | None:
        v = self.s3.get((bucket, key))
        return json.loads(json.dumps(v)) if v is not None else None

    def s3_put_json(self, bucket: str, key: str, body: dict[str, Any]) -> None:
        self.s3[(bucket, key)] = json.loads(json.dumps(body, default=str))

    def s3_copy(self, bucket: str, src_key: str, dst_key: str) -> None:
        self.s3[(bucket, dst_key)] = self.s3.get((bucket, src_key))

    def s3_put_if_absent(self, bucket: str, key: str, body: dict[str, Any]) -> bool:
        if (bucket, key) in self.s3:
            return False
        self.s3[(bucket, key)] = body
        return True

    def s3_delete(self, bucket: str, key: str) -> None:
        self.s3.pop((bucket, key), None)

    def s3_presign(self, bucket: str, key: str, expires: int = 3600) -> str:
        return f"https://signed.example/{bucket}/{key}"
