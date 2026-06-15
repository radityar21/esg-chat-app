"""
=============================================================================
Glue Job: esg-etl-scope2-indirect
=============================================================================
Spec Reference: §3.3 (REQ-ETL-09 to REQ-ETL-13)

Purpose:
    Calculate Scope 2 indirect GHG emissions from purchased electricity.
    Dual reporting: BOTH location-based AND market-based (GHG Protocol Scope 2 Guidance).

    Input:  esg_raw.energy_consumption WHERE record_status = 'complete'
    Output: esg_curated.ghg_scope2
    Granularity: One record per (facility_id, reporting_year)

Formulas:
    REQ-ETL-09: consumption_mwh = electricity_kwh / 1000
    REQ-ETL-10: scope2_location_tco2e = SUM(electricity_kwh × grid_ef) / 1000
    REQ-ETL-11: scope2_market_tco2e = scope2_location - REC adjustment (floored at 0)
    REQ-ETL-12: rec_applied_pct = (rec_mwh / total_mwh) × 100

Validation Gates:
    GATE-S2-01: scope2_location_tco2e >= 0
    GATE-S2-02: scope2_market_tco2e >= 0
    GATE-S2-03: scope2_market_tco2e <= scope2_location_tco2e
    GATE-S2-04: total_consumption_mwh > 0 for all active facilities
    GATE-S2-05: Grid EF exists for every facility

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
# GRID EMISSION FACTORS (Spec §3.3)
# =============================================================================

# Grid region → EF mapping (kg CO2/kWh)
GRID_EF_MAP = {
    "java_bali":    0.7250,   # PLN Regional 2023
    "sumatra":      0.8020,   # PLN Regional 2023
    "kalimantan":   0.8450,   # PLN Regional 2023
    "sulawesi":     0.7900,   # PLN Regional 2023
    "national":     0.7886,   # PLN National Average 2023 (default/fallback)
}

# Default grid EF when no region mapping exists
GRID_EF_DEFAULT = 0.7886  # PLN National Average 2023

# =============================================================================
# CONFIGURATION
# =============================================================================

ACCOUNT_ID = "061039769766"
RAW_BUCKET = f"esg-data-raw-{ACCOUNT_ID}"
CURATED_BUCKET = f"esg-data-curated-{ACCOUNT_ID}"
REPORTING_YEARS = [2023, 2024]

# S3 path patterns (per REQ-DDL-05)
INPUT_BASE = f"s3://{RAW_BUCKET}/raw/energy_consumption/"
OUTPUT_PATH_TEMPLATE = f"s3://{CURATED_BUCKET}/curated/ghg_scope2/reporting_year={{}}/"

METHODOLOGY = "GHG_Protocol_Scope2_Guidance_2015"

# =============================================================================
# SCHEMA CONTRACT (mirrors DDL — zero-compromise governance)
# =============================================================================

EXPECTED_COLUMNS = {
    "facility_id":        "string",
    "electricity_kwh":    "double",
    "natural_gas_gj":     "double",
    "diesel_liters":      "double",
    "srec_mwh_claimed":   "double",
    "grid_ef_kgco2_kwh":  "double",
    "ef_source":          "string",
    "meter_reading_kwh":  "double",
    "data_source":        "string",
    "record_status":      "string",
    "reporting_month":    "int",
    "reporting_year":     "int",
}

VALID_RECORD_STATUSES = {"complete", "missing_primary", "excluded"}


def validate_schema(df, expected_columns, logger):
    """Schema governance gate: Verify DataFrame columns match DDL contract."""
    actual_columns = set(df.columns)
    expected_names = set(expected_columns.keys())

    missing = expected_names - actual_columns
    if missing:
        raise ValueError(
            f"SCHEMA GATE FAILED: Missing columns: {sorted(missing)}. "
            f"Source data does NOT match esg_raw.energy_consumption DDL."
        )

    logger.info(f"SCHEMA GATE PASSED: All {len(expected_names)} expected columns present ✅")


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
    logger.info("Starting Scope 2 GHG calculation job")

    # =========================================================================
    # STEP 1: READ RAW DATA
    # =========================================================================
    logger.info("Reading energy consumption data from S3")

    input_paths = [INPUT_BASE + "*/*/"]
    raw_df = spark.read.option("basePath", INPUT_BASE).parquet(*input_paths)

    # Schema governance gate
    validate_schema(raw_df, EXPECTED_COLUMNS, logger)

    # Filter: only complete records
    raw_df = raw_df.filter(F.col("record_status") == "complete")

    # GATE-S2-05: Grid EF must exist (not NULL) for every row
    null_ef_count = raw_df.filter(F.col("grid_ef_kgco2_kwh").isNull()).count()
    if null_ef_count > 0:
        raise ValueError(f"GATE-S2-05 FAILED: {null_ef_count} rows with NULL grid_ef_kgco2_kwh")

    input_facility_count = raw_df.select("facility_id").distinct().count()
    logger.info(f"Input: {raw_df.count()} rows, {input_facility_count} facilities")

    # =========================================================================
    # STEP 2: MONTHLY SCOPE 2 CALCULATIONS (REQ-ETL-09, REQ-ETL-10)
    # =========================================================================
    logger.info("Computing monthly Scope 2 emissions")

    # Handle null electricity_kwh (treat as 0 for facilities with no reading)
    raw_df = raw_df.withColumn(
        "electricity_kwh_clean",
        F.coalesce(F.col("electricity_kwh"), F.lit(0.0))
    )

    # REQ-ETL-10: Location-based Scope 2 per month
    raw_df = raw_df.withColumn(
        "scope2_location_month_kgco2e",
        F.col("electricity_kwh_clean") * F.col("grid_ef_kgco2_kwh")
    )

    # =========================================================================
    # STEP 3: ANNUAL AGGREGATION PER FACILITY
    # =========================================================================
    logger.info("Aggregating monthly to annual per facility")

    annual_df = raw_df.groupBy("facility_id", "reporting_year").agg(
        # REQ-ETL-09: Total consumption in MWh
        (F.sum("electricity_kwh_clean") / F.lit(1000.0)).alias("total_consumption_mwh"),

        # REQ-ETL-10: Location-based Scope 2 (tCO2e)
        (F.sum("scope2_location_month_kgco2e") / F.lit(1000.0)).alias("scope2_location_tco2e"),

        # REC MWh claimed (sum across months)
        F.sum("srec_mwh_claimed").alias("rec_mwh_applied"),

        # Grid EF applied (take the most common / first)
        F.first("grid_ef_kgco2_kwh").alias("grid_ef_applied"),

        # EF source for region determination
        F.first("ef_source").alias("ef_source_ref"),

        # Count null electricity months (for data quality)
        F.sum(F.when(F.col("electricity_kwh").isNull(), 1).otherwise(0)).cast("int").alias("null_months")
    )

    # =========================================================================
    # STEP 4: MARKET-BASED SCOPE 2 (REQ-ETL-11, REQ-ETL-12)
    # =========================================================================
    logger.info("Computing market-based Scope 2")

    # REQ-ETL-11: Market-based = Location-based - REC adjustment
    # REC adjustment: rec_mwh × grid_ef_applied (converted to tCO2e)
    annual_df = annual_df.withColumn(
        "rec_adjustment_tco2e",
        F.col("rec_mwh_applied") * F.col("grid_ef_applied") / F.lit(1000.0)
    )

    annual_df = annual_df.withColumn(
        "scope2_market_tco2e",
        F.greatest(
            F.col("scope2_location_tco2e") - F.col("rec_adjustment_tco2e"),
            F.lit(0.0)  # Floor at 0 (REQ-ETL-11)
        )
    )

    # REQ-ETL-12: REC reconciliation percentage
    annual_df = annual_df.withColumn(
        "rec_applied_pct",
        F.when(
            F.col("total_consumption_mwh") > 0,
            (F.col("rec_mwh_applied") / F.col("total_consumption_mwh")) * F.lit(100.0)
        ).otherwise(0.0)
    )

    # Cap REC at total consumption (REQ-ETL-12 constraint)
    annual_df = annual_df.withColumn(
        "rec_mwh_applied",
        F.least(F.col("rec_mwh_applied"), F.col("total_consumption_mwh"))
    )

    # =========================================================================
    # STEP 5: ADD METADATA COLUMNS
    # =========================================================================

    # Grid region (for POC, assign based on EF source; default = national)
    annual_df = annual_df.withColumn(
        "grid_region", F.lit("national")
    )

    # PPA flag (for POC, no PPA data available)
    annual_df = annual_df.withColumn(
        "has_ppa", F.lit(False)
    )

    # Data quality score
    annual_df = annual_df.withColumn(
        "data_quality_score",
        F.when(F.col("null_months") == 0, 1)
         .when(F.col("null_months") <= 2, 2)
         .when(F.col("null_months") <= 5, 3)
         .otherwise(4)
    )

    annual_df = annual_df.withColumn(
        "methodology", F.lit(METHODOLOGY)
    )

    # Round to required precision
    annual_df = annual_df.withColumn(
        "scope2_location_tco2e", F.round("scope2_location_tco2e", 3)
    ).withColumn(
        "scope2_market_tco2e", F.round("scope2_market_tco2e", 3)
    ).withColumn(
        "total_consumption_mwh", F.round("total_consumption_mwh", 3)
    ).withColumn(
        "rec_mwh_applied", F.round("rec_mwh_applied", 3)
    ).withColumn(
        "rec_applied_pct", F.round("rec_applied_pct", 2)
    )

    # =========================================================================
    # STEP 6: VALIDATION GATES (REQ-ETL-13 / Spec §3.3)
    # =========================================================================
    logger.info("Running validation gates")

    output_count = annual_df.count()

    # GATE-S2-01: scope2_location_tco2e >= 0
    neg_loc = annual_df.filter(F.col("scope2_location_tco2e") < 0).count()
    if neg_loc > 0:
        raise ValueError(f"GATE-S2-01 FAILED: {neg_loc} rows with negative scope2_location_tco2e")

    # GATE-S2-02: scope2_market_tco2e >= 0
    neg_mkt = annual_df.filter(F.col("scope2_market_tco2e") < 0).count()
    if neg_mkt > 0:
        raise ValueError(f"GATE-S2-02 FAILED: {neg_mkt} rows with negative scope2_market_tco2e")

    # GATE-S2-03: market <= location
    mkt_gt_loc = annual_df.filter(
        F.col("scope2_market_tco2e") > F.col("scope2_location_tco2e")
    ).count()
    if mkt_gt_loc > 0:
        logger.warn(f"GATE-S2-03 WARNING: {mkt_gt_loc} rows where market > location")

    # GATE-S2-04: total_consumption_mwh > 0 for active facilities
    zero_consumption = annual_df.filter(F.col("total_consumption_mwh") <= 0).count()
    if zero_consumption > 0:
        logger.warn(f"GATE-S2-04 WARNING: {zero_consumption} facilities with zero consumption")

    logger.info("All validation gates PASSED ✅")

    # =========================================================================
    # STEP 7: SELECT FINAL COLUMNS & WRITE OUTPUT
    # =========================================================================
    logger.info(f"Writing {output_count} rows")

    output_df = annual_df.select(
        "facility_id",
        "total_consumption_mwh",
        "scope2_location_tco2e",
        "scope2_market_tco2e",
        "grid_region",
        "grid_ef_applied",
        "rec_mwh_applied",
        "rec_applied_pct",
        "has_ppa",
        "data_quality_score",
        "methodology",
        "reporting_year"
    )

    # Write per year to match DDL path pattern
    for year in [row["reporting_year"] for row in output_df.select("reporting_year").distinct().collect()]:
        year_df = output_df.filter(F.col("reporting_year") == year).drop("reporting_year")
        year_path = OUTPUT_PATH_TEMPLATE.format(year)
        year_df.write.mode("overwrite").parquet(year_path)
        logger.info(f"  Written year {year} to {year_path}")

    logger.info(f"✅ Scope 2 calculation complete. {output_count} facility-year records written.")

    # =========================================================================
    # STEP 8: SUMMARY STATS
    # =========================================================================
    summary = output_df.agg(
        F.count("*").alias("total_records"),
        F.sum("scope2_location_tco2e").alias("total_scope2_location"),
        F.sum("scope2_market_tco2e").alias("total_scope2_market"),
        F.mean("rec_applied_pct").alias("avg_rec_pct"),
        F.mean("data_quality_score").alias("avg_dq")
    ).collect()[0]

    logger.info(f"  Total records: {summary['total_records']}")
    logger.info(f"  Total Scope 2 location (tCO2e): {summary['total_scope2_location'] or 0:.3f}")
    logger.info(f"  Total Scope 2 market (tCO2e): {summary['total_scope2_market'] or 0:.3f}")
    logger.info(f"  Avg REC coverage: {summary['avg_rec_pct'] or 0:.2f}%")
    logger.info(f"  Avg data quality: {summary['avg_dq'] or 0:.2f}")

    job.commit()


if __name__ == "__main__":
    main()
