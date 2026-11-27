-- =============================================================================
-- ESG Reporting: group data (raw zone) and the GHG activity ledger (curated view)
-- Source: RDS schema esg (lambda/rds_seed/schema.sql), extracted by the esg-extract-rds Glue job with the data
-- contracts in glue_jobs/esg_contracts.py, written to s3://esg-data-raw-061039769766/raw/<table>/reporting_year=YYYY/
-- Applied by scripts/apply_ddl.py. Replace the account id if different.
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS esg_raw.entity (
    entity_id           STRING  COMMENT 'Legal entity id (ENT-...)',
    entity_name         STRING  COMMENT 'Legal entity name',
    entity_type         STRING  COMMENT 'bank | sharia_bank | multifinance | securities | insurance',
    parent_entity_id    STRING  COMMENT 'Parent entity id, empty for the parent',
    ownership_pct       DOUBLE  COMMENT 'Equity share held by the group, percent',
    operational_control BOOLEAN COMMENT 'True when the group has operational control (GHG Protocol chapter 3)',
    country             STRING  COMMENT 'ISO country code',
    consolidation_note  STRING  COMMENT 'How the entity is consolidated'
)
PARTITIONED BY (reporting_year INT)
STORED AS PARQUET
LOCATION 's3://esg-data-raw-061039769766/raw/entity/'
TBLPROPERTIES (
    'projection.enabled'              = 'true',
    'projection.reporting_year.type'  = 'integer',
    'projection.reporting_year.range' = '2020,2035',
    'storage.location.template'       = 's3://esg-data-raw-061039769766/raw/entity/reporting_year=${reporting_year}',
    'parquet.compress'                = 'SNAPPY'
);

CREATE EXTERNAL TABLE IF NOT EXISTS esg_raw.facility (
    facility_id     STRING  COMMENT 'Facility id',
    entity_id       STRING  COMMENT 'Owning legal entity',
    facility_name   STRING  COMMENT 'Display name',
    facility_type   STRING  COMMENT 'headquarters | regional_office | data_centre | branch | warehouse',
    grid_region     STRING  COMMENT 'Electricity system: java_bali | sumatra | kalimantan | sulawesi | nusa_tenggara | papua_maluku',
    province        STRING  COMMENT 'Province',
    city            STRING  COMMENT 'City',
    floor_area_m2   DOUBLE  COMMENT 'Gross floor area, m2',
    headcount       INT     COMMENT 'People based at the facility at year end',
    ownership_type  STRING  COMMENT 'owned | leased',
    opened_year     INT     COMMENT 'Year the facility opened',
    status          STRING  COMMENT 'active | opened | closed (in the reporting year)'
)
PARTITIONED BY (reporting_year INT)
STORED AS PARQUET
LOCATION 's3://esg-data-raw-061039769766/raw/facility/'
TBLPROPERTIES (
    'projection.enabled'              = 'true',
    'projection.reporting_year.type'  = 'integer',
    'projection.reporting_year.range' = '2020,2035',
    'storage.location.template'       = 's3://esg-data-raw-061039769766/raw/facility/reporting_year=${reporting_year}',
    'parquet.compress'                = 'SNAPPY'
);

CREATE EXTERNAL TABLE IF NOT EXISTS esg_raw.emission_factor (
    ef_set          STRING  COMMENT 'Factor set: ID_NATIONAL (reported basis) | ID_REGIONAL',
    activity_type   STRING  COMMENT 'Activity the factor applies to',
    region          STRING  COMMENT 'Grid region or all',
    unit            STRING  COMMENT 'Activity unit the factor is expressed per',
    scope           INT     COMMENT 'GHG Protocol scope 1 | 2 | 3',
    category        STRING  COMMENT 'Scope category (s1_stationary, s2_electricity, c6_business_travel, ...)',
    co2_kg          DOUBLE  COMMENT 'kg CO2 per unit',
    ch4_kg          DOUBLE  COMMENT 'kg CH4 per unit',
    n2o_kg          DOUBLE  COMMENT 'kg N2O per unit',
    co2e_kg         DOUBLE  COMMENT 'kg CO2e per unit given directly (refrigerants, Scope 3 factors)',
    gwp_ch4         DOUBLE  COMMENT 'GWP100 of CH4',
    gwp_n2o         DOUBLE  COMMENT 'GWP100 of N2O',
    gwp_basis       STRING  COMMENT 'GWP source',
    source          STRING  COMMENT 'Factor source',
    notes           STRING  COMMENT 'Notes'
)
PARTITIONED BY (reporting_year INT)
STORED AS PARQUET
LOCATION 's3://esg-data-raw-061039769766/raw/emission_factor/'
TBLPROPERTIES (
    'projection.enabled'              = 'true',
    'projection.reporting_year.type'  = 'integer',
    'projection.reporting_year.range' = '2020,2035',
    'storage.location.template'       = 's3://esg-data-raw-061039769766/raw/emission_factor/reporting_year=${reporting_year}',
    'parquet.compress'                = 'SNAPPY'
);

CREATE EXTERNAL TABLE IF NOT EXISTS esg_raw.activity_data (
    activity_id     STRING  COMMENT 'Activity record id',
    facility_id     STRING  COMMENT 'Facility',
    entity_id       STRING  COMMENT 'Legal entity',
    activity_type   STRING  COMMENT 'electricity_grid, natural_gas, gasoline_fleet, water_supply, waste_landfill, ...',
    quantity        DOUBLE  COMMENT 'Quantity in unit',
    unit            STRING  COMMENT 'kWh, GJ, litre, kg, m3, ream, passenger-km, room-night, km',
    instrument_qty  DOUBLE  COMMENT 'Electricity covered by certificates (REC), kWh. Market-based Scope 2 only',
    data_source     STRING  COMMENT 'smart_meter, invoice, fuel_card, estimate, employee_survey, ...',
    is_estimated    BOOLEAN COMMENT 'True when the quantity is an estimate',
    evidence_ref    STRING  COMMENT 'Reference to the supporting document',
    reporting_month INT     COMMENT 'Month 1-12'
)
PARTITIONED BY (reporting_year INT)
STORED AS PARQUET
LOCATION 's3://esg-data-raw-061039769766/raw/activity_data/'
TBLPROPERTIES (
    'projection.enabled'              = 'true',
    'projection.reporting_year.type'  = 'integer',
    'projection.reporting_year.range' = '2020,2035',
    'storage.location.template'       = 's3://esg-data-raw-061039769766/raw/activity_data/reporting_year=${reporting_year}',
    'parquet.compress'                = 'SNAPPY'
);

CREATE EXTERNAL TABLE IF NOT EXISTS esg_raw.esg_metric (
    entity_id       STRING  COMMENT 'Legal entity',
    pillar          STRING  COMMENT 'social | governance | finance',
    topic           STRING  COMMENT 'Topic within the pillar',
    metric          STRING  COMMENT 'Metric id (see lambda/_shared/esg_metric_catalog.py)',
    dimension       STRING  COMMENT 'total, or a breakdown (female, renewable_energy, a sector, ...)',
    value           DOUBLE  COMMENT 'Value in unit',
    unit            STRING  COMMENT 'Unit',
    data_source     STRING  COMMENT 'System of record',
    standard_ref    STRING  COMMENT 'Disclosure reference (GRI, POJK 51, PCAF, ...)'
)
PARTITIONED BY (reporting_year INT)
STORED AS PARQUET
LOCATION 's3://esg-data-raw-061039769766/raw/esg_metric/'
TBLPROPERTIES (
    'projection.enabled'              = 'true',
    'projection.reporting_year.type'  = 'integer',
    'projection.reporting_year.range' = '2020,2035',
    'storage.location.template'       = 's3://esg-data-raw-061039769766/raw/esg_metric/reporting_year=${reporting_year}',
    'parquet.compress'                = 'SNAPPY'
);

-- GHG activity ledger: every activity record x its emission factor, for every factor set. Recalculation with another
-- factor set needs no reload: filter on ef_set. Records without a factor keep ef_set NULL (reported as a data alert).
-- Market-based Scope 2 deducts certificate-covered electricity (instrument_qty) before applying the factor.
CREATE OR REPLACE VIEW esg_curated.ghg_ledger AS
SELECT
    a.reporting_year, a.reporting_month, a.activity_id, a.entity_id, a.facility_id,
    f.facility_name, f.facility_type, f.grid_region, f.province, f.floor_area_m2, f.headcount,
    e.entity_name, e.ownership_pct, e.operational_control,
    a.activity_type, a.quantity, a.unit, a.instrument_qty, a.data_source, a.is_estimated, a.evidence_ref,
    ef.ef_set, ef.scope, ef.category, ef.unit AS ef_unit, ef.source AS ef_source, ef.gwp_basis,
    ef.co2_kg + ef.ch4_kg * ef.gwp_ch4 + ef.n2o_kg * ef.gwp_n2o + ef.co2e_kg AS factor_kgco2e,
    a.quantity * (ef.co2_kg + ef.ch4_kg * ef.gwp_ch4 + ef.n2o_kg * ef.gwp_n2o + ef.co2e_kg) / 1000.0 AS tco2e,
    CASE WHEN ef.scope = 2
         THEN greatest(a.quantity - coalesce(a.instrument_qty, 0.0), 0.0) * (ef.co2_kg + ef.ch4_kg * ef.gwp_ch4 + ef.n2o_kg * ef.gwp_n2o + ef.co2e_kg) / 1000.0
         ELSE a.quantity * (ef.co2_kg + ef.ch4_kg * ef.gwp_ch4 + ef.n2o_kg * ef.gwp_n2o + ef.co2e_kg) / 1000.0
    END AS tco2e_market
FROM esg_raw.activity_data a
JOIN esg_raw.facility f ON f.facility_id = a.facility_id AND f.reporting_year = a.reporting_year
JOIN esg_raw.entity e ON e.entity_id = a.entity_id AND e.reporting_year = a.reporting_year
LEFT JOIN esg_raw.emission_factor ef
    ON ef.activity_type = a.activity_type AND ef.reporting_year = a.reporting_year AND (ef.region = f.grid_region OR ef.region = 'all');
