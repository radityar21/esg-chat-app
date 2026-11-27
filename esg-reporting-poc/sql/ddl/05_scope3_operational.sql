-- =============================================================================
-- ESG Reporting POC: operational Scope 3 (GHG Protocol categories 1-7), raw zone
-- Run in Athena (workgroup esg-reporting-workgroup). Replace the account id if different.
-- Source: scripts/generate_scope3_operational.py -> upload to
--   s3://esg-data-raw-061039769766/raw/scope3_operational_activity/reporting_year=YYYY/
-- =============================================================================
CREATE EXTERNAL TABLE IF NOT EXISTS esg_raw.scope3_operational_activity (
    category            STRING  COMMENT 'GHG Protocol category key: c1..c7',
    activity            STRING  COMMENT 'Activity description',
    unit                STRING  COMMENT 'Activity unit (IDR million, MWh, tonne-km, ...)',
    quantity            DOUBLE  COMMENT 'Activity quantity in the stated unit',
    ef_kgco2e_per_unit  DOUBLE  COMMENT 'Emission factor, kg CO2e per unit',
    emissions_tco2e     DOUBLE  COMMENT 'quantity x factor / 1000',
    method              STRING  COMMENT 'spend-based | average-data | distance-based | waste-type-specific',
    ef_source           STRING  COMMENT 'Emission factor source',
    data_quality_score  INT     COMMENT 'Data quality 1 (best) - 5 (worst)'
)
PARTITIONED BY (reporting_year INT)
STORED AS PARQUET
LOCATION 's3://esg-data-raw-061039769766/raw/scope3_operational_activity/'
TBLPROPERTIES (
    'projection.enabled'                 = 'true',
    'projection.reporting_year.type'     = 'integer',
    'projection.reporting_year.range'    = '2020,2035',
    'storage.location.template'          = 's3://esg-data-raw-061039769766/raw/scope3_operational_activity/reporting_year=${reporting_year}',
    'parquet.compress'                   = 'SNAPPY'
);
