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


# ── strategy memory and critic (added with the adaptive loop) ─────────────────────────────────────
def _memory_stats(self, keys):
    return {k: dict(self.memory[k]) for k in keys if k in self.memory}


def _memory_record(self, key, success, cost):
    m = self.memory.setdefault(key, {"trials": 0, "successes": 0, "cost": 0.0})
    m["trials"] += 1
    m["successes"] += 1 if success else 0
    m["cost"] += cost


def _llm_hint(self, prompt):
    self.hints.append(prompt)
    return self.hint_reply


FakeAws.memory_stats = _memory_stats
FakeAws.memory_record = _memory_record
FakeAws.llm_hint = _llm_hint
_orig_init = FakeAws.__init__


def _init(self):
    _orig_init(self)
    self.memory = {}
    self.hints = []
    self.hint_reply = "Replace first-person wording with the third person."


FakeAws.__init__ = _init


# optional hook: finish executions the moment they start (used by the data-sync retry tests)
_orig_start = FakeAws.sfn_start


def _start(self, state_machine_arn, payload, name=None):
    arn = _orig_start(self, state_machine_arn, payload, name)
    hook = getattr(self, "on_start", None)
    if hook:
        hook(self, arn, state_machine_arn, payload)
    return arn


FakeAws.sfn_start = _start
