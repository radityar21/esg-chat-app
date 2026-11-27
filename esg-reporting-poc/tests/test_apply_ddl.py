import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("apply_ddl", ROOT / "scripts" / "apply_ddl.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_semicolons_and_dashes_inside_strings_are_kept():
    sql = "-- header; with semicolon\nCREATE DATABASE a COMMENT 'x; y -- z';\nCREATE TABLE b (c INT) -- trailing\n;"
    assert m.statements(sql) == ["CREATE DATABASE a COMMENT 'x; y -- z'", "CREATE TABLE b (c INT)"]


def test_escaped_quotes_and_bom():
    assert m.statements("\ufeffSELECT 'it''s; fine';") == ["SELECT 'it''s; fine'"]


def test_repo_ddl_splits_into_complete_statements():
    stmts = [s for f in m.FILES for s in m.statements((ROOT / "sql" / "ddl" / f).read_text(encoding="utf-8"))]
    assert len(stmts) == 19  # 3 databases + 15 tables + the ledger view
    assert all(s.upper().startswith("CREATE") and s.count("'") % 2 == 0 for s in stmts)
