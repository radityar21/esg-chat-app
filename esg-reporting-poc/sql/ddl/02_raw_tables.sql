-- =============================================================================
-- ESG Reporting POC — Raw Zone Tables
-- Spec Reference: §2.1-2.3, §4.2-4.3, REQ-DDL-04 to REQ-DDL-10
-- =============================================================================
-- Run each CREATE TABLE separately in Athena Query Editor
-- Workgroup: esg-reporting-workgroup
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Table: esg_raw.energy_consumption
-- Spec: §2.1, §4.3
-- Partition keys: reporting_year (INT), reporting_month (INT)
-- Location template: s3://bucket/raw/energy_consumption/reporting_year=${y}/reporting_month=${m}
-- ---------------------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS esg_raw.energy_consumption (
    facility_id             STRING  COMMENT 'Facility identifier. FK to facility_master. Format: FAC-NNNN.',
    electricity_kwh         DOUBLE  COMMENT 'Monthly electricity consumption. Unit: kWh. Constraint: >= 0 if present. Range: 1500-85000.',
    natural_gas_gj          DOUBLE  COMMENT 'Monthly natural gas consumption. Unit: GJ. Constraint: >= 0 if present. Range: 0-120.',
    diesel_liters           DOUBLE  COMMENT 'Monthly diesel consumption. Unit: liters. Constraint: >= 0 if present. Range: 0-3500.',
    srec_mwh_claimed        DOUBLE  COMMENT 'Renewable Energy Certificates claimed. Unit: MWh. Constraint: >= 0. Default: 0.',
    grid_ef_kgco2_kwh       DOUBLE  COMMENT 'Grid emission factor. Unit: kg CO2/kWh. Constraint: > 0. Default: 0.7886 (PLN 2023).',
    ef_source               STRING  COMMENT 'Emission factor source. ENUM: PLN_Grid_Average_2023, DEFRA_2025, IPCC_AR6_CH4_GWP100.',
    meter_reading_kwh       DOUBLE  COMMENT 'Raw meter reading for reconciliation. Unit: kWh. Constraint: within 0.5pct of electricity_kwh.',
    data_source             STRING  COMMENT 'Data provenance. ENUM: smart_meter_api, manual_entry, estimate.',
    record_status           STRING  COMMENT 'Record status. ENUM: complete, missing_primary, excluded. Excluded rows blocked from curated.'
)
PARTITIONED BY (
    reporting_year          INT     COMMENT 'Reporting fiscal year. Range: 2020-2035. Partition key.',
    reporting_month         INT     COMMENT 'Calendar month. Range: 1-12. Partition key.'
)
STORED AS PARQUET
LOCATION 's3://esg-data-raw-061039769766/raw/energy_consumption/'
TBLPROPERTIES (
    'projection.enabled'                    = 'true',
    'projection.reporting_year.type'        = 'integer',
    'projection.reporting_year.range'       = '2020,2035',
    'projection.reporting_month.type'       = 'integer',
    'projection.reporting_month.range'      = '1,12',
    'storage.location.template'             = 's3://esg-data-raw-061039769766/raw/energy_consumption/reporting_year=${reporting_year}/reporting_month=${reporting_month}',
    'parquet.compress'                      = 'SNAPPY',
    'classification'                        = 'parquet',
    'has_encrypted_data'                    = 'true'
);

-- ---------------------------------------------------------------------------
-- Table: esg_raw.loan_portfolio
-- Spec: §2.2, §4.3
-- Partition key: reporting_year (INT)
-- Location template: s3://bucket/raw/loan_portfolio/reporting_year=${y}
-- ---------------------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS esg_raw.loan_portfolio (
    loan_id                     STRING  COMMENT 'Unique loan identifier. PK. Format: LN-YYYY-NNNNNNN.',
    borrower_id                 STRING  COMMENT 'Borrower entity ID. FK to borrower_master. Format: BOR-NNNNNN.',
    sector_nace                 STRING  COMMENT 'NACE sector code. ENUM: manufacturing_cement, manufacturing_steel, manufacturing_food, real_estate_commercial, real_estate_residential, transportation_road, agriculture, energy_oil_gas, financial_services, retail_trade.',
    loan_type                   STRING  COMMENT 'Loan type. ENUM: term_loan, revolving_credit, mortgage, project_finance, syndicated_loan, leasing.',
    currency                    STRING  COMMENT 'ISO 4217 currency code. ENUM: IDR, USD.',
    outstanding_idr             BIGINT  COMMENT 'Outstanding loan amount. Unit: IDR. Constraint: > 0, <= enterprise value. Range: 500M-2T.',
    total_equity_idr            BIGINT  COMMENT 'Borrower total equity. Unit: IDR. Constraint: > 0. Range: 1B-50T.',
    total_debt_idr              BIGINT  COMMENT 'Borrower total debt. Unit: IDR. Constraint: >= 0. Range: 0-50T.',
    pcaf_attribution_factor     DOUBLE  COMMENT 'PCAF attribution factor. Unit: dimensionless. Constraint: 0 < x <= 1. Precision: 6 dp.',
    borrower_emissions_tco2e    DOUBLE  COMMENT 'Borrower Scope 1+2 emissions. Unit: tCO2e. Constraint: > 0. Range: 500-5000000.',
    pcaf_data_quality_score     DOUBLE  COMMENT 'PCAF data quality tier. ENUM: 1.0, 1.5, 2.0, 3.0, 4.0, 5.0.',
    record_status               STRING  COMMENT 'Validation status. ENUM: validated, pending, rejected. Only validated enters curated.'
)
PARTITIONED BY (
    reporting_year              INT     COMMENT 'Portfolio snapshot year. Range: 2020-2035. Partition key.'
)
STORED AS PARQUET
LOCATION 's3://esg-data-raw-061039769766/raw/loan_portfolio/'
TBLPROPERTIES (
    'projection.enabled'                    = 'true',
    'projection.reporting_year.type'        = 'integer',
    'projection.reporting_year.range'       = '2020,2035',
    'storage.location.template'             = 's3://esg-data-raw-061039769766/raw/loan_portfolio/reporting_year=${reporting_year}',
    'parquet.compress'                      = 'SNAPPY',
    'classification'                        = 'parquet',
    'has_encrypted_data'                    = 'true'
);

-- ---------------------------------------------------------------------------
-- Table: esg_raw.hr_metrics
-- Spec: §2.3, §4.3
-- Partition key: reporting_year (INT)
-- Location template: s3://bucket/raw/hr_metrics/reporting_year=${y}
-- ---------------------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS esg_raw.hr_metrics (
    period_date                 DATE    COMMENT 'Year-end snapshot date. Format: YYYY-12-31.',
    fte_total                   INT     COMMENT 'Total full-time equivalent headcount. Constraint: > 0. Range: 500-50000.',
    fte_female_pct              DOUBLE  COMMENT 'Female employee percentage. Unit: percent. Constraint: 0-100. Precision: 2 dp.',
    fte_management_female_pct   DOUBLE  COMMENT 'Women in management percentage. Unit: percent. Constraint: 0-100. Precision: 2 dp.',
    new_hire_count              INT     COMMENT 'New hires during year. Constraint: >= 0.',
    voluntary_turnover_pct      DOUBLE  COMMENT 'Voluntary attrition rate. Unit: percent. Constraint: 0-100. Precision: 2 dp.',
    training_hours_per_fte      DOUBLE  COMMENT 'Average training hours per FTE. Unit: hours. Constraint: >= 0. Range: 8-120.',
    discrimination_cases        INT     COMMENT 'Reported discrimination cases (GRI 406). Constraint: >= 0.'
)
PARTITIONED BY (
    reporting_year              INT     COMMENT 'Metrics reporting year. Range: 2020-2035. Partition key.'
)
STORED AS PARQUET
LOCATION 's3://esg-data-raw-061039769766/raw/hr_metrics/'
TBLPROPERTIES (
    'projection.enabled'                    = 'true',
    'projection.reporting_year.type'        = 'integer',
    'projection.reporting_year.range'       = '2020,2035',
    'storage.location.template'             = 's3://esg-data-raw-061039769766/raw/hr_metrics/reporting_year=${reporting_year}',
    'parquet.compress'                      = 'SNAPPY',
    'classification'                        = 'parquet',
    'has_encrypted_data'                    = 'true'
);
