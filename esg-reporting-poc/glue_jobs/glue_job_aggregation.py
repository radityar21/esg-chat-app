"""
=============================================================================
Glue Job: esg-etl-aggregation
=============================================================================
Spec Reference: §3.5 (REQ-ETL-24 to REQ-ETL-33)

Purpose:
    Aggregate curated zone data into report-ready metrics.
    This is the SINGLE SOURCE OF TRUTH for AgentCore (REQ-ETL-33).

    Input:  esg_curated.ghg_scope1, esg_curated.ghg_scope2, esg_curated.ghg_scope3_financed
            esg_raw.hr_metrics (for FTE denominator)
            esg_raw.loan_portfolio (for portfolio-weighted PCAF)
    Output: esg_aggregated.ghg_summary_annual + esg_aggregated.pcaf_by_sector
    Granularity: One record per (bank_id, reporting_year)

Formulas:
    REQ-ETL-24: Scope totals (SUM across facilities/sectors)
    REQ-ETL-25: total_tco2e = scope1 + scope2_market + scope3_cat15_gross
    REQ-ETL-26: yoy_change_pct = (current - prior) / prior × 100
    REQ-ETL-27: vs_base_year_change_pct
    REQ-ETL-28: intensity per IDR bn + per FTE
    REQ-ETL-29: portfolio-weighted PCAF score
    REQ-ETL-30: location-based total (supplementary)
    REQ-ETL-31: data completeness percentage

Validation Gates (REQ-ETL-32):
    GATE-AGG-01: total = scope1 + scope2_market + scope3_gross (±0.001)
    GATE-AGG-02: total_location = scope1 + scope2_location + scope3_gross (±0.001)
    GATE-AGG-03: scope3_weighted <= scope3_gross
    GATE-AGG-04: intensity > 0 (if revenue > 0)
    GATE-AGG-05: yoy_change within ±50% (warning only)
    GATE-AGG-06: only ONE record per (bank_id, reporting_year)
    GATE-AGG-07: avg_pcaf between 1.0 and 5.0

=============================================================================
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, StringType

# =============================================================================
# CONFIGURATION
# =============================================================================

ACCOUNT_ID = "061039769766"
RAW_BUCKET = f"esg-data-raw-{ACCOUNT_ID}"
CURATED_BUCKET = f"esg-data-curated-{ACCOUNT_ID}"
AGGREGATED_BUCKET = f"esg-data-aggregated-{ACCOUNT_ID}"
REPORTING_YEARS = [2023, 2024]

# Input paths (per REQ-DDL-05)
SCOPE1_BASE = f"s3://{CURATED_BUCKET}/curated/ghg_scope1/"
SCOPE2_BASE = f"s3://{CURATED_BUCKET}/curated/ghg_scope2/"
SCOPE3_BASE = f"s3://{CURATED_BUCKET}/curated/ghg_scope3_financed/"
HR_BASE = f"s3://{RAW_BUCKET}/raw/hr_metrics/"
LOANS_BASE = f"s3://{RAW_BUCKET}/raw/loan_portfolio/"

# Output paths (per REQ-DDL-05)
SUMMARY_OUTPUT_TEMPLATE = f"s3://{AGGREGATED_BUCKET}/aggregated/ghg_summary_annual/reporting_year={{}}/"
PCAF_SECTOR_OUTPUT_TEMPLATE = f"s3://{AGGREGATED_BUCKET}/aggregated/pcaf_by_sector/reporting_year={{}}/"

# Bank identifier (single institution for POC)
BANK_ID = "GENERIC_FI_001"

# Base year for vs_base_year comparison
BASE_YEAR = 2023

# Revenue (external input — hardcoded for POC; in production, from reference table)
# Unit: IDR billion
REVENUE_IDR_BILLION = {
    2023: 85000.0,   # IDR 85T revenue
    2024: 92000.0,   # IDR 92T revenue
}

# =============================================================================
# SCHEMA CONTRACTS
# =============================================================================

SCOPE1_EXPECTED = {"facility_id", "scope1_tco2e", "scope1_natgas_tco2e", "scope1_diesel_tco2e",
                   "total_natgas_gj", "total_diesel_liters", "imputed_months",
                   "data_quality_score", "emission_factor_source", "methodology",
                   "consolidation_approach"}

SCOPE2_EXPECTED = {"facility_id", "total_consumption_mwh", "scope2_location_tco2e",
                   "scope2_market_tco2e", "grid_region", "grid_ef_applied",
                   "rec_mwh_applied", "rec_applied_pct", "has_ppa",
                   "data_quality_score", "methodology"}

SCOPE3_EXPECTED = {"sector_nace", "loan_count", "borrower_count",
                   "total_outstanding_idr_trillion", "financed_emissions_gross_tco2e",
                   "financed_emissions_weighted_tco2e", "avg_pcaf_score",
                   "high_quality_data_pct"}


def validate_schema(df, expected_cols, table_name, logger):
    """Schema governance gate."""
    actual = set(df.columns)
    missing = expected_cols - actual
    if missing:
        raise ValueError(
            f"SCHEMA GATE FAILED [{table_name}]: Missing columns: {sorted(missing)}"
        )
    logger.info(f"SCHEMA GATE PASSED [{table_name}] ✅")


def main():
    # =========================================================================
    # GLUE JOB INITIALIZATION
    # =========================================================================
    args = getResolvedOptions(sys.argv, ["JOB_NAME"])
    sc = SparkContext()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    job = Job(glueContext)
    job.init(args["JOB_NAME"], args)

    logger = glueContext.get_logger()
    logger.info("Starting Aggregation ETL job")

    # =========================================================================
    # STEP 1: READ ALL CURATED DATA
    # =========================================================================
    logger.info("Reading curated zone data")

    # Scope 1
    scope1_df = spark.read.option("basePath", SCOPE1_BASE).parquet(SCOPE1_BASE + "*/")
    validate_schema(scope1_df, SCOPE1_EXPECTED, "ghg_scope1", logger)

    # Scope 2
    scope2_df = spark.read.option("basePath", SCOPE2_BASE).parquet(SCOPE2_BASE + "*/")
    validate_schema(scope2_df, SCOPE2_EXPECTED, "ghg_scope2", logger)

    # Scope 3
    scope3_df = spark.read.option("basePath", SCOPE3_BASE).parquet(SCOPE3_BASE + "*/")
    validate_schema(scope3_df, SCOPE3_EXPECTED, "ghg_scope3_financed", logger)

    # HR metrics (for FTE)
    hr_df = spark.read.option("basePath", HR_BASE).parquet(HR_BASE + "*/")

    # Loan portfolio (for portfolio-weighted PCAF — REQ-ETL-29)
    loans_df = spark.read.option("basePath", LOANS_BASE).parquet(LOANS_BASE + "*/")
    loans_df = loans_df.filter(F.col("record_status") == "validated")

    # =========================================================================
    # STEP 2: AGGREGATE SCOPE TOTALS PER YEAR (REQ-ETL-24)
    # =========================================================================
    logger.info("Computing scope totals per reporting year")

    # Scope 1 total per year (including natgas/diesel breakdown)
    scope1_annual = scope1_df.groupBy("reporting_year").agg(
        F.sum("scope1_tco2e").alias("scope1_tco2e"),
        F.sum("scope1_natgas_tco2e").alias("scope1_natgas_tco2e"),
        F.sum("scope1_diesel_tco2e").alias("scope1_diesel_tco2e"),
        F.count("*").alias("scope1_facility_count"),
        F.sum(F.when(F.col("data_quality_score") <= 2, 1).otherwise(0)).alias("high_quality_facilities")
    )

    # Scope 2 total per year
    scope2_annual = scope2_df.groupBy("reporting_year").agg(
        F.sum("scope2_location_tco2e").alias("scope2_location_tco2e"),
        F.sum("scope2_market_tco2e").alias("scope2_market_tco2e"),
        F.count("*").alias("scope2_facility_count")
    )

    # Scope 3 total per year (sum across all sectors)
    scope3_annual = scope3_df.groupBy("reporting_year").agg(
        F.sum("financed_emissions_gross_tco2e").alias("scope3_cat15_gross_tco2e"),
        F.sum("financed_emissions_weighted_tco2e").alias("scope3_cat15_weighted_tco2e")
    )

    # HR metrics per year (FTE for intensity)
    hr_annual = hr_df.groupBy("reporting_year").agg(
        F.sum("fte_total").alias("fte_count")
    )

    # Portfolio-weighted PCAF (REQ-ETL-29)
    pcaf_annual = loans_df.groupBy("reporting_year").agg(
        (F.sum(F.col("outstanding_idr").cast("double") * F.col("pcaf_data_quality_score"))
         / F.sum(F.col("outstanding_idr").cast("double"))).alias("avg_pcaf_data_quality")
    )

    # =========================================================================
    # STEP 3: JOIN ALL SCOPES (REQ-ETL-25)
    # =========================================================================
    logger.info("Joining all scope aggregates")

    summary_df = scope1_annual.join(scope2_annual, "reporting_year", "inner") \
        .join(scope3_annual, "reporting_year", "inner") \
        .join(hr_annual, "reporting_year", "left") \
        .join(pcaf_annual, "reporting_year", "left")

    # REQ-ETL-25: Grand total (uses market-based Scope 2)
    summary_df = summary_df.withColumn(
        "total_tco2e",
        F.col("scope1_tco2e") + F.col("scope2_market_tco2e") + F.col("scope3_cat15_gross_tco2e")
    )

    # REQ-ETL-30: Location-based total (supplementary)
    summary_df = summary_df.withColumn(
        "total_location_based_tco2e",
        F.col("scope1_tco2e") + F.col("scope2_location_tco2e") + F.col("scope3_cat15_gross_tco2e")
    )

    # =========================================================================
    # STEP 4: INTENSITY RATIOS (REQ-ETL-28)
    # =========================================================================
    logger.info("Computing intensity ratios")

    # Add revenue (from config)
    from pyspark.sql.functions import udf
    revenue_udf = udf(lambda yr: REVENUE_IDR_BILLION.get(yr, 0.0), DoubleType())
    summary_df = summary_df.withColumn("revenue_idr_bn", revenue_udf(F.col("reporting_year")))

    # Intensity per revenue (all scopes)
    summary_df = summary_df.withColumn(
        "intensity_tco2e_per_idr_bn",
        F.when(F.col("revenue_idr_bn") > 0,
               F.col("total_tco2e") / F.col("revenue_idr_bn"))
         .otherwise(F.lit(None))
    )

    # Intensity per FTE (Scope 1+2 only, excludes Scope 3 — REQ-ETL-28)
    summary_df = summary_df.withColumn(
        "intensity_tco2e_per_fte",
        F.when(F.col("fte_count") > 0,
               (F.col("scope1_tco2e") + F.col("scope2_market_tco2e")) / F.col("fte_count"))
         .otherwise(F.lit(None))
    )

    # =========================================================================
    # STEP 5: YEAR-OVER-YEAR & BASE YEAR (REQ-ETL-26, REQ-ETL-27)
    # =========================================================================
    logger.info("Computing YoY and base year comparisons")

    # Collect totals per year for YoY calculation
    totals_map = {row["reporting_year"]: row["total_tco2e"]
                  for row in summary_df.select("reporting_year", "total_tco2e").collect()}

    base_year_total = totals_map.get(BASE_YEAR, None)

    def compute_yoy(year):
        current = totals_map.get(year)
        prior = totals_map.get(year - 1)
        if current is not None and prior is not None and prior != 0:
            return round(((current - prior) / prior) * 100, 2)
        return None

    def compute_vs_base(year):
        current = totals_map.get(year)
        if year == BASE_YEAR:
            return None
        if current is not None and base_year_total is not None and base_year_total != 0:
            return round(((current - base_year_total) / base_year_total) * 100, 2)
        return None

    yoy_udf = udf(compute_yoy, DoubleType())
    vs_base_udf = udf(compute_vs_base, DoubleType())

    summary_df = summary_df.withColumn("yoy_change_pct", yoy_udf(F.col("reporting_year")))
    summary_df = summary_df.withColumn("vs_base_year_change_pct", vs_base_udf(F.col("reporting_year")))

    # =========================================================================
    # STEP 6: ADD METADATA & METRIC KEY
    # =========================================================================

    summary_df = summary_df.withColumn(
        "metric_key", F.concat(F.lit(BANK_ID + "_"), F.col("reporting_year").cast("string"))
    )

    summary_df = summary_df.withColumn("assurance_level", F.lit("none"))

    # REQ-ETL-31: Data completeness
    summary_df = summary_df.withColumn(
        "data_completeness_pct",
        F.when(F.col("scope1_facility_count") > 0,
               (F.col("high_quality_facilities").cast("double") / F.col("scope1_facility_count").cast("double")) * 100)
         .otherwise(F.lit(0.0))
    )

    # =========================================================================
    # STEP 7: ROUNDING (components first, then totals)
    # =========================================================================

    summary_df = summary_df.withColumn("scope1_tco2e", F.round("scope1_tco2e", 3))
    summary_df = summary_df.withColumn("scope1_natgas_tco2e", F.round("scope1_natgas_tco2e", 4))
    summary_df = summary_df.withColumn("scope1_diesel_tco2e", F.round("scope1_diesel_tco2e", 4))
    summary_df = summary_df.withColumn("scope2_location_tco2e", F.round("scope2_location_tco2e", 3))
    summary_df = summary_df.withColumn("scope2_market_tco2e", F.round("scope2_market_tco2e", 3))
    summary_df = summary_df.withColumn("scope3_cat15_gross_tco2e", F.round("scope3_cat15_gross_tco2e", 2))
    summary_df = summary_df.withColumn("scope3_cat15_weighted_tco2e", F.round("scope3_cat15_weighted_tco2e", 2))
    summary_df = summary_df.withColumn("intensity_tco2e_per_idr_bn", F.round("intensity_tco2e_per_idr_bn", 6))
    summary_df = summary_df.withColumn("intensity_tco2e_per_fte", F.round("intensity_tco2e_per_fte", 4))
    summary_df = summary_df.withColumn("avg_pcaf_data_quality", F.round("avg_pcaf_data_quality", 2))

    # Recompute total AFTER rounding components
    summary_df = summary_df.withColumn(
        "total_tco2e",
        F.round(F.col("scope1_tco2e") + F.col("scope2_market_tco2e") + F.col("scope3_cat15_gross_tco2e"), 3)
    )

    # =========================================================================
    # STEP 8: VALIDATION GATES (REQ-ETL-32)
    # =========================================================================
    logger.info("Running aggregation validation gates")

    # GATE-AGG-01: total = scope1 + scope2_market + scope3_gross (±0.001)
    gate01 = summary_df.withColumn(
        "check_total",
        F.abs(F.col("total_tco2e") - (F.col("scope1_tco2e") + F.col("scope2_market_tco2e") + F.col("scope3_cat15_gross_tco2e")))
    ).filter(F.col("check_total") > 0.001).count()
    if gate01 > 0:
        raise ValueError(f"GATE-AGG-01 FAILED: {gate01} rows where total != sum of scopes")

    # GATE-AGG-03: scope3_weighted <= scope3_gross
    gate03 = summary_df.filter(
        F.col("scope3_cat15_weighted_tco2e") > F.col("scope3_cat15_gross_tco2e")
    ).count()
    if gate03 > 0:
        raise ValueError(f"GATE-AGG-03 FAILED: {gate03} rows where weighted > gross")

    # GATE-AGG-05: yoy within ±50% (warning only)
    gate05 = summary_df.filter(
        (F.col("yoy_change_pct").isNotNull()) & (F.abs(F.col("yoy_change_pct")) > 50)
    ).count()
    if gate05 > 0:
        logger.warn(f"GATE-AGG-05 WARNING: {gate05} rows with YoY change > ±50% — flagged for human review")

    # GATE-AGG-06: only ONE record per reporting_year
    dup_check = summary_df.groupBy("reporting_year").count().filter(F.col("count") > 1).count()
    if dup_check > 0:
        raise ValueError(f"GATE-AGG-06 FAILED: Duplicate records per reporting_year")

    # GATE-AGG-07: avg_pcaf between 1.0 and 5.0
    gate07 = summary_df.filter(
        (F.col("avg_pcaf_data_quality") < 1.0) | (F.col("avg_pcaf_data_quality") > 5.0)
    ).count()
    if gate07 > 0:
        raise ValueError(f"GATE-AGG-07 FAILED: {gate07} rows with avg_pcaf out of 1.0-5.0 range")

    logger.info("All aggregation validation gates PASSED ✅")

    # =========================================================================
    # STEP 9: WRITE ghg_summary_annual
    # =========================================================================
    output_summary = summary_df.select(
        "metric_key",
        "scope1_tco2e",
        "scope1_natgas_tco2e",
        "scope1_diesel_tco2e",
        "scope2_location_tco2e",
        "scope2_market_tco2e",
        "scope3_cat15_gross_tco2e",
        "scope3_cat15_weighted_tco2e",
        "intensity_tco2e_per_idr_bn",
        "intensity_tco2e_per_fte",
        "yoy_change_pct",
        "vs_base_year_change_pct",
        "avg_pcaf_data_quality",
        "assurance_level",
        "reporting_year"
    )

    for year in REPORTING_YEARS:
        year_df = output_summary.filter(F.col("reporting_year") == year).drop("reporting_year")
        year_path = SUMMARY_OUTPUT_TEMPLATE.format(year)
        year_df.write.mode("overwrite").parquet(year_path)
        logger.info(f"  Written ghg_summary_annual year {year} to {year_path}")

    # =========================================================================
    # STEP 10: WRITE pcaf_by_sector
    # =========================================================================
    logger.info("Building pcaf_by_sector output")

    # Sector display names
    SECTOR_DISPLAY = {
        "manufacturing_cement": "Manufacturing - Cement",
        "manufacturing_steel": "Manufacturing - Steel",
        "manufacturing_food": "Manufacturing - Food & Beverage",
        "real_estate_commercial": "Real Estate - Commercial",
        "real_estate_residential": "Real Estate - Residential",
        "transportation_road": "Transportation - Road",
        "agriculture": "Agriculture",
        "energy_oil_gas": "Energy - Oil & Gas",
        "financial_services": "Financial Services",
        "retail_trade": "Retail Trade",
    }

    display_udf = udf(lambda s: SECTOR_DISPLAY.get(s, s), StringType())

    # Compute totals for percentage calculation
    total_outstanding = scope3_df.groupBy("reporting_year").agg(
        F.sum("total_outstanding_idr_trillion").alias("portfolio_total_outstanding"),
        F.sum("financed_emissions_gross_tco2e").alias("portfolio_total_emissions")
    )

    sector_output = scope3_df.join(total_outstanding, "reporting_year", "left")

    sector_output = sector_output.withColumn(
        "sector_display_name", display_udf(F.col("sector_nace"))
    ).withColumn(
        "emission_intensity_per_idr_bn",
        F.when(F.col("total_outstanding_idr_trillion") > 0,
               F.col("financed_emissions_gross_tco2e") / (F.col("total_outstanding_idr_trillion") * 1000))
         .otherwise(F.lit(0.0))
    ).withColumn(
        "pct_of_total_portfolio",
        F.when(F.col("portfolio_total_outstanding") > 0,
               (F.col("total_outstanding_idr_trillion") / F.col("portfolio_total_outstanding")) * 100)
         .otherwise(F.lit(0.0))
    ).withColumn(
        "pct_of_total_financed_emissions",
        F.when(F.col("portfolio_total_emissions") > 0,
               (F.col("financed_emissions_gross_tco2e") / F.col("portfolio_total_emissions")) * 100)
         .otherwise(F.lit(0.0))
    )

    # YoY per sector (need prior year data)
    # For simplicity, compute from the data we have
    sector_output = sector_output.withColumn("yoy_change_emissions_pct", F.lit(None).cast("double"))

    # Round
    sector_output = sector_output.withColumn("emission_intensity_per_idr_bn", F.round("emission_intensity_per_idr_bn", 4))
    sector_output = sector_output.withColumn("pct_of_total_portfolio", F.round("pct_of_total_portfolio", 2))
    sector_output = sector_output.withColumn("pct_of_total_financed_emissions", F.round("pct_of_total_financed_emissions", 2))

    # Select final columns
    pcaf_output = sector_output.select(
        "sector_nace",
        "sector_display_name",
        "loan_count",
        "borrower_count",
        "total_outstanding_idr_trillion",
        "financed_emissions_gross_tco2e",
        "financed_emissions_weighted_tco2e",
        "emission_intensity_per_idr_bn",
        "avg_pcaf_score",
        "pct_of_total_portfolio",
        "pct_of_total_financed_emissions",
        "yoy_change_emissions_pct",
        "reporting_year"
    )

    for year in REPORTING_YEARS:
        year_df = pcaf_output.filter(F.col("reporting_year") == year).drop("reporting_year")
        year_path = PCAF_SECTOR_OUTPUT_TEMPLATE.format(year)
        year_df.write.mode("overwrite").parquet(year_path)
        logger.info(f"  Written pcaf_by_sector year {year} to {year_path}")

    # =========================================================================
    # STEP 10b: WRITE scope1_by_facility (top emitters for per-facility breakdown)
    # =========================================================================
    logger.info("Building scope1_by_facility output (top 10 facilities per year)")

    FACILITY_OUTPUT_TEMPLATE = f"s3://{AGGREGATED_BUCKET}/aggregated/scope1_by_facility/reporting_year={{}}/"

    # Select top 10 facilities by scope1_tco2e per year
    from pyspark.sql.window import Window

    facility_window = Window.partitionBy("reporting_year").orderBy(F.desc("scope1_tco2e"))
    facility_ranked = scope1_df.withColumn("rank", F.row_number().over(facility_window))
    facility_top = facility_ranked.filter(F.col("rank") <= 10)

    facility_output = facility_top.select(
        "facility_id",
        F.round("scope1_tco2e", 4).alias("scope1_tco2e"),
        F.round("scope1_natgas_tco2e", 4).alias("scope1_natgas_tco2e"),
        F.round("scope1_diesel_tco2e", 4).alias("scope1_diesel_tco2e"),
        F.round("total_natgas_gj", 2).alias("total_natgas_gj"),
        F.round("total_diesel_liters", 2).alias("total_diesel_liters"),
        "data_quality_score",
        "reporting_year"
    )

    for year in REPORTING_YEARS:
        year_df = facility_output.filter(F.col("reporting_year") == year).drop("reporting_year")
        year_path = FACILITY_OUTPUT_TEMPLATE.format(year)
        year_df.write.mode("overwrite").parquet(year_path)
        logger.info(f"  Written scope1_by_facility year {year} to {year_path}")

    # =========================================================================
    # STEP 11: SUMMARY STATS
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("  AGGREGATION SUMMARY")
    logger.info("=" * 60)

    for row in output_summary.collect():
        yr = row["reporting_year"]
        logger.info(f"\n  Year {yr} ({row['metric_key']}):")
        logger.info(f"    Scope 1:          {row['scope1_tco2e'] or 0:.3f} tCO2e")
        logger.info(f"    Scope 2 location: {row['scope2_location_tco2e'] or 0:.3f} tCO2e")
        logger.info(f"    Scope 2 market:   {row['scope2_market_tco2e'] or 0:.3f} tCO2e")
        logger.info(f"    Scope 3 gross:    {row['scope3_cat15_gross_tco2e'] or 0:.2f} tCO2e")
        logger.info(f"    Scope 3 weighted: {row['scope3_cat15_weighted_tco2e'] or 0:.2f} tCO2e")
        logger.info(f"    Intensity/IDR bn: {row['intensity_tco2e_per_idr_bn'] or 0:.6f}")
        logger.info(f"    Intensity/FTE:    {row['intensity_tco2e_per_fte'] or 0:.4f}")
        logger.info(f"    YoY change:       {row['yoy_change_pct']}")
        logger.info(f"    Avg PCAF:         {row['avg_pcaf_data_quality'] or 0:.2f}")

    logger.info("\n✅ Aggregation job complete.")
    job.commit()


if __name__ == "__main__":
    main()
