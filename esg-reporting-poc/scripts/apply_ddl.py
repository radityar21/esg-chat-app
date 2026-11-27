#!/usr/bin/env python3
"""Creates the Glue databases and Athena tables (sql/ddl/01..05). Safe to re-run (CREATE ... IF NOT EXISTS).

    python scripts/apply_ddl.py

Needs the workgroup esg-reporting-workgroup and the data buckets (EsgFoundationStack).
"""
import time
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
FILES = ["01_create_databases.sql", "02_raw_tables.sql", "03_curated_tables.sql", "04_aggregated_tables.sql", "05_scope3_operational.sql"]


def statements(text: str) -> list[str]:
    """Split on ';' and drop '--' comments, but only OUTSIDE single-quoted strings (comments in the DDL contain ';')."""
    text = text.lstrip("\ufeff")
    out, buf, i, quoted = [], [], 0, False
    while i < len(text):
        ch = text[i]
        if quoted:
            buf.append(ch)
            if ch == "'":
                if text[i + 1:i + 2] == "'":  # escaped quote ''
                    buf.append("'")
                    i += 1
                else:
                    quoted = False
        elif ch == "'":
            quoted = True
            buf.append(ch)
        elif text.startswith("--", i):
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        elif ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


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
