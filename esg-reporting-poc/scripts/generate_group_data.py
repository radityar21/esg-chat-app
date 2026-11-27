"""Synthetic group-level ESG source data: entities, facilities, emission factors, activity data and ESG metrics.

Writes five seed files next to the existing ones (data/seed/rds/<table>.csv.gz). They are loaded into the source
database by the esg-rds-seed Lambda ({"action": "init"} then {"action": "load", "reload": true}).

    python scripts/generate_group_data.py

Consistency with the existing data:
  * The parent bank's 220 facilities (FAC-0001..FAC-0220) and their monthly electricity, natural gas, diesel and
    certificate (REC) figures are taken from energy_consumption.csv.gz, so the ledger's bank Scope 1 and 2 can be
    reconciled with the reported inventory.
  * The bank's headcount equals hr_metrics.fte_total for the year.
Everything else is generated with a fixed seed, so re-running gives the same files.

Deliberate data problems (they show up as data alerts in the Data Hub):
  * GFI Asuransi has no water data for 2023, and GFI Sekuritas never reported refrigerant top-ups.
  * Every ninth GFI Syariah branch has no electricity data for October-December 2024 (meter migration).
  * One GFI Multifinance branch reports ten times its normal fleet fuel in July 2024 (entry error), and one
    GFI Syariah branch reports six times its normal electricity in May 2023 (meter fault).
  * Most GFI Multifinance waste figures are estimates.
  * Some ESG metrics are not collected for some entities (see MISSING_METRICS).
"""

from __future__ import annotations

import gzip
import io
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed" / "rds"
YEARS = (2023, 2024)
RNG = np.random.default_rng(20261127)

# ── organisation ──────────────────────────────────────────────────────────────────────────────────
# ownership_pct and operational_control per year. GFI Asuransi is a joint venture without operational control: it is
# excluded under the operational-control approach and included at 49 % under the equity-share approach.
ENTITIES = [
    # id, name, type, parent, {year: ownership}, control, facilities per type
    ("ENT-BANK", "Generic Financial Institution (parent bank)", "bank", "", {2023: 100.0, 2024: 100.0}, True, None),
    ("ENT-SYR", "GFI Syariah", "sharia_bank", "ENT-BANK", {2023: 99.9, 2024: 99.9}, True,
     {"headquarters": 1, "regional_office": 4, "branch": 55, "warehouse": 2}),
    ("ENT-MFN", "GFI Multifinance", "multifinance", "ENT-BANK", {2023: 70.0, 2024: 75.0}, True,
     {"headquarters": 1, "regional_office": 3, "branch": 38, "warehouse": 3}),
    ("ENT-SEK", "GFI Sekuritas", "securities", "ENT-BANK", {2023: 85.0, 2024: 85.0}, True,
     {"headquarters": 1, "branch": 11}),
    ("ENT-ASR", "GFI Asuransi (joint venture)", "insurance", "ENT-BANK", {2023: 49.0, 2024: 49.0}, False,
     {"headquarters": 1, "regional_office": 2, "branch": 15}),
]
PREFIX = {"ENT-BANK": "FAC", "ENT-SYR": "SYR", "ENT-MFN": "MFN", "ENT-SEK": "SEK", "ENT-ASR": "ASR"}
NEW_IN_2024 = {"ENT-SYR": 5, "ENT-MFN": 3}  # branches opened in 2024 (not in the 2023 facility list)

REGIONS = {  # grid system -> [(province, city)], share of facilities
    "java_bali": ([("DKI Jakarta", "Jakarta"), ("Jawa Barat", "Bandung"), ("Jawa Barat", "Bekasi"), ("Banten", "Tangerang"),
                   ("Jawa Tengah", "Semarang"), ("Jawa Timur", "Surabaya"), ("Jawa Timur", "Malang"), ("DI Yogyakarta", "Yogyakarta"),
                   ("Bali", "Denpasar")], 0.58),
    "sumatra": ([("Sumatera Utara", "Medan"), ("Sumatera Barat", "Padang"), ("Riau", "Pekanbaru"), ("Sumatera Selatan", "Palembang"),
                 ("Lampung", "Bandar Lampung"), ("Aceh", "Banda Aceh")], 0.20),
    "kalimantan": ([("Kalimantan Timur", "Balikpapan"), ("Kalimantan Selatan", "Banjarmasin"), ("Kalimantan Barat", "Pontianak")], 0.09),
    "sulawesi": ([("Sulawesi Selatan", "Makassar"), ("Sulawesi Utara", "Manado")], 0.08),
    "nusa_tenggara": ([("Nusa Tenggara Barat", "Mataram"), ("Nusa Tenggara Timur", "Kupang")], 0.03),
    "papua_maluku": ([("Papua", "Jayapura"), ("Maluku", "Ambon")], 0.02),
}
TYPE_SPEC = {  # floor area m2 range, headcount range, cars, share of sites with a diesel genset
    "headquarters": ((25000, 45000), (1800, 3500), 25, 1.0),
    "regional_office": ((2000, 5000), (120, 300), 6, 0.8),
    "data_centre": ((3000, 8000), (30, 80), 2, 1.0),
    "branch": ((400, 1200), (15, 40), 1, 0.3),
    "warehouse": ((1500, 4000), (5, 15), 2, 0.5),
}


def _pick_location(ftype: str) -> tuple[str, str, str]:
    if ftype in ("headquarters", "data_centre"):
        prov, city = [("DKI Jakarta", "Jakarta"), ("Banten", "Tangerang"), ("Jawa Barat", "Bekasi")][RNG.integers(0, 3)]
        return "java_bali", prov, city
    names = list(REGIONS)
    region = names[RNG.choice(len(names), p=[REGIONS[r][1] for r in names])]
    prov, city = REGIONS[region][0][RNG.integers(0, len(REGIONS[region][0]))]
    return region, prov, city


# ── facilities ────────────────────────────────────────────────────────────────────────────────────
def facilities(energy: pd.DataFrame, hr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    # bank: types from the electricity profile (largest consumers are data centres, then headquarters, ...)
    avg = energy.groupby("facility_id").electricity_kwh.mean().sort_values(ascending=False)
    order = list(avg.index)
    btypes = {}
    for i, fid in enumerate(order):
        btypes[fid] = ("data_centre" if i < 15 else "headquarters" if i < 20 else "regional_office" if i < 50
                       else "warehouse" if i >= len(order) - 20 else "branch")
    for fid in sorted(order):
        ftype = btypes[fid]
        region, prov, city = _pick_location(ftype)
        area_r, head_r, _, _ = TYPE_SPEC[ftype]
        rows.append({"facility_id": fid, "entity_id": "ENT-BANK", "facility_type": ftype, "grid_region": region, "province": prov,
                     "city": city, "floor_area_m2": float(RNG.integers(*area_r)), "headcount_raw": int(RNG.integers(*head_r)),
                     "ownership_type": "owned" if ftype in ("headquarters", "data_centre") or RNG.random() < 0.35 else "leased",
                     "opened_year": int(RNG.integers(1985, 2020)), "_new": False})
    for ent, _, _, _, _, _, mix in ENTITIES[1:]:
        n = 0
        for ftype, count in mix.items():
            for _ in range(count + (NEW_IN_2024.get(ent, 0) if ftype == "branch" else 0)):
                n += 1
                region, prov, city = _pick_location(ftype)
                area_r, head_r, _, _ = TYPE_SPEC[ftype]
                rows.append({"facility_id": f"{PREFIX[ent]}-F{n:03d}", "entity_id": ent, "facility_type": ftype, "grid_region": region,
                             "province": prov, "city": city, "floor_area_m2": float(int(RNG.integers(*area_r) * 0.8)),
                             "headcount_raw": int(RNG.integers(*head_r) * (0.6 if ftype == "headquarters" else 1)),
                             "ownership_type": "owned" if ftype == "headquarters" else "leased", "opened_year": int(RNG.integers(1995, 2022)),
                             "_new": False})
    base = pd.DataFrame(rows)
    # the last NEW_IN_2024 branches of each subsidiary opened in 2024
    for ent, k in NEW_IN_2024.items():
        idx = base[(base.entity_id == ent) & (base.facility_type == "branch")].index[-k:]
        base.loc[idx, "_new"] = True
        base.loc[idx, "opened_year"] = 2024
    out = []
    for y in YEARS:
        f = base[~base["_new"]].copy() if y == 2023 else base.copy()
        f["reporting_year"] = y
        f["headcount"] = f["headcount_raw"].astype(float)
        bank = f.entity_id == "ENT-BANK"
        fte = float(hr.loc[hr.reporting_year == y, "fte_total"].iloc[0])
        f.loc[bank, "headcount"] = (f.loc[bank, "headcount"] * fte / f.loc[bank, "headcount"].sum()).round()
        hq = f[bank].headcount.idxmax()  # rounding remainder goes to the largest site so the sum equals hr_metrics.fte_total
        f.loc[hq, "headcount"] += fte - f.loc[bank, "headcount"].sum()
        f.loc[~bank, "headcount"] = (f.loc[~bank, "headcount"] * (1.0 if y == 2023 else 1.04)).round()
        f["facility_name"] = f.apply(lambda r: f"{ENT_NAME[r.entity_id].split(' (')[0]} {r.city} {r.facility_type.replace('_', ' ')} {r.facility_id[-3:]}", axis=1)
        f["status"] = np.where(f["opened_year"] == y, "opened", "active")
        out.append(f)
    df = pd.concat(out, ignore_index=True)
    df["headcount"] = df["headcount"].astype(int)
    return df[["facility_id", "entity_id", "facility_name", "facility_type", "grid_region", "province", "city", "floor_area_m2",
               "headcount", "ownership_type", "opened_year", "status", "reporting_year"]]


ENT_NAME = {e[0]: e[1] for e in ENTITIES}


def entities() -> pd.DataFrame:
    rows = []
    for y in YEARS:
        for ent, name, etype, parent, own, control, _ in ENTITIES:
            rows.append({"entity_id": ent, "entity_name": name, "entity_type": etype, "parent_entity_id": parent or None,
                         "ownership_pct": own[y], "operational_control": control, "country": "ID",
                         "consolidation_note": ("Parent company" if not parent else "Subsidiary under operational control" if control
                                                else "Joint venture: equity share only, no operational control"),
                         "reporting_year": y})
    return pd.DataFrame(rows)


# ── emission factors ──────────────────────────────────────────────────────────────────────────────
# Illustrative factor sets for the synthetic dataset. Replace with the officially published values before any
# external use. ID_NATIONAL is the basis of the reported inventory (national grid average, as in energy_consumption);
# ID_REGIONAL uses a factor per electricity system. GWP100 values: IPCC AR6 (CH4 fossil 29.8, N2O 273).
GWP = {"gwp_ch4": 29.8, "gwp_n2o": 273.0, "gwp_basis": "IPCC AR6 GWP100"}
COMMON_FACTORS = [
    # activity_type, unit, scope, category, co2, ch4, n2o, co2e, source, note
    ("natural_gas", "GJ", 1, "s1_stationary", 56.10, 0.001, 0.0001, 0.0, "IPCC 2006 Vol.2 Ch.2 defaults", "Same factor as the reported inventory (Glue Scope 1 job)"),
    ("diesel_stationary", "litre", 1, "s1_stationary", 2.53763, 0.0000097, 0.000121, 0.0, "IPCC 2006 Vol.2 Ch.2 defaults (B30 blend adjusted)", "Same factor as the reported inventory (Glue Scope 1 job)"),
    ("gasoline_fleet", "litre", 1, "s1_mobile", 2.287, 0.000825, 0.000264, 0.0, "IPCC 2006 Vol.2 Ch.3 motor gasoline", "NCV 33.0 MJ/l"),
    ("diesel_fleet", "litre", 1, "s1_mobile", 2.675, 0.000141, 0.000141, 0.0, "IPCC 2006 Vol.2 Ch.3 diesel oil", "NCV 36.1 MJ/l"),
    ("refrigerant_r410a", "kg", 1, "s1_fugitive", 0.0, 0.0, 0.0, 2255.5, "IPCC AR6 GWP100 (50 % HFC-32, 50 % HFC-125)", "Leakage = top-up quantity"),
    ("refrigerant_r32", "kg", 1, "s1_fugitive", 0.0, 0.0, 0.0, 771.0, "IPCC AR6 GWP100 HFC-32", "Leakage = top-up quantity"),
    ("solar_pv", "kWh", 2, "s2_renewable", 0.0, 0.0, 0.0, 0.0, "On-site generation", "Self-generated renewable electricity has no Scope 2 emissions"),
    ("paper_a4", "ream", 3, "c1_purchased_goods", 0.0, 0.0, 0.0, 2.30, "DEFRA-based, approx. 0.92 kgCO2e/kg x 2.5 kg/ream", "Illustrative"),
    ("water_supply", "m3", 3, "c1_purchased_goods", 0.0, 0.0, 0.0, 0.177, "DEFRA-based water supply factor", "Illustrative"),
    ("waste_landfill", "kg", 3, "c5_waste", 0.0, 0.0, 0.0, 0.467, "DEFRA-based commercial waste to landfill", "Illustrative"),
    ("waste_recycled", "kg", 3, "c5_waste", 0.0, 0.0, 0.0, 0.021, "DEFRA-based closed-loop recycling", "Illustrative"),
    ("air_travel_domestic", "passenger-km", 3, "c6_business_travel", 0.0, 0.0, 0.0, 0.246, "DEFRA-based domestic flight with RF", "Illustrative"),
    ("air_travel_international", "passenger-km", 3, "c6_business_travel", 0.0, 0.0, 0.0, 0.151, "DEFRA-based short/long-haul economy with RF", "Illustrative"),
    ("hotel_night", "room-night", 3, "c6_business_travel", 0.0, 0.0, 0.0, 25.0, "Hotel footprinting benchmark, Indonesia (approx.)", "Illustrative"),
    ("commute_car", "km", 3, "c7_commuting", 0.0, 0.0, 0.0, 0.170, "DEFRA-based average petrol car", "Survey-based estimate"),
    ("commute_motorcycle", "km", 3, "c7_commuting", 0.0, 0.0, 0.0, 0.113, "DEFRA-based average motorbike", "Survey-based estimate"),
    ("commute_public", "km", 3, "c7_commuting", 0.0, 0.0, 0.0, 0.040, "DEFRA-based bus/rail average", "Survey-based estimate"),
]
GRID_NATIONAL = 0.7886  # kgCO2/kWh, as in energy_consumption.grid_ef_kgco2_kwh
GRID_REGIONAL = {"java_bali": 0.7250, "sumatra": 0.8020, "kalimantan": 0.8450, "sulawesi": 0.7900, "nusa_tenggara": 0.8100, "papua_maluku": 0.7600}


def emission_factors() -> pd.DataFrame:
    rows = []
    for y in YEARS:
        for ef_set in ("ID_NATIONAL", "ID_REGIONAL"):
            for a, unit, scope, cat, co2, ch4, n2o, co2e, src, note in COMMON_FACTORS:
                rows.append({"ef_set": ef_set, "activity_type": a, "region": "all", "unit": unit, "scope": scope, "category": cat,
                             "co2_kg": co2, "ch4_kg": ch4, "n2o_kg": n2o, "co2e_kg": co2e, **GWP, "source": src, "notes": note, "reporting_year": y})
            grid = {"all": GRID_NATIONAL} if ef_set == "ID_NATIONAL" else GRID_REGIONAL
            for region, v in grid.items():
                rows.append({"ef_set": ef_set, "activity_type": "electricity_grid", "region": region, "unit": "kWh", "scope": 2,
                             "category": "s2_electricity", "co2_kg": v, "ch4_kg": 0.0, "n2o_kg": 0.0, "co2e_kg": 0.0, **GWP,
                             "source": "PLN national grid average (reported basis)" if region == "all" else f"Grid factor, {region.replace('_', '-')} system",
                             "notes": "Used in the published inventory" if region == "all" else "Regional factor; align with the ESDM published grid factors",
                             "reporting_year": y})
    return pd.DataFrame(rows)


# ── activity data ─────────────────────────────────────────────────────────────────────────────────
def activity(energy: pd.DataFrame, fac: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    seq = {"n": 0}

    def add(y, m, f, a, q, unit, source, est=False, inst=None, ev=None):
        seq["n"] += 1
        rows.append({"activity_id": f"ACT-{y}-{seq['n']:07d}", "facility_id": f.facility_id, "entity_id": f.entity_id, "activity_type": a,
                     "quantity": round(float(q), 3), "unit": unit, "instrument_qty": None if inst is None else round(float(inst), 3),
                     "data_source": source, "is_estimated": bool(est), "evidence_ref": ev, "reporting_year": y, "reporting_month": m})

    en = energy.set_index(["reporting_year", "facility_id", "reporting_month"])
    bank_types = fac[fac.entity_id == "ENT-BANK"].drop_duplicates("facility_id").set_index("facility_id")
    # electricity intensity (kWh per m2 per month) by facility type, from the bank's own data
    e = energy.merge(bank_types[["facility_type", "floor_area_m2"]], left_on="facility_id", right_index=True)
    kwh_m2 = (e.electricity_kwh / e.floor_area_m2).groupby(e.facility_type).median().to_dict()
    solar_sites = set(bank_types[bank_types.facility_type == "headquarters"].index) | set(bank_types[bank_types.facility_type == "branch"].index[:10])

    for y in YEARS:
        fy = fac[fac.reporting_year == y]
        for f in fy.itertuples():
            ftype = f.facility_type
            _, _, cars, genset = TYPE_SPEC[ftype]
            sub = f.entity_id != "ENT-BANK"
            frng = np.random.default_rng(zlib.crc32(f"{f.facility_id}|{y}".encode()))
            has_genset = (not sub) or frng.random() < genset
            months = range(1, 13)
            for m in months:
                ev = f"{f.facility_id}-{y}{m:02d}"
                # electricity, natural gas, stationary diesel
                if not sub:
                    try:
                        r = en.loc[(y, f.facility_id, m)]
                    except KeyError:
                        r = None
                    if r is not None and r.record_status != "excluded":
                        kwh, est, src = r.electricity_kwh, False, "smart_meter" if r.data_source == "smart_meter_api" else r.data_source
                        if pd.isna(kwh) and not pd.isna(r.meter_reading_kwh):
                            kwh, est, src = r.meter_reading_kwh, True, "estimate"
                        if not pd.isna(kwh):
                            add(y, m, f, "electricity_grid", kwh, "kWh", "estimate" if r.data_source == "estimate" else src,
                                est or r.data_source == "estimate", inst=(r.srec_mwh_claimed or 0) * 1000, ev=f"PLN-{ev}")
                        if not pd.isna(r.natural_gas_gj):
                            add(y, m, f, "natural_gas", r.natural_gas_gj, "GJ", "invoice", ev=f"PGN-{ev}")
                        if not pd.isna(r.diesel_liters):
                            add(y, m, f, "diesel_stationary", r.diesel_liters, "litre", "fuel_log", ev=f"GEN-{ev}")
                else:
                    gap = f.entity_id == "ENT-SYR" and y == 2024 and m >= 10 and f.facility_type == "branch" and int(f.facility_id[-3:]) % 9 == 0
                    if not gap:
                        kwh = kwh_m2[ftype] * f.floor_area_m2 * frng.normal(1, 0.08) * (1 + 0.06 * np.sin((m - 3) / 12 * 2 * np.pi))
                        if f.entity_id == "ENT-SYR" and y == 2023 and m == 5 and f.facility_id.endswith("F017"):
                            kwh *= 6  # meter fault
                        rec = kwh * 0.3 if (f.entity_id == "ENT-SYR" and ftype == "headquarters" and y == 2024) else 0.0
                        add(y, m, f, "electricity_grid", kwh, "kWh", "invoice", inst=rec, ev=f"PLN-{ev}")
                    if ftype == "headquarters":
                        add(y, m, f, "natural_gas", frng.uniform(20, 60), "GJ", "invoice", ev=f"PGN-{ev}")
                    if has_genset:
                        add(y, m, f, "diesel_stationary", frng.uniform(40, 220) * (4 if ftype != "branch" else 1), "litre", "fuel_log", ev=f"GEN-{ev}")
                # rooftop solar on bank sites from 2024
                if not sub and y == 2024 and f.facility_id in solar_sites:
                    add(y, m, f, "solar_pv", f.floor_area_m2 * (0.9 if ftype == "headquarters" else 1.6) * frng.normal(1, 0.1), "kWh", "inverter_log", ev=f"PV-{ev}")
                # fleet
                if f.entity_id == "ENT-MFN" and ftype == "branch":  # collection motorcycles and cars
                    litres = frng.uniform(900, 1400)
                    if y == 2024 and m == 7 and f.facility_id.endswith("F011"):
                        litres *= 10  # entry error
                    add(y, m, f, "gasoline_fleet", litres, "litre", "fuel_card", ev=f"FC-{ev}")
                elif cars:
                    add(y, m, f, "gasoline_fleet", cars * frng.uniform(90, 140) * (0.93 if y == 2024 else 1), "litre", "fuel_card", ev=f"FC-{ev}")
                    if ftype in ("headquarters", "regional_office"):
                        add(y, m, f, "diesel_fleet", cars * frng.uniform(25, 45), "litre", "fuel_card", ev=f"FC-{ev}")
                # water, waste, paper (per person)
                hc = max(f.headcount, 3)
                if not (f.entity_id == "ENT-ASR" and y == 2023):
                    add(y, m, f, "water_supply", hc * frng.uniform(1.2, 1.8) * (6 if ftype == "data_centre" else 1), "m3", "invoice", ev=f"PDAM-{ev}")
                waste = hc * frng.uniform(6, 10)
                rec_share = (0.15 if y == 2023 else 0.22) + (0.1 if not sub else 0)
                waste_est = f.entity_id == "ENT-MFN" and (y == 2023 or frng.random() < 0.6)
                add(y, m, f, "waste_landfill", waste * (1 - rec_share), "kg", "estimate" if waste_est else "hauler_manifest", waste_est, ev=f"WST-{ev}")
                add(y, m, f, "waste_recycled", waste * rec_share, "kg", "estimate" if waste_est else "hauler_manifest", waste_est, ev=f"WST-{ev}")
                add(y, m, f, "paper_a4", hc * frng.uniform(0.4, 0.7) * (0.85 if y == 2024 else 1), "ream", "procurement", ev=f"PO-{ev}")
            # refrigerant top-ups once a year (not collected by GFI Sekuritas)
            if f.entity_id != "ENT-SEK":
                ac_kg = f.floor_area_m2 / 35 * 1.2
                add(y, 12, f, "refrigerant_r410a", ac_kg * frng.uniform(0.04, 0.08), "kg", "maintenance_log", ev=f"HVAC-{f.facility_id}-{y}")
                if y == 2024 and ftype in ("branch", "regional_office") and frng.random() < 0.3:
                    add(y, 12, f, "refrigerant_r32", ac_kg * 0.2 * frng.uniform(0.03, 0.06), "kg", "maintenance_log", ev=f"HVAC-{f.facility_id}-{y}")
        # entity-level travel (booked on the headquarters) and commuting (annual survey)
        for ent, *_ in ENTITIES:
            hq = fy[(fy.entity_id == ent) & (fy.facility_type == "headquarters")].iloc[0]
            heads = fy[fy.entity_id == ent].headcount.sum()
            for m in range(1, 13):
                k = heads / 1000
                add(y, m, hq, "air_travel_domestic", k * RNG.uniform(70000, 95000), "passenger-km", "travel_agency", ev=f"TRV-{ent}-{y}{m:02d}")
                add(y, m, hq, "air_travel_international", k * RNG.uniform(15000, 30000), "passenger-km", "travel_agency", ev=f"TRV-{ent}-{y}{m:02d}")
                add(y, m, hq, "hotel_night", k * RNG.uniform(120, 180), "room-night", "travel_agency", ev=f"TRV-{ent}-{y}{m:02d}")
            km = heads * 230 * 2 * 14  # 230 working days, return trip, 14 km one way
            for a, share in (("commute_car", 0.32), ("commute_motorcycle", 0.48), ("commute_public", 0.20)):
                add(y, 12, hq, a, km * share * RNG.uniform(0.95, 1.05), "km", "employee_survey", True, ev=f"SURVEY-{ent}-{y}")
    df = pd.DataFrame(rows)
    df["instrument_qty"] = df["instrument_qty"].astype(float)
    return df[["activity_id", "facility_id", "entity_id", "activity_type", "quantity", "unit", "instrument_qty", "data_source",
               "is_estimated", "evidence_ref", "reporting_year", "reporting_month"]]


# ── ESG metrics (social, governance, sustainable finance, subsidiaries' financed emissions) ───────
MISSING_METRICS = {  # (entity, year) -> metrics deliberately not collected
    ("ENT-SEK", 2023): {"remuneration_ratio_female_male"}, ("ENT-SEK", 2024): {"remuneration_ratio_female_male"},
    ("ENT-ASR", 2023): {"community_investment_idr"}, ("ENT-MFN", 2023): {"employees_with_disability"},
    ("ENT-MFN", 2024): {"employees_with_disability"},
}
KUBL = ["renewable_energy", "energy_efficiency", "green_building", "clean_transportation", "sustainable_agriculture",
        "pollution_prevention", "water_waste_management", "msme"]


def metrics(fac: pd.DataFrame, hr: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add(y, ent, pillar, topic, metric, value, unit, ref, dim="total", source="hris"):
        if metric in MISSING_METRICS.get((ent, y), set()):
            return
        rows.append({"entity_id": ent, "pillar": pillar, "topic": topic, "metric": metric, "dimension": dim, "value": round(float(value), 4),
                     "unit": unit, "data_source": source, "standard_ref": ref, "reporting_year": y})

    for y in YEARS:
        h = hr[hr.reporting_year == y].iloc[0]
        for ent, name, etype, *_ in ENTITIES:
            heads = int(fac[(fac.reporting_year == y) & (fac.entity_id == ent)].headcount.sum())
            g = 1.0 if y == 2023 else 1.04
            bank = ent == "ENT-BANK"
            fem = float(h.fte_female_pct) if bank else RNG.uniform(38, 55)
            add(y, ent, "social", "workforce", "headcount", heads, "people", "GRI 2-7")
            add(y, ent, "social", "workforce", "headcount", round(heads * fem / 100), "people", "GRI 2-7", "female")
            add(y, ent, "social", "workforce", "headcount", heads - round(heads * fem / 100), "people", "GRI 2-7", "male")
            add(y, ent, "social", "diversity", "female_pct", fem, "%", "GRI 405-1")
            add(y, ent, "social", "diversity", "female_management_pct", float(h.fte_management_female_pct) if bank else RNG.uniform(22, 38), "%", "GRI 405-1")
            add(y, ent, "social", "diversity", "employees_with_disability", max(1, round(heads * RNG.uniform(0.002, 0.006))), "people", "POJK 51/2017 social")
            add(y, ent, "social", "diversity", "remuneration_ratio_female_male", RNG.uniform(0.86, 0.97), "ratio", "GRI 405-2")
            add(y, ent, "social", "workforce", "new_hires", float(h.new_hire_count) if bank else round(heads * RNG.uniform(0.08, 0.16)), "people", "GRI 401-1")
            add(y, ent, "social", "workforce", "turnover_voluntary_pct", float(h.voluntary_turnover_pct) if bank else RNG.uniform(7, 18), "%", "GRI 401-1")
            tph = float(h.training_hours_per_fte) if bank else RNG.uniform(28, 60)
            add(y, ent, "social", "training", "training_hours_per_fte", tph, "hours", "GRI 404-1")
            add(y, ent, "social", "training", "training_hours_total", tph * heads, "hours", "GRI 404-1")
            add(y, ent, "social", "health_safety", "lost_time_injuries", int(RNG.integers(0, 6)) if etype != "multifinance" else int(RNG.integers(6, 15)), "cases", "GRI 403-9", source="hse_log")
            add(y, ent, "social", "health_safety", "fatalities", 1 if (ent == "ENT-MFN" and y == 2023) else 0, "cases", "GRI 403-9", source="hse_log")
            add(y, ent, "social", "community", "community_investment_idr", heads * RNG.uniform(0.6, 1.4) * 1e6 * g, "IDR", "GRI 203-1 / POJK 51", source="csr_ledger")
            add(y, ent, "social", "community", "financial_literacy_participants", heads * RNG.uniform(2, 6) * g, "people", "POJK 51/2017 social", source="csr_ledger")
            add(y, ent, "social", "customers", "customer_complaints", heads * RNG.uniform(0.3, 1.2), "cases", "POJK 51/2017 social", source="crm")
            add(y, ent, "social", "customers", "complaints_resolved_pct", RNG.uniform(91, 99.5), "%", "POJK 51/2017 social", source="crm")
            # governance
            board = 9 if bank else int(RNG.integers(5, 8))
            add(y, ent, "governance", "board", "board_members", board, "people", "GRI 2-9", source="corporate_secretary")
            add(y, ent, "governance", "board", "independent_commissioner_pct", RNG.uniform(50, 67), "%", "GRI 2-9 / POJK 55/2016", source="corporate_secretary")
            add(y, ent, "governance", "board", "female_board_pct", RNG.uniform(10, 34), "%", "GRI 405-1", source="corporate_secretary")
            add(y, ent, "governance", "ethics", "anti_corruption_training_pct", RNG.uniform(86, 99) if y == 2024 else RNG.uniform(78, 95), "%", "GRI 205-2", source="compliance")
            add(y, ent, "governance", "ethics", "confirmed_corruption_cases", int(RNG.integers(0, 2)), "cases", "GRI 205-3", source="compliance")
            add(y, ent, "governance", "ethics", "whistleblowing_reports", int(RNG.integers(3, 30)), "reports", "POJK 51/2017 governance", source="compliance")
            add(y, ent, "governance", "compliance", "regulatory_fines_idr", float(RNG.choice([0, 0, 0, 25e6, 150e6])), "IDR", "GRI 2-27", source="legal")
            add(y, ent, "governance", "privacy", "data_breaches", int(RNG.integers(0, 3)), "incidents", "GRI 418-1", source="ciso")
            add(y, ent, "governance", "oversight", "esg_committee", 1 if (bank or y == 2024) else 0, "yes/no", "IFRS S2 para 6", source="corporate_secretary")
            # sustainable finance (POJK 51 KUBL / TKBI categories) for lending entities
            book = {"bank": 1_750e12, "sharia_bank": 260e12, "multifinance": 64e12}.get(etype)
            if book:
                book *= (1.0 if y == 2023 else 1.07)
                add(y, ent, "finance", "loan_book", "loan_book_idr", book, "IDR", "POJK 51/2017", source="core_banking")
                shares = {"bank": [0.012, 0.009, 0.014, 0.006, 0.020, 0.004, 0.003, 0.150], "sharia_bank": [0.004, 0.003, 0.018, 0.002, 0.030, 0.001, 0.002, 0.210],
                          "multifinance": [0.0, 0.0, 0.0, 0.035, 0.010, 0.0, 0.0, 0.080]}[etype]
                for cat, s in zip(KUBL, shares):
                    if s:
                        add(y, ent, "finance", "sustainable_finance", "sustainable_finance_idr", book * s * RNG.uniform(0.9, 1.1) * (1.0 if y == 2023 else 1.18),
                            "IDR", "POJK 51/2017 KUBL / TKBI", cat, "core_banking")
            # financed emissions of the subsidiaries (the bank's own book is in loan_portfolio)
            if etype in ("sharia_bank", "multifinance"):
                sectors = ({"real_estate_residential": (0.42, 1.2, 4.0), "retail_trade": (0.18, 3.0, 4.0), "agriculture": (0.12, 22.0, 4.0),
                            "manufacturing_food": (0.10, 9.0, 3.0), "transportation_road": (0.08, 14.0, 3.0)} if etype == "sharia_bank" else
                           {"transportation_road": (0.86, 16.0, 4.0), "retail_trade": (0.09, 3.0, 5.0)})
                for sec, (share, tco2_per_bn, score) in sectors.items():
                    out_idr = book * share
                    add(y, ent, "finance", "financed_emissions", "outstanding_idr", out_idr, "IDR", "PCAF Part A", sec, "pcaf_engine")
                    add(y, ent, "finance", "financed_emissions", "financed_tco2e", out_idr / 1e9 * tco2_per_bn * RNG.uniform(0.92, 1.05) * (1 if y == 2023 else 0.97),
                        "tCO2e", "PCAF Part A / GHG Protocol Scope 3 cat. 15", sec, "pcaf_engine")
                    add(y, ent, "finance", "financed_emissions", "pcaf_score", score, "score", "PCAF Part A", sec, "pcaf_engine")
    return pd.DataFrame(rows)


def write(name: str, df: pd.DataFrame) -> None:
    buf = io.StringIO()
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == bool:
            out[c] = out[c].map({True: "true", False: "false"})
    out.to_csv(buf, index=False)
    (SEED / f"{name}.csv.gz").write_bytes(gzip.compress(buf.getvalue().encode(), mtime=0))
    print(f"{name:22s} {len(df):>7,d} rows")


def main() -> None:
    energy = pd.read_csv(SEED / "energy_consumption.csv.gz")
    hr = pd.read_csv(SEED / "hr_metrics.csv.gz")
    fac = facilities(energy, hr)
    write("entity", entities())
    write("facility", fac)
    write("emission_factor", emission_factors())
    write("activity_data", activity(energy, fac))
    write("esg_metric", metrics(fac, hr))


if __name__ == "__main__":
    main()
