"""ESG Data Hub and GHG accounting: the group's source data, the activity ledger and data alerts.

Everything is read with Athena from the raw zone (esg_raw.*, loaded from the source database by the data sync with
data contracts) and the ledger view esg_curated.ghg_ledger (sql/ddl/06_group_data.sql), which multiplies every
activity record by its emission factor for each factor set. The SQL below is plain ANSI/Trino; the tests run the
same statements on DuckDB against the seed files.

One bundle of queries per year is cached (common.cached). Views (approach, factor set, entity) are computed from the
bundle in Python, so switching them in the UI costs no Athena query.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from . import common

try:
    import esg_metric_catalog as cat
except ImportError:  # pragma: no cover
    from _shared import esg_metric_catalog as cat  # type: ignore

Query = Callable[[str], list[dict[str, Any]]]
FACILITY_ID = re.compile(r"^[A-Z]{3}-[A-Z0-9]{3,6}$")
SCOPES = (1, 2, 3)
RAW_TABLES = {
    "entity": "Legal entities and ownership", "facility": "Facility master", "emission_factor": "Emission factor library",
    "activity_data": "Activity data (energy, fuel, water, waste, travel)", "esg_metric": "Social, governance and finance metrics",
    "energy_consumption": "Bank energy meter data (report pipeline)", "loan_portfolio": "Bank loan book (PCAF)",
    "hr_metrics": "Bank HR summary", "scope3_operational_activity": "Bank Scope 3 categories 1-7 (report pipeline)",
}


def _athena(sql: str) -> list[dict[str, Any]]:
    return common.athena(sql, database="esg_curated")


def _f(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


# ── queries ───────────────────────────────────────────────────────────────────────────────────────
def queries(year: int) -> dict[str, str]:
    y, b = int(year), int(common.BASE_YEAR)
    years = f"{y}, {b}" if b != y else f"{y}"
    monthly = ", ".join(f"('{a}')" for a in cat.MONTHLY_REQUIRED)
    return {
        "summary": f"""
            SELECT reporting_year, entity_id, entity_name, ownership_pct, CAST(operational_control AS INTEGER) AS control,
                   coalesce(ef_set, 'NONE') AS ef_set, coalesce(scope, 0) AS scope, coalesce(category, 'unmapped') AS category,
                   activity_type, unit, min(ef_unit) AS ef_unit, min(ef_source) AS ef_source, min(factor_kgco2e) AS factor_min, max(factor_kgco2e) AS factor_max,
                   sum(quantity) AS quantity, sum(coalesce(instrument_qty, 0.0)) AS instrument_qty,
                   sum(CASE WHEN is_estimated THEN quantity ELSE 0.0 END) AS estimated_qty,
                   sum(coalesce(tco2e, 0.0)) AS tco2e, sum(coalesce(tco2e_market, 0.0)) AS tco2e_market, count(*) AS records
            FROM esg_curated.ghg_ledger WHERE reporting_year IN ({years})
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10""",
        "monthly": f"""
            SELECT entity_id, coalesce(ef_set, 'NONE') AS ef_set, coalesce(scope, 0) AS scope, reporting_month AS month,
                   sum(coalesce(tco2e, 0.0)) AS tco2e, sum(coalesce(tco2e_market, 0.0)) AS tco2e_market
            FROM esg_curated.ghg_ledger WHERE reporting_year = {y} GROUP BY 1, 2, 3, 4""",
        "facilities": f"""
            SELECT facility_id, facility_name, entity_id, facility_type, grid_region, province, floor_area_m2, headcount,
                   coalesce(ef_set, 'NONE') AS ef_set, coalesce(scope, 0) AS scope,
                   sum(coalesce(tco2e, 0.0)) AS tco2e, sum(coalesce(tco2e_market, 0.0)) AS tco2e_market,
                   sum(CASE WHEN is_estimated THEN 1 ELSE 0 END) AS estimated_records, count(*) AS records
            FROM esg_curated.ghg_ledger WHERE reporting_year = {y} GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10""",
        "facility_master": f"""
            SELECT facility_id, facility_name, entity_id, facility_type, grid_region, province, city, floor_area_m2, headcount, ownership_type, status
            FROM esg_raw.facility WHERE reporting_year = {y}""",
        "coverage": f"""
            SELECT f.entity_id, a.activity_type, count(DISTINCT a.facility_id) AS facilities
            FROM esg_raw.activity_data a JOIN esg_raw.facility f ON f.facility_id = a.facility_id AND f.reporting_year = a.reporting_year
            WHERE a.reporting_year = {y} GROUP BY 1, 2""",
        "gaps": f"""
            WITH req AS (SELECT * FROM (VALUES {monthly}) AS t(activity_type)),
                 fac AS (SELECT facility_id, entity_id, facility_name FROM esg_raw.facility WHERE reporting_year = {y}),
                 got AS (SELECT facility_id, activity_type, count(DISTINCT reporting_month) AS months
                         FROM esg_raw.activity_data WHERE reporting_year = {y} GROUP BY 1, 2)
            SELECT fac.entity_id, fac.facility_id, fac.facility_name, req.activity_type, coalesce(got.months, 0) AS months
            FROM fac CROSS JOIN req LEFT JOIN got ON got.facility_id = fac.facility_id AND got.activity_type = req.activity_type
            WHERE coalesce(got.months, 0) BETWEEN 1 AND 11""",
        "outliers": f"""
            SELECT facility_id, entity_id, activity_type, reporting_month, quantity, unit, others_avg FROM (
                SELECT facility_id, entity_id, activity_type, reporting_month, quantity, unit,
                       (sum(quantity) OVER (PARTITION BY facility_id, activity_type) - quantity)
                           / (count(*) OVER (PARTITION BY facility_id, activity_type) - 1) AS others_avg,
                       count(*) OVER (PARTITION BY facility_id, activity_type) AS n
                FROM esg_raw.activity_data
                WHERE reporting_year = {y} AND activity_type IN ('electricity_grid', 'natural_gas', 'diesel_stationary', 'gasoline_fleet', 'diesel_fleet', 'water_supply')
            ) t WHERE n >= 6 AND others_avg > 0 AND quantity > 3 * others_avg
            ORDER BY quantity / others_avg DESC LIMIT 25""",
        "metrics": f"""
            SELECT reporting_year, entity_id, pillar, topic, metric, dimension, value, unit, data_source, standard_ref
            FROM esg_raw.esg_metric WHERE reporting_year IN ({years})""",
        "factors": f"""
            SELECT ef_set, activity_type, region, unit, scope, category, co2_kg, ch4_kg, n2o_kg, co2e_kg, gwp_ch4, gwp_n2o, gwp_basis, source, notes,
                   co2_kg + ch4_kg * gwp_ch4 + n2o_kg * gwp_n2o + co2e_kg AS factor_kgco2e
            FROM esg_raw.emission_factor WHERE reporting_year = {y}""",
        "counts": " UNION ALL ".join(f"SELECT '{t}' AS tbl, count(*) AS n FROM esg_raw.{t} WHERE reporting_year = {y}" for t in RAW_TABLES),
        "reported": f"""
            SELECT scope1_tco2e, scope2_location_tco2e, scope2_market_tco2e FROM esg_aggregated.ghg_summary_annual
            WHERE reporting_year = {y} AND metric_key LIKE '{common.BANK_ID}_%' LIMIT 1""",
        "bank_financed": f"""
            SELECT reporting_year, sum(borrower_emissions_tco2e * pcaf_attribution_factor) AS financed_tco2e, sum(outstanding_idr) AS outstanding_idr,
                   sum(pcaf_data_quality_score * outstanding_idr) / sum(outstanding_idr) AS pcaf_score
            FROM esg_raw.loan_portfolio WHERE reporting_year IN ({years}) AND record_status = 'validated' GROUP BY 1""",
        "stationary_bank": f"""
            SELECT activity_type, sum(tco2e) AS tco2e, sum(tco2e_market) AS tco2e_market FROM esg_curated.ghg_ledger
            WHERE reporting_year = {y} AND entity_id = 'ENT-BANK' AND ef_set = 'ID_NATIONAL'
              AND activity_type IN ('natural_gas', 'diesel_stationary', 'electricity_grid') GROUP BY 1""",
    }


OPTIONAL = {"reported", "bank_financed", "counts", "stationary_bank"}  # these may fail (older tables) without failing the page


def load_bundle(year: int, q: Query | None = None) -> dict[str, Any]:
    """Run every query for the year (in parallel). Required queries raise; optional ones record an error."""
    q = q or _athena
    qs = queries(year)
    out: dict[str, Any] = {"year": int(year), "base_year": int(common.BASE_YEAR), "errors": {}}

    def run(item: tuple[str, str]) -> tuple[str, Any, str | None]:
        name, sql = item
        try:
            return name, q(sql), None
        except Exception as exc:  # noqa: BLE001
            if name not in OPTIONAL:
                raise
            return name, [], str(exc)[:200]

    with ThreadPoolExecutor(max_workers=8) as pool:
        for name, rows, err in pool.map(run, qs.items()):
            out[name] = rows
            if err:
                out["errors"][name] = err
    if not out["summary"]:
        raise LookupError(f"No group activity data for {year}. Run the data sync for {year} (tables entity, facility, emission_factor, activity_data, esg_metric).")
    return out


def _refresh(p: dict[str, Any]) -> bool:
    return str(p.get("refresh") or "").lower() in ("1", "true", "yes")


def bundle(year: int, refresh: bool = False) -> dict[str, Any]:
    return common.cached(f"datahub_bundle_{int(year)}", lambda: load_bundle(year), refresh=refresh)


# ── helpers ───────────────────────────────────────────────────────────────────────────────────────
def _params(p: dict[str, Any]) -> tuple[str, str, str]:
    approach = str(p.get("approach") or "control")
    ef_set = str(p.get("ef_set") or "ID_NATIONAL")
    entity = str(p.get("entity") or "all")
    if approach not in cat.APPROACHES:
        raise ValueError(f"approach must be one of {list(cat.APPROACHES)}")
    if ef_set not in cat.EF_SETS:
        raise ValueError(f"ef_set must be one of {list(cat.EF_SETS)}")
    if entity != "all" and not re.match(r"^ENT-[A-Z]{2,6}$", entity):
        raise ValueError("invalid entity")
    return approach, ef_set, entity


def _entities(b: dict[str, Any], year: int) -> dict[str, dict[str, Any]]:
    ents: dict[str, dict[str, Any]] = {}
    for r in b["summary"]:
        if int(r["reporting_year"]) == year:
            ents.setdefault(r["entity_id"], {"entity_id": r["entity_id"], "name": r["entity_name"], "ownership_pct": _f(r["ownership_pct"]),
                                             "operational_control": bool(int(r["control"] or 0))})
    return ents


def _weight(ent: dict[str, Any], approach: str) -> float:
    if approach == "equity":
        return ent["ownership_pct"] / 100.0
    return 1.0 if ent["operational_control"] else 0.0


def _rows(b: dict[str, Any], year: int, ef_set: str, entity: str) -> list[dict[str, Any]]:
    """Summary rows for one year and factor set (records without a factor are kept so they are visible)."""
    return [r for r in b["summary"] if int(r["reporting_year"]) == year and r["ef_set"] in (ef_set, "NONE")
            and (entity == "all" or r["entity_id"] == entity)]


def _scope_totals(rows: list[dict[str, Any]], weights: dict[str, float]) -> dict[str, float]:
    t = {"s1": 0.0, "s2_location": 0.0, "s2_market": 0.0, "s3": 0.0}
    for r in rows:
        w = weights.get(r["entity_id"], 0.0)
        s = int(r["scope"] or 0)
        if s == 1:
            t["s1"] += _f(r["tco2e"]) * w
        elif s == 2:
            t["s2_location"] += _f(r["tco2e"]) * w
            t["s2_market"] += _f(r["tco2e_market"]) * w
        elif s == 3:
            t["s3"] += _f(r["tco2e"]) * w
    t["total_location"] = t["s1"] + t["s2_location"] + t["s3"]
    t["total_market"] = t["s1"] + t["s2_market"] + t["s3"]
    t["s1_s2_market"] = t["s1"] + t["s2_market"]
    return {k: round(v, 2) for k, v in t.items()}


def _pct(a: float, b: float) -> float | None:
    return round((a - b) / b * 100, 1) if b else None


def _headcount(b: dict[str, Any], entity: str, weights: dict[str, float]) -> tuple[float, float]:
    heads = area = 0.0
    for f in b["facility_master"]:
        if entity in ("all", f["entity_id"]) and weights.get(f["entity_id"], 0) > 0:
            heads += _f(f["headcount"])
            area += _f(f["floor_area_m2"])
    return heads, area


def _financed(b: dict[str, Any], year: int) -> list[dict[str, Any]]:
    out = []
    for r in b.get("bank_financed", []):
        if int(r["reporting_year"]) == year:
            out.append({"entity_id": "ENT-BANK", "financed_tco2e": round(_f(r["financed_tco2e"]), 1), "outstanding_idr": _f(r["outstanding_idr"]),
                        "pcaf_score": round(_f(r["pcaf_score"]), 2), "source": "esg_raw.loan_portfolio"})
    sub: dict[str, dict[str, Any]] = {}
    for m in b["metrics"]:
        if int(m["reporting_year"]) == year and m["topic"] == "financed_emissions":
            e = sub.setdefault(m["entity_id"], {"entity_id": m["entity_id"], "financed_tco2e": 0.0, "outstanding_idr": 0.0, "_score": 0.0, "source": "esg_raw.esg_metric"})
            if m["metric"] == "financed_tco2e":
                e["financed_tco2e"] += _f(m["value"])
            elif m["metric"] == "outstanding_idr":
                e["outstanding_idr"] += _f(m["value"])
    for e in sub.values():
        e["financed_tco2e"] = round(e["financed_tco2e"], 1)
        e.pop("_score")
        out.append(e)
    return out


# ── views ─────────────────────────────────────────────────────────────────────────────────────────
def ledger(p: dict[str, Any], b: dict[str, Any] | None = None) -> dict[str, Any]:
    year = common.year_param(p)
    approach, ef_set, entity = _params(p)
    b = b or bundle(year, _refresh(p))
    ents = _entities(b, year)
    weights = {k: _weight(v, approach) for k, v in ents.items()}
    rows = _rows(b, year, ef_set, entity)
    totals = _scope_totals(rows, weights)

    by_entity = []
    for eid, e in ents.items():
        if entity not in ("all", eid):
            continue
        t = _scope_totals([r for r in rows if r["entity_id"] == eid], {eid: weights[eid]})
        gross = _scope_totals([r for r in rows if r["entity_id"] == eid], {eid: 1.0})
        by_entity.append({**e, "weight": weights[eid], "included": weights[eid] > 0, **t, "gross_total_market": gross["total_market"]})

    cats: dict[tuple, dict[str, Any]] = {}
    for r in rows:
        w = weights.get(r["entity_id"], 0.0)
        key = (int(r["scope"] or 0), r["category"], r["activity_type"])
        c = cats.setdefault(key, {"scope": key[0], "category": key[1], "category_label": cat.CATEGORY_LABELS.get(key[1], key[1]),
                                  "activity_type": key[2], "activity_label": cat.ACTIVITY_LABELS.get(key[2], key[2]), "unit": r["unit"],
                                  "ef_unit": r.get("ef_unit"), "ef_source": r.get("ef_source"), "factor_min": r.get("factor_min"), "factor_max": r.get("factor_max"),
                                  "quantity": 0.0, "estimated_qty": 0.0, "tco2e": 0.0, "tco2e_market": 0.0, "records": 0})
        c["quantity"] += _f(r["quantity"]) * w
        c["estimated_qty"] += _f(r["estimated_qty"]) * w
        c["tco2e"] += _f(r["tco2e"]) * w
        c["tco2e_market"] += _f(r["tco2e_market"]) * w
        c["records"] += int(r["records"] or 0)
    by_activity = []
    for c in sorted(cats.values(), key=lambda c: (c["scope"], -c["tco2e"])):
        c["estimated_pct"] = round(c["estimated_qty"] / c["quantity"] * 100, 1) if c["quantity"] else 0.0
        for k in ("quantity", "estimated_qty", "tco2e", "tco2e_market"):
            c[k] = round(c[k], 2)
        by_activity.append(c)

    months = {m: {"month": m, "s1": 0.0, "s2_location": 0.0, "s2_market": 0.0, "s3": 0.0} for m in range(1, 13)}
    for r in b["monthly"]:
        if r["ef_set"] not in (ef_set, "NONE") or (entity != "all" and r["entity_id"] != entity):
            continue
        w = weights.get(r["entity_id"], 0.0)
        m, s = int(r["month"]), int(r["scope"] or 0)
        if s == 1:
            months[m]["s1"] += _f(r["tco2e"]) * w
        elif s == 2:
            months[m]["s2_location"] += _f(r["tco2e"]) * w
            months[m]["s2_market"] += _f(r["tco2e_market"]) * w
        elif s == 3:
            months[m]["s3"] += _f(r["tco2e"]) * w
    by_month = [{k: (round(v, 1) if k != "month" else v) for k, v in m.items()} for m in months.values()]

    facs = facility_totals(b, ef_set, weights, entity)
    regions: dict[str, dict[str, Any]] = {}
    for f in facs:
        g = regions.setdefault(f["grid_region"], {"grid_region": f["grid_region"], "facilities": 0, "s1": 0.0, "s2_market": 0.0, "s2_location": 0.0, "s3": 0.0})
        g["facilities"] += 1
        for k in ("s1", "s2_market", "s2_location", "s3"):
            g[k] += f[k]
    by_region = sorted(({**g, **{k: round(g[k], 1) for k in ("s1", "s2_market", "s2_location", "s3")}} for g in regions.values()),
                       key=lambda g: -(g["s1"] + g["s2_market"]))

    heads, area = _headcount(b, entity, weights)
    base_rows = _rows(b, b["base_year"], ef_set, entity)
    base_ents = _entities(b, b["base_year"])
    base = _scope_totals(base_rows, {k: _weight(v, approach) for k, v in base_ents.items()}) if base_rows else None
    recalc = {s: _scope_totals(_rows(b, year, s, entity), weights) for s in cat.EF_SETS}
    tgt = cat.TARGET
    trajectory = None
    if base and year >= tgt["base_year"]:
        start = base["s1_s2_market"]
        path = [{"year": y, "target": round(start * (1 - tgt["reduction_pct"] / 100 * (y - tgt["base_year"]) / (tgt["target_year"] - tgt["base_year"])), 1)}
                for y in range(tgt["base_year"], tgt["target_year"] + 1)]
        actual = {b["base_year"]: start, year: totals["s1_s2_market"]}
        for pt in path:
            pt["actual"] = round(actual[pt["year"]], 1) if pt["year"] in actual else None
        on_track = totals["s1_s2_market"] <= next(pt["target"] for pt in path if pt["year"] == year)
        trajectory = {**tgt, "path": path, "on_track": on_track}

    reported = (b.get("reported") or [None])[0]
    recon = None
    if reported and entity in ("all", "ENT-BANK"):
        st = {r["activity_type"]: r for r in b.get("stationary_bank", [])}
        led_s1 = _f(st.get("natural_gas", {}).get("tco2e")) + _f(st.get("diesel_stationary", {}).get("tco2e"))
        led_s2l = _f(st.get("electricity_grid", {}).get("tco2e"))
        led_s2m = _f(st.get("electricity_grid", {}).get("tco2e_market"))
        recon = {"note": "Parent bank, stationary combustion and grid electricity only, national factor set: the scope of the published inventory.",
                 "explanation": "Differences come from missing records: the report pipeline fills missing fuel readings with the monthly mean, "
                                "the ledger counts recorded activity only and raises a data alert for each gap.",
                 "rows": [{"item": label, "ledger": round(a, 1), "reported": round(_f(r), 1), "diff_pct": _pct(a, _f(r))}
                          for label, a, r in (("Scope 1 stationary", led_s1, reported.get("scope1_tco2e")),
                                              ("Scope 2 location-based", led_s2l, reported.get("scope2_location_tco2e")),
                                              ("Scope 2 market-based", led_s2m, reported.get("scope2_market_tco2e")))]}
    financed = [f for f in _financed(b, year) if entity in ("all", f["entity_id"])]
    for f in financed:
        f["weighted_tco2e"] = round(f["financed_tco2e"] * weights.get(f["entity_id"], 0.0), 1)
    return {
        "year": year, "base_year": b["base_year"], "approach": approach, "approach_label": cat.APPROACHES[approach], "ef_set": ef_set,
        "ef_set_label": cat.EF_SETS[ef_set], "entity": entity, "totals": totals, "base_totals": base,
        "change_pct": {k: _pct(totals[k], base[k]) for k in totals} if base and year != b["base_year"] else None,
        "by_entity": by_entity, "by_activity": by_activity, "by_month": by_month, "by_region": by_region,
        "top_facilities": sorted(facs, key=lambda f: -f["total_market"])[:15],
        "intensity": {"per_fte": round(totals["s1_s2_market"] / heads, 3) if heads else None, "per_m2_kg": round(totals["s1_s2_market"] * 1000 / area, 2) if area else None,
                      "headcount": heads, "floor_area_m2": area},
        "recalc": {s: {"label": cat.EF_SETS[s], **v} for s, v in recalc.items()}, "trajectory": trajectory, "reconciliation": recon,
        "financed": financed, "unmapped_records": sum(int(r["records"] or 0) for r in rows if r["ef_set"] == "NONE"),
        "entities": [{"id": k, "name": v["name"]} for k, v in ents.items()],
    }


def facility_totals(b: dict[str, Any], ef_set: str, weights: dict[str, float], entity: str = "all") -> list[dict[str, Any]]:
    facs: dict[str, dict[str, Any]] = {}
    for r in b["facilities"]:
        if r["ef_set"] not in (ef_set, "NONE") or (entity != "all" and r["entity_id"] != entity):
            continue
        w = weights.get(r["entity_id"], 0.0)
        f = facs.setdefault(r["facility_id"], {k: r[k] for k in ("facility_id", "facility_name", "entity_id", "facility_type", "grid_region", "province")}
                            | {"floor_area_m2": _f(r["floor_area_m2"]), "headcount": int(_f(r["headcount"])), "weight": w,
                               "s1": 0.0, "s2_location": 0.0, "s2_market": 0.0, "s3": 0.0, "records": 0, "estimated_records": 0})
        s = int(r["scope"] or 0)
        if s == 1:
            f["s1"] += _f(r["tco2e"]) * w
        elif s == 2:
            f["s2_location"] += _f(r["tco2e"]) * w
            f["s2_market"] += _f(r["tco2e_market"]) * w
        elif s == 3:
            f["s3"] += _f(r["tco2e"]) * w
        f["records"] += int(r["records"] or 0)
        f["estimated_records"] += int(r["estimated_records"] or 0)
    out = []
    for f in facs.values():
        for k in ("s1", "s2_location", "s2_market", "s3"):
            f[k] = round(f[k], 2)
        f["total_market"] = round(f["s1"] + f["s2_market"] + f["s3"], 2)
        f["kg_per_m2"] = round((f["s1"] + f["s2_market"]) * 1000 / f["floor_area_m2"], 2) if f["floor_area_m2"] else None
        f["estimated_pct"] = round(f["estimated_records"] / f["records"] * 100, 1) if f["records"] else 0.0
        out.append(f)
    return out


def facilities(p: dict[str, Any], b: dict[str, Any] | None = None) -> dict[str, Any]:
    year = common.year_param(p)
    approach, ef_set, entity = _params(p)
    b = b or bundle(year, _refresh(p))
    ents = _entities(b, year)
    weights = {k: _weight(v, approach) for k, v in ents.items()}
    facs = {f["facility_id"]: f for f in facility_totals(b, ef_set, {k: 1.0 for k in ents}, entity)}  # facility view is gross (100 %)
    alerts_by_fac: dict[str, int] = {}
    for a in data_alerts(b)["alerts"]:
        if a.get("facility_id"):
            alerts_by_fac[a["facility_id"]] = alerts_by_fac.get(a["facility_id"], 0) + 1
    rows = []
    for m in b["facility_master"]:
        if entity not in ("all", m["entity_id"]):
            continue
        f = facs.get(m["facility_id"], {})
        rows.append({**{k: m[k] for k in ("facility_id", "facility_name", "entity_id", "facility_type", "grid_region", "province", "city", "ownership_type", "status")},
                     "floor_area_m2": _f(m["floor_area_m2"]), "headcount": int(_f(m["headcount"])), "included": weights.get(m["entity_id"], 0) > 0,
                     **{k: f.get(k, 0.0) for k in ("s1", "s2_location", "s2_market", "s3", "total_market", "kg_per_m2", "estimated_pct")},
                     "records": f.get("records", 0), "alerts": alerts_by_fac.get(m["facility_id"], 0)})
    return {"year": year, "ef_set": ef_set, "approach": approach, "facilities": sorted(rows, key=lambda r: -(r["total_market"] or 0)),
            "entities": [{"id": k, "name": v["name"]} for k, v in ents.items()]}


def facility_detail(p: dict[str, Any], q: Query | None = None) -> dict[str, Any]:
    """Every activity record of one facility with its factor and calculation (the audit trail of a number)."""
    year = common.year_param(p)
    _, ef_set, _ = _params(p)
    fid = str(p.get("facility_id") or p.get("id") or "")
    if not FACILITY_ID.match(fid):
        raise ValueError("invalid facility id")
    q = q or _athena
    sql = f"""
        SELECT reporting_month AS month, activity_id, activity_type, quantity, unit, instrument_qty, data_source,
               CAST(is_estimated AS INTEGER) AS estimated, evidence_ref, ef_set, scope, category, ef_unit, ef_source, gwp_basis,
               factor_kgco2e, tco2e, tco2e_market, facility_name, entity_id, entity_name, facility_type, grid_region, province, floor_area_m2, headcount
        FROM esg_curated.ghg_ledger
        WHERE reporting_year = {year} AND facility_id = '{fid}' AND (ef_set = '{ef_set}' OR ef_set IS NULL)
        ORDER BY activity_type, reporting_month"""

    def build() -> dict[str, Any]:
        rows = q(sql)
        if not rows:
            raise LookupError(f"No activity data for {fid} in {year}")
        head = rows[0]
        recs = [{k: r[k] for k in ("month", "activity_id", "activity_type", "quantity", "unit", "instrument_qty", "data_source", "evidence_ref",
                                   "scope", "category", "ef_unit", "ef_source", "factor_kgco2e", "tco2e", "tco2e_market")}
                | {"estimated": bool(int(r["estimated"] or 0)), "activity_label": cat.ACTIVITY_LABELS.get(r["activity_type"], r["activity_type"])} for r in rows]
        summary: dict[str, dict[str, Any]] = {}
        for r in recs:
            s = summary.setdefault(r["activity_type"], {"activity_type": r["activity_type"], "activity_label": r["activity_label"], "unit": r["unit"],
                                                        "scope": r["scope"], "factor_kgco2e": r["factor_kgco2e"], "ef_source": r["ef_source"],
                                                        "quantity": 0.0, "tco2e": 0.0, "tco2e_market": 0.0, "months": set(), "estimated": 0})
            s["quantity"] += _f(r["quantity"])
            s["tco2e"] += _f(r["tco2e"])
            s["tco2e_market"] += _f(r["tco2e_market"])
            s["months"].add(r["month"])
            s["estimated"] += int(r["estimated"])
        acts = []
        for s in summary.values():
            s["months"] = len(s["months"])
            for k in ("quantity", "tco2e", "tco2e_market"):
                s[k] = round(s[k], 3)
            acts.append(s)
        return {"year": year, "ef_set": ef_set, "facility": {k: head[k] for k in ("facility_name", "entity_id", "entity_name", "facility_type", "grid_region", "province", "floor_area_m2", "headcount")}
                | {"facility_id": fid}, "activities": sorted(acts, key=lambda s: (s["scope"] or 9, -s["tco2e"])), "records": recs}

    return build() if q is not _athena else common.cached(f"datahub_facility_{year}_{ef_set}_{fid}", build)


def factors(p: dict[str, Any], b: dict[str, Any] | None = None) -> dict[str, Any]:
    year = common.year_param(p)
    b = b or bundle(year, _refresh(p))
    rows = sorted(b["factors"], key=lambda r: (r["ef_set"], int(r["scope"]), r["category"], r["activity_type"], r["region"]))
    for r in rows:
        r["activity_label"] = cat.ACTIVITY_LABELS.get(r["activity_type"], r["activity_type"])
        r["category_label"] = cat.CATEGORY_LABELS.get(r["category"], r["category"])
    return {"year": year, "sets": [{"id": k, "label": v} for k, v in cat.EF_SETS.items()], "factors": rows,
            "note": "Illustrative factor sets for the synthetic dataset. Replace them with the officially published values before external use."}


def _env_metrics(b: dict[str, Any], year: int) -> dict[str, dict[str, float]]:
    """Environmental metrics per entity derived from activity quantities (factor set does not matter here)."""
    q: dict[str, dict[str, float]] = {}
    for r in b["summary"]:
        if int(r["reporting_year"]) != year or r["ef_set"] not in ("ID_NATIONAL", "NONE"):
            continue
        e = q.setdefault(r["entity_id"], {})
        e[r["activity_type"]] = e.get(r["activity_type"], 0.0) + _f(r["quantity"])
        if r["activity_type"] == "electricity_grid":
            e["_rec_kwh"] = e.get("_rec_kwh", 0.0) + _f(r["instrument_qty"])
    heads = {}
    for m in b["metrics"]:
        if int(m["reporting_year"]) == year and m["metric"] == "headcount" and m["dimension"] == "total":
            heads[m["entity_id"]] = _f(m["value"])
    out: dict[str, dict[str, float]] = {}
    for eid, a in q.items():
        energy = sum(a.get(k, 0.0) * f for k, f in cat.ENERGY_GJ.items())
        elec = a.get("electricity_grid", 0.0) + a.get("solar_pv", 0.0)
        waste = a.get("waste_landfill", 0.0) + a.get("waste_recycled", 0.0)
        m: dict[str, float] = {"energy_total_gj": energy, "electricity_mwh": elec / 1000}
        if elec:
            m["renewable_share_pct"] = (a.get("solar_pv", 0.0) + a.get("_rec_kwh", 0.0)) / elec * 100
        if heads.get(eid):
            m["energy_intensity_gj_per_fte"] = energy / heads[eid]
        if "water_supply" in a:
            m["water_withdrawal_m3"] = a["water_supply"]
        if waste:
            m["waste_total_t"] = waste / 1000
            m["waste_diverted_pct"] = a.get("waste_recycled", 0.0) / waste * 100
        if "paper_a4" in a:
            m["paper_reams"] = a["paper_a4"]
        out[eid] = {k: round(v, 3) for k, v in m.items()}
    return out


def _entity_types(b: dict[str, Any]) -> dict[str, str]:
    types = {"ENT-BANK": "bank", "ENT-SYR": "sharia_bank", "ENT-MFN": "multifinance", "ENT-SEK": "securities", "ENT-ASR": "insurance"}
    return types  # entity types are not in the summary query; ids are stable in the dataset


def _applies(metric: dict[str, Any], etype: str) -> bool:
    return metric["applies"] == "all" or etype in metric["applies"]


def metrics(p: dict[str, Any], b: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every catalog metric per entity for the year and the base year, with coverage. Missing values stay None."""
    year = common.year_param(p)
    b = b or bundle(year, _refresh(p))
    ents = _entities(b, year)
    types = _entity_types(b)
    vals: dict[tuple[int, str, str], float] = {}
    dims_all: dict[tuple[int, str, str], dict[str, float]] = {}
    for y in {year, b["base_year"]}:
        for eid, m in _env_metrics(b, y).items():
            for k, v in m.items():
                vals[(y, eid, k)] = v
    for m in b["metrics"]:
        y = int(m["reporting_year"])
        if m["dimension"] == "total":
            vals[(y, m["entity_id"], m["metric"])] = _f(m["value"])
        else:
            dims_all.setdefault((y, m["entity_id"], m["metric"]), {})[m["dimension"]] = _f(m["value"])
    # derived: totals of the broken-down metrics (sustainable finance by category, financed emissions by sector)
    for (y, eid, metric), dims in dims_all.items():
        if metric in ("sustainable_finance_idr", "financed_tco2e"):
            vals[(y, eid, metric)] = sum(dims.values())
    breakdown = {(eid, metric): dims for (y, eid, metric), dims in dims_all.items() if y == year}
    for y in {year, b["base_year"]}:
        for f in _financed(b, y):
            if f["entity_id"] == "ENT-BANK":
                vals[(y, "ENT-BANK", "financed_tco2e")] = f["financed_tco2e"]
    rows = []
    for meta in cat.METRICS:
        per = []
        for eid, e in ents.items():
            etype = types.get(eid, "")
            applies = _applies(meta, etype)
            v = vals.get((year, eid, meta["id"]))
            bv = vals.get((b["base_year"], eid, meta["id"]))
            per.append({"entity_id": eid, "applies": applies, "value": v, "base": bv, "change_pct": _pct(v, bv) if (v is not None and bv) else None,
                        "status": "not_applicable" if not applies else "reported" if v is not None else "missing",
                        "breakdown": breakdown.get((eid, meta["id"]))})
        applicable = [x for x in per if x["applies"]]
        rows.append({**meta, "entities": per, "coverage": f"{sum(1 for x in applicable if x['status'] == 'reported')}/{len(applicable)}"})
    kubl = {}
    for (eid, metric), dims in breakdown.items():
        if metric == "sustainable_finance_idr":
            for d, v in dims.items():
                kubl.setdefault(d, {"category": d, "label": cat.KUBL_LABELS.get(d, d), "total_idr": 0.0, "by_entity": {}})
                kubl[d]["total_idr"] += v
                kubl[d]["by_entity"][eid] = v
    reported = sum(1 for r in rows for x in r["entities"] if x["status"] == "reported")
    applicable = sum(1 for r in rows for x in r["entities"] if x["applies"])
    return {"year": year, "base_year": b["base_year"], "entities": [{"id": k, "name": v["name"], "type": types.get(k)} for k, v in ents.items()],
            "metrics": rows, "kubl": sorted(kubl.values(), key=lambda k: -k["total_idr"]),
            "coverage": {"reported": reported, "applicable": applicable, "pct": round(reported / applicable * 100, 1) if applicable else None}}


SEVERITY = {"high": 0, "medium": 1, "low": 2}


def data_alerts(b: dict[str, Any]) -> dict[str, Any]:
    """Data gaps and quality problems. Every alert says what is wrong, where, why it matters and what to do."""
    year = b["year"]
    alerts: list[dict[str, Any]] = []
    ents = _entities(b, year)
    fac_count: dict[str, int] = {}
    for f in b["facility_master"]:
        fac_count[f["entity_id"]] = fac_count.get(f["entity_id"], 0) + 1
    cov = {(r["entity_id"], r["activity_type"]): int(r["facilities"] or 0) for r in b["coverage"]}
    for eid in ents:
        for a in cat.MONTHLY_REQUIRED + cat.ANNUAL_REQUIRED:
            n, total = cov.get((eid, a), 0), fac_count.get(eid, 0)
            label = cat.ACTIVITY_LABELS.get(a, a)
            if total and n == 0:
                alerts.append({"id": f"NC-{eid}-{a}", "severity": "high", "kind": "not_collected", "entity_id": eid,
                               "title": f"{label} is not collected for {ents[eid]['name']}",
                               "detail": f"None of the {total} facilities reported {label.lower()} in {year}.",
                               "impact": "The group total is understated and the disclosure is incomplete; it is shown as missing, not as zero.",
                               "action": f"Ask {ents[eid]['name']} to submit {label.lower()} data, or document an estimate method."})
            elif total and n < total * 0.9:
                alerts.append({"id": f"CV-{eid}-{a}", "severity": "medium", "kind": "coverage", "entity_id": eid,
                               "title": f"{label}: {n} of {total} facilities reported ({ents[eid]['name']})",
                               "detail": f"{total - n} facilities have no {label.lower()} data for {year}.", "impact": "Partial coverage.",
                               "action": "Collect the missing facilities or extrapolate by floor area and disclose it."})
    small: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for g in b["gaps"]:
        missing = 12 - int(g["months"])
        label = cat.ACTIVITY_LABELS.get(g["activity_type"], g["activity_type"])
        if missing <= 2:  # one or two missing months: one alert per entity and activity, listing the facilities
            small.setdefault((g["entity_id"], g["activity_type"]), []).append(g)
            continue
        fid = g["facility_id"]
        alerts.append({"id": f"GAP-{fid}-{g['activity_type']}", "severity": "high" if g["activity_type"] == "electricity_grid" else "medium",
                       "kind": "missing_months", "entity_id": g["entity_id"], "facility_id": fid,
                       "title": f"{g['facility_name']}: {missing} months of {label.lower()} missing",
                       "detail": f"{g['months']} of 12 months reported for {year}.",
                       "impact": "Scope 2 is understated for this facility." if g["activity_type"] == "electricity_grid" else "The annual figure is incomplete.",
                       "action": "Request the missing invoices or meter readings; otherwise estimate from the facility's other months and flag it."})
    for (eid, act), gs in small.items():
        label = cat.ACTIVITY_LABELS.get(act, act)
        alerts.append({"id": f"GAPS-{eid}-{act}", "severity": "medium", "kind": "missing_months", "entity_id": eid,
                       "facilities": [g["facility_id"] for g in gs][:50],
                       "title": f"{ents.get(eid, {}).get('name', eid)}: {len(gs)} facilities miss 1-2 months of {label.lower()}",
                       "detail": "Records marked as excluded at the source or not delivered. " + ", ".join(g["facility_id"] for g in gs[:8]) + (" ..." if len(gs) > 8 else ""),
                       "impact": "The annual total is slightly understated.", "action": "Confirm whether the facilities were closed in those months or request the data."})
    for o in b["outliers"]:
        ratio = _f(o["quantity"]) / _f(o["others_avg"]) if _f(o["others_avg"]) else 0
        label = cat.ACTIVITY_LABELS.get(o["activity_type"], o["activity_type"])
        alerts.append({"id": f"OUT-{o['facility_id']}-{o['activity_type']}-{o['reporting_month']}", "severity": "medium", "kind": "outlier",
                       "entity_id": o["entity_id"], "facility_id": o["facility_id"],
                       "title": f"{o['facility_id']}: {label.lower()} in month {o['reporting_month']} is {ratio:.1f}x its usual level",
                       "detail": f"{_f(o['quantity']):,.0f} {o['unit']} against an average of {_f(o['others_avg']):,.0f} {o['unit']} in the other months.",
                       "impact": "A data-entry or meter error would overstate emissions.", "action": "Check the source document (evidence reference) and correct or confirm it."})
    for r in b["summary"]:
        if int(r["reporting_year"]) != year:
            continue
        if r["ef_set"] == "NONE":
            alerts.append({"id": f"EF-{r['entity_id']}-{r['activity_type']}", "severity": "high", "kind": "missing_factor", "entity_id": r["entity_id"],
                           "title": f"No emission factor for {r['activity_type']}", "detail": f"{r['records']} record(s) have no factor in the library for {year}.",
                           "impact": "These activities are not converted to emissions.", "action": "Add the factor to the emission factor library."})
        elif r["ef_set"] == "ID_NATIONAL":
            if r.get("ef_unit") and r["ef_unit"] != r["unit"]:
                alerts.append({"id": f"UNIT-{r['entity_id']}-{r['activity_type']}", "severity": "high", "kind": "unit_mismatch", "entity_id": r["entity_id"],
                               "title": f"Unit mismatch for {r['activity_type']}", "detail": f"Activity in {r['unit']}, factor per {r['ef_unit']}.",
                               "impact": "Emissions are wrong by the conversion factor.", "action": "Convert the activity data or use a factor in the same unit."})
            q, est = _f(r["quantity"]), _f(r["estimated_qty"])
            if q and est / q > 0.25 and r["activity_type"] not in ("commute_car", "commute_motorcycle", "commute_public"):
                alerts.append({"id": f"EST-{r['entity_id']}-{r['activity_type']}", "severity": "low", "kind": "estimated", "entity_id": r["entity_id"],
                               "title": f"{ents.get(r['entity_id'], {}).get('name', r['entity_id'])}: {est / q * 100:.0f}% of {cat.ACTIVITY_LABELS.get(r['activity_type'], r['activity_type']).lower()} is estimated",
                               "detail": "Estimates lower the data quality score and must be disclosed.", "impact": "Lower confidence in the figure.",
                               "action": "Replace estimates with measured data (invoices, hauler manifests)."})
    # catalog metrics that are missing
    m = metrics({"year": year}, b)
    for row in m["metrics"]:
        for x in row["entities"]:
            # environmental gaps are already reported per activity (not_collected / coverage); keep metric alerts for the rest
            if x["status"] == "missing" and (row["pillar"] != "environment" or row["id"] == "water_discharge_m3"):
                name = ents.get(x["entity_id"], {}).get("name", x["entity_id"])
                alerts.append({"id": f"MET-{x['entity_id']}-{row['id']}", "severity": "high" if row["required"] else "low", "kind": "missing_metric",
                               "entity_id": x["entity_id"], "metric": row["id"], "title": f"{row['label']} not reported by {name}",
                               "detail": f"{row['ref']} · {'required' if row['required'] else 'recommended'} for the sustainability report.",
                               "impact": "Shown as 'not reported' in the report; the disclosure checklist stays open.",
                               "action": f"Collect {row['label'].lower()} ({row['unit']}) for {year} from the {row['pillar']} data owner."})
    for k, err in (b.get("errors") or {}).items():
        alerts.append({"id": f"SRC-{k}", "severity": "low", "kind": "source", "title": f"Part of the data could not be read ({k})", "detail": err,
                       "impact": "Some figures on this page may be incomplete.", "action": "Run the data sync and scripts/apply_ddl.py."})
    alerts.sort(key=lambda a: (SEVERITY[a["severity"]], a["kind"], a["id"]))
    counts = {s: sum(1 for a in alerts if a["severity"] == s) for s in SEVERITY}
    kinds: dict[str, int] = {}
    for a in alerts:
        kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
    return {"year": year, "alerts": alerts, "counts": counts, "kinds": kinds}


def alerts(p: dict[str, Any], b: dict[str, Any] | None = None) -> dict[str, Any]:
    year = common.year_param(p)
    return data_alerts(b or bundle(year, _refresh(p)))


def overview(p: dict[str, Any], b: dict[str, Any] | None = None) -> dict[str, Any]:
    year = common.year_param(p)
    b = b or bundle(year, _refresh(p))
    led = ledger({"year": year, "approach": p.get("approach") or "control", "ef_set": p.get("ef_set") or "ID_NATIONAL"}, b)
    al = data_alerts(b)
    met = metrics({"year": year}, b)
    counts = {r["tbl"]: int(r["n"]) for r in b.get("counts", [])}
    contracts = {}
    for t in RAW_TABLES:
        rep = None
        try:
            rep = common.s3_get(f"etl-reports/latest/{t}_{year}.json")
        except Exception:  # noqa: BLE001 - contract reports are informative only
            rep = None
        if rep:
            contracts[t] = {"status": rep.get("status"), "warnings": rep.get("warnings"), "blocking": rep.get("blocking"), "generated_at": rep.get("generated_at")}
    facs_by_ent: dict[str, dict[str, float]] = {}
    for f in b["facility_master"]:
        e = facs_by_ent.setdefault(f["entity_id"], {"facilities": 0, "headcount": 0.0, "floor_area_m2": 0.0})
        e["facilities"] += 1
        e["headcount"] += _f(f["headcount"])
        e["floor_area_m2"] += _f(f["floor_area_m2"])
    types = _entity_types(b)
    entities = [{**e, **facs_by_ent.get(e["entity_id"], {}), "type": types.get(e["entity_id"]), "type_label": cat.ENTITY_TYPES.get(types.get(e["entity_id"], ""), ""),
                 "alerts": sum(1 for a in al["alerts"] if a.get("entity_id") == e["entity_id"])} for e in led["by_entity"]]
    datasets = [{"table": t, "label": label, "rows": counts.get(t), "contract": contracts.get(t),
                 "group": "group" if t in ("entity", "facility", "emission_factor", "activity_data", "esg_metric") else "bank"} for t, label in RAW_TABLES.items()]
    return {"year": year, "approach": led["approach"], "ef_set": led["ef_set"], "totals": led["totals"], "change_pct": led["change_pct"],
            "entities": entities, "datasets": datasets, "alerts": {"counts": al["counts"], "kinds": al["kinds"], "top": al["alerts"][:8]},
            "coverage": met["coverage"], "records": sum(int(r["records"] or 0) for r in b["summary"] if int(r["reporting_year"]) == year and r["ef_set"] in ("ID_NATIONAL", "NONE")),
            "lineage": [
                {"step": "Source database", "detail": "Amazon RDS PostgreSQL, schema esg (9 tables)", "where": "EsgDatabaseStack"},
                {"step": "Extract with data contracts", "detail": "Glue job esg-extract-rds checks types, keys, ranges and enums before writing", "where": "glue_jobs/esg_contracts.py"},
                {"step": "Raw zone", "detail": "S3 Parquet, one partition per reporting year, Athena tables esg_raw.*", "where": "sql/ddl/02, 05, 06"},
                {"step": "Activity ledger", "detail": "Athena view esg_curated.ghg_ledger: activity x emission factor, every factor set", "where": "sql/ddl/06_group_data.sql"},
                {"step": "Data Hub API", "detail": "Totals, breakdowns, alerts; cached 10 minutes", "where": "lambda/platform_api/datahub.py"},
                {"step": "Reports and agent", "detail": "Report pipeline (bank inventory) and the AgentCore agent's data tools", "where": "agentcore/orchestrator/agent.py"},
            ], "source_errors": b.get("errors")}


def agent_query(p: dict[str, Any]) -> dict[str, Any]:
    """Compact answers for the AgentCore agent (direct invocation)."""
    view = str(p.get("view") or "overview")
    year = common.year_param(p)
    if view == "facility":
        d = facility_detail(p)
        return {"facility": d["facility"], "activities": d["activities"]}
    b = bundle(year)
    if view == "ledger":
        led = ledger(p, b)
        return {k: led[k] for k in ("year", "approach_label", "ef_set_label", "totals", "base_totals", "change_pct", "by_entity", "recalc", "trajectory", "reconciliation", "financed", "intensity")} | {
            "by_activity": [{k: a[k] for k in ("category_label", "activity_label", "quantity", "unit", "tco2e", "estimated_pct", "ef_source")} for a in led["by_activity"]],
            "top_facilities": led["top_facilities"][:5]}
    if view == "alerts":
        al = data_alerts(b)
        return {"counts": al["counts"], "alerts": al["alerts"][:25]}
    if view == "metrics":
        m = metrics(p, b)
        return {"coverage": m["coverage"], "metrics": [{"id": r["id"], "label": r["label"], "unit": r["unit"], "ref": r["ref"],
                                                       "values": {x["entity_id"]: x["value"] if x["status"] == "reported" else x["status"] for x in r["entities"]}}
                                                      for r in m["metrics"] if p.get("pillar") in (None, "", r["pillar"])],
                "kubl": m["kubl"]}
    o = overview(p, b)
    return {k: o[k] for k in ("year", "totals", "change_pct", "entities", "coverage", "records")} | {"alerts": o["alerts"]["counts"], "top_alerts": o["alerts"]["top"][:5]}
