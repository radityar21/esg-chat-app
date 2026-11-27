"""LLM usage metering for the token FinOps dashboard.

Every Bedrock call made by the pipeline records one item in the DynamoDB table named by ``USAGE_TABLE``.
If the variable is unset the meter is a no-op, so it is safe to import everywhere (tests, local runs).

Key design:  PK = ``day`` (YYYY-MM-DD)   SK = ``ts#uuid``   -> a day's usage is one Query.
Attribution to a subsidiary is done at read time by joining ``execution_id`` with the execution metadata
object written by the AgentCore orchestrator (``executions/<id>/meta.json``), so the Step Functions
definition does not need to carry a ``subsidiary`` field.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

try:  # pragma: no cover - import guard for local tests
    from model_routing import alias_for_model_id, cost_usd
except ImportError:  # when imported as part of a package
    from ._shared.model_routing import alias_for_model_id, cost_usd  # type: ignore

logger = logging.getLogger(__name__)
_table = None


def _get_table():
    global _table
    name = os.environ.get("USAGE_TABLE")
    if not name:
        return None
    if _table is None:
        import boto3

        _table = boto3.resource("dynamodb").Table(name)
    return _table


def record(task: str, model_id: str, tokens_in: int, tokens_out: int, *, execution_id: str = "",
           section_id: str = "", source: str = "pipeline", cached_in: int = 0, latency_ms: int = 0, user: str = "") -> dict[str, Any]:
    alias = alias_for_model_id(model_id)
    item = {
        "day": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sk": f"{int(time.time() * 1000)}#{uuid.uuid4().hex[:8]}",
        "task": task,
        "model": alias,
        "model_id": model_id,
        "tokens_in": int(tokens_in),
        "tokens_out": int(tokens_out),
        "cached_in": int(cached_in),
        "cost_usd": Decimal(str(round(cost_usd(alias, tokens_in, tokens_out, cached_in), 6))),
        "baseline_cost_usd": Decimal(str(round(cost_usd("sonnet", tokens_in, tokens_out, cached_in), 6))),
        "execution_id": execution_id.split(":")[-1] if execution_id else "",
        "section_id": section_id,
        "source": source,
        "latency_ms": int(latency_ms),
        "user": user,
        "ttl": int(time.time()) + int(os.environ.get("USAGE_TTL_DAYS", "14")) * 86400,  # DynamoDB TTL attribute
    }
    table = _get_table()
    if table is not None:
        try:
            table.put_item(Item=item)
        except Exception as exc:  # metering must never break generation
            logger.warning("usage_meter put_item failed: %s", exc)
    return item
