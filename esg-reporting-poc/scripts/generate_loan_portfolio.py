#!/usr/bin/env python3
# =============================================================================
# Synthetic Data Generator: esg_raw.loan_portfolio
# =============================================================================
# Generates synthetic loan portfolio data per ESG_Kiro_Requirements_Spec §2.2
#
# Requirements:
#   - 2,000+ borrowers
#   - PCAF scores distribution: {1.0:3.5%, 1.5:1.5%, 2.0:15%, 3.0:30%, 4.0:35%, 5.0:15%}
#   - 10 sector NACE codes
#   - Outstanding amounts, borrower emissions
#   - Output: Parquet files partitioned by reporting_year
#
# Output path: ../data/synthetic/loan_portfolio/
# =============================================================================

import os
import random
import numpy as np
import pandas as pd
from pathlib import Path

# Reproducibility
random.seed(123)
np.random.seed(123)

# =============================================================================
# CONFIGURATION
# =============================================================================

NUM_BORROWERS = 2200
REPORTING_YEARS = [2023, 2024]

# PCAF data quality score distribution (from spec §2.2)
PCAF_SCORES = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
PCAF_DISTRIBUTION = [0.035, 0.015, 0.15, 0.30, 0.35, 0.15]

# Sector NACE codes (10 values as per spec)
SECTOR_NACE = [
    "manufacturing_cement",
    "manufacturing_steel",
    "manufacturing_food",
    "real_estate_commercial",
    "real_estate_residential",
    "transportation_road",
    "agriculture",
    "energy_oil_gas",
    "financial_services",
    "retail_trade",
]

# Sector weights (some sectors more common in banking portfolio)
SECTOR_WEIGHTS = [0.08, 0.06, 0.10, 0.15, 0.12, 0.10, 0.08, 0.07, 0.12, 0.12]

# Loan types
LOAN_TYPES = ["term_loan", "revolving_credit", "mortgage", "project_finance", "syndicated_loan", "leasing"]
LOAN_TYPE_WEIGHTS = [0.30, 0.20, 0.15, 0.10, 0.15, 0.10]

# Currency
CURRENCIES = ["IDR", "USD"]
CURRENCY_WEIGHTS = [0.80, 0.20]
USD_TO_IDR = 15750  # Reference rate

# Outstanding range (IDR): 500M - 2T
OUTSTANDING_MIN = 500_000_000          # IDR 500M
OUTSTANDING_MAX = 2_000_000_000_000    # IDR 2T

# Equity range (IDR): 1B - 50T
EQUITY_MIN = 1_000_000_000            # IDR 1B
EQUITY_MAX = 50_000_000_000_000       # IDR 50T

# Debt range (IDR): 0 - 50T
DEBT_MIN = 0
DEBT_MAX = 50_000_000_000_000         # IDR 50T

# Borrower emissions range: 500 - 5,000,000 tCO2e/year
EMISSIONS_MIN = 500
EMISSIONS_MAX = 5_000_000

# Sector-specific emission ranges (tCO2e/year)
SECTOR_EMISSION_RANGES = {
    "manufacturing_cement": (50000, 5000000),
    "manufacturing_steel": (30000, 3000000),
    "manufacturing_food": (5000, 500000),
    "real_estate_commercial": (1000, 100000),
    "real_estate_residential": (500, 50000),
    "transportation_road": (5000, 800000),
    "agriculture": (2000, 300000),
    "energy_oil_gas": (100000, 5000000),
    "financial_services": (500, 30000),
    "retail_trade": (1000, 80000),
}

RECORD_STATUSES = ["validated", "pending", "rejected"]
RECORD_STATUS_WEIGHTS = [0.88, 0.08, 0.04]


def generate_borrower_ids(num: int) -> list[str]:
    """Generate borrower IDs in format BOR-NNNNNN."""
    return [f"BOR-{i:06d}" for i in range(1, num + 1)]


def generate_loan_id(year: int, counter: int) -> str:
    """Generate loan ID in format LN-YYYY-NNNNNNN."""
    return f"LN-{year}-{counter:07d}"


def generate_outstanding(equity: int, debt: int) -> int:
    """Generate outstanding amount that doesn't exceed enterprise value (equity + debt)."""
    ev = equity + debt
    max_outstanding = min(OUTSTANDING_MAX, ev)
    min_outstanding = min(OUTSTANDING_MIN, max_outstanding)

    # Use log-normal distribution for more realistic spread
    outstanding = int(np.random.lognormal(mean=np.log(500_000_000_000), sigma=1.5))
    outstanding = max(min_outstanding, min(outstanding, max_outstanding))

    # Round to nearest million
    return int(round(outstanding / 1_000_000) * 1_000_000)


def generate_loan_portfolio() -> pd.DataFrame:
    """Generate full loan portfolio dataset."""
    borrower_ids = generate_borrower_ids(NUM_BORROWERS)

    records = []
    loan_counter = {2023: 0, 2024: 0}

    for borrower_id in borrower_ids:
        # Assign sector (consistent across years for same borrower)
        sector = np.random.choice(SECTOR_NACE, p=SECTOR_WEIGHTS)

        # Generate base financials for this borrower
        base_equity = int(np.random.lognormal(mean=np.log(10_000_000_000_000), sigma=1.2))
        base_equity = max(EQUITY_MIN, min(base_equity, EQUITY_MAX))

        base_debt = int(np.random.lognormal(mean=np.log(5_000_000_000_000), sigma=1.3))
        base_debt = max(DEBT_MIN, min(base_debt, DEBT_MAX))

        # Ensure equity + debt > 0 (always true since equity > 0)

        # PCAF score (consistent for borrower, may improve slightly in 2024)
        pcaf_score = np.random.choice(PCAF_SCORES, p=PCAF_DISTRIBUTION)

        # Base emissions for this borrower based on sector
        emission_range = SECTOR_EMISSION_RANGES[sector]
        base_emissions = np.random.lognormal(
            mean=np.log(np.sqrt(emission_range[0] * emission_range[1])),
            sigma=0.8
        )
        base_emissions = max(emission_range[0], min(base_emissions, emission_range[1]))

        # Loan type
        loan_type = np.random.choice(LOAN_TYPES, p=LOAN_TYPE_WEIGHTS)

        # Currency
        currency = np.random.choice(CURRENCIES, p=CURRENCY_WEIGHTS)

        for year in REPORTING_YEARS:
            loan_counter[year] += 1
            loan_id = generate_loan_id(year, loan_counter[year])

            # Year-over-year adjustments
            yoy_equity = np.random.uniform(0.95, 1.10)
            yoy_debt = np.random.uniform(0.90, 1.15)
            yoy_emissions = np.random.uniform(0.92, 1.05)  # Slight reduction trend

            total_equity_idr = int(round(base_equity * (yoy_equity if year == 2024 else 1.0) / 1_000_000) * 1_000_000)
            total_equity_idr = max(EQUITY_MIN, min(total_equity_idr, EQUITY_MAX))

            total_debt_idr = int(round(base_debt * (yoy_debt if year == 2024 else 1.0) / 1_000_000) * 1_000_000)
            total_debt_idr = max(DEBT_MIN, min(total_debt_idr, DEBT_MAX))

            # Generate outstanding (must not exceed EV)
            outstanding_idr = generate_outstanding(total_equity_idr, total_debt_idr)

            # Attribution factor: outstanding / (equity + debt)
            ev = total_equity_idr + total_debt_idr
            pcaf_attribution_factor = round(outstanding_idr / ev, 6)

            # Ensure attribution factor is 0 < x <= 1
            pcaf_attribution_factor = max(0.000001, min(pcaf_attribution_factor, 1.0))

            # Borrower emissions
            borrower_emissions_tco2e = round(
                base_emissions * (yoy_emissions if year == 2024 else 1.0), 2
            )
            borrower_emissions_tco2e = max(EMISSIONS_MIN, min(borrower_emissions_tco2e, EMISSIONS_MAX))

            # PCAF score may improve slightly in 2024
            year_pcaf = pcaf_score
            if year == 2024 and random.random() < 0.08:
                # 8% chance of score improvement
                score_idx = PCAF_SCORES.index(pcaf_score)
                if score_idx > 0:
                    year_pcaf = PCAF_SCORES[score_idx - 1]

            # Record status
            record_status = np.random.choice(RECORD_STATUSES, p=RECORD_STATUS_WEIGHTS)

            records.append({
                "loan_id": loan_id,
                "borrower_id": borrower_id,
                "sector_nace": sector,
                "loan_type": loan_type,
                "currency": currency,
                "outstanding_idr": outstanding_idr,
                "total_equity_idr": total_equity_idr,
                "total_debt_idr": total_debt_idr,
                "pcaf_attribution_factor": pcaf_attribution_factor,
                "borrower_emissions_tco2e": borrower_emissions_tco2e,
                "pcaf_data_quality_score": year_pcaf,
                "record_status": record_status,
                "reporting_year": year,
            })

    df = pd.DataFrame(records)

    # Enforce types
    df["reporting_year"] = df["reporting_year"].astype("int32")
    df["outstanding_idr"] = df["outstanding_idr"].astype("int64")
    df["total_equity_idr"] = df["total_equity_idr"].astype("int64")
    df["total_debt_idr"] = df["total_debt_idr"].astype("int64")
    df["pcaf_attribution_factor"] = df["pcaf_attribution_factor"].astype("float64")
    df["borrower_emissions_tco2e"] = df["borrower_emissions_tco2e"].astype("float64")
    df["pcaf_data_quality_score"] = df["pcaf_data_quality_score"].astype("float64")

    return df


def validate_data(df: pd.DataFrame) -> None:
    """Run validation checks per spec constraints."""
    print("\n" + "=" * 60)
    print("  VALIDATION CHECKS")
    print("=" * 60)

    errors = []

    # Check outstanding <= EV
    df["ev"] = df["total_equity_idr"] + df["total_debt_idr"]
    violations = df[df["outstanding_idr"] > df["ev"]]
    if len(violations) > 0:
        errors.append(f"❌ {len(violations)} rows where outstanding > EV")
    else:
        print("  ✅ outstanding_idr <= (equity + debt) for all rows")

    # Check attribution factor
    af_violations = df[(df["pcaf_attribution_factor"] <= 0) | (df["pcaf_attribution_factor"] > 1)]
    if len(af_violations) > 0:
        errors.append(f"❌ {len(af_violations)} rows with invalid attribution factor")
    else:
        print("  ✅ pcaf_attribution_factor in (0, 1] for all rows")

    # Check emissions range
    em_violations = df[(df["borrower_emissions_tco2e"] < 500) | (df["borrower_emissions_tco2e"] > 5_000_000)]
    if len(em_violations) > 0:
        errors.append(f"❌ {len(em_violations)} rows with emissions out of range")
    else:
        print("  ✅ borrower_emissions_tco2e in [500, 5,000,000] for all rows")

    # Check PCAF score enum
    valid_scores = set(PCAF_SCORES)
    invalid_scores = df[~df["pcaf_data_quality_score"].isin(valid_scores)]
    if len(invalid_scores) > 0:
        errors.append(f"❌ {len(invalid_scores)} rows with invalid PCAF score")
    else:
        print("  ✅ pcaf_data_quality_score in valid ENUM set")

    # Check unique loan_id
    dupes = df[df.duplicated(subset=["loan_id"], keep=False)]
    if len(dupes) > 0:
        errors.append(f"❌ {len(dupes)} duplicate loan_ids")
    else:
        print("  ✅ loan_id is unique across all rows")

    # Check PCAF distribution
    print("\n  PCAF Score Distribution (target vs actual):")
    total = len(df)
    for score, target_pct in zip(PCAF_SCORES, PCAF_DISTRIBUTION):
        actual_count = len(df[df["pcaf_data_quality_score"] == score])
        actual_pct = actual_count / total
        status = "✅" if abs(actual_pct - target_pct) < 0.05 else "⚠️"
        print(f"    {status} Score {score}: target={target_pct*100:.1f}%, actual={actual_pct*100:.1f}%")

    df.drop(columns=["ev"], inplace=True)

    if errors:
        print("\n  ERRORS:")
        for e in errors:
            print(f"    {e}")
    else:
        print("\n  ✅ All validation checks passed!")


def main():
    print("=" * 60)
    print("  ESG Synthetic Data Generator: loan_portfolio")
    print("=" * 60)

    # Output directory
    output_dir = Path(__file__).parent.parent / "data" / "synthetic" / "loan_portfolio"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate data
    print(f"\nGenerating data for {NUM_BORROWERS} borrowers × {len(REPORTING_YEARS)} years...")
    df = generate_loan_portfolio()

    print(f"Total records: {len(df):,}")
    print(f"Unique borrowers: {df['borrower_id'].nunique():,}")
    print(f"Unique loans: {df['loan_id'].nunique():,}")

    # Validate
    validate_data(df)

    # Save partitioned by reporting_year
    # Partition column NOT stored inside parquet (derived from path per REQ-DDL-05)
    for year in REPORTING_YEARS:
        year_df = df[df["reporting_year"] == year].drop(columns=["reporting_year"])
        year_dir = output_dir / f"reporting_year={year}"
        year_dir.mkdir(parents=True, exist_ok=True)

        output_path = year_dir / "loan_portfolio.parquet"
        year_df.to_parquet(output_path, index=False, engine="pyarrow")
        print(f"\n✅ Written: {output_path} ({len(year_df):,} rows, {output_path.stat().st_size / 1024:.1f} KB)")

    # Sample CSV
    csv_path = output_dir / "loan_portfolio_sample.csv"
    df.head(100).to_csv(csv_path, index=False)
    print(f"\n📋 Sample CSV (100 rows): {csv_path}")

    # Summary stats
    print("\n" + "=" * 60)
    print("  SUMMARY STATISTICS")
    print("=" * 60)
    print(f"\n  Borrowers: {df['borrower_id'].nunique():,}")
    print(f"  Total loans: {len(df):,}")
    print(f"  Sector distribution:")
    for sector, count in df['sector_nace'].value_counts().items():
        print(f"    {sector}: {count} ({count/len(df)*100:.1f}%)")
    print(f"\n  Outstanding (IDR) — mean: {df['outstanding_idr'].mean():,.0f}")
    print(f"  Outstanding (IDR) — median: {df['outstanding_idr'].median():,.0f}")
    print(f"  Emissions (tCO2e) — mean: {df['borrower_emissions_tco2e'].mean():,.0f}")
    print(f"  Emissions (tCO2e) — median: {df['borrower_emissions_tco2e'].median():,.0f}")
    print(f"  Record status:")
    for status, count in df['record_status'].value_counts().items():
        print(f"    {status}: {count} ({count/len(df)*100:.1f}%)")


if __name__ == "__main__":
    main()
