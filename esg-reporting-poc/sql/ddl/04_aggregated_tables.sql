-- =============================================================================
-- ESG Reporting POC — Aggregated Zone Tables
-- Spec Reference: §2.6, §3.5, §4.3, REQ-DDL-04 to REQ-DDL-10
-- =============================================================================
-- Run each CREATE TABLE separately in Athena Query Editor
-- Workgroup: esg-reporting-workgroup
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Table: esg_aggregated.ghg_summary_annual
-- Spec: §2.6, §3.5
-- One record per (bank_id, reporting_year)
-- SINGLE SOURCE OF TRUTH for AgentCore (REQ-ETL-33)
-- Location: s3://bucket/aggregated/ghg_summary_annual/reporting_year=${y}
-- ---------------------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS esg_aggregated.ghg_summary_annual (
    metric_key                  STRING  COMMENT 'Composite PK: {bank_id}_{reporting_year}. Unique per record.',
    scope1_tco2e                DOUBLE  COMMENT 'Total Scope 1. Unit: tCO2e. Precision: 3 dp. SUM across all facilities.',
    scope1_natgas_tco2e         DOUBLE  COMMENT 'Scope 1 from natural gas. Unit: tCO2e. Precision: 4 dp. SUM across all facilities.',
    scope1_diesel_tco2e         DOUBLE  COMMENT 'Scope 1 from diesel. Unit: tCO2e. Precision: 4 dp. SUM across all facilities.',
    scope2_location_tco2e       DOUBLE  COMMENT 'Total Scope 2 location-based. Unit: tCO2e. Precision: 3 dp.',
    scope2_market_tco2e         DOUBLE  COMMENT 'Total Scope 2 market-based. Unit: tCO2e. Precision: 3 dp. Can be 0.',
    scope3_cat15_gross_tco2e    DOUBLE  COMMENT 'Scope 3 Cat.15 gross financed emissions. Unit: tCO2e. Precision: 2 dp.',
    scope3_cat15_weighted_tco2e DOUBLE  COMMENT 'Scope 3 Cat.15 confidence-weighted emissions. Unit: tCO2e. Precision: 2 dp.',
    intensity_tco2e_per_idr_bn  DOUBLE  COMMENT 'Emission intensity per revenue. Unit: tCO2e/IDR bn. Precision: 6 dp.',
    intensity_tco2e_per_fte     DOUBLE  COMMENT 'Emission intensity per FTE. Unit: tCO2e/FTE. Precision: 4 dp. Scope 1+2 only.',
    yoy_change_pct              DOUBLE  COMMENT 'Year-over-year change. Unit: percent. Precision: 2 dp. NULL for base year.',
    vs_base_year_change_pct     DOUBLE  COMMENT 'Change vs base year. Unit: percent. Precision: 2 dp. NULL for base year.',
    avg_pcaf_data_quality       DOUBLE  COMMENT 'Portfolio-weighted PCAF score. Constraint: 1.0-5.0.',
    assurance_level             STRING  COMMENT 'ENUM: none, limited, reasonable. Default: none.'
)
PARTITIONED BY (
    reporting_year              INT     COMMENT 'Reporting year. Range: 2020-2035. Partition key.'
)
STORED AS PARQUET
LOCATION 's3://esg-data-aggregated-061039769766/aggregated/ghg_summary_annual/'
TBLPROPERTIES (
    'projection.enabled'                    = 'true',
    'projection.reporting_year.type'        = 'integer',
    'projection.reporting_year.range'       = '2020,2035',
    'storage.location.template'             = 's3://esg-data-aggregated-061039769766/aggregated/ghg_summary_annual/reporting_year=${reporting_year}',
    'parquet.compress'                      = 'SNAPPY',
    'classification'                        = 'parquet',
    'has_encrypted_data'                    = 'true'
);

-- ---------------------------------------------------------------------------
-- Table: esg_aggregated.pcaf_by_sector
-- Spec: §4.3
-- One record per (sector_nace, reporting_year)
-- Location: s3://bucket/aggregated/pcaf_by_sector/reporting_year=${y}
-- ---------------------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS esg_aggregated.pcaf_by_sector (
    sector_nace                         STRING  COMMENT 'NACE sector code. PK component.',
    sector_display_name                 STRING  COMMENT 'Human-readable sector name.',
    loan_count                          INT     COMMENT 'Loans in sector. Constraint: > 0.',
    borrower_count                      INT     COMMENT 'Distinct borrowers. Constraint: > 0.',
    total_outstanding_idr_trillion      DOUBLE  COMMENT 'Sector outstanding. Unit: IDR trillion. Precision: 6 dp.',
    financed_emissions_gross_tco2e      DOUBLE  COMMENT 'Sector gross financed emissions. Unit: tCO2e. Precision: 2 dp.',
    financed_emissions_weighted_tco2e   DOUBLE  COMMENT 'Sector weighted emissions. Unit: tCO2e. Precision: 2 dp.',
    emission_intensity_per_idr_bn       DOUBLE  COMMENT 'Sector intensity. Unit: tCO2e/IDR bn. Precision: 4 dp.',
    avg_pcaf_score                      DOUBLE  COMMENT 'Sector avg PCAF quality. Constraint: 1.0-5.0.',
    pct_of_total_portfolio              DOUBLE  COMMENT 'Sector share of total outstanding. Unit: percent. Precision: 2 dp.',
    pct_of_total_financed_emissions     DOUBLE  COMMENT 'Sector share of total financed emissions. Unit: percent. Precision: 2 dp.',
    yoy_change_emissions_pct            DOUBLE  COMMENT 'YoY change in sector financed emissions. Unit: percent. Precision: 2 dp.'
)
PARTITIONED BY (
    reporting_year                      INT     COMMENT 'Reporting year. Range: 2020-2035. Partition key.'
)
STORED AS PARQUET
LOCATION 's3://esg-data-aggregated-061039769766/aggregated/pcaf_by_sector/'
TBLPROPERTIES (
    'projection.enabled'                    = 'true',
    'projection.reporting_year.type'        = 'integer',
    'projection.reporting_year.range'       = '2020,2035',
    'storage.location.template'             = 's3://esg-data-aggregated-061039769766/aggregated/pcaf_by_sector/reporting_year=${reporting_year}',
    'parquet.compress'                      = 'SNAPPY',
    'classification'                        = 'parquet',
    'has_encrypted_data'                    = 'true'
);


-- ---------------------------------------------------------------------------
-- Table: esg_aggregated.scope1_by_facility
-- Top 10 emitting facilities per year (for per-facility breakdown in report)
-- Location: s3://bucket/aggregated/scope1_by_facility/reporting_year=${y}
-- ---------------------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS esg_aggregated.scope1_by_facility (
    facility_id             STRING  COMMENT 'Facility identifier.',
    scope1_tco2e            DOUBLE  COMMENT 'Facility total Scope 1. Unit: tCO2e. Precision: 4 dp.',
    scope1_natgas_tco2e     DOUBLE  COMMENT 'Facility Scope 1 from natural gas. Unit: tCO2e. Precision: 4 dp.',
    scope1_diesel_tco2e     DOUBLE  COMMENT 'Facility Scope 1 from diesel. Unit: tCO2e. Precision: 4 dp.',
    total_natgas_gj         DOUBLE  COMMENT 'Annual natural gas consumed. Unit: GJ.',
    total_diesel_liters     DOUBLE  COMMENT 'Annual diesel consumed. Unit: liters.',
    data_quality_score      INT     COMMENT 'Quality score 1-4.'
)
PARTITIONED BY (
    reporting_year          INT     COMMENT 'Reporting year. Range: 2020-2035. Partition key.'
)
STORED AS PARQUET
LOCATION 's3://esg-data-aggregated-061039769766/aggregated/scope1_by_facility/'
TBLPROPERTIES (
    'projection.enabled'                    = 'true',
    'projection.reporting_year.type'        = 'integer',
    'projection.reporting_year.range'       = '2020,2035',
    'storage.location.template'             = 's3://esg-data-aggregated-061039769766/aggregated/scope1_by_facility/reporting_year=${reporting_year}',
    'parquet.compress'                      = 'SNAPPY',
    'classification'                        = 'parquet',
    'has_encrypted_data'                    = 'true'
);
