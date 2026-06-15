-- =============================================================================
-- ESG Reporting POC — Database Creation (REQ-DDL-01, REQ-DDL-02, REQ-DDL-03)
-- =============================================================================
-- Run each statement separately in Athena Query Editor
-- Replace ${BUCKET} with: esg-data-raw-061039769766
-- =============================================================================

CREATE DATABASE IF NOT EXISTS esg_raw
COMMENT 'ESG Raw Zone - Source data as ingested from ERP, utilities, and banking systems'
LOCATION 's3://esg-data-raw-061039769766/'
WITH DBPROPERTIES (
    'creator' = 'esg-reporting-poc',
    'environment' = 'poc',
    'managed_by' = 'kiro-generated'
);

CREATE DATABASE IF NOT EXISTS esg_curated
COMMENT 'ESG Curated Zone - ETL-computed GHG emissions per facility and sector'
LOCATION 's3://esg-data-curated-061039769766/'
WITH DBPROPERTIES (
    'creator' = 'esg-reporting-poc',
    'environment' = 'poc',
    'managed_by' = 'kiro-generated'
);

CREATE DATABASE IF NOT EXISTS esg_aggregated
COMMENT 'ESG Aggregated Zone - Report-ready annual metrics; AgentCore reads ONLY from this zone'
LOCATION 's3://esg-data-aggregated-061039769766/'
WITH DBPROPERTIES (
    'creator' = 'esg-reporting-poc',
    'environment' = 'poc',
    'managed_by' = 'kiro-generated'
);
