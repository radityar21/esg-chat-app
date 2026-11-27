"""Climate scenario engine (PSPK 2 / IFRS S2 ¶22 scenario analysis): 1.5°C, 2°C and 3°C+.

A deliberately simple, transparent model so every number can be traced and explained:

    transition ΔECL_s = exposure_s × min(1, sens_s × carbon/100) × pass_through
    physical   loss   = collateral × flood_share × hazard × haircut
    opportunity       = green_base × ((1+cagr)^years − 1) × NIM

It is a screening model. Replace the parameters with the bank's internal credit-risk models for production.
Pure Python, no AWS dependency.
"""

from __future__ import annotations

from typing import Any

try:
    from esg_domain import sector_profile
except ImportError:  # package import
    from ._shared.esg_domain import sector_profile  # type: ignore

SCENARIOS: list[dict[str, Any]] = [
    {"id": "s15", "name": "1.5°C · Net Zero 2050", "short": "1.5°C", "carbon": 130.0, "hazard": 1.0, "green_cagr": 18.0},
    {"id": "s2", "name": "2°C · Below 2°C", "short": "2°C", "carbon": 75.0, "hazard": 1.4, "green_cagr": 12.0},
    {"id": "s3", "name": "3°C+ · Current policies", "short": "3°C+", "carbon": 25.0, "hazard": 2.2, "green_cagr": 6.0},
]

DEFAULTS = {"flood_share_pct": 22.0, "haircut": 0.03, "nim": 0.028, "years": 5, "pass_through": 0.05, "green_ratio_pct": 12.0}


def sectors_from_pcaf(pcaf_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert pcaf_by_sector rows (display name + total_outstanding_idr_trillion) to scenario sectors."""
    out = []
    for r in pcaf_rows or []:
        label = r.get("sector_nace") or r.get("sector_display_name") or ""
        code, prof = sector_profile(str(label))
        exposure = float(r.get("total_outstanding_idr_trillion") or 0.0)
        out.append({"code": code, "name": prof["name"] if prof["name"] != "Other" else str(label), "exposure_tn": exposure,
                    "sens": prof["sens"], "high_emission": prof["high_emission"]})
    return out


def run_scenario(sectors: list[dict[str, Any]], scenario: dict[str, Any], *, total_loans_tn: float | None = None,
                 whatif: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = {**DEFAULTS, **(params or {})}
    w = whatif or {}
    carbon = float(w["carbon_override"]) if w.get("carbon_override") is not None else float(scenario["carbon"])
    shift = float(w.get("shift_pct", 0.0)) / 100.0
    flood = float(w.get("flood_share_pct", p["flood_share_pct"])) / 100.0
    boost = float(w.get("green_boost_pp", 0.0))

    total = total_loans_tn if total_loans_tn is not None else sum(s["exposure_tn"] for s in sectors)
    collateral = float(p.get("collateral_tn") or sum(s["exposure_tn"] for s in sectors if s["code"].startswith("real_estate")))
    green_base = float(p.get("green_base_tn") or total * p["green_ratio_pct"] / 100.0)

    by_sector = []
    for s in sectors:
        exposure = s["exposure_tn"] * ((1 - shift) if s["high_emission"] else 1.0)
        ebitda_hit = min(1.0, s["sens"] * carbon / 100.0)
        by_sector.append({"sector": s["name"], "code": s["code"], "exposure_tn": round(exposure, 3),
                          "ebitda_hit_pct": round(ebitda_hit * 100, 2), "delta_ecl_tn": round(exposure * ebitda_hit * p["pass_through"], 4)})
    transition = sum(x["delta_ecl_tn"] for x in by_sector)
    physical = collateral * flood * scenario["hazard"] * p["haircut"]
    cagr = (scenario["green_cagr"] + boost) / 100.0
    opportunity = green_base * ((1 + cagr) ** p["years"] - 1) * p["nim"]
    net = opportunity - transition - physical
    return {
        "scenario_id": scenario["id"], "scenario": scenario["name"], "carbon_price_usd_per_t": round(carbon, 1),
        "transition_delta_ecl_tn": round(transition, 3), "physical_loss_tn": round(physical, 3),
        "green_opportunity_tn": round(opportunity, 3), "net_impact_tn": round(net, 3),
        "downside_pct_of_loans": round((transition + physical) / total * 100, 3) if total else None,
        "by_sector": sorted(by_sector, key=lambda x: -x["delta_ecl_tn"]),
    }


def run_all(sectors: list[dict[str, Any]], *, total_loans_tn: float | None = None, whatif: dict[str, Any] | None = None,
            params: dict[str, Any] | None = None) -> dict[str, Any]:
    results = [run_scenario(sectors, sc, total_loans_tn=total_loans_tn, whatif=whatif, params=params) for sc in SCENARIOS]
    return {
        "method": "screening model: ΔECL = exposure × carbon-cost share of EBITDA × pass-through; physical = collateral × flood share × hazard × haircut",
        "horizon_years": (params or {}).get("years", DEFAULTS["years"]),
        "scenarios": results,
        "assumptions": {**DEFAULTS, **(params or {})},
    }


def narrative(result: dict[str, Any]) -> str:
    """Plain-language, number-faithful summary of one scenario result (no numbers beyond those in `result`)."""
    top = result["by_sector"][0] if result["by_sector"] else {"sector": "n/a", "delta_ecl_tn": 0}
    return (
        f"Under the {result['scenario']} scenario (carbon price USD {result['carbon_price_usd_per_t']:.0f}/tCO2e), "
        f"transition risk adds IDR {result['transition_delta_ecl_tn']:.2f} trillion of expected credit losses, "
        f"concentrated in {top['sector'].lower()} (IDR {top['delta_ecl_tn']:.2f} trillion). "
        f"Physical risk to property collateral adds IDR {result['physical_loss_tn']:.2f} trillion. "
        f"Green financing contributes IDR {result['green_opportunity_tn']:.2f} trillion of incremental net interest income. "
        f"The net effect is IDR {result['net_impact_tn']:.2f} trillion."
    )
