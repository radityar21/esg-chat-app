#!/usr/bin/env python3
# =============================================================================
# Synthetic Data Generator: esg_raw.hr_metrics
# =============================================================================
# Generates synthetic HR/social metrics per ESG_Kiro_Requirements_Spec §2.3
#
# Requirements:
#   - GRI 401, 405, 406 and CSRD/ESRS S1 disclosures
#   - FTE count feeds GHG intensity denominators in aggregated zone
#   - Year-end snapshot (YYYY-12-31)
#   - Output: Parquet files partitioned by reporting_year
#
# Output path: ../data/synthetic/hr_metrics/
# =============================================================================

import os
import random
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date

# Reproducibility
random.seed(789)
np.random.seed(789)

# =============================================================================
# CONFIGURATION
# =============================================================================

REPORTING_YEARS = [2023, 2024]

# FTE range: 500 - 50,000
FTE_RANGE = (500, 50000)

# Base FTE for our company (banking institution, ~25,000 employees)
BASE_FTE = 24500


def generate_hr_metrics() -> pd.DataFrame:
    """Generate HR metrics dataset with one row per reporting year."""
    records = []

    for year in REPORTING_YEARS:
        # FTE total (slight growth year over year)
        if year == 2023:
            fte_total = BASE_FTE
        else:
            # 2-5% growth
            fte_total = int(BASE_FTE * np.random.uniform(1.02, 1.05))

        fte_total = max(FTE_RANGE[0], min(fte_total, FTE_RANGE[1]))

        # Female percentage (Indonesian banking sector typically 45-55%)
        fte_female_pct = round(np.random.uniform(42.0, 55.0), 2)

        # Female in management (typically lower, 25-40%)
        fte_management_female_pct = round(np.random.uniform(25.0, 40.0), 2)

        # New hire count (typically 5-15% of headcount)
        new_hire_rate = np.random.uniform(0.05, 0.15)
        new_hire_count = int(fte_total * new_hire_rate)

        # Voluntary turnover (Indonesian banking: 8-18%)
        voluntary_turnover_pct = round(np.random.uniform(8.0, 18.0), 2)

        # Training hours per FTE (range 8-120, banking avg 30-60)
        training_hours_per_fte = round(np.random.uniform(30.0, 65.0), 2)

        # Discrimination cases (GRI 406, typically low for large banks, 0-5)
        discrimination_cases = int(np.random.choice(
            [0, 1, 2, 3, 4, 5],
            p=[0.30, 0.25, 0.20, 0.15, 0.07, 0.03]
        ))

        # Period date: year-end snapshot
        period_date = date(year, 12, 31)

        records.append({
            "period_date": period_date,
            "reporting_year": year,
            "fte_total": fte_total,
            "fte_female_pct": fte_female_pct,
            "fte_management_female_pct": fte_management_female_pct,
            "new_hire_count": new_hire_count,
            "voluntary_turnover_pct": voluntary_turnover_pct,
            "training_hours_per_fte": training_hours_per_fte,
            "discrimination_cases": discrimination_cases,
        })

    df = pd.DataFrame(records)

    # Enforce types
    # period_date stays as datetime.date (writes as DATE in parquet, not TIMESTAMP)
    df["reporting_year"] = df["reporting_year"].astype("int32")
    df["fte_total"] = df["fte_total"].astype("int32")
    df["new_hire_count"] = df["new_hire_count"].astype("int32")
    df["discrimination_cases"] = df["discrimination_cases"].astype("int32")
    df["fte_female_pct"] = df["fte_female_pct"].astype("float64")
    df["fte_management_female_pct"] = df["fte_management_female_pct"].astype("float64")
    df["voluntary_turnover_pct"] = df["voluntary_turnover_pct"].astype("float64")
    df["training_hours_per_fte"] = df["training_hours_per_fte"].astype("float64")

    return df


def validate_data(df: pd.DataFrame) -> None:
    """Run validation checks per spec constraints."""
    print("\n" + "=" * 60)
    print("  VALIDATION CHECKS")
    print("=" * 60)

    # Check FTE > 0
    assert (df["fte_total"] > 0).all(), "fte_total must be > 0"
    print("  ✅ fte_total > 0 for all rows")

    # Check percentages 0-100
    for col in ["fte_female_pct", "fte_management_female_pct", "voluntary_turnover_pct"]:
        assert ((df[col] >= 0) & (df[col] <= 100)).all(), f"{col} must be 0-100"
    print("  ✅ All percentage columns in [0, 100]")

    # Check training hours >= 0
    assert (df["training_hours_per_fte"] >= 0).all(), "training_hours must be >= 0"
    print("  ✅ training_hours_per_fte >= 0")

    # Check discrimination_cases >= 0
    assert (df["discrimination_cases"] >= 0).all(), "discrimination_cases must be >= 0"
    print("  ✅ discrimination_cases >= 0")

    # Check period_date is Dec 31
    for _, row in df.iterrows():
        d = row["period_date"]
        assert d.month == 12 and d.day == 31, f"period_date must be YYYY-12-31, got {d}"
    print("  ✅ period_date is YYYY-12-31 format")

    # Check new_hire_count >= 0
    assert (df["new_hire_count"] >= 0).all(), "new_hire_count must be >= 0"
    print("  ✅ new_hire_count >= 0")

    print("\n  ✅ All validation checks passed!")


def main():
    print("=" * 60)
    print("  ESG Synthetic Data Generator: hr_metrics")
    print("=" * 60)

    # Output directory
    output_dir = Path(__file__).parent.parent / "data" / "synthetic" / "hr_metrics"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate data
    print(f"\nGenerating HR metrics for {len(REPORTING_YEARS)} reporting years...")
    df = generate_hr_metrics()

    print(f"Total records: {len(df)}")
    print(f"\nData preview:")
    print(df.to_string(index=False))

    # Validate
    validate_data(df)

    # Save partitioned by reporting_year
    # Partition column NOT stored inside parquet (derived from path per REQ-DDL-05)
    for year in REPORTING_YEARS:
        year_df = df[df["reporting_year"] == year].drop(columns=["reporting_year"])
        year_dir = output_dir / f"reporting_year={year}"
        year_dir.mkdir(parents=True, exist_ok=True)

        output_path = year_dir / "hr_metrics.parquet"
        # Use PyArrow table directly to ensure period_date writes as DATE (not TIMESTAMP)
        import pyarrow as pa
        import pyarrow.parquet as pq
        table = pa.Table.from_pandas(year_df)
        # Cast period_date from timestamp to date32
        idx = table.schema.get_field_index("period_date")
        table = table.set_column(idx, "period_date", table.column("period_date").cast(pa.date32()))
        pq.write_table(table, output_path)
        print(f"\n✅ Written: {output_path} ({len(year_df)} rows, {output_path.stat().st_size / 1024:.1f} KB)")

    # Also save combined CSV
    csv_path = output_dir / "hr_metrics.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n📋 Full CSV: {csv_path}")

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for _, row in df.iterrows():
        print(f"\n  Year {row['reporting_year']}:")
        print(f"    FTE Total: {row['fte_total']:,}")
        print(f"    Female %: {row['fte_female_pct']:.1f}%")
        print(f"    Female Mgmt %: {row['fte_management_female_pct']:.1f}%")
        print(f"    New Hires: {row['new_hire_count']:,}")
        print(f"    Voluntary Turnover: {row['voluntary_turnover_pct']:.1f}%")
        print(f"    Training Hours/FTE: {row['training_hours_per_fte']:.1f}")
        print(f"    Discrimination Cases: {row['discrimination_cases']}")


if __name__ == "__main__":
    main()
