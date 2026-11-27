"""esg-data-tools: read-only tools for the AgentCore orchestrator (and a ready-made target for an AgentCore Gateway).

    {"action": "source_tables"}                                      tables, row counts per reporting year
    {"action": "source_preview", "table": ..., "year": ..., "limit": 10}   a few rows (at most 20)
    {"action": "etl_report", "table": ..., "year": ...}              latest data-contract report written by the extract job

The database user has SELECT only. Table names are checked against the catalogue and values are bound parameters.
"""

from __future__ import annotations

import json
import os
from typing import Any

from _shared import rds_conn

READER = os.environ.get("READER_SECRET_ARN", "")
REPORT_BUCKET = os.environ.get("REPORT_BUCKET", "")
SCHEMA = "esg"
MAX_PREVIEW = 20
_s3 = None


def _conn():
    return rds_conn.connect(READER)


def _tables(conn: Any) -> list[str]:
    return [r["table_name"] for r in rds_conn.rows(conn, "SELECT table_name FROM information_schema.tables WHERE table_schema = :s ORDER BY 1", s=SCHEMA)]


def source_tables(connect=_conn) -> dict[str, Any]:
    conn = connect()
    try:
        out = []
        for t in _tables(conn):
            cols = rds_conn.rows(conn, "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = :s AND table_name = :t ORDER BY ordinal_position", s=SCHEMA, t=t)
            years = rds_conn.rows(conn, f'SELECT reporting_year, count(*) AS rows FROM "{SCHEMA}"."{t}" GROUP BY 1 ORDER BY 1')  # t comes from the catalogue
            out.append({"table": t, "columns": [c["column_name"] for c in cols], "rows_by_year": {str(y["reporting_year"]): y["rows"] for y in years}})
        return {"tables": out}
    finally:
        conn.close()


def source_preview(table: str, year: int, limit: int = 10, connect=_conn) -> dict[str, Any]:
    limit = max(1, min(int(limit), MAX_PREVIEW))
    year = int(year)
    conn = connect()
    try:
        if table not in _tables(conn):
            raise ValueError(f"Unknown table {table!r}")
        return {"table": table, "year": year, "rows": json.loads(json.dumps(
            rds_conn.rows(conn, f'SELECT * FROM "{SCHEMA}"."{table}" WHERE reporting_year = :y LIMIT {limit}', y=year), default=str))}
    finally:
        conn.close()


def etl_report(table: str, year: int) -> dict[str, Any]:
    global _s3
    import boto3

    _s3 = _s3 or boto3.client("s3")
    from botocore.exceptions import ClientError

    if not table.replace("_", "").isalnum():
        raise ValueError("invalid table name")
    try:
        body = _s3.get_object(Bucket=REPORT_BUCKET, Key=f"etl-reports/latest/{table}_{int(year)}.json")["Body"].read()
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return {"found": False, "note": "No extract has run for this table and year (or the report expired after 14 days)."}
        raise
    return {"found": True, "report": json.loads(body)}


def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    try:
        a = event.get("action")
        if a == "source_tables":
            return source_tables()
        if a == "source_preview":
            return source_preview(event["table"], event["year"], event.get("limit", 10))
        if a == "etl_report":
            return etl_report(event["table"], event["year"])
        return {"error": f"unknown action {a!r}", "actions": ["source_tables", "source_preview", "etl_report"]}
    except (KeyError, ValueError) as exc:
        return {"error": f"invalid request: {exc}"}
    except Exception:  # noqa: BLE001 - details stay in the Lambda log
        import logging

        logging.getLogger().exception("data tools failed")
        return {"error": "the data tool failed; see the function log"}
