"""Portfolio analytics: PCAF data quality by asset class, TKBI-style green finance classification, peer benchmark
and the climate scenario run (which reuses the same loan-book aggregation).

Source: esg_raw.loan_portfolio (validated records only). The TKBI split per sector is an ASSUMPTION stored in
esg_domain.SECTOR_PROFILES (not an official classification); the response says so in ``basis``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from . import common
from .compliance import SCENARIO_RUN_KEY

try:
    import scenario_engine as se
    from esg_domain import PCAF_ASSET_CLASSES, SECTOR_PROFILES, asset_class_for, sector_profile
except ImportError:  # pragma: no cover
    from _shared import scenario_engine as se  # type: ignore
    from _shared.esg_domain import PCAF_ASSET_CLASSES, SECTOR_PROFILES, asset_class_for, sector_profile  # type: ignore

PEERS = json.loads((Path(__file__).parent / "config" / "peers.json").read_text())
GREEN_TARGET_2030 = 40.0  # % of the loan book, an assumption of the demo (override with env GREEN_TARGET_2030)
TN = 1e12

Q = common.athena


def _book(year: int, q: Callable[..., Any]) -> list[dict[str, Any]]:
    """Aggregate the validated loan book by (sector, loan type, rounded PCAF score)."""
    return q(f"""SELECT sector_nace, loan_type, CAST(ROUND(pcaf_data_quality_score) AS INTEGER) AS score,
        SUM(outstanding_idr) AS outstanding, SUM(borrower_emissions_tco2e * pcaf_attribution_factor) AS financed, COUNT(*) AS n
        FROM esg_raw.loan_portfolio WHERE reporting_year = {year} AND record_status = 'validated'
        GROUP BY 1, 2, 3""", "esg_raw")


def pcaf(year: int, q: Callable[..., Any] | None = None, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = rows if rows is not None else _book(year, q or Q)
    classes: dict[str, dict[str, Any]] = {}
    for r in rows:
        cid = asset_class_for(r["loan_type"], r["sector_nace"])
        c = classes.setdefault(cid, {"id": cid, "name": PCAF_ASSET_CLASSES[cid], "outstanding": 0.0, "financed": 0.0, "loans": 0, "by_score": {s: 0.0 for s in range(1, 6)}})
        sc = min(5, max(1, int(r["score"] or 5)))
        out = float(r["outstanding"] or 0)
        c["outstanding"] += out
        c["financed"] += float(r["financed"] or 0)
        c["loans"] += int(r["n"] or 0)
        c["by_score"][sc] += out
    total = sum(c["outstanding"] for c in classes.values())
    out_classes = []
    for c in classes.values():
        o = c["outstanding"] or 1.0
        dist = [round(c["by_score"][s] / o * 100, 1) for s in range(1, 6)]
        out_classes.append({"id": c["id"], "name": c["name"], "outstanding_tn": round(c["outstanding"] / TN, 3), "loans": c["loans"],
                            "financed_tco2e": round(c["financed"], 0), "dist_pct": dist,
                            "weighted_score": round(sum(c["by_score"][s] * s for s in range(1, 6)) / o, 2)})
    out_classes.sort(key=lambda x: -x["outstanding_tn"])
    portfolio = round(sum(c["weighted_score"] * c["outstanding_tn"] for c in out_classes) / (total / TN), 2) if total else None
    tot_dist = [round(sum(c["by_score"][s] for c in classes.values()) / total * 100, 1) if total else 0 for s in range(1, 6)]
    return {"year": year, "total_outstanding_tn": round(total / TN, 3), "portfolio_score": portfolio, "dist_pct": tot_dist,
            "classes": out_classes, "basis": "esg_raw.loan_portfolio, validated records, score rounded to the nearest PCAF tier"}


def tkbi(year: int, q: Callable[..., Any] | None = None, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = rows if rows is not None else _book(year, q or Q)
    by_sector: dict[str, float] = {}
    for r in rows:
        by_sector[r["sector_nace"]] = by_sector.get(r["sector_nace"], 0.0) + float(r["outstanding"] or 0)
    g = t = b = 0.0
    sectors = []
    for code, out in by_sector.items():
        key, prof = sector_profile(code)
        gs, ts, bs = prof["split"]
        g, t, b = g + out * gs, t + out * ts, b + out * bs
        sectors.append({"sector": prof["name"], "code": key, "exposure_tn": round(out / TN, 3),
                        "green_tn": round(out * gs / TN, 3), "transition_tn": round(out * ts / TN, 3), "brown_tn": round(out * bs / TN, 3)})
    total = g + t + b
    sectors.sort(key=lambda s: -s["exposure_tn"])
    return {"year": year, "total_tn": round(total / TN, 3), "green_tn": round(g / TN, 3), "transition_tn": round(t / TN, 3), "brown_tn": round(b / TN, 3),
            "green_ratio_pct": round(g / total * 100, 2) if total else None, "sectors": sectors,
            "basis": "ASSUMED TKBI-style split per sector (esg_domain.SECTOR_PROFILES); not an official classification"}


def green_trend(years: list[int], q: Callable[..., Any] | None = None, target: float | None = None) -> dict[str, Any]:
    """Actual green ratio for the years with data, then a straight-line projection to the 2030 target."""
    target = GREEN_TARGET_2030 if target is None else target
    actual = []
    for y in years:
        try:
            k = tkbi(y, q)
        except Exception:  # noqa: BLE001
            continue
        if k["green_ratio_pct"] is not None:
            actual.append({"year": y, "green_ratio_pct": k["green_ratio_pct"], "green_tn": k["green_tn"]})
    points = [dict(a, kind="actual") for a in actual]
    if actual:
        last = actual[-1]
        span = 2030 - last["year"]
        for y in range(last["year"] + 1, 2031):
            points.append({"year": y, "kind": "projection", "green_ratio_pct": round(last["green_ratio_pct"] + (target - last["green_ratio_pct"]) * (y - last["year"]) / span, 2)})
    return {"target_2030_pct": target, "points": points, "basis": "projection is a straight line to the target, not a forecast"}


def composite(p: dict[str, Any], w: dict[str, float]) -> float:
    return round(p["E"] * w["E"] + p["S"] * w["S"] + p["G"] * w["G"], 1)


def benchmark(own_name: str = "Bank Nusantara Sejahtera", own_intensity: float | None = None, own_green_pct: float | None = None) -> dict[str, Any]:
    w = PEERS["weights"]
    own = {"id": "own", "name": own_name, "us": True, **PEERS["own"], "intensity": own_intensity, "green": own_green_pct}
    rows = [own] + PEERS["peers"]
    for r in rows:
        r["composite"] = composite(r, w)
    rows.sort(key=lambda r: -r["composite"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return {"weights": w, "rows": rows, "illustrative": True, "note": PEERS["_note"]}


def overview(params: dict[str, Any]) -> dict[str, Any]:
    year = common.year_param(params)

    def build() -> dict[str, Any]:
        rows = _book(year, Q)
        pc, tk = pcaf(year, rows=rows), tkbi(year, rows=rows)
        return {"pcaf": pc, "tkbi": tk, "green_trend": green_trend([2023, 2024], Q), "benchmark": benchmark(own_green_pct=tk["green_ratio_pct"])}

    return common.cached(f"portfolio_{year}", build, refresh=str(params.get("refresh", "")).lower() == "true")


# ── Scenario analysis / what-if ───────────────────────────────────────────────────────────────────
def scenario(params: dict[str, Any], q: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Run the three climate scenarios on the loan book. ``whatif`` may carry carbon_override, shift_pct,
    flood_share_pct and green_boost_pp. Stores a run record that the compliance probe reads."""
    year = common.year_param(params)
    whatif = params.get("whatif") or None
    rows = _book(year, q or Q)
    by_sector: dict[str, float] = {}
    for r in rows:
        by_sector[r["sector_nace"]] = by_sector.get(r["sector_nace"], 0.0) + float(r["outstanding"] or 0)
    sectors = se.sectors_from_pcaf([{"sector_nace": k, "total_outstanding_idr_trillion": v / TN} for k, v in by_sector.items()])
    total = sum(s["exposure_tn"] for s in sectors)
    tk = tkbi(year, rows=rows)
    ctx = {"green_ratio_pct": tk["green_ratio_pct"] or se.DEFAULTS["green_ratio_pct"]}
    result = se.run_all(sectors, total_loans_tn=total, whatif=whatif, params=ctx)
    result["narratives"] = {s["scenario_id"]: se.narrative(s) for s in result["scenarios"]}
    result.update({"year": year, "total_loans_tn": round(total, 3), "whatif": whatif or {}})
    if not whatif:  # only baseline runs count as evidence for IFRS S2 ¶22 / PSPK readiness
        try:
            common.s3_put(SCENARIO_RUN_KEY, {"ts": time.time(), "year": year, "total_loans_tn": result["total_loans_tn"]})
        except Exception:  # noqa: BLE001
            pass
    return result
