"""esg-rds-seed: create the source schema, the read-only role and (re)load the synthetic data. Invoked manually.

    {"action": "init"}                              schema + read-only user + grants (idempotent)
    {"action": "load", "reload": true}              load the CSV files from s3://<raw bucket>/seed/rds/ (reload truncates first)
    {"action": "inject", "kind": "range"|"rename_column"}   plant a data problem to demonstrate agent triage
    {"action": "reset"}                             drop the tables and reload the clean data

Master credentials are only used here. Everything else uses the read-only user.
"""

from __future__ import annotations

import gzip
import io
import json
import os
from pathlib import Path
from typing import Any

import boto3
import pg8000.native as pg

from _shared import rds_conn

TABLES = {  # table -> columns in CSV order are read from the header
    "energy_consumption": "esg.energy_consumption", "loan_portfolio": "esg.loan_portfolio",
    "hr_metrics": "esg.hr_metrics", "scope3_operational_activity": "esg.scope3_operational_activity",
}
SEED_BUCKET = os.environ.get("SEED_BUCKET", "")
MASTER = os.environ.get("MASTER_SECRET_ARN", "")
READER = os.environ.get("READER_SECRET_ARN", "")


def _init(conn: Any) -> dict[str, Any]:
    for stmt in [s.strip() for s in Path(__file__).with_name("schema.sql").read_text().split(";") if s.strip()]:
        conn.run(stmt)
    reader = rds_conn._secret(READER)
    role = pg.identifier(reader["username"])
    exists = conn.run("SELECT 1 FROM pg_roles WHERE rolname = :n", n=reader["username"])
    pw = pg.literal(reader["password"])
    conn.run(f"ALTER ROLE {role} WITH LOGIN PASSWORD {pw}" if exists else f"CREATE ROLE {role} LOGIN PASSWORD {pw}")
    conn.run(f"GRANT USAGE ON SCHEMA esg TO {role}")
    conn.run(f"GRANT SELECT ON ALL TABLES IN SCHEMA esg TO {role}")
    conn.run(f"ALTER DEFAULT PRIVILEGES IN SCHEMA esg GRANT SELECT ON TABLES TO {role}")
    conn.run(f"REVOKE CREATE ON SCHEMA public FROM {role}")
    return {"schema": "esg", "tables": list(TABLES), "reader": reader["username"]}


def _load(conn: Any, reload: bool) -> dict[str, Any]:
    s3 = boto3.client("s3")
    out = {}
    for name, full in TABLES.items():
        body = gzip.decompress(s3.get_object(Bucket=SEED_BUCKET, Key=f"seed/rds/{name}.csv.gz")["Body"].read())
        header = body.split(b"\n", 1)[0].decode().strip().split(",")
        if reload:
            conn.run(f"TRUNCATE {full}")
        cols = ", ".join(pg.identifier(c) for c in header)
        conn.run(f"COPY {full} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true)", stream=io.BytesIO(body))
        out[name] = conn.run(f"SELECT count(*) FROM {full}")[0][0]
    return out


def _inject(conn: Any, kind: str) -> dict[str, Any]:
    if kind == "range":  # usable but suspicious: the contract reports a warning
        conn.run("UPDATE esg.loan_portfolio SET pcaf_data_quality_score = 9 WHERE loan_id = (SELECT loan_id FROM esg.loan_portfolio WHERE reporting_year = 2024 LIMIT 1) AND reporting_year = 2024")
        return {"injected": "one loan with PCAF score 9 (outside 1-5) in 2024"}
    if kind == "rename_column":  # breaking: the contract blocks the load
        conn.run("ALTER TABLE esg.hr_metrics RENAME COLUMN fte_total TO fte_headcount")
        return {"injected": "esg.hr_metrics.fte_total renamed to fte_headcount"}
    raise ValueError("kind must be 'range' or 'rename_column'")


def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    action = event.get("action")
    conn = rds_conn.connect(MASTER)
    try:
        if action == "init":
            return _init(conn)
        if action == "load":
            return {"loaded": _load(conn, bool(event.get("reload")))}
        if action == "inject":
            return _inject(conn, str(event.get("kind")))
        if action == "reset":
            for full in TABLES.values():
                conn.run(f"DROP TABLE IF EXISTS {full}")
            res = _init(conn)
            return {**res, "loaded": _load(conn, False)}
        raise ValueError("action must be init, load, inject or reset")
    finally:
        conn.close()
