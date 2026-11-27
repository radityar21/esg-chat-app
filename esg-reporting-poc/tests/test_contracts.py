import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "glue_jobs"))
import esg_contracts as C  # noqa: E402


def good_stats(table):
    cols = {}
    for n, r in C.CONTRACTS[table]["columns"].items():
        cols[n] = {"type": r["type"], "nulls": 0, "min": r.get("min"), "max": r.get("max"), "distinct": r.get("enum")}
    return {"row_count": 10, "columns": cols, "duplicate_keys": 0}


def test_clean_load_is_ok():
    for t in C.CONTRACTS:
        assert C.summarize(C.evaluate(t, good_stats(t)))["status"] == "OK", t


def test_missing_column_and_zero_rows_block():
    s = good_stats("loan_portfolio")
    del s["columns"]["sector_nace"]
    s["row_count"] = 0
    v = C.evaluate("loan_portfolio", s)
    assert {x["rule"] for x in v if x["level"] == "blocking"} == {"ROWS", "MISSING_COLUMN"}


def test_type_widening_rules():
    assert C._type_ok("double", "decimal") and C._type_ok("double", "int") and C._type_ok("bigint", "int")
    assert not C._type_ok("int", "double") and not C._type_ok("string", "int")


def test_wrong_type_blocks():
    s = good_stats("hr_metrics")
    s["columns"]["fte_total"]["type"] = "string"
    assert any(x["rule"] == "TYPE" and x["level"] == "blocking" for x in C.evaluate("hr_metrics", s))


def test_range_enum_nulls_are_warnings_only():
    s = good_stats("loan_portfolio")
    s["columns"]["pcaf_data_quality_score"]["max"] = 9
    s["columns"]["currency"]["distinct"] = ["IDR", "EUR"]
    s["columns"]["borrower_emissions_tco2e"]["nulls"] = 5
    v = C.evaluate("loan_portfolio", s)
    assert {x["level"] for x in v} == {"warning"} and {x["rule"] for x in v} == {"RANGE", "ENUM", "NULLS"}
    assert C.summarize(v) == {"status": "WARN", "blocking": 0, "warnings": 3}


def test_null_key_and_duplicates_block():
    s = good_stats("loan_portfolio")
    s["columns"]["loan_id"]["nulls"] = 2
    s["duplicate_keys"] = 3
    assert {x["rule"] for x in C.evaluate("loan_portfolio", s) if x["level"] == "blocking"} == {"NULL_KEY", "DUPLICATE_KEYS"}


def test_extra_column_warns():
    s = good_stats("hr_metrics")
    s["columns"]["salary_total"] = {"type": "double", "nulls": 0}
    assert any(x["rule"] == "EXTRA_COLUMN" for x in C.evaluate("hr_metrics", s))
