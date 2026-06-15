"""
=============================================================================
Glue Job: esg-etl-scope3-pcaf
=============================================================================
Spec Reference: §3.4 (REQ-ETL-14 to REQ-ETL-23)

Purpose:
    Calculate Scope 3 Category 15 financed emissions using PCAF methodology.
    Aggregates at sector level per reporting year.

    Input:  esg_raw.loan_portfolio WHERE record_status = 'validated'
    Output: esg_curated.ghg_scope3_financed
    Granularity: One record per (sector_nace, reporting_year)
    Methodology: PCAF Global GHG Accounting Standard, Part A (2022 revision)

Formulas:
    REQ-ETL-14: attribution_factor = outstanding_idr / (total_equity_idr + total_debt_idr)
    REQ-ETL-15: financed_emissions_loan = attribution_factor × borrower_emissions_tco2e
    REQ-ETL-16: financed_emissions_weighted = financed_emissions_loan × PCAF_CONFIDENCE[score]
    REQ-ETL-17: Sector-level aggregation (loan_count, borrower_count, totals, avgs)

Validation Gates:
    REQ-ETL-18: Reject if (equity + debt) <= 0
    REQ-ETL-19: Cap attribution_factor at 1.0 if outstanding > EV
    REQ-ETL-20: Reject if borrower_emissions <= 0
    REQ-ETL-23: weighted MUST always <= gross

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
# PCAF CONFIDENCE FACTORS (Spec §3.1, Table 4.2)
# =============================================================================

PCAF_CONFIDENCE = {
    1.0: 1.00,   # Verified CDP/equivalent
    1.5: 0.95,   # Audited + unverified (interpolated)
    2.0: 0.90,   # Reported, unverified
    3.0: 0.75,   # EEIO + revenue-based
    4.0: 0.60,   # EEIO + asset-based
    5.0: 0.45,   # Sector-average proxy
}

# =============================================================================
# CONFIGURATION
# =============================================================================

ACCOUNT_ID = "061039769766"
RAW_BUCKET = f"esg-data-raw-{ACCOUNT_ID}"
CURATED_BUCKET = f"esg-data-curated-{ACCOUNT_ID}"
REPORTING_YEARS = [2023, 2024]

# S3 path patterns (per REQ-DDL-05)
INPUT_BASE = f"s3://{RAW_BUCKET}/raw/loan_portfolio/"
OUTPUT_PATH_TEMPLATE = f"s3://{CURATED_BUCKET}/curated/ghg_scope3_financed/reporting_year={{}}/"
ERROR_PATH = f"s3://{CURATED_BUCKET}/curated/errors/ghg_scope3_errors/"

# =============================================================================
# SCHEMA CONTRACT (mirrors DDL — zero-compromise governance)
# =============================================================================

EXPECTED_COLUMNS = {
    "loan_id":                  "string",
    "borrower_id":              "string",
    "sector_nace":              "string",
    "loan_type":                "string",
    "currency":                 "string",
    "outstanding_idr":          "bigint",
    "total_equity_idr":         "bigint",
    "total_debt_idr":           "bigint",
    "pcaf_attribution_factor":  "double",
    "borrower_emissions_tco2e": "double",
    "pcaf_data_quality_score":  "double",
    "record_status":            "string",
    "reporting_year":           "int",
}

VALID_SECTORS = {
    "manufacturing_cement", "manufacturing_steel", "manufacturing_food",
    "real_estate_commercial", "real_estate_residential", "transportation_road",
    "agriculture", "energy_oil_gas", "financial_services", "retail_trade"
}

VALID_RECORD_STATUSES = {"validated", "pending", "rejected"}


def validate_schema(df, expected_columns, logger):
    """Schema governance gate."""
    actual_columns = set(df.columns)
    expected_names = set(expected_columns.keys())

    missing = expected_names - actual_columns
    if missing:
        raise ValueError(
            f"SCHEMA GATE FAILED: Missing columns: {sorted(missing)}. "
            f"Source data does NOT match esg_raw.loan_portfolio DDL."
        )

    logger.info(f"SCHEMA GATE PASSED: All {len(expected_names)} expected columns present ✅")


def map_pcaf_confidence(score):
    """Map PCAF data quality score to confidence factor."""
    return PCAF_CONFIDENCE.get(score, 0.45)  # Default to lowest if unknown


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
    logger.info("Starting Scope 3 PCAF financed emissions calculation job")

    # =========================================================================
    # STEP 1: READ RAW DATA
    # =========================================================================
    logger.info("Reading loan portfolio data from S3")

    input_paths = [INPUT_BASE + "*/"]
    raw_df = spark.read.option("basePath", INPUT_BASE).parquet(*input_paths)

    # Schema governance gate
    validate_schema(raw_df, EXPECTED_COLUMNS, logger)

    # ENUM validation
    actual_sectors = set(row["sector_nace"] for row in raw_df.select("sector_nace").distinct().collect())
    invalid_sectors = actual_sectors - VALID_SECTORS
    if invalid_sectors:
        raise ValueError(f"ENUM GATE FAILED: Invalid sector_nace values: {invalid_sectors}")

    actual_rs = set(row["record_status"] for row in raw_df.select("record_status").distinct().collect())
    invalid_rs = actual_rs - VALID_RECORD_STATUSES
    if invalid_rs:
        raise ValueError(f"ENUM GATE FAILED: Invalid record_status values: {invalid_rs}")

    logger.info("ENUM GATES PASSED ✅")

    # Filter: only validated records (spec: only validated enters curated)
    raw_df = raw_df.filter(F.col("record_status") == "validated")

    total_input = raw_df.count()
    logger.info(f"Input after filter: {total_input} validated loans")

    # =========================================================================
    # STEP 2: VALIDATION GATES (REQ-ETL-18, 19, 20)
    # =========================================================================
    logger.info("Applying pre-processing validation gates")

    # Compute enterprise value
    raw_df = raw_df.withColumn(
        "enterprise_value", F.col("total_equity_idr") + F.col("total_debt_idr")
    )

    # REQ-ETL-18: Gate 1 — Reject if (equity + debt) <= 0
    gate18_reject = raw_df.filter(F.col("enterprise_value") <= 0)
    gate18_count = gate18_reject.count()
    if gate18_count > 0:
        logger.warn(f"REQ-ETL-18: Rejecting {gate18_count} loans with EV <= 0")
        gate18_reject.write.mode("append").parquet(ERROR_PATH + "gate18_ev_nonpositive/")
        raw_df = raw_df.filter(F.col("enterprise_value") > 0)

    # REQ-ETL-20: Gate 3 — Reject if borrower_emissions <= 0
    gate20_reject = raw_df.filter(F.col("borrower_emissions_tco2e") <= 0)
    gate20_count = gate20_reject.count()
    if gate20_count > 0:
        logger.warn(f"REQ-ETL-20: Rejecting {gate20_count} loans with emissions <= 0")
        gate20_reject.write.mode("append").parquet(ERROR_PATH + "gate20_emissions_nonpositive/")
        raw_df = raw_df.filter(F.col("borrower_emissions_tco2e") > 0)

    # REQ-ETL-19: Gate 2 — Cap attribution_factor at 1.0 if outstanding > EV
    raw_df = raw_df.withColumn(
        "attribution_factor_calc",
        F.col("outstanding_idr").cast("double") / F.col("enterprise_value").cast("double")
    ).withColumn(
        "af_capped",
        F.when(F.col("attribution_factor_calc") > 1.0, F.lit(1.0))
         .otherwise(F.col("attribution_factor_calc"))
    ).withColumn(
        "data_quality_flag",
        F.when(F.col("attribution_factor_calc") > 1.0, F.lit("AF_CAPPED"))
         .otherwise(F.lit("OK"))
    )

    capped_count = raw_df.filter(F.col("data_quality_flag") == "AF_CAPPED").count()
    if capped_count > 0:
        logger.warn(f"REQ-ETL-19: {capped_count} loans had attribution factor capped at 1.0")

    logger.info(f"After gates: {raw_df.count()} loans remaining")

    # =========================================================================
    # STEP 3: PER-LOAN CALCULATIONS (REQ-ETL-15, REQ-ETL-16)
    # =========================================================================
    logger.info("Computing per-loan financed emissions")

    # REQ-ETL-15: Gross financed emissions per loan
    raw_df = raw_df.withColumn(
        "financed_emissions_loan_tco2e",
        F.col("af_capped") * F.col("borrower_emissions_tco2e")
    )

    # REQ-ETL-16: Confidence-weighted financed emissions
    # Map PCAF score → confidence factor using a when/otherwise chain
    confidence_expr = F.lit(0.45)  # default (score 5)
    for score, factor in sorted(PCAF_CONFIDENCE.items(), reverse=True):
        confidence_expr = F.when(
            F.col("pcaf_data_quality_score") == score, F.lit(factor)
        ).otherwise(confidence_expr)

    raw_df = raw_df.withColumn("confidence_factor", confidence_expr)

    raw_df = raw_df.withColumn(
        "financed_emissions_weighted_tco2e",
        F.col("financed_emissions_loan_tco2e") * F.col("confidence_factor")
    )

    # =========================================================================
    # STEP 4: SECTOR-LEVEL AGGREGATION (REQ-ETL-17)
    # =========================================================================
    logger.info("Aggregating to sector level")

    sector_df = raw_df.groupBy("sector_nace", "reporting_year").agg(
        # loan_count
        F.count("*").cast("int").alias("loan_count"),

        # borrower_count (distinct)
        F.countDistinct("borrower_id").cast("int").alias("borrower_count"),

        # total_outstanding_idr_trillion
        (F.sum("outstanding_idr").cast("double") / F.lit(1e12)).alias("total_outstanding_idr_trillion"),

        # financed_emissions_gross_tco2e
        F.sum("financed_emissions_loan_tco2e").alias("financed_emissions_gross_tco2e"),

        # financed_emissions_weighted_tco2e
        F.sum("financed_emissions_weighted_tco2e").alias("financed_emissions_weighted_tco2e"),

        # avg_pcaf_score
        F.mean("pcaf_data_quality_score").alias("avg_pcaf_score"),

        # high_quality_data_pct: COUNT(score <= 2) / COUNT(*) × 100
        (F.sum(F.when(F.col("pcaf_data_quality_score") <= 2.0, 1).otherwise(0)).cast("double")
         / F.count("*").cast("double") * F.lit(100.0)).alias("high_quality_data_pct")
    )

    # =========================================================================
    # STEP 5: ROUNDING & PRECISION
    # =========================================================================

    sector_df = sector_df.withColumn(
        "total_outstanding_idr_trillion", F.round("total_outstanding_idr_trillion", 6)
    ).withColumn(
        "financed_emissions_gross_tco2e", F.round("financed_emissions_gross_tco2e", 2)
    ).withColumn(
        "financed_emissions_weighted_tco2e", F.round("financed_emissions_weighted_tco2e", 2)
    ).withColumn(
        "avg_pcaf_score", F.round("avg_pcaf_score", 2)
    ).withColumn(
        "high_quality_data_pct", F.round("high_quality_data_pct", 4)
    )

    # =========================================================================
    # STEP 6: VALIDATION GATES (POST-AGGREGATION)
    # =========================================================================
    logger.info("Running post-aggregation validation gates")

    output_count = sector_df.count()

    # REQ-ETL-23: weighted MUST always <= gross
    weighted_gt_gross = sector_df.filter(
        F.col("financed_emissions_weighted_tco2e") > F.col("financed_emissions_gross_tco2e")
    ).count()
    if weighted_gt_gross > 0:
        raise ValueError(
            f"REQ-ETL-23 FAILED: {weighted_gt_gross} sectors where weighted > gross. "
            f"This violates the fundamental PCAF constraint."
        )

    # loan_count > 0
    zero_loans = sector_df.filter(F.col("loan_count") <= 0).count()
    if zero_loans > 0:
        raise ValueError(f"VALIDATION FAILED: {zero_loans} sectors with loan_count <= 0")

    # avg_pcaf_score between 1.0 and 5.0
    bad_pcaf = sector_df.filter(
        (F.col("avg_pcaf_score") < 1.0) | (F.col("avg_pcaf_score") > 5.0)
    ).count()
    if bad_pcaf > 0:
        raise ValueError(f"VALIDATION FAILED: {bad_pcaf} sectors with avg_pcaf_score out of range")

    logger.info("All validation gates PASSED ✅")

    # =========================================================================
    # STEP 7: SELECT FINAL COLUMNS & WRITE OUTPUT
    # =========================================================================
    logger.info(f"Writing {output_count} sector-year records")

    output_df = sector_df.select(
        "sector_nace",
        "loan_count",
        "borrower_count",
        "total_outstanding_idr_trillion",
        "financed_emissions_gross_tco2e",
        "financed_emissions_weighted_tco2e",
        "avg_pcaf_score",
        "high_quality_data_pct",
        "reporting_year"
    )

    # Write per year
    for year in [row["reporting_year"] for row in output_df.select("reporting_year").distinct().collect()]:
        year_df = output_df.filter(F.col("reporting_year") == year).drop("reporting_year")
        year_path = OUTPUT_PATH_TEMPLATE.format(year)
        year_df.write.mode("overwrite").parquet(year_path)
        logger.info(f"  Written year {year} to {year_path}")

    logger.info(f"✅ Scope 3 PCAF calculation complete. {output_count} sector-year records written.")

    # =========================================================================
    # STEP 8: SUMMARY STATS
    # =========================================================================
    summary = output_df.agg(
        F.count("*").alias("total_sectors"),
        F.sum("loan_count").alias("total_loans"),
        F.sum("financed_emissions_gross_tco2e").alias("total_gross_tco2e"),
        F.sum("financed_emissions_weighted_tco2e").alias("total_weighted_tco2e"),
        F.mean("avg_pcaf_score").alias("portfolio_avg_pcaf")
    ).collect()[0]

    logger.info(f"  Total sector-year records: {summary['total_sectors']}")
    logger.info(f"  Total loans processed: {summary['total_loans']}")
    logger.info(f"  Total gross financed emissions (tCO2e): {summary['total_gross_tco2e'] or 0:.2f}")
    logger.info(f"  Total weighted financed emissions (tCO2e): {summary['total_weighted_tco2e'] or 0:.2f}")
    logger.info(f"  Portfolio avg PCAF score: {summary['portfolio_avg_pcaf'] or 0:.2f}")

    # REQ-ETL-21: Portfolio weighted PCAF (for reference)
    pwp = raw_df.agg(
        (F.sum(F.col("outstanding_idr").cast("double") * F.col("pcaf_data_quality_score"))
         / F.sum(F.col("outstanding_idr").cast("double"))).alias("portfolio_weighted_pcaf")
    ).collect()[0]["portfolio_weighted_pcaf"]
    logger.info(f"  Portfolio weighted PCAF (REQ-ETL-21): {pwp or 0:.2f}")

    job.commit()


if __name__ == "__main__":
    main()
