-- Source database schema (PostgreSQL). Mirrors the raw zone tables (sql/ddl/02_raw_tables.sql, 05_scope3_operational.sql).
-- Applied by the esg-rds-seed Lambda with the master user. Re-runnable.
CREATE SCHEMA IF NOT EXISTS esg;

CREATE TABLE IF NOT EXISTS esg.energy_consumption (
    facility_id TEXT NOT NULL, electricity_kwh DOUBLE PRECISION, natural_gas_gj DOUBLE PRECISION, diesel_liters DOUBLE PRECISION,
    srec_mwh_claimed DOUBLE PRECISION, grid_ef_kgco2_kwh DOUBLE PRECISION, ef_source TEXT, meter_reading_kwh DOUBLE PRECISION,
    data_source TEXT, record_status TEXT NOT NULL, reporting_year INTEGER NOT NULL, reporting_month INTEGER NOT NULL,
    PRIMARY KEY (reporting_year, reporting_month, facility_id));

CREATE TABLE IF NOT EXISTS esg.loan_portfolio (
    loan_id TEXT NOT NULL, borrower_id TEXT NOT NULL, sector_nace TEXT NOT NULL, loan_type TEXT, currency TEXT,
    outstanding_idr BIGINT NOT NULL, total_equity_idr BIGINT, total_debt_idr BIGINT, pcaf_attribution_factor DOUBLE PRECISION,
    borrower_emissions_tco2e DOUBLE PRECISION, pcaf_data_quality_score DOUBLE PRECISION, record_status TEXT NOT NULL,
    reporting_year INTEGER NOT NULL, PRIMARY KEY (reporting_year, loan_id));

CREATE TABLE IF NOT EXISTS esg.hr_metrics (
    period_date DATE NOT NULL, fte_total INTEGER NOT NULL, fte_female_pct DOUBLE PRECISION, fte_management_female_pct DOUBLE PRECISION,
    new_hire_count INTEGER, voluntary_turnover_pct DOUBLE PRECISION, training_hours_per_fte DOUBLE PRECISION, discrimination_cases INTEGER,
    reporting_year INTEGER NOT NULL PRIMARY KEY);

CREATE TABLE IF NOT EXISTS esg.scope3_operational_activity (
    category TEXT NOT NULL, activity TEXT NOT NULL, unit TEXT, quantity DOUBLE PRECISION, ef_kgco2e_per_unit DOUBLE PRECISION,
    emissions_tco2e DOUBLE PRECISION, method TEXT, ef_source TEXT, data_quality_score INTEGER, reporting_year INTEGER NOT NULL,
    PRIMARY KEY (reporting_year, category, activity));

-- Group data (scripts/generate_group_data.py): organisational boundary, emission factor library, activity data, ESG metrics.
CREATE TABLE IF NOT EXISTS esg.entity (
    entity_id TEXT NOT NULL, entity_name TEXT NOT NULL, entity_type TEXT NOT NULL, parent_entity_id TEXT,
    ownership_pct DOUBLE PRECISION NOT NULL, operational_control BOOLEAN NOT NULL, country TEXT, consolidation_note TEXT,
    reporting_year INTEGER NOT NULL, PRIMARY KEY (reporting_year, entity_id));

CREATE TABLE IF NOT EXISTS esg.facility (
    facility_id TEXT NOT NULL, entity_id TEXT NOT NULL, facility_name TEXT, facility_type TEXT NOT NULL, grid_region TEXT NOT NULL,
    province TEXT, city TEXT, floor_area_m2 DOUBLE PRECISION, headcount INTEGER, ownership_type TEXT, opened_year INTEGER, status TEXT,
    reporting_year INTEGER NOT NULL, PRIMARY KEY (reporting_year, facility_id));

CREATE TABLE IF NOT EXISTS esg.emission_factor (
    ef_set TEXT NOT NULL, activity_type TEXT NOT NULL, region TEXT NOT NULL, unit TEXT NOT NULL, scope INTEGER NOT NULL, category TEXT NOT NULL,
    co2_kg DOUBLE PRECISION NOT NULL, ch4_kg DOUBLE PRECISION NOT NULL, n2o_kg DOUBLE PRECISION NOT NULL, co2e_kg DOUBLE PRECISION NOT NULL,
    gwp_ch4 DOUBLE PRECISION NOT NULL, gwp_n2o DOUBLE PRECISION NOT NULL, gwp_basis TEXT, source TEXT, notes TEXT,
    reporting_year INTEGER NOT NULL, PRIMARY KEY (reporting_year, ef_set, activity_type, region));

CREATE TABLE IF NOT EXISTS esg.activity_data (
    activity_id TEXT NOT NULL, facility_id TEXT NOT NULL, entity_id TEXT NOT NULL, activity_type TEXT NOT NULL, quantity DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL, instrument_qty DOUBLE PRECISION, data_source TEXT, is_estimated BOOLEAN NOT NULL, evidence_ref TEXT,
    reporting_year INTEGER NOT NULL, reporting_month INTEGER NOT NULL, PRIMARY KEY (reporting_year, activity_id));

CREATE TABLE IF NOT EXISTS esg.esg_metric (
    entity_id TEXT NOT NULL, pillar TEXT NOT NULL, topic TEXT NOT NULL, metric TEXT NOT NULL, dimension TEXT NOT NULL, value DOUBLE PRECISION NOT NULL,
    unit TEXT, data_source TEXT, standard_ref TEXT, reporting_year INTEGER NOT NULL,
    PRIMARY KEY (reporting_year, entity_id, metric, dimension))
