"""AI governance: PII masking for HR data (UU PDP) and the token FinOps summary."""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from . import common

try:
    import model_routing as mr
    import pii_guard
except ImportError:  # pragma: no cover
    from _shared import model_routing as mr, pii_guard  # type: ignore

MAX_PAYLOAD_CHARS = 200_000


# ── PII masking ───────────────────────────────────────────────────────────────────────────────────
def pii_mask(params: dict[str, Any]) -> dict[str, Any]:
    """Mask a record list or free text. ``mode`` is ``tokenize`` (stable pseudonyms, joinable) or ``redact``."""
    mode = params.get("mode", "tokenize")
    if mode not in ("tokenize", "redact"):
        raise ValueError("mode must be 'tokenize' or 'redact'")
    payload = params.get("records", params.get("text"))
    if payload is None:
        raise ValueError("provide 'records' (list of objects) or 'text'")
    if len(common.dumps(payload)) > MAX_PAYLOAD_CHARS:
        raise ValueError(f"payload larger than {MAX_PAYLOAD_CHARS} characters")
    masked, report = pii_guard.mask_payload(payload, mode, params.get("roster"))
    cols: list[str] = []
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        cols = list(payload[0].keys())
    return {"masked": masked, "findings": report, "total_findings": sum(report.values()), "mode": mode,
            "classification": pii_guard.classify_columns(cols) if cols else [],
            "guardrail": pii_guard.guardrail_check(payload if isinstance(payload, str) else common.dumps(masked)),
            "note": "Tokens are HMAC-based and stable per value, so masked data can still be joined and aggregated."}


# ── Token FinOps ──────────────────────────────────────────────────────────────────────────────────
def _query_day(table: Any, day: str) -> list[dict[str, Any]]:
    from boto3.dynamodb.conditions import Key

    items: list[dict[str, Any]] = []
    kw: dict[str, Any] = {"KeyConditionExpression": Key("day").eq(day)}
    while True:
        r = table.query(**kw)
        items += r.get("Items", [])
        if "LastEvaluatedKey" not in r:
            return items
        kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]


def _table() -> Any:
    import boto3

    return boto3.resource("dynamodb", region_name=common.REGION).Table(os.environ["USAGE_TABLE"])


def _subsidiary(exec_id: str, cache: dict[str, str], meta_get: Callable[[str], Any]) -> str:
    if not exec_id:
        return "Unattributed"
    if exec_id not in cache:
        try:
            m = meta_get(f"executions/{exec_id}/meta.json") or {}
        except Exception:  # noqa: BLE001
            m = {}
        cache[exec_id] = m.get("subsidiary") or m.get("entity") or "Head office"
    return cache[exec_id]


def summarize(items: list[dict[str, Any]], days: int, meta_get: Callable[[str], Any] | None = None, today: datetime | None = None) -> dict[str, Any]:
    """Aggregate usage items. Pure function (no AWS) so it is unit-testable."""
    meta_get = meta_get or common.s3_get
    today = today or datetime.now(timezone.utc)
    cache: dict[str, str] = {}
    f = lambda x: float(x or 0)  # noqa: E731
    tot = defaultdict(float)
    by_day: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    by_model: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    by_task: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    by_sub: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    projected = {p: 0.0 for p in mr.PROFILES}
    for it in items:
        c, b = f(it.get("cost_usd")), f(it.get("baseline_cost_usd"))
        ti, to, ci = int(f(it.get("tokens_in"))), int(f(it.get("tokens_out"))), int(f(it.get("cached_in")))
        for agg, key in ((by_day, it.get("day")), (by_model, it.get("model")), (by_task, it.get("task")),
                         (by_sub, _subsidiary(it.get("execution_id", ""), cache, meta_get))):
            a = agg[key]
            a["calls"] += 1
            a["tokens_in"] += ti
            a["tokens_out"] += to
            a["cost_usd"] += c
        tot["calls"] += 1
        tot["tokens_in"] += ti
        tot["tokens_out"] += to
        tot["cached_in"] += ci
        tot["cost_usd"] += c
        tot["baseline_usd"] += b
        for p in mr.PROFILES:  # what the same tokens would have cost under each routing profile
            alias, _ = mr.resolve(it.get("task", "section_complex"), p)
            projected[p] += mr.cost_usd(alias, ti, to, ci)
    cache_saved = tot["cached_in"] * mr.MODELS["sonnet"]["in"] * (1 - mr.CACHE_READ_DISCOUNT) / 1_000_000
    series = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        v = by_day.get(d, {})
        series.append({"day": d, "calls": int(v.get("calls", 0)), "tokens": int(v.get("tokens_in", 0) + v.get("tokens_out", 0)), "cost_usd": round(v.get("cost_usd", 0), 4)})
    rows = lambda agg: sorted(({"key": k, **{m: (round(x, 4) if m == "cost_usd" else int(x)) for m, x in v.items()}} for k, v in agg.items()), key=lambda r: -r["cost_usd"])  # noqa: E731
    return {
        "days": days, "profile": mr.active_profile(), "has_data": bool(items),
        "totals": {"calls": int(tot["calls"]), "tokens_in": int(tot["tokens_in"]), "tokens_out": int(tot["tokens_out"]),
                   "cost_usd": round(tot["cost_usd"], 4), "all_sonnet_baseline_usd": round(tot["baseline_usd"], 4),
                   "saved_vs_baseline_usd": round(tot["baseline_usd"] - tot["cost_usd"], 4),
                   "prompt_cache_saved_usd": round(cache_saved, 4)},
        "projection_by_profile_usd": {p: round(v, 4) for p, v in projected.items()},
        "daily": series, "by_model": rows(by_model), "by_task": rows(by_task), "by_subsidiary": rows(by_sub),
        "pricing_note": "List prices in model_routing.MODELS; estimates only. Cache saving counts cached input tokens billed at 10%.",
    }


def finops_summary(params: dict[str, Any], table: Any | None = None, meta_get: Callable[[str], Any] | None = None) -> dict[str, Any]:
    try:
        days = max(1, min(14, int(params.get("days", 14))))
    except (TypeError, ValueError):
        raise ValueError("days must be an integer between 1 and 14") from None
    if table is None and not os.environ.get("USAGE_TABLE"):
        return {**summarize([], days, meta_get), "warning": "USAGE_TABLE is not configured: metering is off."}
    table = table or _table()
    now = datetime.now(timezone.utc)
    items: list[dict[str, Any]] = []
    for i in range(days):
        items += _query_day(table, (now - timedelta(days=i)).strftime("%Y-%m-%d"))
    return summarize(items, days, meta_get, now)
