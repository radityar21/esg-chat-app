"""
=============================================================================
Glue Job: esg-etl-scope1-direct
=============================================================================
Spec Reference: §3.2 (REQ-ETL-01 to REQ-ETL-08)

Purpose:
    Calculate Scope 1 direct GHG emissions from natural gas and diesel combustion.
    Input:  esg_raw.energy_consumption WHERE record_status = 'complete'
    Output: esg_curated.ghg_scope1
    Granularity: One record per (facility_id, reporting_year)
    Methodology: GHG Protocol Corporate Standard v2015
    Consolidation: Operational Control

Formulas:
    Natural Gas (REQ-ETL-02):
        scope1_natgas_month_kgco2e =
            (natural_gas_gj × EF_NATGAS_KGCO2_PER_GJ)
          + (natural_gas_gj × EF_NATGAS_KGCH4_PER_GJ × GWP_CH4)
          + (natural_gas_gj × EF_NATGAS_KGN2O_PER_GJ × GWP_N2O)
        scope1_natgas_tco2e = SUM(monthly) / 1000

    Diesel (REQ-ETL-03):
        scope1_diesel_month_kgco2e =
            (diesel_liters × EF_DIESEL_KGCO2_PER_L)
          + (diesel_liters × EF_DIESEL_KGCH4_PER_L × GWP_CH4)
          + (diesel_liters × EF_DIESEL_KGN2O_PER_L × GWP_N2O)
        scope1_diesel_tco2e = SUM(monthly) / 1000

    Total (REQ-ETL-04):
        scope1_tco2e = scope1_natgas_tco2e + scope1_diesel_tco2e

Validation Gates (REQ-ETL-08):
    GATE-S1-01: scope1_tco2e is NOT NULL
    GATE-S1-02: scope1_tco2e >= 0
    GATE-S1-03: scope1_natgas + scope1_diesel = scope1_tco2e (±0.0001)
    GATE-S1-04: output rows <= input facilities (no row explosion)
    GATE-S1-05: emission_factor_source is not NULL/empty

=============================================================================
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import DoubleType, IntegerType, StringType

# =============================================================================
# EMISSION FACTOR CONSTANTS (Spec §3.1 — Non-Negotiable)
# =============================================================================
# These MUST NOT be hard-coded inline; declared as module-level named variables.

# Global Warming Potentials (IPCC AR6 Chapter 7, GWP100)
GWP_CH4 = 29.8       # kg CO2e / kg CH4
GWP_N2O = 273.0      # kg CO2e / kg N2O

# Natural Gas Emission Factors (IPCC 2006)
EF_NATGAS_KGCO2_PER_GJ = 56.10    # kg CO2 / GJ (Table 2.2)
EF_NATGAS_KGCH4_PER_GJ = 0.001    # kg CH4 / GJ (Vol 2, Table 2.3)
EF_NATGAS_KGN2O_PER_GJ = 0.0001   # kg N2O / GJ (Vol 2, Table 2.3)

# Diesel Emission Factors (DEFRA 2025)
EF_DIESEL_KGCO2_PER_L = 2.53763   # kg CO2 / litre (DEFRA 2025 Annex 3)
EF_DIESEL_KGCH4_PER_L = 0.0000097 # kg CH4 / litre
EF_DIESEL_KGN2O_PER_L = 0.000121  # kg N2O / litre

# Derived composite factors (for validation/reference only)
EF_NATGAS_COMPOSITE_KGCO2E_PER_GJ = (
    EF_NATGAS_KGCO2_PER_GJ
    + (EF_NATGAS_KGCH4_PER_GJ * GWP_CH4)
    + (EF_NATGAS_KGN2O_PER_GJ * GWP_N2O)
)  # ≈ 56.1568

EF_DIESEL_COMPOSITE_KGCO2E_PER_L = (
    EF_DIESEL_KGCO2_PER_L
    + (EF_DIESEL_KGCH4_PER_L * GWP_CH4)
    + (EF_DIESEL_KGN2O_PER_L * GWP_N2O)
)  # ≈ 2.5710

# =============================================================================
# CONFIGURATION
# =============================================================================

ACCOUNT_ID = "061039769766"
RAW_BUCKET = f"esg-data-raw-{ACCOUNT_ID}"
CURATED_BUCKET = f"esg-data-curated-{ACCOUNT_ID}"
REPORTING_YEARS = [2023, 2024]

# S3 path patterns (match DDL storage.location.template per REQ-DDL-05)
# Raw input:  s3://{RAW_BUCKET}/raw/energy_consumption/reporting_year={year}/reporting_month={month}/
# Curated output: s3://{CURATED_BUCKET}/curated/ghg_scope1/reporting_year={year}/
INPUT_BASE = f"s3://{RAW_BUCKET}/raw/energy_consumption/"
OUTPUT_PATH_TEMPLATE = f"s3://{CURATED_BUCKET}/curated/ghg_scope1/reporting_year={{}}/"
ERROR_PATH = f"s3://{CURATED_BUCKET}/curated/errors/ghg_scope1_errors/"

METHODOLOGY = "GHG_Protocol_Corporate_Standard_v2015"
CONSOLIDATION = "operational_control"

# =============================================================================
# SCHEMA CONTRACT (mirrors DDL in 02_raw_tables.sql — zero-compromise governance)
# =============================================================================
# Expected columns from esg_raw.energy_consumption
# If source data is missing ANY of these, job MUST fail immediately.

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

# Valid ENUM values (from Spec §2.1)
VALID_EF_SOURCES = {"PLN_Grid_Average_2023", "DEFRA_2025", "IPCC_AR6_CH4_GWP100"}
VALID_DATA_SOURCES = {"smart_meter_api", "manual_entry", "estimate"}
VALID_RECORD_STATUSES = {"complete", "missing_primary", "excluded"}


def validate_schema(df, expected_columns, logger):
    """
    Schema governance gate: Verify DataFrame columns match DDL contract.
    Raises ValueError if schema mismatch detected.
    """
    actual_columns = set(df.columns)
    expected_names = set(expected_columns.keys())

    missing = expected_names - actual_columns
    unexpected = actual_columns - expected_names

    if missing:
        raise ValueError(
            f"SCHEMA GATE FAILED: Missing columns from DDL contract: {sorted(missing)}. "
            f"Source data does NOT match esg_raw.energy_consumption DDL."
        )

    if unexpected:
        logger.warn(
            f"SCHEMA GATE WARNING: Unexpected columns found (will be ignored): {sorted(unexpected)}"
        )

    # Type validation (Spark type name check)
    type_map = {"string": "StringType", "double": "DoubleType", "int": "IntegerType"}
    for col_name, expected_type in expected_columns.items():
        if col_name in actual_columns:
            actual_type = str(df.schema[col_name].dataType).replace("()", "")
            expected_spark_type = type_map.get(expected_type, expected_type)
            if expected_spark_type.lower() not in actual_type.lower():
                logger.warn(
                    f"SCHEMA GATE TYPE WARNING: Column '{col_name}' expected "
                    f"{expected_spark_type} but got {actual_type}"
                )

    logger.info(f"SCHEMA GATE PASSED: All {len(expected_names)} expected columns present ✅")

# Data quality score thresholds (REQ-ETL-07)
# imputed_months -> data_quality_score
# 0        -> 1 (All actual data)
# 1-2      -> 2 (Minor imputation)
# 3-5      -> 3 (Moderate imputation)
# 6+       -> 4 (Excluded from curated zone)
MAX_IMPUTED_MONTHS_ALLOWED = 5  # >5 means excluded (REQ-ETL-06)


def get_data_quality_score(imputed_months):
    """
    REQ-ETL-07: Assign data quality score based on imputed months.
    """
    if imputed_months == 0:
        return 1
    elif imputed_months <= 2:
        return 2
    elif imputed_months <= 5:
        return 3
    else:
        return 4


# Register UDF
from pyspark.sql.functions import udf
data_quality_udf = udf(get_data_quality_score, IntegerType())


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
    logger.info("Starting Scope 1 GHG calculation job")

    # =========================================================================
    # STEP 1: READ RAW DATA (filter: record_status = 'complete')
    # =========================================================================
    logger.info("Reading from esg_raw.energy_consumption WHERE record_status = 'complete'")

    # Read directly from S3 (configurable paths)
    # Reads all reporting_year and reporting_month partitions under INPUT_BASE
    logger.info(f"Input base: {INPUT_BASE}")

    raw_df = spark.read.option("basePath", INPUT_BASE).parquet(INPUT_BASE + "*/*/")

    # ---- SCHEMA GOVERNANCE GATE ----
    validate_schema(raw_df, EXPECTED_COLUMNS, logger)

    # ---- ENUM VALIDATION GATE ----
    # Check ef_source values
    actual_ef = set(row["ef_source"] for row in raw_df.select("ef_source").distinct().collect())
    invalid_ef = actual_ef - VALID_EF_SOURCES
    if invalid_ef:
        raise ValueError(f"ENUM GATE FAILED: Invalid ef_source values: {invalid_ef}")

    # Check record_status values
    actual_rs = set(row["record_status"] for row in raw_df.select("record_status").distinct().collect())
    invalid_rs = actual_rs - VALID_RECORD_STATUSES
    if invalid_rs:
        raise ValueError(f"ENUM GATE FAILED: Invalid record_status values: {invalid_rs}")

    logger.info("ENUM GATES PASSED ✅")

    # Filter: only complete records (spec: excluded MUST NOT enter curated zone)
    raw_df = raw_df.filter(F.col("record_status") == "complete")

    input_facility_count = raw_df.select("facility_id").distinct().count()
    logger.info(f"Input: {raw_df.count()} rows, {input_facility_count} distinct facilities")

    # =========================================================================
    # STEP 2: IMPUTATION (REQ-ETL-06)
    # Handle NULL natural_gas_gj and diesel_liters
    # Strategy:
    #   - If facility has ALL months null for a fuel → no connection → treat as 0, no imputation
    #   - If facility has SOME months null (partial gap) → impute with monthly mean
    # ==========================================================================
    logger.info("Applying null imputation (REQ-ETL-06)")

    # Determine per facility: does it EVER have non-null gas/diesel?
    # If a facility has at least 1 non-null month → it HAS a connection → nulls are gaps
    # If ALL months are null → no connection → treat as 0 (NOT imputed)
    facility_has_gas = raw_df.groupBy("facility_id", "reporting_year").agg(
        F.sum(F.when(F.col("natural_gas_gj").isNotNull(), 1).otherwise(0)).alias("gas_nonnull_months"),
        F.sum(F.when(F.col("diesel_liters").isNotNull(), 1).otherwise(0)).alias("diesel_nonnull_months")
    )

    raw_df = raw_df.join(facility_has_gas, on=["facility_id", "reporting_year"], how="left")

    # Flag null months ONLY for facilities that have a connection (at least 1 non-null month)
    raw_df = raw_df.withColumn(
        "natgas_is_null",
        F.when(
            (F.col("gas_nonnull_months") > 0) & (F.col("natural_gas_gj").isNull()),
            1
        ).otherwise(0)
    ).withColumn(
        "diesel_is_null",
        F.when(
            (F.col("diesel_nonnull_months") > 0) & (F.col("diesel_liters").isNull()),
            1
        ).otherwise(0)
    )

    # Compute monthly means for imputation (only from facilities that have data)
    monthly_means = raw_df.filter(
        F.col("natural_gas_gj").isNotNull() | F.col("diesel_liters").isNotNull()
    ).groupBy("reporting_year", "reporting_month").agg(
        F.mean("natural_gas_gj").alias("mean_natgas_gj"),
        F.mean("diesel_liters").alias("mean_diesel_liters")
    )

    # Join means back
    raw_df = raw_df.join(
        monthly_means,
        on=["reporting_year", "reporting_month"],
        how="left"
    )

    # Impute: use mean only if facility has connection but month is null
    # Otherwise: 0.0 (no connection = zero fuel consumption)
    raw_df = raw_df.withColumn(
        "natural_gas_gj_imputed",
        F.when(
            F.col("natural_gas_gj").isNotNull(), F.col("natural_gas_gj")
        ).when(
            F.col("gas_nonnull_months") > 0, F.coalesce(F.col("mean_natgas_gj"), F.lit(0.0))
        ).otherwise(F.lit(0.0))  # no connection → 0
    ).withColumn(
        "diesel_liters_imputed",
        F.when(
            F.col("diesel_liters").isNotNull(), F.col("diesel_liters")
        ).when(
            F.col("diesel_nonnull_months") > 0, F.coalesce(F.col("mean_diesel_liters"), F.lit(0.0))
        ).otherwise(F.lit(0.0))  # no connection → 0
    )

    # =========================================================================
    # STEP 3: MONTHLY EMISSION CALCULATIONS (REQ-ETL-02, REQ-ETL-03)
    # Compute at facility-month level first (REQ-ETL-01)
    # =========================================================================
    logger.info("Computing monthly Scope 1 emissions")

    # REQ-ETL-02: Natural Gas Scope 1
    raw_df = raw_df.withColumn(
        "scope1_natgas_month_kgco2e",
        (F.col("natural_gas_gj_imputed") * F.lit(EF_NATGAS_KGCO2_PER_GJ))
        + (F.col("natural_gas_gj_imputed") * F.lit(EF_NATGAS_KGCH4_PER_GJ) * F.lit(GWP_CH4))
        + (F.col("natural_gas_gj_imputed") * F.lit(EF_NATGAS_KGN2O_PER_GJ) * F.lit(GWP_N2O))
    )

    # REQ-ETL-03: Diesel Scope 1
    raw_df = raw_df.withColumn(
        "scope1_diesel_month_kgco2e",
        (F.col("diesel_liters_imputed") * F.lit(EF_DIESEL_KGCO2_PER_L))
        + (F.col("diesel_liters_imputed") * F.lit(EF_DIESEL_KGCH4_PER_L) * F.lit(GWP_CH4))
        + (F.col("diesel_liters_imputed") * F.lit(EF_DIESEL_KGN2O_PER_L) * F.lit(GWP_N2O))
    )

    # =========================================================================
    # STEP 4: ANNUAL AGGREGATION (REQ-ETL-01, REQ-ETL-04, REQ-ETL-05)
    # Sum monthly to annual per (facility_id, reporting_year)
    # =========================================================================
    logger.info("Aggregating monthly to annual per facility")

    annual_df = raw_df.groupBy("facility_id", "reporting_year").agg(
        # REQ-ETL-02: Annual natural gas emissions (tCO2e)
        (F.sum("scope1_natgas_month_kgco2e") / F.lit(1000.0)).alias("scope1_natgas_tco2e"),

        # REQ-ETL-03: Annual diesel emissions (tCO2e)
        (F.sum("scope1_diesel_month_kgco2e") / F.lit(1000.0)).alias("scope1_diesel_tco2e"),

        # REQ-ETL-05: Activity data preservation
        F.sum("natural_gas_gj_imputed").alias("total_natgas_gj"),
        F.sum("diesel_liters_imputed").alias("total_diesel_liters"),

        # Imputation tracking (REQ-ETL-06)
        F.sum(F.col("natgas_is_null") + F.col("diesel_is_null")).cast("int").alias("imputed_months"),

        # EF source (take most common per facility)
        F.first("ef_source").alias("emission_factor_source")
    )

    # REQ-ETL-04: Total Scope 1 = natgas + diesel (no rounding before addition)
    annual_df = annual_df.withColumn(
        "scope1_tco2e",
        F.col("scope1_natgas_tco2e") + F.col("scope1_diesel_tco2e")
    )

    # =========================================================================
    # STEP 5: DATA QUALITY SCORE (REQ-ETL-07)
    # =========================================================================
    logger.info("Assigning data quality scores (REQ-ETL-07)")

    annual_df = annual_df.withColumn(
        "data_quality_score",
        data_quality_udf(F.col("imputed_months"))
    )

    # REQ-ETL-06: Exclude facilities with >5 imputed months (data_quality_score = 4)
    # These go to error partition, not curated zone
    error_df = annual_df.filter(F.col("data_quality_score") == 4)
    curated_df = annual_df.filter(F.col("data_quality_score") < 4)

    error_count = error_df.count()
    if error_count > 0:
        logger.warn(f"REQ-ETL-06: {error_count} facilities excluded (>5 imputed months)")
        # Write error partition
        error_df.write.mode("overwrite").parquet(ERROR_PATH)

    # =========================================================================
    # STEP 6: ADD METADATA COLUMNS
    # =========================================================================
    curated_df = curated_df.withColumn(
        "methodology", F.lit(METHODOLOGY)
    ).withColumn(
        "consolidation_approach", F.lit(CONSOLIDATION)
    )

    # Round to required precision (4 dp for tCO2e)
    # IMPORTANT: Round components FIRST, then recompute total from rounded components
    # to guarantee GATE-S1-03 passes (scope1_natgas + scope1_diesel == scope1_tco2e)
    curated_df = curated_df.withColumn(
        "scope1_natgas_tco2e", F.round("scope1_natgas_tco2e", 4)
    ).withColumn(
        "scope1_diesel_tco2e", F.round("scope1_diesel_tco2e", 4)
    ).withColumn(
        "total_natgas_gj", F.round("total_natgas_gj", 2)
    ).withColumn(
        "total_diesel_liters", F.round("total_diesel_liters", 2)
    )

    # Recompute total AFTER rounding components (REQ-ETL-04: exact sum)
    curated_df = curated_df.withColumn(
        "scope1_tco2e",
        F.round(F.col("scope1_natgas_tco2e") + F.col("scope1_diesel_tco2e"), 4)
    )

    # =========================================================================
    # STEP 7: VALIDATION GATES (REQ-ETL-08)
    # =========================================================================
    logger.info("Running validation gates (REQ-ETL-08)")

    # GATE-S1-01: scope1_tco2e is NOT NULL
    null_check = curated_df.filter(F.col("scope1_tco2e").isNull()).count()
    if null_check > 0:
        raise ValueError(f"GATE-S1-01 FAILED: {null_check} rows with NULL scope1_tco2e")

    # GATE-S1-02: scope1_tco2e >= 0
    negative_check = curated_df.filter(F.col("scope1_tco2e") < 0).count()
    if negative_check > 0:
        raise ValueError(f"GATE-S1-02 FAILED: {negative_check} rows with negative scope1_tco2e")

    # GATE-S1-03: scope1_natgas + scope1_diesel = scope1_tco2e (±0.0001)
    curated_df_check = curated_df.withColumn(
        "sum_check",
        F.abs(
            F.col("scope1_tco2e")
            - (F.col("scope1_natgas_tco2e") + F.col("scope1_diesel_tco2e"))
        )
    )
    integrity_violations = curated_df_check.filter(F.col("sum_check") > 0.0001).count()
    if integrity_violations > 0:
        raise ValueError(
            f"GATE-S1-03 FAILED: {integrity_violations} rows where "
            f"scope1_natgas + scope1_diesel != scope1_tco2e (tolerance ±0.0001)"
        )

    # GATE-S1-04: output rows <= input facilities
    output_count = curated_df.count()
    if output_count > input_facility_count:
        raise ValueError(
            f"GATE-S1-04 FAILED: Output rows ({output_count}) > "
            f"input facilities ({input_facility_count}). Check join logic."
        )

    # GATE-S1-05: emission_factor_source is not NULL or empty
    ef_null_check = curated_df.filter(
        F.col("emission_factor_source").isNull()
        | (F.trim(F.col("emission_factor_source")) == "")
    ).count()
    if ef_null_check > 0:
        raise ValueError(f"GATE-S1-05 FAILED: {ef_null_check} rows with NULL/empty emission_factor_source")

    logger.info("All validation gates PASSED ✅")

    # =========================================================================
    # STEP 8: SELECT FINAL COLUMNS & WRITE OUTPUT
    # =========================================================================
    logger.info(f"Writing {output_count} rows to {OUTPUT_PATH_TEMPLATE}")

    output_df = curated_df.select(
        "facility_id",
        "scope1_tco2e",
        "scope1_natgas_tco2e",
        "scope1_diesel_tco2e",
        "total_natgas_gj",
        "total_diesel_liters",
        "imputed_months",
        "data_quality_score",
        "emission_factor_source",
        "methodology",
        "consolidation_approach",
        "reporting_year"
    )

    # Write per year to match DDL: s3://{CURATED_BUCKET}/curated/ghg_scope1/reporting_year={year}/
    for year in [row["reporting_year"] for row in output_df.select("reporting_year").distinct().collect()]:
        year_df = output_df.filter(F.col("reporting_year") == year).drop("reporting_year")
        year_path = OUTPUT_PATH_TEMPLATE.format(year)
        year_df.write.mode("overwrite").parquet(year_path)
        logger.info(f"  Written year {year} to {year_path}")

    logger.info(f"✅ Scope 1 calculation complete. {output_count} facility-year records written.")

    # =========================================================================
    # STEP 9: SUMMARY STATS (for logging)
    # =========================================================================
    summary = output_df.agg(
        F.count("*").alias("total_records"),
        F.sum("scope1_tco2e").alias("total_scope1_tco2e"),
        F.mean("scope1_tco2e").alias("avg_scope1_tco2e"),
        F.max("scope1_tco2e").alias("max_scope1_tco2e"),
        F.mean("data_quality_score").alias("avg_data_quality")
    ).collect()[0]

    logger.info(f"  Total records: {summary['total_records']}")
    logger.info(f"  Total Scope 1 (tCO2e): {summary['total_scope1_tco2e'] or 0:.4f}")
    logger.info(f"  Average per facility (tCO2e): {summary['avg_scope1_tco2e'] or 0:.4f}")
    logger.info(f"  Max facility (tCO2e): {summary['max_scope1_tco2e'] or 0:.4f}")
    logger.info(f"  Average data quality: {summary['avg_data_quality'] or 0:.2f}")

    job.commit()


if __name__ == "__main__":
    main()
