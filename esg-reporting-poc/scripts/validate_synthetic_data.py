#!/usr/bin/env python3
"""
Validate all synthetic data against ESG_Kiro_Requirements_Spec §2.1, §2.2, §2.3
"""
import re
import pandas as pd
from pathlib import Path

base = Path(__file__).parent.parent / "data" / "synthetic"

ISSUES = []

def check(condition, desc):
    status = "✅" if condition else "❌"
    print(f"  {status} {desc}")
    if not condition:
        ISSUES.append(desc)

# =============================================================================
# §2.1 ENERGY CONSUMPTION
# =============================================================================
print("=" * 70)
print("  §2.1 ENERGY CONSUMPTION VALIDATION")
print("=" * 70)

e23 = pd.read_parquet(base / "energy_consumption" / "reporting_year=2023" / "energy_consumption.parquet")
e24 = pd.read_parquet(base / "energy_consumption" / "reporting_year=2024" / "energy_consumption.parquet")
energy = pd.concat([e23.assign(reporting_year=2023), e24.assign(reporting_year=2024)], ignore_index=True)
print(f"  Total rows: {len(energy)}")
print()

# facility_id format FAC-NNNN
fac_pattern = re.compile(r"^FAC-\d{4}$")
fac_valid = energy["facility_id"].apply(lambda x: bool(fac_pattern.match(str(x)))).all()
check(fac_valid, "facility_id format FAC-NNNN (4-digit zero-padded)")

# reporting_year 2020-2035
yr_valid = energy["reporting_year"].between(2020, 2035).all()
check(yr_valid, f"reporting_year in 2020-2035 (actual: {sorted(energy['reporting_year'].unique())})")

# reporting_month 1-12
mo_valid = energy["reporting_month"].between(1, 12).all()
check(mo_valid, f"reporting_month in 1-12 (actual: {sorted(energy['reporting_month'].unique())})")

# electricity_kwh >= 0 where present
e_nn = energy["electricity_kwh"].dropna()
check((e_nn >= 0).all(), f"electricity_kwh >= 0 where present (min={e_nn.min():.1f})")

# electricity_kwh range 1500-85000
e_in_range = ((e_nn >= 1500) & (e_nn <= 85000)).mean() * 100
check(e_in_range >= 95, f"electricity_kwh within 1500-85000: {e_in_range:.1f}% (spec range, allow minor outliers)")

# natural_gas_gj >= 0 where present
g_nn = energy["natural_gas_gj"].dropna()
check((g_nn >= 0).all(), f"natural_gas_gj >= 0 where present (min={g_nn.min():.2f})")

# natural_gas_gj range 0-120
g_in_range = ((g_nn >= 0) & (g_nn <= 120)).mean() * 100
check(g_in_range >= 95, f"natural_gas_gj within 0-120: {g_in_range:.1f}%")

# diesel_liters >= 0 where present
d_nn = energy["diesel_liters"].dropna()
check((d_nn >= 0).all(), f"diesel_liters >= 0 where present (min={d_nn.min():.2f})")

# diesel_liters range 0-3500
d_in_range = ((d_nn >= 0) & (d_nn <= 3500)).mean() * 100
check(d_in_range >= 95, f"diesel_liters within 0-3500: {d_in_range:.1f}%")

# srec_mwh_claimed NOT nullable, >= 0
check(energy["srec_mwh_claimed"].isnull().sum() == 0, "srec_mwh_claimed: no NULLs (NOT nullable)")
check((energy["srec_mwh_claimed"] >= 0).all(), "srec_mwh_claimed: all >= 0")

# grid_ef_kgco2_kwh NOT nullable, > 0
check(energy["grid_ef_kgco2_kwh"].isnull().sum() == 0, "grid_ef_kgco2_kwh: no NULLs (NOT nullable)")
check((energy["grid_ef_kgco2_kwh"] > 0).all(), "grid_ef_kgco2_kwh: all > 0")

# ef_source ENUM
valid_ef = {"PLN_Grid_Average_2023", "DEFRA_2025", "IPCC_AR6_CH4_GWP100"}
actual_ef = set(energy["ef_source"].unique())
check(actual_ef.issubset(valid_ef), f"ef_source ENUM valid: {sorted(actual_ef)}")

# Check ef_source matches grid_ef value
pln_rows = energy[energy["ef_source"] == "PLN_Grid_Average_2023"]
pln_ef_match = (pln_rows["grid_ef_kgco2_kwh"] == 0.7886).all()
check(pln_ef_match, "grid_ef = 0.7886 when ef_source = PLN_Grid_Average_2023")

# data_source ENUM
valid_ds = {"smart_meter_api", "manual_entry", "estimate"}
actual_ds = set(energy["data_source"].unique())
check(actual_ds.issubset(valid_ds), f"data_source ENUM valid: {sorted(actual_ds)}")

# record_status ENUM
valid_rs = {"complete", "missing_primary", "excluded"}
actual_rs = set(energy["record_status"].unique())
check(actual_rs.issubset(valid_rs), f"record_status ENUM valid: {sorted(actual_rs)}")

# meter_reading_kwh within 0.5% of electricity_kwh
meter_df = energy.dropna(subset=["meter_reading_kwh", "electricity_kwh"])
if len(meter_df) > 0:
    tolerance = meter_df["electricity_kwh"] * 0.005
    within = (abs(meter_df["meter_reading_kwh"] - meter_df["electricity_kwh"]) <= tolerance).mean() * 100
    check(within >= 99, f"meter_reading_kwh within 0.5% of electricity_kwh: {within:.1f}%")

# Facility count >= 200
fac_count = energy["facility_id"].nunique()
check(fac_count >= 200, f"Facility count >= 200 (actual: {fac_count})")

print()

# =============================================================================
# §2.2 LOAN PORTFOLIO
# =============================================================================
print("=" * 70)
print("  §2.2 LOAN PORTFOLIO VALIDATION")
print("=" * 70)

l23 = pd.read_parquet(base / "loan_portfolio" / "reporting_year=2023" / "loan_portfolio.parquet")
l24 = pd.read_parquet(base / "loan_portfolio" / "reporting_year=2024" / "loan_portfolio.parquet")
loans = pd.concat([l23.assign(reporting_year=2023), l24.assign(reporting_year=2024)], ignore_index=True)
print(f"  Total rows: {len(loans)}")
print()

# loan_id format LN-YYYY-NNNNNNN
loan_pattern = re.compile(r"^LN-\d{4}-\d{7}$")
loan_valid = loans["loan_id"].apply(lambda x: bool(loan_pattern.match(str(x)))).all()
check(loan_valid, "loan_id format LN-YYYY-NNNNNNN")

# loan_id UNIQUE
check(loans["loan_id"].is_unique, "loan_id is UNIQUE (PK)")

# borrower_id format BOR-NNNNNN
bor_pattern = re.compile(r"^BOR-\d{6}$")
bor_valid = loans["borrower_id"].apply(lambda x: bool(bor_pattern.match(str(x)))).all()
check(bor_valid, "borrower_id format BOR-NNNNNN")

# sector_nace ENUM (10 values)
valid_sectors = {
    "manufacturing_cement", "manufacturing_steel", "manufacturing_food",
    "real_estate_commercial", "real_estate_residential", "transportation_road",
    "agriculture", "energy_oil_gas", "financial_services", "retail_trade"
}
actual_sectors = set(loans["sector_nace"].unique())
check(actual_sectors.issubset(valid_sectors), f"sector_nace ENUM valid ({len(actual_sectors)} values)")

# loan_type ENUM (6 values)
valid_lt = {"term_loan", "revolving_credit", "mortgage", "project_finance", "syndicated_loan", "leasing"}
actual_lt = set(loans["loan_type"].unique())
check(actual_lt.issubset(valid_lt), f"loan_type ENUM valid ({len(actual_lt)} values)")

# currency ENUM
valid_cur = {"IDR", "USD"}
actual_cur = set(loans["currency"].unique())
check(actual_cur.issubset(valid_cur), f"currency ENUM valid: {sorted(actual_cur)}")

# outstanding_idr > 0
check((loans["outstanding_idr"] > 0).all(), f"outstanding_idr > 0 (min={loans['outstanding_idr'].min():,})")

# outstanding_idr <= enterprise value (equity + debt)
loans["ev"] = loans["total_equity_idr"] + loans["total_debt_idr"]
ov_check = (loans["outstanding_idr"] <= loans["ev"]).all()
check(ov_check, "outstanding_idr <= (equity + debt) for ALL rows")

# outstanding_idr range 500M-2T
ost_min = loans["outstanding_idr"].min()
ost_max = loans["outstanding_idr"].max()
check(ost_min >= 500_000_000, f"outstanding_idr >= 500M (min={ost_min:,})")
check(ost_max <= 2_000_000_000_000, f"outstanding_idr <= 2T (max={ost_max:,})")

# total_equity_idr > 0, range 1B-50T
check((loans["total_equity_idr"] > 0).all(), "total_equity_idr > 0")
eq_min = loans["total_equity_idr"].min()
eq_max = loans["total_equity_idr"].max()
check(eq_min >= 1_000_000_000, f"total_equity_idr >= 1B (min={eq_min:,})")
check(eq_max <= 50_000_000_000_000, f"total_equity_idr <= 50T (max={eq_max:,})")

# total_debt_idr >= 0
check((loans["total_debt_idr"] >= 0).all(), "total_debt_idr >= 0")

# (equity + debt) > 0
check((loans["ev"] > 0).all(), "(equity + debt) > 0 for ALL rows")

# pcaf_attribution_factor: 0 < x <= 1
af = loans["pcaf_attribution_factor"]
check((af > 0).all() and (af <= 1).all(), f"pcaf_attribution_factor in (0, 1] (min={af.min():.6f}, max={af.max():.6f})")

# Verify attribution = outstanding / ev
loans["af_calc"] = loans["outstanding_idr"] / loans["ev"]
af_diff = abs(loans["pcaf_attribution_factor"] - loans["af_calc"])
check((af_diff < 0.000001).all(), "pcaf_attribution_factor = outstanding/(equity+debt) ±0.000001")

# borrower_emissions_tco2e > 0, range 500-5M
be = loans["borrower_emissions_tco2e"]
check((be > 0).all(), "borrower_emissions_tco2e > 0")
check(be.min() >= 500, f"borrower_emissions_tco2e >= 500 (min={be.min():.2f})")
check(be.max() <= 5_000_000, f"borrower_emissions_tco2e <= 5M (max={be.max():.2f})")

# pcaf_data_quality_score ENUM
valid_pcaf = {1.0, 1.5, 2.0, 3.0, 4.0, 5.0}
actual_pcaf = set(loans["pcaf_data_quality_score"].unique())
check(actual_pcaf.issubset(valid_pcaf), f"pcaf_data_quality_score ENUM valid: {sorted(actual_pcaf)}")

# PCAF distribution check
print("\n  PCAF Score Distribution:")
target_dist = {1.0: 3.5, 1.5: 1.5, 2.0: 15.0, 3.0: 30.0, 4.0: 35.0, 5.0: 15.0}
for score, target in target_dist.items():
    actual_pct = (loans["pcaf_data_quality_score"] == score).mean() * 100
    diff = abs(actual_pct - target)
    status = "✅" if diff < 5 else "⚠️"
    print(f"    {status} Score {score}: target={target:.1f}%, actual={actual_pct:.1f}% (diff={diff:.1f}%)")

# record_status ENUM
valid_lrs = {"validated", "pending", "rejected"}
actual_lrs = set(loans["record_status"].unique())
check(actual_lrs.issubset(valid_lrs), f"record_status ENUM valid: {sorted(actual_lrs)}")

# Borrower count >= 2000
bor_count = loans["borrower_id"].nunique()
check(bor_count >= 2000, f"Borrower count >= 2000 (actual: {bor_count})")

print()

# =============================================================================
# §2.3 HR METRICS
# =============================================================================
print("=" * 70)
print("  §2.3 HR METRICS VALIDATION")
print("=" * 70)

h23 = pd.read_parquet(base / "hr_metrics" / "reporting_year=2023" / "hr_metrics.parquet")
h24 = pd.read_parquet(base / "hr_metrics" / "reporting_year=2024" / "hr_metrics.parquet")
hr = pd.concat([h23.assign(reporting_year=2023), h24.assign(reporting_year=2024)], ignore_index=True)
print(f"  Total rows: {len(hr)}")
print()

# period_date is YYYY-12-31
hr["period_date"] = pd.to_datetime(hr["period_date"])
date_check = ((hr["period_date"].dt.month == 12) & (hr["period_date"].dt.day == 31)).all()
check(date_check, "period_date format YYYY-12-31")

# fte_total > 0, range 500-50000
check((hr["fte_total"] > 0).all(), "fte_total > 0")
check(hr["fte_total"].between(500, 50000).all(), f"fte_total in 500-50000 (actual: {hr['fte_total'].tolist()})")

# fte_female_pct 0-100
check(hr["fte_female_pct"].between(0, 100).all(), "fte_female_pct in 0-100")

# fte_management_female_pct 0-100
check(hr["fte_management_female_pct"].between(0, 100).all(), "fte_management_female_pct in 0-100")

# new_hire_count >= 0
check((hr["new_hire_count"] >= 0).all(), "new_hire_count >= 0")

# voluntary_turnover_pct 0-100
check(hr["voluntary_turnover_pct"].between(0, 100).all(), "voluntary_turnover_pct in 0-100")

# training_hours_per_fte >= 0, range 8-120
check((hr["training_hours_per_fte"] >= 0).all(), "training_hours_per_fte >= 0")
check(hr["training_hours_per_fte"].between(8, 120).all(), f"training_hours_per_fte in 8-120 (actual: {hr['training_hours_per_fte'].tolist()})")

# discrimination_cases >= 0
check((hr["discrimination_cases"] >= 0).all(), "discrimination_cases >= 0")

print()

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print("=" * 70)
if ISSUES:
    print(f"  ❌ VALIDATION COMPLETE: {len(ISSUES)} ISSUES FOUND")
    print("=" * 70)
    for i, issue in enumerate(ISSUES, 1):
        print(f"    {i}. {issue}")
else:
    print("  ✅ ALL VALIDATIONS PASSED — DATA COMPLIANT WITH SPEC §2.1-2.3")
    print("=" * 70)
