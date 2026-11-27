"""Data Hub: the ledger view and every Data Hub query run on DuckDB against the seed files (same SQL as Athena)."""
import gzip
import sys
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")
pd = pytest.importorskip("pandas")

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "lambda"), str(ROOT / "lambda" / "_shared"), str(ROOT / "scripts"), str(ROOT / "glue_jobs"), str(Path(__file__).resolve().parent)]
import datahub_local as L  # noqa: E402
import esg_contracts as C  # noqa: E402
from platform_api import common, datahub, handler  # noqa: E402
from test_platform_api import _http  # noqa: E402

SEED = ROOT / "data" / "seed" / "rds"


@pytest.fixture(scope="module")
def q():
    return L.query_fn(L.connect())


@pytest.fixture(scope="module")
def b24(q):
    return datahub.load_bundle(2024, q)


@pytest.fixture(scope="module")
def b23(q):
    return datahub.load_bundle(2023, q)


@pytest.fixture(autouse=True)
def no_s3(monkeypatch):
    monkeypatch.setattr(common, "s3_get", lambda *a, **k: None)


# ── ledger arithmetic ─────────────────────────────────────────────────────────────────────────────
def test_ledger_row_is_quantity_times_factor(q):
    r = q("SELECT quantity, instrument_qty, factor_kgco2e, tco2e, tco2e_market FROM esg_curated.ghg_ledger "
          "WHERE activity_type = 'electricity_grid' AND ef_set = 'ID_NATIONAL' AND instrument_qty > 0 LIMIT 1")[0]
    assert r["factor_kgco2e"] == pytest.approx(0.7886)
    assert r["tco2e"] == pytest.approx(r["quantity"] * 0.7886 / 1000)
    assert r["tco2e_market"] == pytest.approx(max(r["quantity"] - r["instrument_qty"], 0) * 0.7886 / 1000)


def test_combustion_factor_includes_ch4_and_n2o_with_gwp(q):
    r = q("SELECT factor_kgco2e FROM esg_curated.ghg_ledger WHERE activity_type = 'natural_gas' AND ef_set = 'ID_NATIONAL' LIMIT 1")[0]
    assert r["factor_kgco2e"] == pytest.approx(56.10 + 0.001 * 29.8 + 0.0001 * 273)


def test_every_activity_has_exactly_one_factor_per_set(q):
    dup = q("SELECT activity_id, ef_set, count(*) AS n FROM esg_curated.ghg_ledger GROUP BY 1, 2 HAVING count(*) > 1 LIMIT 5")
    assert dup == []
    assert q("SELECT count(*) AS n FROM esg_curated.ghg_ledger WHERE ef_set IS NULL")[0]["n"] == 0


# ── views ─────────────────────────────────────────────────────────────────────────────────────────
def test_operational_control_excludes_the_joint_venture_equity_share_includes_49_pct(b24):
    ctl = datahub.ledger({"year": 2024, "approach": "control"}, b24)
    eq = datahub.ledger({"year": 2024, "approach": "equity"}, b24)
    asr_c = next(e for e in ctl["by_entity"] if e["entity_id"] == "ENT-ASR")
    asr_e = next(e for e in eq["by_entity"] if e["entity_id"] == "ENT-ASR")
    assert asr_c["included"] is False and asr_c["total_market"] == 0
    assert asr_e["total_market"] == pytest.approx(asr_e["gross_total_market"] * 0.49, rel=1e-6)
    mfn = next(e for e in eq["by_entity"] if e["entity_id"] == "ENT-MFN")
    assert mfn["weight"] == pytest.approx(0.75)  # ownership changed from 70 % to 75 % in 2024
    assert sum(e["total_market"] for e in ctl["by_entity"]) == pytest.approx(ctl["totals"]["total_market"], rel=1e-6)


def test_regional_factors_change_scope2_only(b24):
    nat = datahub.ledger({"year": 2024, "ef_set": "ID_NATIONAL"}, b24)["totals"]
    reg = datahub.ledger({"year": 2024, "ef_set": "ID_REGIONAL"}, b24)["totals"]
    assert nat["s1"] == pytest.approx(reg["s1"]) and nat["s3"] == pytest.approx(reg["s3"])
    assert nat["s2_location"] != pytest.approx(reg["s2_location"])


def test_breakdowns_add_up_and_base_year_is_compared(b24):
    led = datahub.ledger({"year": 2024}, b24)
    assert sum(m["s1"] + m["s2_market"] + m["s3"] for m in led["by_month"]) == pytest.approx(led["totals"]["total_market"], rel=1e-3)
    assert sum(a["tco2e_market"] for a in led["by_activity"]) == pytest.approx(led["totals"]["total_market"], rel=1e-6)
    assert led["base_totals"] and led["change_pct"]["s1"] is not None
    assert led["trajectory"]["path"][0]["year"] == 2023 and led["trajectory"]["path"][-1]["year"] == 2030
    assert led["reconciliation"] is None  # the published inventory is not available locally
    assert {f["entity_id"] for f in led["financed"]} == {"ENT-BANK", "ENT-SYR", "ENT-MFN"}


def test_alerts_surface_the_planted_data_problems(b23, b24):
    a24 = datahub.data_alerts(b24)["alerts"]
    ids = {a["id"] for a in a24}
    assert "NC-ENT-SEK-refrigerant_r410a" in ids  # never collected
    assert any(a["kind"] == "missing_months" and a.get("facility_id", "").startswith("SYR-") for a in a24)  # meter migration Oct-Dec 2024
    assert any(a["kind"] == "outlier" and a["facility_id"] == "MFN-F011" and a["id"].endswith("-7") for a in a24)  # 10x fleet fuel in July
    assert "MET-ENT-MFN-employees_with_disability" in ids
    assert next(a for a in a24 if a["id"] == "MET-ENT-SEK-remuneration_ratio_female_male")["severity"] == "low"  # recommended, not required
    a23 = {a["id"] for a in datahub.data_alerts(b23)["alerts"]}
    assert "NC-ENT-ASR-water_supply" in a23 and "MET-ENT-ASR-community_investment_idr" in a23
    assert all(a["severity"] in ("high", "medium", "low") and a["title"] and a["action"] for a in a24)


def test_metrics_show_missing_as_missing_not_zero(b24):
    m = datahub.metrics({"year": 2024}, b24)
    row = {r["id"]: r for r in m["metrics"]}
    sek = {x["entity_id"]: x for x in row["remuneration_ratio_female_male"]["entities"]}["ENT-SEK"]
    assert sek["status"] == "missing" and sek["value"] is None
    kubl_sek = {x["entity_id"]: x for x in row["sustainable_finance_idr"]["entities"]}["ENT-SEK"]
    assert kubl_sek["status"] == "not_applicable"
    bank_heads = {x["entity_id"]: x for x in row["headcount"]["entities"]}["ENT-BANK"]
    assert bank_heads["value"] == 24997  # equals hr_metrics.fte_total
    assert row["energy_total_gj"]["entities"][0]["value"] > 0
    assert m["kubl"] and 0 < m["coverage"]["pct"] < 100


def test_facility_list_and_audit_trail(q, b24):
    facs = datahub.facilities({"year": 2024}, b24)["facilities"]
    assert len(facs) == len(b24["facility_master"])
    fid = facs[0]["facility_id"]
    d = datahub.facility_detail({"year": 2024, "facility_id": fid}, q)
    assert d["facility"]["facility_id"] == fid and d["records"]
    assert sum(r["tco2e_market"] for r in d["records"]) == pytest.approx(facs[0]["total_market"], rel=1e-3)
    with pytest.raises(ValueError):
        datahub.facility_detail({"year": 2024, "facility_id": "x'; DROP"}, q)


def test_bad_parameters_are_rejected(b24):
    for p in ({"approach": "x"}, {"ef_set": "DEFRA"}, {"entity": "ENT-1; --"}):
        with pytest.raises(ValueError):
            datahub.ledger({"year": 2024, **p}, b24)


def test_overview_and_agent_views(b24, monkeypatch):
    monkeypatch.setattr(datahub, "bundle", lambda year, refresh=False: b24)
    o = datahub.overview({"year": 2024}, b24)
    assert {d["table"] for d in o["datasets"]} == set(datahub.RAW_TABLES)
    assert all(d["rows"] for d in o["datasets"])
    assert o["alerts"]["counts"]["high"] > 0 and len(o["lineage"]) == 6
    for view in ("overview", "ledger", "alerts", "metrics"):
        assert datahub.agent_query({"view": view, "year": 2024})


def test_http_routes(b24, monkeypatch):
    monkeypatch.setattr(datahub, "bundle", lambda year, refresh=False: b24)
    for path in ("/data/overview", "/data/ledger", "/data/facilities", "/data/metrics", "/data/alerts", "/data/factors"):
        res = handler.lambda_handler(_http("GET", path, qs={"year": "2024"}))
        assert res["statusCode"] == 200, (path, res["body"][:200])


# ── seed data honours its contracts ───────────────────────────────────────────────────────────────
SPARK_TYPE = {"object": "string", "float64": "double", "int64": "int", "bool": "boolean"}


@pytest.mark.parametrize("table", ["entity", "facility", "emission_factor", "activity_data", "esg_metric"])
def test_seed_files_pass_their_contract(table):
    df = pd.read_csv(gzip.open(SEED / f"{table}.csv.gz"), keep_default_na=True)
    spec = C.CONTRACTS[table]
    for y in (2023, 2024):
        d = df[df.reporting_year == y].drop(columns=["reporting_year"])
        cols = {}
        for c in d.columns:
            t = SPARK_TYPE.get(str(d[c].dtype), "string")
            if spec["columns"].get(c, {}).get("type") == "double" and t == "int":
                t = "double"  # integral-looking doubles are DOUBLE PRECISION in the database
            entry = {"type": t, "nulls": int(d[c].isna().sum())}
            if t in ("double", "int"):
                entry["min"], entry["max"] = (float(d[c].min()), float(d[c].max())) if d[c].notna().any() else (None, None)
            if spec["columns"].get(c, {}).get("enum"):
                entry["distinct"] = list(d[c].dropna().unique())
            cols[c] = entry
        dup = int(d.duplicated(subset=spec["unique"]).sum()) if spec["unique"] else 0
        violations = C.evaluate(table, {"row_count": len(d), "columns": cols, "duplicate_keys": dup})
        assert violations == [], (table, y, violations)
