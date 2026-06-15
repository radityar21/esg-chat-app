-- =============================================================================
-- ESG Reporting POC — Drop All Tables (run before re-creating)
-- =============================================================================
-- Run EACH statement separately in Athena (1 per execution)
-- =============================================================================

-- Raw zone
DROP TABLE IF EXISTS esg_raw.energy_consumption;

DROP TABLE IF EXISTS esg_raw.loan_portfolio;

DROP TABLE IF EXISTS esg_raw.hr_metrics;

-- Curated zone
DROP TABLE IF EXISTS esg_curated.ghg_scope1;

DROP TABLE IF EXISTS esg_curated.ghg_scope2;

DROP TABLE IF EXISTS esg_curated.ghg_scope3_financed;

-- Aggregated zone
DROP TABLE IF EXISTS esg_aggregated.ghg_summary_annual;

DROP TABLE IF EXISTS esg_aggregated.pcaf_by_sector;
