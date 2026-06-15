#!/usr/bin/env python3
"""
=============================================================================
Synthetic Data Generator: esg_raw.energy_consumption
=============================================================================
Spec Reference: §2.1, REQ-DDL-05

Output path pattern (per spec):
    data/synthetic/energy_consumption/reporting_year={YYYY}/reporting_month={M}/energy_consumption.parquet

Partition keys (NOT in parquet file, derived from path):
    - reporting_year (INT, 2023-2024)
    - reporting_month (INT, 1-12)

Data columns (IN parquet file):
    facility_id, electricity_kwh, natural_gas_gj, diesel_liters,
    srec_mwh_claimed, grid_ef_kgco2_kwh, ef_source, meter_reading_kwh,
    data_source, record_status

Requirements:
    - 220 facilities, 2 reporting years (2023, 2024), 12 months
    - Natural gas (GJ) + Diesel (litres) + Electricity (kWh)
    - Output: 24 parquet files (2 years × 12 months), ~220 rows each
=============================================================================
"""

import random
import numpy as np
import pandas as pd
from pathlib import Path

# Reproducibility
random.seed(42)
np.random.seed(42)

# =============================================================================
# CONFIGURATION
# =============================================================================

NUM_FACILITIES = 220
REPORTING_YEARS = [2023, 2024]
MONTHS = list(range(1, 13))

# Facility types and their characteristics
FACILITY_TYPES = {
    "branch":          {"count": 150, "elec_range": (1500, 25000), "gas_range": (0.0, 0.0), "diesel_range": (0.0, 0.0)},
    "regional_office": {"count": 30,  "elec_range": (15000, 55000), "gas_range": (5.0, 40.0), "diesel_range": (100.0, 1500.0)},
    "data_centre":     {"count": 15,  "elec_range": (50000, 85000), "gas_range": (0.0, 0.0), "diesel_range": (500.0, 3500.0)},
    "headquarters":    {"count": 5,   "elec_range": (60000, 85000), "gas_range": (50.0, 120.0), "diesel_range": (1000.0, 3500.0)},
    "warehouse":       {"count": 20,  "elec_range": (5000, 35000), "gas_range": (10.0, 60.0), "diesel_range": (200.0, 2000.0)},
}

# Allowed ENUM values (§2.1)
EF_SOURCES = ["PLN_Grid_Average_2023", "DEFRA_2025", "IPCC_AR6_CH4_GWP100"]
DATA_SOURCES = ["smart_meter_api", "manual_entry", "estimate"]
RECORD_STATUSES = ["complete", "missing_primary", "excluded"]

# Grid emission factor (PLN 2023)
GRID_EF = 0.7886  # kg CO2/kWh


def generate_facility_ids(num):
    """Generate facility IDs in format FAC-NNNN."""
    return [f"FAC-{i:04d}" for i in range(1, num + 1)]


def assign_facility_types(facility_ids):
    """Assign facility types to IDs based on configured counts."""
    assignments = {}
    idx = 0
    for ftype, config in FACILITY_TYPES.items():
        for _ in range(config["count"]):
            if idx < len(facility_ids):
                assignments[facility_ids[idx]] = ftype
                idx += 1
    while idx < len(facility_ids):
        assignments[facility_ids[idx]] = "branch"
        idx += 1
    return assignments


def generate_monthly_value(base_range, month, year):
    """Generate a monthly value with seasonal variation and noise."""
    base = np.random.uniform(base_range[0], base_range[1])
    if base == 0.0:
        return 0.0

    seasonal = 1.0 + 0.15 * np.sin((month - 1) * np.pi / 6)
    yoy_factor = 1.0 if year == 2023 else np.random.uniform(0.97, 1.05)
    value = base * seasonal * yoy_factor * np.random.uniform(0.92, 1.08)

    return max(0.0, round(value, 2))


def generate_energy_data():
    """Generate full energy consumption dataset."""
    facility_ids = generate_facility_ids(NUM_FACILITIES)
    facility_types = assign_facility_types(facility_ids)

    records = []

    for facility_id in facility_ids:
        ftype = facility_types[facility_id]
        config = FACILITY_TYPES[ftype]

        for year in REPORTING_YEARS:
            for month in MONTHS:
                # Electricity (always present)
                electricity_kwh = generate_monthly_value(config["elec_range"], month, year)

                # Natural gas (nullable for branches)
                if config["gas_range"] == (0.0, 0.0):
                    natural_gas_gj = None if random.random() < 0.95 else 0.0
                else:
                    natural_gas_gj = generate_monthly_value(config["gas_range"], month, year)

                # Diesel (nullable for branches)
                if config["diesel_range"] == (0.0, 0.0):
                    diesel_liters = None if random.random() < 0.95 else 0.0
                else:
                    diesel_liters = generate_monthly_value(config["diesel_range"], month, year)

                # SREC claimed
                if ftype in ["headquarters", "data_centre"] and random.random() < 0.6:
                    srec_mwh_claimed = round(electricity_kwh * np.random.uniform(0.05, 0.30) / 1000, 3)
                else:
                    srec_mwh_claimed = 0.0

                # EF source
                ef_source = np.random.choice(EF_SOURCES, p=[0.85, 0.10, 0.05])
                if ef_source == "PLN_Grid_Average_2023":
                    grid_ef_kgco2_kwh = 0.7886
                elif ef_source == "DEFRA_2025":
                    grid_ef_kgco2_kwh = 0.8012
                else:
                    grid_ef_kgco2_kwh = 0.7950

                # Meter reading (within 0.5% of electricity_kwh)
                if random.random() < 0.85:
                    tolerance = electricity_kwh * 0.005
                    meter_reading_kwh = round(
                        electricity_kwh + np.random.uniform(-tolerance, tolerance), 2
                    )
                else:
                    meter_reading_kwh = None

                # Data source
                if meter_reading_kwh is not None:
                    data_source = np.random.choice(["smart_meter_api", "manual_entry"], p=[0.7, 0.3])
                else:
                    data_source = np.random.choice(["manual_entry", "estimate"], p=[0.6, 0.4])

                # Record status
                if electricity_kwh is None or (natural_gas_gj is None and config["gas_range"] != (0.0, 0.0)):
                    record_status = "missing_primary"
                elif random.random() < 0.02:
                    record_status = "excluded"
                else:
                    record_status = "complete"

                # Rare null electricity
                if random.random() < 0.005:
                    electricity_kwh = None
                    record_status = "missing_primary"

                records.append({
                    "facility_id": facility_id,
                    "reporting_year": year,
                    "reporting_month": month,
                    "electricity_kwh": electricity_kwh,
                    "natural_gas_gj": natural_gas_gj,
                    "diesel_liters": diesel_liters,
                    "srec_mwh_claimed": srec_mwh_claimed,
                    "grid_ef_kgco2_kwh": grid_ef_kgco2_kwh,
                    "ef_source": ef_source,
                    "meter_reading_kwh": meter_reading_kwh,
                    "data_source": data_source,
                    "record_status": record_status,
                })

    df = pd.DataFrame(records)
    df["srec_mwh_claimed"] = df["srec_mwh_claimed"].astype("float64")
    df["grid_ef_kgco2_kwh"] = df["grid_ef_kgco2_kwh"].astype("float64")

    return df


def main():
    print("=" * 60)
    print("  ESG Synthetic Data Generator: energy_consumption")
    print("  Output: per-month parquet (spec REQ-DDL-05 compliant)")
    print("=" * 60)

    # Output directory
    output_dir = Path(__file__).parent.parent / "data" / "synthetic" / "energy_consumption"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate data
    print(f"\nGenerating {NUM_FACILITIES} facilities x {len(REPORTING_YEARS)} years x 12 months...")
    df = generate_energy_data()

    print(f"Total records: {len(df):,}")
    print(f"Record status:\n{df['record_status'].value_counts().to_string()}")

    # Save partitioned by reporting_year AND reporting_month
    # Partition columns are NOT stored inside parquet (derived from path)
    total_files = 0
    for year in REPORTING_YEARS:
        for month in MONTHS:
            partition_df = df[(df["reporting_year"] == year) & (df["reporting_month"] == month)]

            # Drop partition columns from file (they come from path)
            file_df = partition_df.drop(columns=["reporting_year", "reporting_month"])

            # Create Hive-style partition path
            part_dir = output_dir / f"reporting_year={year}" / f"reporting_month={month}"
            part_dir.mkdir(parents=True, exist_ok=True)

            output_path = part_dir / "energy_consumption.parquet"
            file_df.to_parquet(output_path, index=False, engine="pyarrow")
            total_files += 1

    print(f"\n✅ Written {total_files} parquet files")
    print(f"   Path: {output_dir}/reporting_year={{year}}/reporting_month={{month}}/")
    print(f"   Rows per file: ~{NUM_FACILITIES}")

    # Summary stats
    print(f"\n{'=' * 60}")
    print(f"  Facilities: {df['facility_id'].nunique()}")
    print(f"  Electricity (kWh) mean: {df['electricity_kwh'].mean():,.0f}")
    print(f"  Natural gas (GJ) mean: {df['natural_gas_gj'].mean():,.2f}")
    print(f"  Diesel (L) mean: {df['diesel_liters'].mean():,.2f}")
    print(f"  EF source: PLN={len(df[df['ef_source']=='PLN_Grid_Average_2023'])}, "
          f"DEFRA={len(df[df['ef_source']=='DEFRA_2025'])}, "
          f"IPCC={len(df[df['ef_source']=='IPCC_AR6_CH4_GWP100'])}")


if __name__ == "__main__":
    main()
