#!/usr/bin/env python3
# =============================================================================
# Synthetic Data Generator: esg_raw.scope3_operational_activity
# =============================================================================
# Operational Scope 3 (GHG Protocol categories 1-7) activity data for a bank. Category 15 (financed
# emissions) already comes from the loan book via the PCAF Glue job; categories 8-14 are not relevant to a bank.
#
# One row per (category, activity). Emissions = quantity x emission factor / 1000 (tCO2e). Factors are
# spend-based (EEIO) or activity-based averages. Everything is SYNTHETIC and for demonstration only.
#
# Output: ../data/synthetic/scope3_operational/reporting_year=YYYY/scope3_operational_activity.parquet (+ CSV sample)
# Upload: s3://esg-data-raw-<account>/raw/scope3_operational_activity/reporting_year=YYYY/
# =============================================================================

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(2026)
np.random.seed(2026)

OUT = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "scope3_operational"

# category, activity, unit, 2024 quantity, kg CO2e per unit, method, source, PCAF-style data quality 1-5
ACTIVITIES = [
    ("c1", "Purchased services and supplies", "IDR million", 6_250_000, 2.40, "spend-based", "EEIO_ID_2022", 4),
    ("c2", "Capital goods (IT hardware, fit-out)", "IDR million", 2_600_000, 1.90, "spend-based", "EEIO_ID_2022", 4),
    ("c3", "Upstream energy (WTT, T&D losses)", "MWh", 41_000, 85.0, "average-data", "DEFRA_2025", 3),
    ("c4", "Upstream transport of goods", "tonne-km", 4_800_000, 0.12, "distance-based", "DEFRA_2025", 3),
    ("c5", "Waste generated in operations", "tonne", 1_850, 220.0, "waste-type-specific", "DEFRA_2025", 3),
    ("c6", "Business travel: air", "passenger-km", 14_000_000, 0.15, "distance-based", "DEFRA_2025", 2),
    ("c6", "Business travel: hotel nights", "room-night", 38_000, 24.0, "average-data", "DEFRA_2025", 3),
    ("c7", "Employee commuting", "commute-day", 5_500_000, 1.50, "average-data", "HR survey + DEFRA_2025", 3),
]

YEAR_SCALE = {2023: 1.06, 2024: 1.00}


def generate() -> pd.DataFrame:
    rows = []
    for year, scale in YEAR_SCALE.items():
        for cat, act, unit, qty, ef, method, src, dq in ACTIVITIES:
            q = qty * scale * np.random.uniform(0.97, 1.03)
            rows.append({
                "category": cat, "activity": act, "unit": unit, "quantity": round(float(q), 2),
                "ef_kgco2e_per_unit": ef, "emissions_tco2e": round(float(q * ef / 1000), 4),
                "method": method, "ef_source": src, "data_quality_score": dq, "reporting_year": year,
            })
    return pd.DataFrame(rows)


def main() -> None:
    df = generate()
    for year, part in df.groupby("reporting_year"):
        d = OUT / f"reporting_year={year}"
        d.mkdir(parents=True, exist_ok=True)
        part.drop(columns=["reporting_year"]).to_parquet(d / "scope3_operational_activity.parquet", index=False)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "scope3_operational_activity_sample.csv", index=False)
    print(df.groupby(["reporting_year", "category"]).emissions_tco2e.sum().round(1).unstack(0))
    print("Total by year:", df.groupby("reporting_year").emissions_tco2e.sum().round(1).to_dict())


if __name__ == "__main__":
    main()
