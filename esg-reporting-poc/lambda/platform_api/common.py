"""Shared helpers for the platform API: configuration, Athena runner, S3 JSON cache, HTTP responses."""

from __future__ import annotations

import json
import os
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

# Shared domain modules live in ../_shared (flat imports, same layout as the container image)
_SHARED = Path(__file__).resolve().parent.parent / "_shared"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "061039769766")
REGION = os.environ.get("AWS_REGION", "us-east-1")
ATHENA_WORKGROUP = os.environ.get("ATHENA_WORKGROUP", "esg-reporting-workgroup")
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET", f"esg-output-reports-{ACCOUNT_ID}")
BANK_ID = os.environ.get("BANK_ID", "GENERIC_FI_001")
COMPANY_NAME = os.environ.get("COMPANY_NAME", "Generic Financial Institution")
BASE_YEAR = int(os.environ.get("BASE_YEAR", "2023"))
CACHE_TTL = int(os.environ.get("CACHE_TTL_SECONDS", "600"))

CORS = {
    "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
    "Access-Control-Allow-Headers": "Content-Type,x-api-key",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Content-Type": "application/json",
}

_clients: dict[str, Any] = {}


def client(name: str) -> Any:
    if name not in _clients:
        import boto3
        from botocore.config import Config

        _clients[name] = boto3.client(name, region_name=REGION, config=Config(retries={"max_attempts": 3, "mode": "standard"}, read_timeout=60))
    return _clients[name]


class _Enc(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return int(o) if o == o.to_integral_value() else float(o)
        return super().default(o)


def dumps(obj: Any) -> str:
    return json.dumps(obj, cls=_Enc, ensure_ascii=False)


def response(status: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status, "headers": CORS, "body": dumps(body)}


# ── Athena ────────────────────────────────────────────────────────────────────────────────────────
class AthenaError(RuntimeError):
    pass


def _parse(v: str | None) -> Any:
    if v is None or v == "":
        return None
    try:
        f = float(v)
        return int(f) if f.is_integer() and "." not in v and "e" not in v.lower() else f
    except ValueError:
        return v


def athena(sql: str, database: str = "esg_aggregated", timeout: int = 45) -> list[dict[str, Any]]:
    """Run a query and return rows as dicts. Raises AthenaError on failure or timeout."""
    a = client("athena")
    qid = a.start_query_execution(QueryString=sql, QueryExecutionContext={"Database": database}, WorkGroup=ATHENA_WORKGROUP)["QueryExecutionId"]
    t0 = time.time()
    while True:
        st = a.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
        if st["State"] == "SUCCEEDED":
            break
        if st["State"] in ("FAILED", "CANCELLED"):
            raise AthenaError(st.get("StateChangeReason", st["State"])[:300])
        if time.time() - t0 > timeout:
            raise AthenaError(f"Athena query timed out after {timeout}s")
        time.sleep(0.8)
    rows: list[dict[str, Any]] = []
    cols: list[str] | None = None
    for page in a.get_paginator("get_query_results").paginate(QueryExecutionId=qid):
        for i, r in enumerate(page["ResultSet"]["Rows"]):
            vals = [d.get("VarCharValue") for d in r["Data"]]
            if cols is None:
                cols = vals  # header row
                continue
            rows.append({c: _parse(v) for c, v in zip(cols, vals)})
    return rows


# ── S3 JSON helpers ───────────────────────────────────────────────────────────────────────────────
def s3_get(key: str, bucket: str | None = None) -> Any | None:
    s3 = client("s3")
    try:
        return json.loads(s3.get_object(Bucket=bucket or OUTPUT_BUCKET, Key=key)["Body"].read())
    except s3.exceptions.NoSuchKey:
        return None


def s3_put(key: str, body: Any, bucket: str | None = None) -> None:
    client("s3").put_object(Bucket=bucket or OUTPUT_BUCKET, Key=key, Body=dumps(body).encode(), ContentType="application/json")


def cached(key: str, builder, ttl: int = CACHE_TTL, refresh: bool = False) -> Any:
    """Return builder() result cached in S3 for ``ttl`` seconds."""
    full = f"platform-cache/{key}.json"
    if not refresh:
        hit = s3_get(full)
        if hit and time.time() - hit.get("_cached_at", 0) < ttl:
            return hit["data"]
    data = builder()
    try:
        s3_put(full, {"_cached_at": time.time(), "data": data})
    except Exception:  # noqa: BLE001 - cache is best effort
        pass
    return data


def year_param(params: dict[str, Any], default: int = 2024) -> int:
    try:
        y = int(params.get("year") or default)
    except (TypeError, ValueError):
        y = default
    if not 2020 <= y <= 2035:
        raise ValueError("year must be between 2020 and 2035")
    return y
