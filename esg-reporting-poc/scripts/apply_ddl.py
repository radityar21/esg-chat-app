#!/usr/bin/env python3
"""Creates the Glue databases and Athena tables (sql/ddl/01..05). Safe to re-run (CREATE ... IF NOT EXISTS).

    python scripts/apply_ddl.py

Needs the workgroup esg-reporting-workgroup and the data buckets (EsgFoundationStack).
"""
import re
import time
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
FILES = ["01_create_databases.sql", "02_raw_tables.sql", "03_curated_tables.sql", "04_aggregated_tables.sql", "05_scope3_operational.sql"]


def statements(text: str) -> list[str]:
    text = re.sub(r"--[^\n]*", "", text)  # comments
    return [s.strip() for s in text.split(";") if s.strip()]


def main() -> None:
    athena = boto3.client("athena", region_name="us-east-1")
    total = 0
    for name in FILES:
        for sql in statements((ROOT / "sql" / "ddl" / name).read_text(encoding="utf-8")):
            qid = athena.start_query_execution(QueryString=sql, WorkGroup="esg-reporting-workgroup")["QueryExecutionId"]
            while True:
                st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
                if st["State"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
                    break
                time.sleep(1)
            label = " ".join(sql.split()[:6])
            if st["State"] != "SUCCEEDED":
                raise SystemExit(f"FAILED in {name}: {label}\n  {st.get('StateChangeReason')}")
            total += 1
            print(f"ok  {name}: {label}")
    print(f"{total} statements applied")


if __name__ == "__main__":
    main()
