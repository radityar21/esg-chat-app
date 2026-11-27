"""Agent ledger: a small JSON document in S3 per Step Functions execution.

It is the single source of truth for what the orchestrator did (and why), and is what the UI shows as the
"agent timeline". It also provides an atomic claim (S3 conditional write) so that the chat tool and the
EventBridge trigger can never supervise the same execution twice at the same time.
"""

from __future__ import annotations

from typing import Any

from .aws import AwsGateway, iso, short_id
from .config import Settings

MAX_EVENTS = 300


class Ledger:
    def __init__(self, aws: AwsGateway, settings: Settings) -> None:
        self.aws = aws
        self.s = settings

    # keys ------------------------------------------------------------------------------------------
    def key(self, execution: str) -> str:
        return f"agent-ledger/{short_id(execution)}.json"

    def lock_key(self, execution: str) -> str:
        return f"agent-ledger/{short_id(execution)}.lock"

    def meta_key(self, execution: str) -> str:
        return f"executions/{short_id(execution)}/meta.json"

    # document --------------------------------------------------------------------------------------
    def load(self, execution: str) -> dict[str, Any]:
        doc = self.aws.s3_get_json(self.s.output_bucket, self.key(execution))
        if doc is None:
            now = iso(self.aws.now())
            doc = {"execution_id": short_id(execution), "status": "pending", "pipeline": None, "created_at": now,
                   "updated_at": now, "events": [], "sections": {}, "result": None}
        return doc

    def save(self, execution: str, doc: dict[str, Any]) -> None:
        doc["updated_at"] = iso(self.aws.now())
        doc["events"] = doc["events"][-MAX_EVENTS:]
        self.aws.s3_put_json(self.s.output_bucket, self.key(execution), doc)

    def event(self, execution: str, doc: dict[str, Any], type_: str, message: str, **detail: Any) -> None:
        doc["events"].append({"ts": iso(self.aws.now()), "type": type_, "message": message, **({"detail": detail} if detail else {})})
        self.save(execution, doc)

    def write_meta(self, execution: str, meta: dict[str, Any]) -> None:
        self.aws.s3_put_json(self.s.output_bucket, self.meta_key(execution), meta)

    # lock ------------------------------------------------------------------------------------------
    def claim(self, execution: str) -> bool:
        body = {"claimed_at": self.aws.now()}
        if self.aws.s3_put_if_absent(self.s.output_bucket, self.lock_key(execution), body):
            return True
        existing = self.aws.s3_get_json(self.s.output_bucket, self.lock_key(execution)) or {}
        if self.aws.now() - float(existing.get("claimed_at", 0)) > self.s.lock_ttl_seconds:
            self.aws.s3_delete(self.s.output_bucket, self.lock_key(execution))  # stale lock: previous supervisor died
            return self.aws.s3_put_if_absent(self.s.output_bucket, self.lock_key(execution), body)
        return False

    def release(self, execution: str) -> None:
        self.aws.s3_delete(self.s.output_bucket, self.lock_key(execution))
