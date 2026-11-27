"""Run the Data Hub queries locally on DuckDB against the seed files (no AWS needed).

Used by the tests (tests/platform_api/test_datahub.py) and to refresh the frontend's demo snapshot:

    pip install duckdb
    python scripts/datahub_local.py            # writes ../esg-chat-app-react/src/data/datahub_demo.json

The same SQL text runs on Athena: the raw tables are created from data/seed/rds/*.csv.gz and the ledger view from
sql/ddl/06_group_data.sql.
"""

from __future__ import annotations

import json
import math
import os
import sys
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "lambda"), str(ROOT / "lambda" / "_shared"), str(ROOT / "scripts")]
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

RAW = ["entity", "facility", "emission_factor", "activity_data", "esg_metric", "energy_consumption", "loan_portfolio", "hr_metrics", "scope3_operational_activity"]


def connect():
    import duckdb
    from apply_ddl import statements

    con = duckdb.connect()
    for s in ("esg_raw", "esg_curated", "esg_aggregated"):
        con.execute(f"CREATE SCHEMA {s}")
    for t in RAW:
        con.execute(f"CREATE TABLE esg_raw.{t} AS SELECT * FROM read_csv('{ROOT / 'data' / 'seed' / 'rds' / (t + '.csv.gz')}')")
    con.execute("CREATE TABLE esg_aggregated.ghg_summary_annual (metric_key VARCHAR, reporting_year INTEGER, scope1_tco2e DOUBLE, "
                "scope2_location_tco2e DOUBLE, scope2_market_tco2e DOUBLE)")
    # the published inventory comes from the report pipeline in AWS; locally the table is empty, so no reconciliation is shown
    for stmt in statements((ROOT / "sql" / "ddl" / "06_group_data.sql").read_text(encoding="utf-8")):
        if stmt.upper().startswith("CREATE OR REPLACE VIEW"):
            con.execute(stmt)
    return con


def query_fn(con):
    lock = threading.Lock()

    def clean(v: Any) -> Any:
        if v is None:
            return None
        if hasattr(v, "item"):
            v = v.item()
        if isinstance(v, float) and math.isnan(v):
            return None
        return v

    def q(sql: str) -> list[dict[str, Any]]:
        with lock:
            cur = con.execute(sql)
            cols = [d[0] for d in cur.description]
            return [{c: clean(v) for c, v in zip(cols, row)} for row in cur.fetchall()]

    return q


def snapshot() -> dict[str, Any]:
    from platform_api import common, datahub

    common.s3_get = lambda *a, **k: None  # offline: no data-contract reports
    q = query_fn(connect())
    out: dict[str, Any] = {}
    for y in (2023, 2024):
        b = datahub.load_bundle(y, q)
        led = {f"{a}|{s}": datahub.ledger({"year": y, "approach": a, "ef_set": s}, b) for a in ("control", "equity") for s in ("ID_NATIONAL", "ID_REGIONAL")}
        facs = datahub.facilities({"year": y}, b)
        tops = [f["facility_id"] for f in facs["facilities"][:3]]
        out[str(y)] = {
            "overview": datahub.overview({"year": y}, b), "ledger": led, "facilities": facs, "metrics": datahub.metrics({"year": y}, b),
            "alerts": datahub.alerts({"year": y}, b), "factors": datahub.factors({"year": y}, b),
            "facility": {fid: datahub.facility_detail({"year": y, "facility_id": fid}, q) for fid in tops},
        }
    return out


if __name__ == "__main__":
    target = ROOT.parent / "esg-chat-app-react" / "src" / "data" / "datahub_demo.json"
    data = snapshot()
    target.write_text(json.dumps(data, default=str, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {target} ({target.stat().st_size // 1024} KB)")
