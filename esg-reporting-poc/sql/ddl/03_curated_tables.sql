-- =============================================================================
-- ESG Reporting POC — Curated Zone Tables
-- Spec Reference: §2.4, §2.5, §3.2-3.4, §4.3, REQ-DDL-04 to REQ-DDL-10
-- =============================================================================
-- Run each CREATE TABLE separately in Athena Query Editor
-- Workgroup: esg-reporting-workgroup
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Table: esg_curated.ghg_scope1
-- Spec: §2.4, §3.2
-- One record per (facility_id, reporting_year)
-- Location: s3://bucket/curated/ghg_scope1/reporting_year=${y}
-- ---------------------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS esg_curated.ghg_scope1 (
    facility_id             STRING  COMMENT 'Facility identifier. FK to facility_master. Joins to facility_type, province.',
    scope1_tco2e            DOUBLE  COMMENT 'Total Scope 1 emissions. Unit: tCO2e. Constraint: >= 0. Precision: 4 dp. Formula: natgas + diesel.',
    scope1_natgas_tco2e     DOUBLE  COMMENT 'Scope 1 from natural gas. Unit: tCO2e. Constraint: >= 0. Precision: 4 dp.',
    scope1_diesel_tco2e     DOUBLE  COMMENT 'Scope 1 from diesel. Unit: tCO2e. Constraint: >= 0. Precision: 4 dp.',
    total_natgas_gj         DOUBLE  COMMENT 'Annual natural gas consumed. Unit: GJ. Constraint: >= 0.',
    total_diesel_liters     DOUBLE  COMMENT 'Annual diesel consumed. Unit: liters. Constraint: >= 0.',
    imputed_months          INT     COMMENT 'Count of imputed months. Constraint: 0-12. Drives data_quality_score.',
    data_quality_score      INT     COMMENT 'Quality score. ENUM: 1(0 imputed), 2(1-2), 3(3-5), 4(6+ excluded).',
    emission_factor_source  STRING  COMMENT 'EF source reference. Must match raw zone ef_source.',
    methodology             STRING  COMMENT 'Fixed: GHG_Protocol_Corporate_Standard_v2015.',
    consolidation_approach  STRING  COMMENT 'ENUM: operational_control, equity_share. Default: operational_control.'
)
PARTITIONED BY (
    reporting_year          INT     COMMENT 'Emission reporting year. Range: 2020-2035. Partition key.'
)
STORED AS PARQUET
LOCATION 's3://esg-data-curated-061039769766/curated/ghg_scope1/'
TBLPROPERTIES (
    'projection.enabled'                    = 'true',
    'projection.reporting_year.type'        = 'integer',
    'projection.reporting_year.range'       = '2020,2035',
    'storage.location.template'             = 's3://esg-data-curated-061039769766/curated/ghg_scope1/reporting_year=${reporting_year}',
    'parquet.compress'                      = 'SNAPPY',
    'classification'                        = 'parquet',
    'has_encrypted_data'                    = 'true'
);

-- ---------------------------------------------------------------------------
-- Table: esg_curated.ghg_scope2
-- Spec: §3.3
-- One record per (facility_id, reporting_year)
-- Location: s3://bucket/curated/ghg_scope2/reporting_year=${y}
-- ---------------------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS esg_curated.ghg_scope2 (
    facility_id             STRING  COMMENT 'Facility identifier. FK to facility_master.',
    total_consumption_mwh   DOUBLE  COMMENT 'Annual electricity consumed. Unit: MWh. Formula: SUM(electricity_kwh)/1000.',
    scope2_location_tco2e   DOUBLE  COMMENT 'Location-based Scope 2. Unit: tCO2e. Precision: 3 dp. Always computed.',
    scope2_market_tco2e     DOUBLE  COMMENT 'Market-based Scope 2. Unit: tCO2e. Precision: 3 dp. Floored at 0.',
    grid_region             STRING  COMMENT 'Grid region used for EF selection. ENUM: java_bali, sumatra, kalimantan, sulawesi, national.',
    grid_ef_applied         DOUBLE  COMMENT 'Grid EF applied. Unit: kg CO2/kWh. From region mapping.',
    rec_mwh_applied         DOUBLE  COMMENT 'REC MWh deducted from market-based. Constraint: <= total_consumption_mwh.',
    rec_applied_pct         DOUBLE  COMMENT 'REC coverage percentage. Unit: percent. Formula: rec_mwh/total_mwh x 100.',
    has_ppa                 BOOLEAN COMMENT 'Power Purchase Agreement flag.',
    data_quality_score      INT     COMMENT 'Quality score 1-4.',
    methodology             STRING  COMMENT 'Fixed: GHG_Protocol_Scope2_Guidance_2015.'
)
PARTITIONED BY (
    reporting_year          INT     COMMENT 'Emission reporting year. Range: 2020-2035. Partition key.'
)
STORED AS PARQUET
LOCATION 's3://esg-data-curated-061039769766/curated/ghg_scope2/'
TBLPROPERTIES (
    'projection.enabled'                    = 'true',
    'projection.reporting_year.type'        = 'integer',
    'projection.reporting_year.range'       = '2020,2035',
    'storage.location.template'             = 's3://esg-data-curated-061039769766/curated/ghg_scope2/reporting_year=${reporting_year}',
    'parquet.compress'                      = 'SNAPPY',
    'classification'                        = 'parquet',
    'has_encrypted_data'                    = 'true'
);

-- ---------------------------------------------------------------------------
-- Table: esg_curated.ghg_scope3_financed
-- Spec: §2.5, §3.4
-- One record per (sector_nace, reporting_year)
-- Location: s3://bucket/curated/ghg_scope3_financed/reporting_year=${y}
-- ---------------------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS esg_curated.ghg_scope3_financed (
    sector_nace                         STRING  COMMENT 'NACE sector code. PK component. One of 10 allowed values.',
    loan_count                          INT     COMMENT 'Count of validated loans in sector. Constraint: > 0.',
    borrower_count                      INT     COMMENT 'Count distinct borrowers. Constraint: > 0.',
    total_outstanding_idr_trillion      DOUBLE  COMMENT 'Total outstanding. Unit: IDR trillion. Precision: 6 dp.',
    financed_emissions_gross_tco2e      DOUBLE  COMMENT 'Gross financed emissions. Unit: tCO2e. Precision: 2 dp.',
    financed_emissions_weighted_tco2e   DOUBLE  COMMENT 'Confidence-weighted emissions. Unit: tCO2e. Precision: 2 dp. Must be <= gross.',
    avg_pcaf_score                      DOUBLE  COMMENT 'Average PCAF quality. Constraint: 1.0-5.0. Precision: 2 dp.',
    high_quality_data_pct               DOUBLE  COMMENT 'Pct loans with PCAF score 1-2. Unit: percent. Precision: 4 dp.'
)
PARTITIONED BY (
    reporting_year                      INT     COMMENT 'Emission reporting year. Range: 2020-2035. Partition key.'
)
STORED AS PARQUET
LOCATION 's3://esg-data-curated-061039769766/curated/ghg_scope3_financed/'
TBLPROPERTIES (
    'projection.enabled'                    = 'true',
    'projection.reporting_year.type'        = 'integer',
    'projection.reporting_year.range'       = '2020,2035',
    'storage.location.template'             = 's3://esg-data-curated-061039769766/curated/ghg_scope3_financed/reporting_year=${reporting_year}',
    'parquet.compress'                      = 'SNAPPY',
    'classification'                        = 'parquet',
    'has_encrypted_data'                    = 'true'
);
