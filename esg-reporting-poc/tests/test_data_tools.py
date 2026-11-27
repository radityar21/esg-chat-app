import json
import sys
from pathlib import Path

import pytest

LAMBDA = Path(__file__).resolve().parents[1] / "lambda"
sys.path.insert(0, str(LAMBDA))
sys.path.insert(0, str(LAMBDA / "data_tools"))
import handler as H  # noqa: E402


class FakeConn:
    def __init__(self):
        self.columns = []
        self.sql = []
        self.closed = False

    def run(self, sql, **p):
        self.sql.append((sql, p))
        if "information_schema.tables" in sql:
            self.columns = [{"name": "table_name"}]
            return [["loan_portfolio"], ["hr_metrics"]]
        if "information_schema.columns" in sql:
            self.columns = [{"name": "column_name"}, {"name": "data_type"}]
            return [["loan_id", "text"], ["reporting_year", "integer"]]
        if "GROUP BY" in sql:
            self.columns = [{"name": "reporting_year"}, {"name": "rows"}]
            return [[2023, 10], [2024, 12]]
        self.columns = [{"name": "loan_id"}, {"name": "outstanding"}]
        return [["L1", __import__("decimal").Decimal("5.5")]]

    def close(self):
        self.closed = True


def test_source_tables_summarises_rows_by_year():
    c = FakeConn()
    out = H.source_tables(connect=lambda: c)
    assert out["tables"][0] == {"table": "loan_portfolio", "columns": ["loan_id", "reporting_year"], "rows_by_year": {"2023": 10, "2024": 12}}
    assert c.closed


def test_preview_rejects_unknown_tables_and_clamps_limit():
    c = FakeConn()
    with pytest.raises(ValueError):
        H.source_preview("users; DROP TABLE x", 2024, connect=lambda: c)
    out = H.source_preview("loan_portfolio", "2024", limit=9999, connect=lambda: c)
    sql, params = c.sql[-1]
    assert "LIMIT 20" in sql and params == {"y": 2024}
    assert out["rows"][0]["outstanding"] == "5.5"  # Decimal made JSON-safe


def test_handler_returns_errors_instead_of_raising():
    assert "invalid request" in H.lambda_handler({"action": "source_preview"})["error"]
    assert "unknown action" in H.lambda_handler({"action": "zzz"})["error"]


def test_etl_report_name_is_validated():
    with pytest.raises(ValueError):
        H.etl_report("../../x", 2024)
