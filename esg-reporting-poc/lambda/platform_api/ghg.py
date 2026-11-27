"""GHG inventory structured like the GHG Protocol Corporate Value Chain (Scope 3) reporting template.

Part 1 descriptive info · Part 2 emissions (+ by gas) · Part 3 biogenic · Part 4 methodologies and data quality ·
Part 5 base year · Part 6 optional information.

Sources (all produced by the existing pipeline unless noted):
    esg_aggregated.ghg_summary_annual     Scope 1, Scope 2, Cat 15, intensity, assurance level, PCAF quality
    esg_curated.ghg_scope1 / ghg_scope2   fuel volumes, MWh, REC, facility data quality
    esg_curated.ghg_scope3_financed       Cat 15 data quality
    esg_raw.scope3_operational_activity   Cat 1-7 (NEW, see sql/ddl/05_scope3_operational.sql). If the table is
                                          missing the categories are reported as "not measured", never as zero.
"""

from __future__ import annotations

from typing import Any, Callable

from . import common
from .common import BASE_YEAR, COMPANY_NAME, BANK_ID

try:
    from esg_domain import GWP, SCOPE1_GAS_FACTORS, SCOPE3_OPERATIONAL_CATEGORIES
except ImportError:  # pragma: no cover
    from _shared.esg_domain import GWP, SCOPE1_GAS_FACTORS, SCOPE3_OPERATIONAL_CATEGORIES  # type: ignore

DOWNSTREAM_EXCLUDED = {
    "c8": "Cat 8 · Upstream leased assets", "c9": "Cat 9 · Downstream transportation and distribution",
    "c10": "Cat 10 · Processing of sold products", "c11": "Cat 11 · Use of sold products",
    "c12": "Cat 12 · End-of-life treatment of sold products", "c13": "Cat 13 · Downstream leased assets", "c14": "Cat 14 · Franchises",
}

Q = common.athena  # indirection so tests can monkeypatch `ghg.Q`


def _one(sql: str, db: str, q: Callable[..., list[dict[str, Any]]]) -> dict[str, Any]:
    rows = q(sql, db)
    return rows[0] if rows else {}


def _summary(year: int, q) -> dict[str, Any]:
    return _one(f"""SELECT scope1_tco2e, scope1_natgas_tco2e, scope1_diesel_tco2e, scope2_location_tco2e, scope2_market_tco2e,
        scope3_cat15_gross_tco2e, scope3_cat15_weighted_tco2e, intensity_tco2e_per_idr_bn, intensity_tco2e_per_fte,
        yoy_change_pct, vs_base_year_change_pct, avg_pcaf_data_quality, assurance_level
        FROM esg_aggregated.ghg_summary_annual WHERE reporting_year = {year} AND metric_key LIKE '{BANK_ID}_%' LIMIT 1""", "esg_aggregated", q)


def _operational(year: int, q) -> dict[str, dict[str, Any]] | None:
    try:
        rows = q(f"""SELECT category, SUM(emissions_tco2e) AS t, AVG(data_quality_score) AS dq, MIN(method) AS method,
            ARRAY_JOIN(ARRAY_AGG(DISTINCT ef_source), ', ') AS src, ARRAY_JOIN(ARRAY_AGG(DISTINCT activity), '; ') AS acts
            FROM esg_raw.scope3_operational_activity WHERE reporting_year = {year} GROUP BY category""", "esg_raw", q)
    except Exception:  # noqa: BLE001 - table not created yet
        return None
    return {r["category"]: r for r in rows} if rows else None


def gas_breakdown(natgas_gj: float | None, diesel_l: float | None, scope1_total: float | None) -> dict[str, Any]:
    """Split Scope 1 by gas from fuel volumes (IPCC defaults, AR6 GWP100) and reconcile with the ETL total."""
    if natgas_gj is None and diesel_l is None:
        return {"available": False}
    ng, dl = natgas_gj or 0.0, diesel_l or 0.0
    f1, f2 = SCOPE1_GAS_FACTORS["natural_gas_per_gj"], SCOPE1_GAS_FACTORS["diesel_per_litre"]
    co2 = (ng * f1["CO2"] + dl * f2["CO2"]) / 1000.0
    ch4_t = (ng * f1["CH4"] + dl * f2["CH4"]) / 1000.0
    n2o_t = (ng * f1["N2O"] + dl * f2["N2O"]) / 1000.0
    ch4_e, n2o_e = ch4_t * GWP["CH4"], n2o_t * GWP["N2O"]
    computed = co2 + ch4_e + n2o_e
    delta = None if not scope1_total else round((computed - scope1_total) / scope1_total * 100, 3)
    return {"available": True, "vals": [round(co2, 3), round(ch4_e, 3), round(n2o_e, 3), 0.0, 0.0, 0.0],
            "computed_total": round(computed, 3), "etl_total": scope1_total, "delta_pct": delta,
            "note": "Computed from fuel volumes with IPCC defaults and AR6 GWP100; delta shows the difference to the ETL total. HFCs, PFCs and SF6 are not captured (no refrigerant data)."}


def build_inventory(year: int, q: Callable[..., list[dict[str, Any]]] | None = None) -> dict[str, Any]:
    q = q or Q
    cur, base = _summary(year, q), _summary(BASE_YEAR, q)
    if not cur:
        raise LookupError(f"No aggregated GHG summary for {year}. Run the aggregation job first.")
    s1 = _one(f"SELECT SUM(total_natgas_gj) AS gj, SUM(total_diesel_liters) AS l, AVG(data_quality_score) AS dq, COUNT(*) AS n FROM esg_curated.ghg_scope1 WHERE reporting_year = {year}", "esg_curated", q)
    s2 = _one(f"SELECT SUM(total_consumption_mwh) AS mwh, SUM(rec_mwh_applied) AS rec, AVG(data_quality_score) AS dq FROM esg_curated.ghg_scope2 WHERE reporting_year = {year}", "esg_curated", q)
    s3 = _one(f"SELECT AVG(avg_pcaf_score) AS pcaf, AVG(high_quality_data_pct) AS hq, SUM(loan_count) AS loans FROM esg_curated.ghg_scope3_financed WHERE reporting_year = {year}", "esg_curated", q)
    op, op_base = _operational(year, q), _operational(BASE_YEAR, q)

    rows: list[dict[str, Any]] = [
        {"k": "s1", "label": "Scope 1 · Direct emissions", "group": "Scope 1", "v": cur.get("scope1_tco2e"), "base": base.get("scope1_tco2e"), "inc": True},
        {"k": "s2", "label": "Scope 2 · Purchased electricity (location-based)", "group": "Scope 2", "v": cur.get("scope2_location_tco2e"),
         "base": base.get("scope2_location_tco2e"), "inc": True, "market": cur.get("scope2_market_tco2e")},
    ]
    for k, label in SCOPE3_OPERATIONAL_CATEGORIES.items():
        have = bool(op and k in op)
        rows.append({"k": k, "label": label, "group": "Upstream", "v": round(op[k]["t"], 3) if have else None,
                     "base": round(op_base[k]["t"], 3) if op_base and k in op_base else None, "inc": have,
                     "note": None if have else "Not measured: no activity data in esg_raw.scope3_operational_activity"})
    rows.append({"k": "c8", "label": DOWNSTREAM_EXCLUDED["c8"], "group": "Upstream", "v": None, "base": None, "inc": False})
    for k in ("c9", "c10", "c11", "c12", "c13", "c14"):
        rows.append({"k": k, "label": DOWNSTREAM_EXCLUDED[k], "group": "Downstream", "v": None, "base": None, "inc": False})
    rows.append({"k": "c15", "label": "Cat 15 · Investments (financed emissions)", "group": "Downstream", "v": cur.get("scope3_cat15_gross_tco2e"),
                 "base": base.get("scope3_cat15_gross_tco2e"), "inc": True, "weighted": cur.get("scope3_cat15_weighted_tco2e")})

    inc = [r for r in rows if r["inc"] and r["v"] is not None]
    total = sum(r["v"] for r in inc)
    base_total = sum(r["base"] for r in inc if r["base"] is not None)
    cat15 = cur.get("scope3_cat15_gross_tco2e") or 0.0
    gases = gas_breakdown(s1.get("gj"), s1.get("l"), cur.get("scope1_tco2e"))

    part4 = [
        {"scope": "Scope 1", "method": "GHG Protocol Corporate Standard; fuel activity data x emission factors.", "data": f"Natural gas (GJ) and diesel (litres) from {int(s1.get('n') or 0)} facilities.",
         "quality": f"Facility score {s1.get('dq'):.1f}/4" if s1.get("dq") is not None else "n/a", "supplier": 0},
        {"scope": "Scope 2", "method": "GHG Protocol Scope 2 Guidance; location-based with regional grid factors, market-based with REC adjustment.",
         "data": f"{(s2.get('mwh') or 0):,.0f} MWh of electricity; {(s2.get('rec') or 0):,.0f} MWh covered by RECs.",
         "quality": f"Facility score {s2.get('dq'):.1f}/4" if s2.get("dq") is not None else "n/a", "supplier": 100},
    ]
    for k, label in SCOPE3_OPERATIONAL_CATEGORIES.items():
        r = (op or {}).get(k)
        part4.append({"scope": label, "method": (r or {}).get("method") or "Not measured", "data": (r or {}).get("acts") or "No activity data",
                      "quality": f"Score {r['dq']:.1f}/5" if r and r.get("dq") is not None else "n/a", "supplier": 0})
    part4.append({"scope": "Cat 15 · Investments", "method": "PCAF Global GHG Accounting Standard Part A; attribution = outstanding / (EVIC or equity + debt).",
                  "data": "Loan book from Core Banking; borrower emissions where reported, otherwise PCAF sector averages.",
                  "quality": f"Weighted PCAF score {(cur.get('avg_pcaf_data_quality') or s3.get('pcaf') or 0):.2f}", "supplier": round(s3.get("hq") or 0, 1)})

    assurance = cur.get("assurance_level") or "none"
    part6 = [
        ("Emissions subdivided by business unit / facility", True), ("Scope 3 disaggregated within categories", bool(op)),
        ("Emissions by individual gas", gases.get("available", False)), ("Other GHGs with IPCC GWP (e.g. NF3, CFCs)", False),
        ("Historic vs future scope 3 emissions", False), ("Qualitative information on unquantified sources", True),
        ("GHG removals / sequestration (separate)", False), ("Project-based reductions (separate)", False),
        ("Quantitative data quality assessment", True), ("Inventory uncertainty and quality-improvement policy", cur.get("avg_pcaf_data_quality") is not None),
        ("Type of assurance and assurer opinion", assurance in ("limited", "reasonable")),
        ("Intensity ratios and performance indicators", cur.get("intensity_tco2e_per_idr_bn") is not None),
        ("GHG management and reduction activities / targets", False), ("Supplier / partner engagement information", False),
        ("Benchmark comparison with external peers", True), ("Purchases of GHG reduction instruments / offsets", (s2.get("rec") or 0) > 0),
        ("Contractual provisions on GHG risks or obligations", False),
        ("Causes of changes that did not trigger base-year recalculation", False),
        ("Emissions for all years between base year and reporting year", bool(base)), ("Additional explanations for context", True),
    ]
    return {
        "source": "athena", "year": year, "base_year": BASE_YEAR,
        "part1": [["Company name", f"{COMPANY_NAME} ({BANK_ID})"], ["Consolidation approach", "Operational control"], ["Reporting period", f"1 Jan - 31 Dec {year}"],
                  ["Scope 3 activities included", ", ".join(r["label"].split(" · ")[0] for r in rows if r["k"].startswith("c") and r["inc"])],
                  ["Activities excluded (with justification)", "Categories 8-14: not relevant to a bank (no physical products sold, no franchises, no upstream leased assets under operational control)."],
                  ["Base year and rationale", f"{BASE_YEAR}: first year with complete facility-level energy data and a full PCAF-aligned loan book."],
                  ["Base-year recalculation policy", "Recalculate when structural or methodology changes alter emissions by more than 5%."]],
        "part2": rows, "gases": [{"scope": "Scope 1", **gases}, {"scope": "Scope 2", "available": False, "vals": None,
                                                              "note": "Grid factors are published as CO2e; no gas split available."}],
        "part3": {"total": 0, "note": "Biogenic CO2 is not applicable: no biomass combustion in owned operations."},
        "part4": part4, "part6": [[a, b] for a, b in part6],
        "totals": {"total": total, "base_total": base_total, "ops": total - cat15, "fin": cat15, "fin_share": (cat15 / total * 100) if total else None,
                   "change_pct": ((total - base_total) / base_total * 100) if base_total else None,
                   "intensity_per_idr_bn": cur.get("intensity_tco2e_per_idr_bn"), "intensity_per_fte": cur.get("intensity_tco2e_per_fte")},
        "part6_coverage": round(sum(1 for _, b in part6 if b) / len(part6) * 100),
        "assurance_level": assurance,
    }


def handle(params: dict[str, Any]) -> dict[str, Any]:
    year = common.year_param(params)
    return common.cached(f"ghg_inventory_{year}", lambda: build_inventory(year), refresh=str(params.get("refresh", "")).lower() == "true")


def build_and_store(event: dict[str, Any]) -> dict[str, Any]:
    """Step Functions task: build the inventory and persist it so the UI and the agent can read it."""
    year = int(event["year"])
    inv = build_inventory(year)
    key = f"ghg-inventory/{year}/inventory.json"
    common.s3_put(key, inv)
    common.cached(f"ghg_inventory_{year}", lambda: inv, refresh=True)
    return {"s3_key": key, "bucket": common.OUTPUT_BUCKET, "year": year, "total_tco2e": inv["totals"]["total"], "categories_measured": sum(1 for r in inv["part2"] if r["inc"])}
