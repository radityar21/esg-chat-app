1. Purpose, Scope, and Document Conventions
This document is the authoritative specification that Kiro IDE shall consume to generate all implementation artefacts for the AI-Powered ESG Reporting System. Every section below is written as a requirement, rule, or constraint — not as executable code. Kiro IDE is expected to produce code, configurations, and infrastructure definitions that satisfy every numbered requirement (REQ-*) in this document.
This document is aligned with two companion documents: (1) AI-Powered ESG Reporting Architecture v1.0 (data schema, architecture diagram, five-layer pipeline overview) and (2) AI-Powered ESG Reporting Technical Specification v1.0 (complete implementation code reference). Any conflict between this specification and a companion document shall be resolved in favour of this specification.
1.1 Requirement Notation
Each requirement is tagged with a unique identifier and a keyword:
Tag	Keyword	Meaning
REQ-	MUST	Mandatory — non-compliance constitutes a system defect.
CON-	MUST NOT	Prohibited — implementation is explicitly forbidden.
REC-	SHOULD	Recommended — deviation requires documented justification.
OPT-	MAY	Optional — included for guidance; implementation at discretion.
1.2 System Boundary
The system boundary encompasses: (a) a three-zone S3 data lake (raw, curated, aggregated), (b) AWS Glue ETL jobs for GHG calculation, (c) Amazon Athena as the SQL query layer, (d) Amazon Bedrock AgentCore as the orchestration runtime, (e) Amazon Bedrock Knowledge Base for RAG, (f) AWS Step Functions for workflow orchestration, (g) AWS Lambda for compute, and (h) a DOCX assembly layer using python-docx. All LLM invocations use Amazon Bedrock with Claude 3.5 Sonnet as the foundation model.
The system boundary explicitly excludes: user interfaces, authentication/authorisation beyond IAM, data archiving beyond 90-day retention, and production report publication workflows.
 
2. Data Schema Specifications
This section specifies all table schemas that the ETL pipeline MUST produce and the agent MUST consume. Each schema definition states column name, data type, unit of measure, nullability, value range, and inter-table relationships. These specifications constitute the Data Contract between the ETL layer and the AgentCore agent.
2.1 Raw Zone — Table: esg_raw.energy_consumption
Partition key: reporting_year (INT). Ingested as-is from source systems. Null values preserved. Schema enforced on read via Athena. Governed by the following column specifications:
Column Name	Type	Nullable	Constraints	Value Range / Notes
facility_id	STRING	NO	FK to facility_master	Format: FAC-NNNN (4-digit zero-padded integer)
reporting_year	INT	NO	PARTITION KEY	Range: 2020–2035 inclusive
reporting_month	INT	NO	CHECK 1–12	Calendar month; 1 = January, 12 = December
electricity_kwh	DOUBLE	YES	>=0 if present	1,500–85,000 kWh/month per facility; HQ up to 85,000
natural_gas_gj	DOUBLE	YES	>=0 if present	0.0–120.0 GJ/month; 0 if facility has no gas connection
diesel_liters	DOUBLE	YES	>=0 if present	0.0–3,500 L/month; non-zero only for HQ, data centres, regionals
rec_mwh_claimed	DOUBLE	NO	>=0	Renewable energy certificates claimed (MWh); 0 if not applicable
grid_ef_kgco2_kwh	DOUBLE	NO	>0	PLN 2023 national grid: 0.7886 kg CO2/kWh; must match ef_source value
ef_source	STRING	NO	ENUM	Allowed: PLN_Grid_Average_2023 | DEFRA_2025 | IPCC_AR6_CH4_GWP100
meter_reading_kwh	DOUBLE	YES	>=0 if present	Raw meter reading for reconciliation; tolerance: within 0.5% of electricity_kwh
data_source	STRING	NO	ENUM	Allowed: smart_meter_api | manual_entry | estimate
record_status	STRING	NO	ENUM	Allowed: complete | missing_primary | excluded. Rows with excluded MUST NOT enter curated zone.
2.2 Raw Zone — Table: esg_raw.loan_portfolio
Partition key: reporting_year (INT). Loan-level PCAF financed emissions input data. Foreign key: borrower_id references esg_raw.borrower_master. The following columns are mandatory:
Column Name	Type	Nullable	Constraints	Value Range / Notes
loan_id	STRING	NO	PK; UNIQUE	Format: LN-YYYY-NNNNNNN (year + 7-digit counter)
borrower_id	STRING	NO	FK borrower_master	Format: BOR-NNNNNN (6-digit counter)
sector_nace	STRING	NO	ENUM; 10 values	manufacturing_cement | manufacturing_steel | manufacturing_food | real_estate_commercial | real_estate_residential | transportation_road | agriculture | energy_oil_gas | financial_services | retail_trade
loan_type	STRING	NO	ENUM; 6 values	term_loan | revolving_credit | mortgage | project_finance | syndicated_loan | leasing
currency	STRING	NO	ISO 4217	Allowed: IDR | USD. Exchange rate 1 USD = 15,750 IDR (reference rate)
outstanding_idr	BIGINT	NO	>0; <=EV	Range: 500,000,000 (IDR 500M) – 2,000,000,000,000 (IDR 2T). MUST NOT exceed enterprise value (equity + debt).
total_equity_idr	BIGINT	NO	>0	Range: 1,000,000,000 (IDR 1B) – 50,000,000,000,000 (IDR 50T)
total_debt_idr	BIGINT	NO	>=0	Range: 0 – 50,000,000,000,000; (equity + debt) MUST be > 0
pcaf_attribution_factor	DOUBLE	NO	0 < x <= 1	Pre-calculated: outstanding_idr / (total_equity_idr + total_debt_idr). Precision: 6 decimal places.
borrower_emissions_tco2e	DOUBLE	NO	>0	Range: 500 – 5,000,000 tCO2e/year. Borrower Scope 1 + Scope 2 only.
pcaf_data_quality_score	DOUBLE	NO	ENUM {1.0, 1.5, 2.0, 3.0, 4.0, 5.0}	1.0 = Audited + verified (PCAF 1a)
1.5 = Audited + unverified (PCAF 1b)
2.0 = Physical activity-based
3.0 = EEIO + revenue
4.0 = EEIO + assets
5.0 = Sector-average proxy. 
Distribution: 1:3.5%, 1.5:1.5%, 2:15%, 3:30%, 4:35%, 5:15%
record_status	STRING	NO	ENUM	Allowed: validated | pending | rejected. Only validated records enter curated zone.
2.3 Raw Zone — Table: esg_raw.hr_metrics
Partition key: reporting_year (INT). HR and social metrics for GRI 401, 405, 406 and CSRD/ESRS S1 disclosures. Full-time-equivalent (FTE) count feeds GHG intensity denominators in the aggregated zone.
Column Name	Type	Nullable	Constraints	Value Range / Notes
period_date	DATE	NO	YYYY-12-31 format	Year-end snapshot date; must be the last calendar day of reporting_year
fte_total	INT	NO	>0	Total full-time-equivalent headcount at period end; range 500–50,000
fte_female_pct	DOUBLE	NO	0–100	Percentage of female employees; 2 decimal places
fte_management_female_pct	DOUBLE	NO	0–100	Percentage of female employees in management (Director level and above)
new_hire_count	INT	NO	>=0	Total new hires during reporting year
voluntary_turnover_pct	DOUBLE	NO	0–100	Voluntary attrition rate as a percentage; 2 decimal places
training_hours_per_fte	DOUBLE	NO	>=0	Average training hours per FTE per year; range 8–120 hours
discrimination_cases	INT	NO	>=0	Reported cases under GRI 406; must be reconcilable with HR case management system
2.4 Curated Zone — Table: esg_curated.ghg_scope1
Partition key: reporting_year (INT). This table contains the ETL-computed, annually aggregated Scope 1 GHG results per facility. Schema is enforced at write time; rows with nulls on mandatory fields MUST be routed to an error partition, not written to the curated zone.
Column Name	Type	Nullable	Constraints	Semantics / Formula Reference
facility_id	STRING	NO	FK facility_master	Surrogate key; joins to facility_type, province
scope1_tco2e	DOUBLE	NO	>=0; 4 dp	SUM(scope1_natgas_tco2e + scope1_diesel_tco2e); in metric tonnes CO2e
scope1_natgas_tco2e	DOUBLE	NO	>=0; 4 dp	SUM over 12 months: (natgas_gj x EF_CO2 + natgas_gj x EF_CH4 x GWP_CH4 + natgas_gj x EF_N2O x GWP_N2O) / 1000
scope1_diesel_tco2e	DOUBLE	NO	>=0; 4 dp	SUM over 12 months: (diesel_L x EF_CO2 + diesel_L x EF_CH4 x GWP_CH4 + diesel_L x EF_N2O x GWP_N2O) / 1000
total_natgas_gj	DOUBLE	NO	>=0	Sum of monthly natural gas GJ consumed; used for intensity cross-check
total_diesel_liters	DOUBLE	NO	>=0	Sum of monthly diesel consumed in litres
imputed_months	INT	NO	0–12	Count of months where electricity_kwh was null and replaced with facility-type mean
data_quality_score	INT	NO	ENUM 1–4	1 = 0 imputed months; 2 = 1–2; 3 = 3–5; 4 = 6+ imputed months
emission_factor_source	STRING	NO	Ref to ef_source	Must match ef_source value in source raw record
methodology	STRING	NO	LITERAL	Fixed value: GHG_Protocol_Corporate_Standard_v2015
consolidation_approach	STRING	NO	ENUM	Allowed: operational_control | equity_share. Default: operational_control
2.5 Curated Zone — Table: esg_curated.ghg_scope3_financed
Partition key: reporting_year (INT). Sector-level PCAF financed emissions aggregated from loan_portfolio raw data. One record per (sector_nace, reporting_year) pair.
Column Name	Type	Nullable	Constraints	Semantics
sector_nace	STRING	NO	PK component	One of 10 allowed NACE sector values (see esg_raw.loan_portfolio)
loan_count	INT	NO	>0	COUNT of validated loans in this sector for reporting year
borrower_count	INT	NO	>0	COUNT DISTINCT of borrower_id in this sector
total_outstanding_idr_trillion	DOUBLE	NO	>0; 6 dp	SUM(outstanding_idr) / 1e12. Precision: 6 decimal places.
financed_emissions_gross_tco2e	DOUBLE	NO	>0; 2 dp	SUM(pcaf_attribution_factor x borrower_emissions_tco2e) per validated loan in sector
financed_emissions_weighted_tco2e	DOUBLE	NO	>0; 2 dp	SUM(gross_financed_emissions x confidence_factor) where confidence_factor from PCAF tier map
avg_pcaf_score	DOUBLE	NO	1.0–5.0; 2 dp	AVG(pcaf_data_quality_score) across all loans in sector
high_quality_data_pct	DOUBLE	NO	0–100; 4 dp	COUNT(score<=2) / COUNT(*) x 100. Percentage of loans with PCAF score 1 or 2.
2.6 Aggregated Zone — Table: esg_aggregated.ghg_summary_annual
Partition key: reporting_year (INT). This is the report-ready table. AgentCore MUST read exclusively from this table when populating section generation prompt templates. The table contains one record per (bank_id, reporting_year) pair.
Column Name	Type	Nullable	Constraints	Semantics
metric_key	STRING	NO	PK; UNIQUE	Composite: {bank_id}_{reporting_year}
scope1_tco2e	DOUBLE	NO	>0; 3 dp	SUM(scope1_tco2e) across all facilities in curated zone
scope2_location_tco2e	DOUBLE	NO	>0; 3 dp	SUM(electricity_kwh x grid_ef_kgco2_kwh) / 1000 minus REC-adjusted correction
scope2_market_tco2e	DOUBLE	NO	>=0; 3 dp	scope2_location_tco2e minus REC_MWh_claimed x grid_ef. Can be zero if 100% renewable.
scope3_cat15_gross_tco2e	DOUBLE	NO	>0; 2 dp	SUM(financed_emissions_gross_tco2e) across all sectors
scope3_cat15_weighted_tco2e	DOUBLE	NO	>0; 2 dp	SUM(financed_emissions_weighted_tco2e) across all sectors; for disclosure alongside gross
intensity_tco2e_per_idr_bn	DOUBLE	NO	>0; 6 dp	(scope1 + scope2_market + scope3_cat15_gross) / revenue_idr_billion
intensity_tco2e_per_fte	DOUBLE	NO	>0; 4 dp	(scope1 + scope2_market) / fte_count. Excludes Scope 3 from per-FTE intensity.
yoy_change_pct	DOUBLE	YES	+/-500 max	NULL for base year. Formula: (current_total - prior_total) / prior_total x 100. 2 dp.
vs_base_year_change_pct	DOUBLE	YES	+/-500 max	NULL for base year itself. Formula: (current_total - base_total) / base_total x 100. 2 dp.
avg_pcaf_data_quality	DOUBLE	NO	1.0–5.0	Portfolio-weighted PCAF average: SUM(outstanding x score) / SUM(outstanding)
assurance_level	STRING	NO	ENUM	Allowed: none | limited | reasonable. Default for POC: none.
 
3. ETL Business Logic — Formulas and Rules
All GHG calculations MUST be performed deterministically in the Glue ETL layer. The LLM MUST NOT perform any numerical calculation. The rules below define every formula the ETL MUST implement. Emission factor constants are declared once and referenced throughout; they MUST NOT be hard-coded inline in application code.
3.1 Emission Factor Constants (Non-Negotiable)
The following constants MUST be declared as named module-level variables in the Glue PySpark job. Any deviation from these values constitutes a data integrity defect.
Constant Name	Value	Unit	Source / Notes
GWP_CH4	29.8	kg CO2e / kg CH4	IPCC AR6 Chapter 7, GWP100 metric
GWP_N2O	273.0	kg CO2e / kg N2O	IPCC AR6 Chapter 7, GWP100 metric
EF_NATGAS_KGCO2_PER_GJ	56.10	kg CO2 / GJ	Pipeline natural gas, Indonesia; IPCC 2006 Table 2.2
EF_NATGAS_KGCH4_PER_GJ	0.001	kg CH4 / GJ	IPCC 2006 Volume 2, Table 2.3
EF_NATGAS_KGN2O_PER_GJ	0.0001	kg N2O / GJ	IPCC 2006 Volume 2, Table 2.3
EF_DIESEL_KGCO2_PER_L	2.53763	kg CO2 / litre	Road diesel; IPCC 2006 / DEFRA 2025 Annex 3
EF_DIESEL_KGCH4_PER_L	0.0000097	kg CH4 / litre	DEFRA 2025 conversion factors
EF_DIESEL_KGN2O_PER_L	0.000121	kg N2O / litre	DEFRA 2025 conversion factors
GRID_EF_PLN_2023	0.7886	kg CO2 / kWh	PLN National Grid Average 2023; used for location-based Scope 2
PCAF_CONFIDENCE	{1:1.00, 2:0.90, 3:0.75, 4:0.60, 5:0.45}	Dimensionless	PCAF Standard Part A Table 4.2 (2022 revision)
3.2 Scope 1 GHG Calculation Rules
Overview
Attribute	Value
Glue Job Name	esg-etl-scope1-direct
Input Table	esg_raw.energy_consumption WHERE record_status = 'complete'
Output Table	esg_curated.ghg_scope1
Granularity	One record per (facility_id, reporting_year)
Methodology	GHG Protocol Corporate Standard v2015
Consolidation	Operational Control

Emission Factor Constants (from Section 3.1)
Constant	Value	Unit	Source
EF_NATGAS_KGCO2_PER_GJ	56.10	kg CO2 / GJ	IPCC 2006 Table 2.2
EF_NATGAS_KGCH4_PER_GJ	0.001	kg CH4 / GJ	IPCC 2006 Vol 2 Table 2.3
EF_NATGAS_KGN2O_PER_GJ	0.0001	kg N2O / GJ	IPCC 2006 Vol 2 Table 2.3
EF_DIESEL_KGCO2_PER_L	2.6710	kg CO2 / litre	DEFRA 2025 Annex 3
EF_DIESEL_KGCH4_PER_L	0.000136	kg CH4 / litre	DEFRA 2025
EF_DIESEL_KGN2O_PER_L	0.000136	kg N2O / litre	DEFRA 2025
GWP_CH4	29.8	kg CO2e / kg CH4	IPCC AR6 GWP100
GWP_N2O	273.0	kg CO2e / kg N2O	IPCC AR6 GWP100
Calculation Formulas
REQ-ETL-01: Computation Granularity
Scope 1 MUST be computed at facility-month level first (12 monthly records per facility), then summed annually per facility to produce the curated zone output.

REQ-ETL-02: Natural Gas Scope 1 Formula
For each facility-month where natural_gas_gj > 0:
scope1_natgas_month_kgco2e = 
    (natural_gas_gj × EF_NATGAS_KGCO2_PER_GJ)
  + (natural_gas_gj × EF_NATGAS_KGCH4_PER_GJ × GWP_CH4)
  + (natural_gas_gj × EF_NATGAS_KGN2O_PER_GJ × GWP_N2O)
Annual aggregation:
scope1_natgas_tco2e = SUM(scope1_natgas_month_kgco2e for month 1..12) / 1000

Precision: 4 decimal places in tCO2e.

REQ-ETL-03: Diesel Scope 1 Formula
For each facility-month where diesel_liters > 0:
scope1_diesel_month_kgco2e = 
    (diesel_liters × EF_DIESEL_KGCO2_PER_L)
  + (diesel_liters × EF_DIESEL_KGCH4_PER_L × GWP_CH4)
  + (diesel_liters × EF_DIESEL_KGN2O_PER_L × GWP_N2O)
Annual aggregation:
scope1_diesel_tco2e = SUM(scope1_diesel_month_kgco2e for month 1..12) / 1000
Precision: 4 decimal places in tCO2e.

REQ-ETL-04: Scope 1 Total per Facility
scope1_tco2e = scope1_natgas_tco2e + scope1_diesel_tco2e
Constraint: This sum MUST be exact (no rounding before addition). The stored scope1_tco2e MUST equal the sum of its components to ±0.0001 tCO2e.

REQ-ETL-05: Activity Data Preservation
The curated output MUST retain:
•	total_natgas_gj = SUM(natural_gas_gj) across 12 months
•	total_diesel_liters = SUM(diesel_liters) across 12 months
These serve as cross-check denominators for intensity validation.

Imputation Rules

REQ-ETL-06: Null Value Handling
When natural_gas_gj or diesel_liters is NULL for a given facility-month:
1.	Compute facility-type mean for that month across all non-null facilities of the same facility_type
2.	Substitute the mean value for the null
3.	Increment imputed_months counter by 1 for that facility
Constraint: Imputation MUST NOT be applied if more than 6 months are null for a single facility. In that case, set record_status = 'excluded' and route to error partition.

REQ-ETL-07: Data Quality Score Assignment
imputed_months	data_quality_score		Interpretation
0	1		All actual data
1–2	2		Minor imputation
3–5	3		Moderate imputation
6+	4		Excluded from curated zone





Validation Gates (Pre-Output)
REQ-ETL-08: Scope 1 Output Validation
Gate	Rule	Tolerance	Action on Fail
GATE-S1-01	scope1_tco2e is NOT NULL for any output row	Zero	Block write; route to error
GATE-S1-02	scope1_tco2e >= 0 for all rows	Zero	Block write; route to error
GATE-S1-03	scope1_natgas_tco2e + scope1_diesel_tco2e = scope1_tco2e	±0.0001 tCO2e	Block write; log discrepancy
GATE-S1-04	Total output records ≤ total input facilities (no row explosion)	Zero	Block write; investigate join logic
GATE-S1-05	emission_factor_source is not NULL or empty	Zero	Block write; metadata integrity

3.3 Scope 2 GHG Calculation Rules
Overview
Attribute	Value
Glue Job Name	esg-etl-scope2-indirect
Input Table	esg_raw.energy_consumption WHERE source_type = 'electricity'
Output Table	esg_curated.ghg_scope2
Granularity	One record per (facility_id, reporting_year)
Reporting	Dual method — BOTH location-based AND market-based (GHG Protocol Scope 2 Guidance)
Grid Emission Factors
Grid Region	ef_location (kg CO2/kWh)	Source	Applicable Provinces
PLN National Average	0.7886	PLN RUPTL 2023	Default / fallback
Java-Bali Grid	0.7250	PLN Regional 2023	DKI Jakarta, Jawa Barat, Jawa Tengah, Jawa Timur, Banten, Bali
Sumatra Grid	0.8020	PLN Regional 2023	Sumatera Utara, Sumatera Selatan
Kalimantan Grid	0.8450	PLN Regional 2023	Kalimantan Timur
Sulawesi Grid	0.7900	PLN Regional 2023	Sulawesi Selatan
Rule: Grid EF is selected by mapping facility.region → grid region. If no mapping exists, use PLN National Average (0.7886).

Calculation Formulas

REQ-ETL-09: Unit Conversion
consumption_mwh = electricity_kwh / 1000
Computed per facility-month, then summed annually.

REQ-ETL-10: Location-Based Scope 2
scope2_location_month_kgco2e = electricity_kwh × grid_ef_kgco2_kwh
Annual aggregation:
scope2_location_tco2e = SUM(scope2_location_month_kgco2e for month 1..12) / 1000

Precision: 3 decimal places in tCO2e.
Constraint: This method MUST always be computed regardless of REC/PPA status. GHG Protocol requires location-based as the primary disclosure.

REQ-ETL-11: Market-Based Scope 2
The market-based method adjusts for contractual instruments:
IF rec_mwh_claimed > 0:
    rec_adjustment_tco2e = (rec_mwh_claimed × grid_ef_kgco2_kwh * 1000) / 1000
    scope2_market_tco2e = scope2_location_tco2e - rec_adjustment_tco2e
ELIF has_ppa = TRUE:
    scope2_market_tco2e = (total_consumption_mwh - ppa_mwh) × grid_ef / 1000
ELSE:
    scope2_market_tco2e = scope2_location_tco2e  (residual mix = grid average)
Floor Rule: scope2_market_tco2e MUST be floored at 0.0. If REC adjustment exceeds location-based, set to 0.0 (100% renewable claim).

REQ-ETL-12: REC Reconciliation
rec_applied_pct = (rec_mwh_claimed / total_consumption_mwh) × 100
Constraint: rec_mwh_claimed MUST NOT exceed total_consumption_mwh. If it does, cap at total_consumption_mwh and log warning.

REQ-ETL-13: Dual Reporting Requirement
The curated output MUST contain BOTH:
•	scope2_location_tco2e — always non-zero (unless zero electricity consumed)
•	scope2_market_tco2e — can be zero (if 100% renewable)
Both MUST appear in the aggregated zone AND in the final report narrative. GRI 305-2 mandates dual reporting.




Validation Gates (Pre-Output)
Gate	Rule	Tolerance	Action on Fail
GATE-S2-01	scope2_location_tco2e >= 0	Zero	Block write
GATE-S2-02	scope2_market_tco2e >= 0	Zero	Block write (floor at 0)
GATE-S2-03	scope2_market_tco2e <= scope2_location_tco2e	Zero	Warning log (market cannot exceed location unless residual mix > grid avg)
GATE-S2-04	total_consumption_mwh > 0 for all active facilities	Zero	Flag inactive facilities
GATE-S2-05	Grid EF exists for every facility (no NULL grid_ef_kgco2_kwh)	Zero	Block write; check region mapping

3.4 Scope 3 Category 15 — PCAF Financed Emissions Rules
Overview
Attribute	Value
Glue Job Name	esg-etl-scope3-pcaf
Input Tables	esg_raw.loan_portfolio JOIN esg_raw.borrower_emissions (on borrower_id + reporting_year)
Output Table	esg_curated.ghg_scope3_financed
Granularity	One record per (sector_nace, reporting_year)
Methodology	PCAF Global GHG Accounting and Reporting Standard, Part A (2022 revision)
Asset Classes	Corporate loans, project finance, commercial real estate, mortgages, motor vehicles

PCAF Formula
REQ-ETL-14: Attribution Factor Calculation
For each loan record:
attribution_factor = outstanding_idr / (total_equity_idr + total_debt_idr)
Precision: 6 decimal places.
Constraints:
•	Denominator (total_equity_idr + total_debt_idr) MUST be > 0
•	Result MUST be in range: 0 < attribution_factor <= 1.0
•	If calculated value > 1.0, CAP at 1.0 and log warning (indicates outstanding exceeds enterprise value — data quality issue)

REQ-ETL-15: Gross Financed Emissions (per loan)
financed_emissions_loan_tco2e = attribution_factor × borrower_emissions_tco2e
Where borrower_emissions_tco2e = borrower's reported Scope 1 + Scope 2 emissions.
Precision: 2 decimal places.

REQ-ETL-16: Confidence-Weighted Financed Emissions (per loan)
PCAF Confidence Factors (from Section 3.1):
PCAF Tier	Confidence Factor	Description
1	1.00	Verified CDP / equivalent
2	0.90	Reported, unverified
3	0.75	EEIO + revenue-based
4	0.60	EEIO + asset-based
5	0.45	Sector-average proxy
financed_emissions_weighted_tco2e = financed_emissions_loan_tco2e × PCAF_CONFIDENCE[pcaf_data_quality_score]
Purpose: The weighted figure represents a "confidence-adjusted" view. Disclosed alongside gross for transparency.
Constraint: financed_emissions_weighted_tco2e MUST always be <= financed_emissions_loan_tco2e (since confidence factors are all ≤ 1.0).

REQ-ETL-17: Sector-Level Aggregation
FOR EACH (sector_nace, reporting_year):
    loan_count = COUNT(validated loans in sector)
    borrower_count = COUNT DISTINCT(borrower_id in sector)
    total_outstanding_idr_trillion = SUM(outstanding_idr) / 1e12
    financed_emissions_gross_tco2e = SUM(financed_emissions_loan_tco2e)
    financed_emissions_weighted_tco2e = SUM(financed_emissions_weighted_tco2e)
    avg_pcaf_score = AVG(pcaf_data_quality_score)
    high_quality_data_pct = (COUNT WHERE pcaf_data_quality_score <= 2) / loan_count × 100

Three Validation Gates (Pre-Processing)
REQ-ETL-18: Gate 1 — Enterprise Value Non-Positive
IF (total_equity_idr + total_debt_idr) <= 0:
    ACTION: REJECT loan record
    REASON: Cannot compute attribution factor (division by zero or negative)
    LOG: borrower_id, loan_id, equity, debt values
    ROUTE: error partition
REQ-ETL-19: Gate 2 — Outstanding Exceeds Enterprise Value
IF outstanding_idr > (total_equity_idr + total_debt_idr):
    ACTION: CAP attribution_factor at 1.0
    REASON: Data quality issue — outstanding may include unreconciled facilities
    LOG: borrower_id, loan_id, original attribution_factor value
    FLAG: data_quality_flag = 'AF_CAPPED'
REQ-ETL-20: Gate 3 — Borrower Emissions Non-Positive
IF borrower_emissions_tco2e <= 0:
    ACTION: REJECT loan record from financed emissions calculation
    REASON: Cannot attribute negative or zero emissions
    LOG: borrower_id, reported emissions value, ef_source
    ROUTE: error partition
    NOTE: These borrowers still appear in portfolio outstanding but NOT in financed emissions
Portfolio-Level Quality Metrics

REQ-ETL-21: Weighted PCAF Data Quality Score
portfolio_weighted_pcaf = SUM(outstanding_idr_i × pcaf_data_quality_score_i) / SUM(outstanding_idr_i)
For all validated loans across all sectors. This becomes avg_pcaf_data_quality in the aggregated zone.
Range: 1.0 – 5.0 (2 decimal places)

REQ-ETL-22: Portfolio Coverage Percentage
portfolio_coverage_pct = (
    SUM(outstanding_idr WHERE financed_emissions_computed = TRUE) 
    / SUM(total_outstanding_idr_all_loans)
) × 100
Must be disclosed in the report narrative. Target for PCAF signatory: >90%.

Output Constraint
REQ-ETL-23: Gross vs Weighted Distinction
The curated output MUST store BOTH financed_emissions_gross_tco2e AND financed_emissions_weighted_tco2e as separate columns. They MUST NEVER be conflated, averaged, or merged into a single value. The agent prompt validation rule VAL-NUM-06 enforces this distinction in narrative text.

3.5 Aggregated Zone Computation Rules
Overview
Attribute	Value
Glue Job Name	esg-etl-aggregation
Input Tables	esg_curated.ghg_scope1, esg_curated.ghg_scope2, esg_curated.ghg_scope3_financed
Output Table	esg_aggregated.ghg_summary_annual
Granularity	One record per (bank_id, reporting_year)
Purpose	Single source of truth for all numerical claims in the generated report

Core Aggregation Formulas
REQ-ETL-24: Scope Totals
scope1_tco2e = SUM(curated.ghg_scope1.scope1_tco2e) for all facilities in reporting_year
scope2_location_tco2e = SUM(curated.ghg_scope2.scope2_location_tco2e) for all facilities in reporting_year
scope2_market_tco2e = SUM(curated.ghg_scope2.scope2_market_tco2e) for all facilities in reporting_year
scope3_cat15_gross_tco2e = SUM(curated.ghg_scope3_financed.financed_emissions_gross_tco2e) for all sectors in reporting_year
scope3_cat15_weighted_tco2e = SUM(curated.ghg_scope3_financed.financed_emissions_weighted_tco2e) for all sectors in reporting_year
Precision: 3 decimal places for Scope 1 & 2; 2 decimal places for Scope 3.

REQ-ETL-25: Grand Total
total_tco2e = scope1_tco2e + scope2_market_tco2e + scope3_cat15_gross_tco2e
CRITICAL CONSTRAINT (Validation Rule R2): total_tco2e MUST equal scope1_tco2e + scope2_market_tco2e + scope3_cat15_gross_tco2e to a tolerance of ±0.001 tCO2e. This is the single most important data integrity rule in the system.
NOTE: The total uses market-based Scope 2 (not location-based). This follows GHG Protocol hierarchy: if market-based is available, use it for the total. Location-based is reported separately.

REQ-ETL-26: Year-over-Year Change
IF prior_year_record EXISTS:
    yoy_change_pct = ((current_year_total_tco2e - prior_year_total_tco2e) / prior_year_total_tco2e) × 100
ELSE:
    yoy_change_pct = NULL
Precision: 2 decimal places. Constraint: This value is PRE-COMPUTED here. The LLM MUST use this value verbatim. The LLM MUST NOT recalculate YoY from raw scope values.

REQ-ETL-27: Base Year Comparison
base_year = 2022  (configurable per institution)
base_year_total_tco2e = total_tco2e WHERE reporting_year = base_year

IF reporting_year = base_year:
    vs_base_year_change_pct = NULL
ELSE:
    vs_base_year_change_pct = ((current_year_total_tco2e - base_year_total_tco2e) / base_year_total_tco2e) × 100
Precision: 2 decimal places.

REQ-ETL-28: Emission Intensity Ratios
Intensity per Revenue:
intensity_tco2e_per_idr_bn = (scope1_tco2e + scope2_market_tco2e + scope3_cat15_gross_tco2e) / revenue_idr_billion
Precision: 6 decimal places. Source of revenue_idr_billion: External input parameter (from financial statements). Passed as Glue job argument or read from a reference table.
Intensity per FTE:
intensity_tco2e_per_fte = (scope1_tco2e + scope2_market_tco2e) / fte_count
NOTE: Per-FTE intensity uses Scope 1+2 ONLY (excludes Scope 3 financed emissions, which are not operational). Precision: 4 decimal places. Source of fte_count: From esg_raw.hr_metrics.fte_total for the same reporting_year.

REQ-ETL-29: PCAF Portfolio Quality (Aggregated)
avg_pcaf_data_quality = SUM(outstanding_idr × pcaf_data_quality_score) / SUM(outstanding_idr)
Across all validated loans. This is the portfolio-weighted average.

Derived Metrics for Location-Based Reporting

REQ-ETL-30: Location-Based Total (Supplementary)
total_location_based_tco2e = scope1_tco2e + scope2_location_tco2e + scope3_cat15_gross_tco2e
This is reported SEPARATELY as supplementary information per GHG Protocol. It MUST NOT replace the primary total (which uses market-based Scope 2).
Data Completeness Score

REQ-ETL-31: Data Completeness
data_completeness_pct = (
    COUNT(facilities with data_quality_score <= 2) / COUNT(all active facilities)
) × 100
Interpretation:
•	≥ 95%: High confidence
•	80–94%: Moderate confidence
•	< 80%: Disclose as limitation

Aggregated Zone Validation Gates
REQ-ETL-32: Final Aggregation Validation
Gate	Rule	Tolerance	Action on Fail
GATE-AGG-01	total_tco2e = scope1 + scope2_market + scope3_cat15_gross	±0.001 tCO2e	BLOCK REPORT — fundamental integrity failure
GATE-AGG-02	total_location_based_tco2e = scope1 + scope2_location + scope3_cat15_gross	±0.001 tCO2e	Block write
GATE-AGG-03	scope3_cat15_weighted_tco2e <= scope3_cat15_gross_tco2e	Zero	Block write — weighted cannot exceed gross
GATE-AGG-04	intensity_tco2e_per_idr_bn > 0 (if revenue > 0)	Zero	Block write — check revenue input
GATE-AGG-05	yoy_change_pct is within ±50% (sanity check)	±50 ppt	WARNING only — flag for human review but allow write
GATE-AGG-06	Only ONE record per (bank_id, reporting_year)	Zero	Block write — dedup before write
GATE-AGG-07	avg_pcaf_data_quality is between 1.0 and 5.0	Zero	Block write — check PCAF score computation

Critical Architecture Rule
REQ-ETL-33: Aggregated Zone as Single Source of Truth
The esg_aggregated.ghg_summary_annual table is the ONLY table that the AgentCore agent is permitted to read for numerical data. This is enforced by:
1.	The agent's Athena tool ONLY has SELECT permission on the esg_aggregated database
2.	The base system prompt explicitly states: "ALL numbers in DATA INPUT come from esg_aggregated tables"
3.	Validation rule R1 cross-checks narrative numbers against aggregated zone values
Flow:
Raw (source) → Curated (calculated) → Aggregated (report-ready) → Agent reads ONLY this

 
4. Amazon Athena DDL Specifications
This section specifies the DDL requirements for all Athena external table definitions. Kiro IDE MUST generate SQL DDL files that comply with every requirement below. DDL files are the authoritative schema definition layer; they MUST NOT diverge from the Data Contract in Section 2.
4.1 Database Creation Requirements
REQ-DDL-01: Three Databases
Kiro IDE MUST generate CREATE DATABASE statements for exactly three databases:
Database Name	Purpose	Comment String
esg_raw	Source data as ingested, no transformation applied	"ESG Raw Zone — Source data as ingested from ERP, utility APIs, loan systems, and HR platforms"
esg_curated	Normalized, unit-converted, GHG-calculated data	"ESG Curated Zone — ETL-computed GHG emissions per facility and sector"
esg_aggregated	Report-ready metrics; single source of truth for agent	"ESG Aggregated Zone — Report-ready annual metrics; AgentCore reads ONLY from this zone"

REQ-DDL-02: Database Properties
Each CREATE DATABASE statement MUST include:
•	COMMENT clause with the description above
•	LOCATION clause pointing to the zone root: s3://${BUCKET}/{zone_name}/
•	IF NOT EXISTS clause for idempotency
REQ-DDL-03: Database Naming Convention
•	All database names MUST use lowercase with underscore separator
•	Pattern: esg_{zone} where zone ∈ {raw, curated, aggregated}
•	No hyphens, no camelCase, no uppercase
DDL Template:
CREATE DATABASE IF NOT EXISTS esg_{zone}
COMMENT '{comment_string}'
LOCATION 's3://${ESG_DATALAKE_BUCKET}/{zone_name}/'
WITH DBPROPERTIES (
    'creator' = 'esg-reporting-poc',
    'environment' = '${ENVIRONMENT}',
    'managed_by' = 'kiro-generated'
);

4.2 Partition Projection Configuration
EQ-DDL-04: Partition Projection Enabled
ALL tables with partition keys MUST use Athena partition projection. Manual MSCK REPAIR TABLE or ALTER TABLE ADD PARTITION is PROHIBITED (CON-DDL-01).
Required TBLPROPERTIES for Partition Projection:
TBLPROPERTY Key	Required Value	Notes
projection.enabled	true	Enables automatic partition resolution without MSCK REPAIR
projection.reporting_year.type	integer	Partition column is an integer year
projection.reporting_year.range	2020,2035	Inclusive range; update by 2034 for extension
projection.reporting_month.type	integer	Only for tables with month partition (energy_consumption)
projection.reporting_month.range	1,12	Calendar months
storage.location.template	s3://${BUCKET}/{path}/reporting_year=${reporting_year}	MUST match actual S3 partition path exactly

REQ-DDL-05: Location Template Patterns
Table	Location Template
esg_raw.energy_consumption	s3://${BUCKET}/raw/energy_consumption/reporting_year=${reporting_year}/reporting_month=${reporting_month}
esg_raw.loan_portfolio	s3://${BUCKET}/raw/loan_portfolio/reporting_year=${reporting_year}
esg_raw.borrower_emissions	s3://${BUCKET}/raw/borrower_emissions/reporting_year=${reporting_year}
esg_raw.hr_metrics	s3://${BUCKET}/raw/hr_metrics/reporting_year=${reporting_year}
esg_curated.ghg_scope1	s3://${BUCKET}/curated/ghg_scope1/reporting_year=${reporting_year}
esg_curated.ghg_scope2	s3://${BUCKET}/curated/ghg_scope2/reporting_year=${reporting_year}
esg_curated.ghg_scope3_financed	s3://${BUCKET}/curated/ghg_scope3_financed/reporting_year=${reporting_year}
esg_aggregated.ghg_summary_annual	s3://${BUCKET}/aggregated/ghg_summary_annual/reporting_year=${reporting_year}
esg_aggregated.pcaf_by_sector	s3://${BUCKET}/aggregated/pcaf_by_sector/reporting_year=${reporting_year}

REQ-DDL-06: Additional Required TBLPROPERTIES
Property	Value	Purpose
parquet.compress	SNAPPY	Compression codec for all Parquet files
classification	parquet	Glue Data Catalog classification
has_encrypted_data	true	SSE-KMS enforcement flag
transient_lastDdlTime	(auto)	Athena auto-manages; do not hardcode

4.3 Column Definition Requirements
REQ-DDL-07: Column Specifications
Every column in every DDL MUST include:
1.	Column name — lowercase, underscore-separated (no camelCase)
2.	Data type — from allowed Athena types (see mapping below)
3.	COMMENT — mandatory for every column; describes semantics, unit, and constraints

REQ-DDL-08: Data Type Mapping
Specification Type	Athena DDL Type	Notes
STRING	STRING	Variable-length UTF-8
INT	INT	32-bit signed integer
BIGINT	BIGINT	64-bit signed integer (for IDR amounts > 2.1B)
DOUBLE	DOUBLE	64-bit IEEE 754 floating point
BOOLEAN	BOOLEAN	true/false
DATE	DATE	YYYY-MM-DD format
ARRAY	ARRAY<STRING>	Only if explicitly specified in schema

REQ-DDL-09: Column Comment Format
Each column COMMENT MUST follow this pattern:
'{Description}. Unit: {unit}. Constraint: {constraint}. Precision: {decimal_places} dp.'
Examples:
•	'Total Scope 1 GHG emissions from natural gas combustion. Unit: tCO2e. Constraint: >= 0. Precision: 4 dp.'
•	'PCAF attribution factor. Unit: dimensionless. Constraint: 0 < x <= 1. Precision: 6 dp.'
•	'Reporting fiscal year. Unit: year. Constraint: 2020-2035. Partition key.'
REQ-DDL-10: Partition Column Placement
Partition columns MUST be declared in the PARTITIONED BY clause, NOT in the main column list. This is standard Athena/Hive DDL behavior.

Complete Column Definitions per Table:

Table: esg_raw.energy_consumption
Column	Type	Comment
facility_id	STRING	'Facility identifier. FK to facility_master. Format: FAC-NNNN.'
electricity_kwh	DOUBLE	'Monthly electricity consumption. Unit: kWh. Constraint: >= 0 if present. Range: 1500-85000.'
natural_gas_gj	DOUBLE	'Monthly natural gas consumption. Unit: GJ. Constraint: >= 0 if present. Range: 0-120.'
diesel_liters	DOUBLE	'Monthly diesel consumption. Unit: liters. Constraint: >= 0 if present. Range: 0-3500.'
rec_mwh_claimed	DOUBLE	'Renewable Energy Certificates claimed. Unit: MWh. Constraint: >= 0. Default: 0.'
grid_ef_kgco2_kwh	DOUBLE	'Grid emission factor. Unit: kg CO2/kWh. Constraint: > 0. Default: 0.7886 (PLN 2023).'
ef_source	STRING	'Emission factor source. ENUM: PLN_Grid_Average_2023, DEFRA_2025, IPCC_AR6_CH4_GWP100.'
meter_reading_kwh	DOUBLE	'Raw meter reading for reconciliation. Unit: kWh. Constraint: within 0.5% of electricity_kwh.'
data_source	STRING	'Data provenance. ENUM: smart_meter_api, manual_entry, estimate.'
record_status	STRING	'Record status. ENUM: complete, missing_primary, excluded. Excluded rows blocked from curated.'
PARTITIONED BY		
reporting_year	INT	'Reporting fiscal year. Range: 2020-2035.'
reporting_month	INT	'Calendar month. Range: 1-12.'

Table: esg_raw.loan_portfolio
Column	Type	Comment
loan_id	STRING	'Unique loan identifier. PK. Format: LN-YYYY-NNNNNNN.'
borrower_id	STRING	'Borrower entity ID. FK to borrower_master. Format: BOR-NNNNNN.'
sector_nace	STRING	'NACE sector code. ENUM: 10 values (see Data Contract 2.2).'
loan_type	STRING	'Loan type. ENUM: term_loan, revolving_credit, mortgage, project_finance, syndicated_loan, leasing.'
currency	STRING	'ISO 4217 currency code. ENUM: IDR, USD.'
outstanding_idr	BIGINT	'Outstanding loan amount. Unit: IDR. Constraint: > 0, <= enterprise value. Range: 500M-2T.'
total_equity_idr	BIGINT	'Borrower total equity. Unit: IDR. Constraint: > 0. Range: 1B-50T.'
total_debt_idr	BIGINT	'Borrower total debt. Unit: IDR. Constraint: >= 0. Range: 0-50T.'
pcaf_attribution_factor	DOUBLE	'PCAF attribution factor. Unit: dimensionless. Constraint: 0 < x <= 1. Precision: 6 dp.'
borrower_emissions_tco2e	DOUBLE	'Borrower Scope 1+2 emissions. Unit: tCO2e. Constraint: > 0. Range: 500-5000000.'
pcaf_data_quality_score	INT	'PCAF data quality tier. ENUM: 1-5. Distribution: 1:5%, 2:15%, 3:30%, 4:35%, 5:15%.'
record_status	STRING	'Validation status. ENUM: validated, pending, rejected. Only validated enters curated.'
PARTITIONED BY		
reporting_year	INT	'Portfolio snapshot year. Range: 2020-2035.'

Table: esg_raw.hr_metrics
Column	Type	Comment
period_date	DATE	'Year-end snapshot date. Format: YYYY-12-31.'
fte_total	INT	'Total full-time equivalent headcount. Constraint: > 0. Range: 500-50000.'
fte_female_pct	DOUBLE	'Female employee percentage. Unit: %. Constraint: 0-100. Precision: 2 dp.'
fte_management_female_pct	DOUBLE	'Women in management percentage. Unit: %. Constraint: 0-100. Precision: 2 dp.'
new_hire_count	INT	'New hires during year. Constraint: >= 0.'
voluntary_turnover_pct	DOUBLE	'Voluntary attrition rate. Unit: %. Constraint: 0-100. Precision: 2 dp.'
training_hours_per_fte	DOUBLE	'Average training hours per FTE. Unit: hours. Constraint: >= 0. Range: 8-120.'
discrimination_cases	INT	'Reported discrimination cases (GRI 406). Constraint: >= 0.'
PARTITIONED BY		
reporting_year	INT	'Metrics reporting year. Range: 2020-2035.'

Table: esg_curated.ghg_scope1
Column	Type	Comment
facility_id	STRING	'Facility identifier. FK to facility_master. Joins to facility_type, province.'
scope1_tco2e	DOUBLE	'Total Scope 1 emissions. Unit: tCO2e. Constraint: >= 0. Precision: 4 dp. Formula: natgas + diesel.'
scope1_natgas_tco2e	DOUBLE	'Scope 1 from natural gas. Unit: tCO2e. Constraint: >= 0. Precision: 4 dp.'
scope1_diesel_tco2e	DOUBLE	'Scope 1 from diesel. Unit: tCO2e. Constraint: >= 0. Precision: 4 dp.'
total_natgas_gj	DOUBLE	'Annual natural gas consumed. Unit: GJ. Constraint: >= 0.'
total_diesel_liters	DOUBLE	'Annual diesel consumed. Unit: liters. Constraint: >= 0.'
imputed_months	INT	'Count of imputed months. Constraint: 0-12. Drives data_quality_score.'
data_quality_score	INT	'Quality score. ENUM: 1(0 imputed), 2(1-2), 3(3-5), 4(6+ excluded).'
emission_factor_source	STRING	'EF source reference. Must match raw zone ef_source.'
methodology	STRING	'Fixed: GHG_Protocol_Corporate_Standard_v2015.'
consolidation_approach	STRING	'ENUM: operational_control, equity_share. Default: operational_control.'
PARTITIONED BY		
reporting_year	INT	'Emission reporting year. Range: 2020-2035.'

Table: esg_curated.ghg_scope2
Column	Type	Comment
facility_id	STRING	'Facility identifier. FK to facility_master.'
total_consumption_mwh	DOUBLE	'Annual electricity consumed. Unit: MWh. Formula: SUM(electricity_kwh)/1000.'
scope2_location_tco2e	DOUBLE	'Location-based Scope 2. Unit: tCO2e. Precision: 3 dp. Always computed.'
scope2_market_tco2e	DOUBLE	'Market-based Scope 2. Unit: tCO2e. Precision: 3 dp. Floored at 0.'
grid_region	STRING	'Grid region used for EF selection. ENUM: java_bali, sumatra, kalimantan, sulawesi, national.'
grid_ef_applied	DOUBLE	'Grid EF applied. Unit: kg CO2/kWh. From region mapping.'
rec_mwh_applied	DOUBLE	'REC MWh deducted from market-based. Constraint: <= total_consumption_mwh.'
rec_applied_pct	DOUBLE	'REC coverage percentage. Unit: %. Formula: rec_mwh/total_mwh × 100.'
has_ppa	BOOLEAN	'Power Purchase Agreement flag.'
data_quality_score	INT	'Quality score 1-4.'
methodology	STRING	'Fixed: GHG_Protocol_Scope2_Guidance_2015.'
PARTITIONED BY		
reporting_year	INT	'Emission reporting year. Range: 2020-2035.'

Table: esg_curated.ghg_scope3_financed
Column	Type	Comment
sector_nace	STRING	'NACE sector code. PK component. One of 10 allowed values.'
loan_count	INT	'Count of validated loans in sector. Constraint: > 0.'
borrower_count	INT	'Count distinct borrowers. Constraint: > 0.'
total_outstanding_idr_trillion	DOUBLE	'Total outstanding. Unit: IDR trillion. Precision: 6 dp.'
financed_emissions_gross_tco2e	DOUBLE	'Gross financed emissions. Unit: tCO2e. Precision: 2 dp.'
financed_emissions_weighted_tco2e	DOUBLE	'Confidence-weighted emissions. Unit: tCO2e. Precision: 2 dp. Must be <= gross.'
avg_pcaf_score	DOUBLE	'Average PCAF quality. Constraint: 1.0-5.0. Precision: 2 dp.'
high_quality_data_pct	DOUBLE	'Pct loans with PCAF 1-2. Unit: %. Precision: 4 dp.'
PARTITIONED BY		
reporting_year	INT	'Emission reporting year. Range: 2020-2035.'

Table: esg_aggregated.ghg_summary_annual
Column	Type	Comment
metric_key	STRING	'Composite PK: {bank_id}_{reporting_year}. Unique per record.'
scope1_tco2e	DOUBLE	'Total Scope 1. Unit: tCO2e. Precision: 3 dp. SUM across all facilities.'
scope2_location_tco2e	DOUBLE	'Total Scope 2 location-based. Unit: tCO2e. Precision: 3 dp.'
scope2_market_tco2e	DOUBLE	'Total Scope 2 market-based. Unit: tCO2e. Precision: 3 dp. Can be 0.'
scope3_cat15_gross_tco2e	DOUBLE	'Scope 3 Cat.15 gross financed. Unit: tCO2e. Precision: 2 dp.'
scope3_cat15_weighted_tco2e	DOUBLE	'Scope 3 Cat.15 confidence-weighted. Unit: tCO2e. Precision: 2 dp.'
intensity_tco2e_per_idr_bn	DOUBLE	'Emission intensity per revenue. Unit: tCO2e/IDR bn. Precision: 6 dp.'
intensity_tco2e_per_fte	DOUBLE	'Emission intensity per FTE. Unit: tCO2e/FTE. Precision: 4 dp. Scope 1+2 only.'
yoy_change_pct	DOUBLE	'Year-over-year change. Unit: %. Precision: 2 dp. NULL for base year.'
vs_base_year_change_pct	DOUBLE	'Change vs base year. Unit: %. Precision: 2 dp. NULL for base year.'
avg_pcaf_data_quality	DOUBLE	'Portfolio-weighted PCAF score. Constraint: 1.0-5.0.'
assurance_level	STRING	'ENUM: none, limited, reasonable. Default: none.'
PARTITIONED BY		
reporting_year	INT	'Reporting year. Range: 2020-2035.'

Table: esg_aggregated.pcaf_by_sector
Column	Type	Comment
sector_nace	STRING	'NACE sector code. PK component.'
sector_display_name	STRING	'Human-readable sector name.'
loan_count	INT	'Loans in sector. Constraint: > 0.'
borrower_count	INT	'Distinct borrowers. Constraint: > 0.'
total_outstanding_idr_trillion	DOUBLE	'Sector outstanding. Unit: IDR trillion. Precision: 6 dp.'
financed_emissions_gross_tco2e	DOUBLE	'Sector gross financed emissions. Unit: tCO2e. Precision: 2 dp.'
financed_emissions_weighted_tco2e	DOUBLE	'Sector weighted emissions. Unit: tCO2e. Precision: 2 dp.'
emission_intensity_per_idr_bn	DOUBLE	'Sector intensity. Unit: tCO2e/IDR bn. Precision: 4 dp.'
avg_pcaf_score	DOUBLE	'Sector avg PCAF quality. Constraint: 1.0-5.0.'
pct_of_total_portfolio	DOUBLE	'Sector share of total outstanding. Unit: %. Precision: 2 dp.'
pct_of_total_financed_emissions	DOUBLE	'Sector share of total financed emissions. Unit: %. Precision: 2 dp.'
yoy_change_emissions_pct	DOUBLE	'YoY change in sector financed emissions. Unit: %. Precision: 2 dp.'
PARTITIONED BY		
reporting_year	INT	'Reporting year. Range: 2020-2035.'

4.4 Athena Query Requirements
REQ-DDL-11: Prepared Statement Queries
Kiro IDE MUST generate parameterized Athena queries (prepared statements) for the following use cases. These queries are invoked by the AthenaQueryFn Lambda at runtime.

Query 1: GHG Summary for Report Year
Purpose: Fetch all aggregated metrics for a single reporting year. Used as primary DATA INPUT for section generation. 
Parameters: reporting_year (INT), bank_id (STRING)
PREPARE ghg_summary_query FROM
SELECT
    metric_key,
    scope1_tco2e,
    scope2_location_tco2e,
    scope2_market_tco2e,
    scope3_cat15_gross_tco2e,
    scope3_cat15_weighted_tco2e,
    intensity_tco2e_per_idr_bn,
    intensity_tco2e_per_fte,
    yoy_change_pct,
    vs_base_year_change_pct,
    avg_pcaf_data_quality,
    assurance_level
FROM esg_aggregated.ghg_summary_annual
WHERE reporting_year = ?
  AND metric_key LIKE CONCAT(?, '_%');
Execution: EXECUTE ghg_summary_query USING 2025, 'GENERIC_FI_001';
________________________________________
Query 2: PCAF Sector Breakdown (Top Emitters)
Purpose: Fetch sector-level financed emissions ranked by contribution. Used for PCAF section generation. Parameters: reporting_year (INT)
PREPARE pcaf_sector_query FROM
SELECT
    sector_nace,
    sector_display_name,
    loan_count,
    borrower_count,
    total_outstanding_idr_trillion,
    financed_emissions_gross_tco2e,
    financed_emissions_weighted_tco2e,
    emission_intensity_per_idr_bn,
    avg_pcaf_score,
    pct_of_total_portfolio,
    pct_of_total_financed_emissions,
    yoy_change_emissions_pct
FROM esg_aggregated.pcaf_by_sector
WHERE reporting_year = ?
ORDER BY financed_emissions_gross_tco2e DESC
LIMIT 10;
________________________________________
Query 3: Multi-Year Trend (YoY Narrative)
Purpose: Fetch all available years for trend analysis and YoY narrative generation.
Parameters: bank_id (STRING)
PREPARE trend_query FROM
SELECT
    reporting_year,
    scope1_tco2e,
    scope2_location_tco2e,
    scope2_market_tco2e,
    scope3_cat15_gross_tco2e,
    (scope1_tco2e + scope2_market_tco2e + scope3_cat15_gross_tco2e) AS total_tco2e,
    yoy_change_pct,
    intensity_tco2e_per_idr_bn
FROM esg_aggregated.ghg_summary_annual
WHERE metric_key LIKE CONCAT(?, '_%')
ORDER BY reporting_year ASC;
________________________________________
Query 4: Validation Cross-Check (Sum Consistency — Rule R2)
Purpose: Verify that stored total equals component sum. Used by ValidationFn Lambda. 
Parameters: reporting_year (INT), bank_id (STRING)
PREPARE validation_sum_check FROM
SELECT
    reporting_year,
    scope1_tco2e,
    scope2_market_tco2e,
    scope3_cat15_gross_tco2e,
    (scope1_tco2e + scope2_market_tco2e + scope3_cat15_gross_tco2e) AS computed_total,
    -- Note: total_tco2e not stored separately; it IS the sum.
    -- This query validates that the individual components are internally consistent.
    ABS(
        scope1_tco2e + scope2_market_tco2e + scope3_cat15_gross_tco2e
        - (scope1_tco2e + scope2_market_tco2e + scope3_cat15_gross_tco2e)
    ) AS discrepancy_tco2e
FROM esg_aggregated.ghg_summary_annual
WHERE reporting_year = ?
  AND metric_key LIKE CONCAT(?, '_%');
Validation Rule: discrepancy_tco2e MUST be ≤ 0.001. If exceeded, GATE-AGG-01 fails.
________________________________________
Query 5: Scope 1 Component Reconciliation
Purpose: Verify Scope 1 natgas + diesel = total at curated level before aggregation. Parameters: reporting_year (INT)
PREPARE scope1_reconciliation FROM
SELECT
    facility_id,
    scope1_natgas_tco2e,
    scope1_diesel_tco2e,
    scope1_tco2e,
    ABS(scope1_natgas_tco2e + scope1_diesel_tco2e - scope1_tco2e) AS component_discrepancy
FROM esg_curated.ghg_scope1
WHERE reporting_year = ?
  AND ABS(scope1_natgas_tco2e + scope1_diesel_tco2e - scope1_tco2e) > 0.0001;
Expected Result: Zero rows returned. Any rows indicate ETL calculation defect (GATE-S1-03 failure).
________________________________________
Query 6: PCAF Gross vs Weighted Consistency
Purpose: Verify weighted ≤ gross for all sectors (VAL-NUM-06 pre-check). Parameters: reporting_year (INT)
PREPARE pcaf_consistency_check FROM
SELECT
    sector_nace,
    financed_emissions_gross_tco2e,
    financed_emissions_weighted_tco2e,
    (financed_emissions_weighted_tco2e - financed_emissions_gross_tco2e) AS excess
FROM esg_aggregated.pcaf_by_sector
WHERE reporting_year = ?
  AND financed_emissions_weighted_tco2e > financed_emissions_gross_tco2e;
Expected Result: Zero rows returned. Any rows indicate confidence factor miscalculation.
________________________________________
REQ-DDL-12: Query Workgroup Configuration
Property	Required Value	Purpose
Workgroup name	esg-reporting-workgroup	Isolation from other Athena workloads
Result location	s3://${BUCKET}/athena-results/	Query result storage
Encryption	SSE-KMS with ESG-dedicated key	Data at rest encryption
Bytes scanned limit	10 GB per query	Cost control
Query timeout	300 seconds	Prevent runaway queries
Publish metrics to CloudWatch	true	Monitoring

REQ-DDL-13: Query Tagging (Traceability)
Every Athena query executed by the system MUST include the following request tags:
Tag Key	Tag Value	Purpose
esg:execution_id	Step Functions execution ARN	Links query to workflow run
esg:component	athena_query_fn	Identifies calling component
esg:reporting_year	{year}	Audit trail
esg:purpose	section_data or validation	Distinguishes data fetch from validation

 
5. Hybrid Prompt Architecture Specifications
The agent uses a two-layer modular prompt architecture: a universal Base Prompt combined at runtime with one of four mutually exclusive Framework Overlay prompts. This section specifies the requirements for each layer, the required disclosures each overlay MUST mandate, and the runtime composition rules.
5.1 Prompt Architecture Overview
Component	File Name	Token Budget	Role and Responsibility
Base System Prompt	system_base.txt	~900 tokens	Universal rules: institution identity, data integrity rules (5 absolute prohibitions), writing style, output JSON contract, and hallucination prevention checklist.
GRI 305 Overlay	overlay_gri305.txt	~450 tokens	GRI Standard structure, disclosure-level requirements (GRI 305-1 through 305-5), required GRI Content Index entry format per section, and GRI-native terminology list.
IFRS S2 Overlay	overlay_ifrs_s2.txt	~500 tokens	TCFD four-pillar structure (Governance, Strategy, Risk Management, Metrics & Targets), paragraph-level requirements per pillar, SASB FN-CB-410 industry standard reference, and IFRS-native phrase conventions.
CSRD/ESRS E1 Overlay	overlay_esrs_e1.txt	~550 tokens	ESRS E1 datapoint coverage checklist (E1-1 through E1-9), EU Taxonomy alignment disclosure requirements, double materiality terminology, and IRO (Impact, Risk, Opportunity) categorisation instructions.
OJK PSPK Overlay	overlay_ojk_pspk.txt	~400 tokens	Indonesian banking regulator format, POJK 51/POJK.03/2017 structural requirements, Bahasa Indonesia toggle instruction (default: English), and OJK-specific table format mandates.

Token Budget Constraint
Total prompt per invocation MUST NOT exceed 4,000 tokens (system + overlay + section template + DATA INPUT). This ensures maximum output token allocation for Claude 3.5 Sonnet's 200K context window.
Runtime Token Allocation:
├── System Base Prompt:     ~900 tokens (fixed)
├── Framework Overlay:      ~400-550 tokens (varies by framework)
├── Section Template:       ~300-500 tokens (varies by section)
├── DATA INPUT (Athena):    ~500-2,000 tokens (varies by data volume)
├── RAG Context (KB):       ~500-700 tokens (capped per section)
└── TOTAL INPUT:            ~2,600-4,650 tokens
    OUTPUT BUDGET:          ~2,000-4,000 tokens (section narrative)

5.2 Base Prompt — Mandatory Structural Requirements
REQ-PROMPT-01: Five Data Integrity Rules (Absolute Prohibitions)
The base prompt MUST contain these five rules verbatim (or semantically equivalent). These are the anti-hallucination backbone:
Rule #	Rule Text (Mandatory)	Rationale
DI-1	"You MUST NOT generate, fabricate, estimate, or infer any numerical value. Every number in your output MUST exist verbatim in the DATA INPUT section below."	Prevents LLM from inventing metrics
DI-2	"You MUST NOT perform arithmetic calculations. All totals, percentages, year-over-year changes, and intensity ratios are PRE-COMPUTED in DATA INPUT. Use them as-is."	Prevents miscalculation of GHG totals
DI-3	"You MUST NOT round, truncate, or modify any numerical value from DATA INPUT. Report numbers exactly as provided, including decimal places."	Preserves audit-grade precision
DI-4	"If a required data point is not present in DATA INPUT, you MUST state: 'Data not available for this reporting period.' You MUST NOT substitute with estimates or industry averages."	Prevents gap-filling hallucination
DI-5	"You MUST NOT reference, cite, or quote any external source not provided in the RAG_CONTEXT section. If regulatory text is needed but not in RAG_CONTEXT, state: 'Refer to [Standard Name] for detailed requirements.'"	Prevents fabricated citations

REQ-PROMPT-02: Output JSON Contract
The base prompt MUST specify this exact output structure. Every section generation MUST return JSON conforming to this schema:
{
  "section_id": "STRING — format: {framework}_{section_type}_{year}",
  "title": "STRING — section heading for DOCX",
  "paragraphs": [
    {
      "text": "STRING — markdown-formatted paragraph text",
      "paragraph_type": "ENUM: narrative | methodology | footnote | forward_looking"
    }
  ],
  "tables": [
    {
      "caption": "STRING — table title",
      "headers": ["STRING array — column headers"],
      "rows": [["STRING array — cell values"]],
      "source_note": "STRING — data source attribution"
    }
  ],
  "key_metrics": [
    {
      "label": "STRING — metric display name",
      "value": "NUMBER — exact value from DATA INPUT",
      "unit": "STRING — tCO2e | % | tCO2e/IDR bn | etc.",
      "source_column": "STRING — aggregated zone column name"
    }
  ],
  "footnotes": ["STRING array — methodology notes, caveats"],
  "framework_references": ["STRING array — e.g., GRI 305-1a, IFRS S2 para 29"],
  "data_sources_used": ["STRING array — column names from DATA INPUT actually referenced"]
}
Constraint: If the LLM returns non-JSON or malformed JSON, the ValidationFn MUST trigger RETRY (Section 7.4).
REQ-PROMPT-03: Writing Style Mandates
Attribute	Requirement
Person	Third person: "The institution", "The bank" (never "we", "our", "I")
Voice	Active voice preferred; passive acceptable for methodology descriptions
Tense	Past tense for reporting period data; present tense for ongoing policies; future tense ONLY for targets
Register	Formal professional English; no colloquialisms, no marketing language
Precision	Numbers reported to exact decimal places as in DATA INPUT
Hedging	Prohibited for factual claims. Allowed ONLY for forward-looking statements with qualifier: "subject to market conditions" or "pending regulatory developments"
Length	Controlled by section template {paragraph_count} parameter

REQ-PROMPT-04: Conditional Disclosure Rules
Condition	Trigger	Required Action
data_quality_score >= 3	Imputation detected	Add footnote: "X months of data for Y facilities were estimated using facility-type averages. Data quality score: Z/4."
rec_applied_pct > 0	REC instruments used	Add paragraph explaining market-based adjustment methodology
yoy_change_pct is NULL	Base year or first year	Omit YoY comparison paragraph entirely; do not state "0% change"
assurance_level = 'none'	No external assurance	Add footnote: "These figures have not been subject to external assurance for the current reporting period."
avg_pcaf_data_quality > 3.5	Low PCAF quality	Add paragraph on data quality improvement roadmap

5.3 Framework Overlay — Required Disclosures per Framework
5.3.1 GRI 305 Overlay — Required Disclosures
File: prompts/overlay_gri305.txt
Disclosure	GRI Reference	Required Content / Mandatory Fields
GRI 305-1	Direct (Scope 1) GHG Emissions	Gross direct GHG in tCO2e; gases included (CO2, CH4, N2O); biogenic CO2 if material; base year; recalculation rationale; emission factor source; consolidation approach; GRI Content Index entry.
GRI 305-2	Energy Indirect (Scope 2) GHG	Location-based AND market-based Scope 2 (dual reporting mandatory); contractual instruments (PPAs, RECs, green tariffs); residual mix emission factor for market-based.
GRI 305-3	Other Indirect (Scope 3) GHG	Material Scope 3 categories only; Category 15 (Investments/Financed Emissions) is material for financial institutions; PCAF methodology reference required.
GRI 305-4	GHG Emissions Intensity	Intensity metric: tCO2e per IDR billion operating revenue; state whether market-based or location-based Scope 2 is used; denominator definition required.
GRI 305-5	Reduction of GHG Emissions	Absolute reductions in tCO2e achieved during period; calculation methodology; exclusion of offsets from reduction figure unless labelled separately.

GRI-Specific Terminology (MUST use in narrative):
Term	Usage Context
"The organization"	Subject of all disclosure statements
"Operational control"	Consolidation approach (default)
"Base year"	Reference year for comparison
"Recalculation"	When base year data is restated
"Biogenic emissions"	CO2 from biological sources (report separately)
"Contractual instruments"	RECs, PPAs, green tariffs for market-based

GRI Content Index Entry Format (per section):
| GRI Standard | Disclosure | Page Reference | Omission Reason |
Each section MUST end with a Content Index entry row that maps to the generated section.

5.3.2 IFRS S2 Overlay — Required Disclosures
File: prompts/overlay_ifrs_s2.txt

Pillar	IFRS S2 Reference	Required Content
Governance	S2.6–S2.10	Role of governing body in overseeing climate risks; management-level processes; terminology: "governing body", "management", "oversight".
Strategy	S2.11–S2.22	Climate risks and opportunities over short/medium/long term; business model impact; scenario analysis referencing 1.5°C and 2.0°C pathways; transition risks (policy, legal, technology, market, reputational); physical risks (acute and chronic) with geographic specificity.
Risk Management	S2.23–S2.25	Processes to identify, assess, and manage climate-related risks; integration of climate risk into enterprise risk management framework.
Metrics & Targets	S2.26–S2.42	SASB FN-CB-410 industry-based metrics; GHG Scope 1, 2, 3 in tCO2e; GHG Protocol methodology; financed emissions via PCAF Standard; absolute or intensity climate targets with base year; internal carbon price if applied.

IFRS S2 Mandatory Phrase Conventions (REQ-PROMPT-05):
Phrase	When to Use	Never Use Instead
"climate-related risks and opportunities"	Every Strategy paragraph	"climate risks" alone
"financed emissions"	Scope 3 Cat.15 context	"portfolio emissions" or "lending emissions"
"transition plan"	Strategy section	"decarbonisation plan"
"scenario analysis"	Strategy section	"stress testing" (unless ERM context)
"cross-industry metric"	Metrics section	"universal metric"
"industry-based metric"	SASB FN-CB-410 context	"sector metric"
"governing body"	Governance section	"board" (unless quoting local regulation)

IFRS S2 Time Horizon Definitions (MUST state in Strategy):
Horizon	Definition	Typical Range
Short-term	Aligned with financial reporting cycle	0–2 years
Medium-term	Aligned with strategic planning cycle	2–5 years
Long-term	Beyond strategic planning horizon	5–30+ years

SASB FN-CB-410 Industry Metrics (Financial Institutions):
Metric Code	Metric Name	Required Disclosure
FN-CB-410a.1	Commercial and industrial credit exposure by industry	Sector breakdown of loan portfolio
FN-CB-410a.2	Description of approach to incorporation of ESG factors in credit analysis	Qualitative methodology
FN-CB-410a.3	Financed emissions (Scope 3 Cat.15)	PCAF-calculated tCO2e

5.3.3 CSRD/ESRS E1 Overlay — Required Disclosures

File: prompts/overlay_esrs_e1.txt
REQ-PROMPT-06: The overlay MUST mandate coverage of ALL nine E1 datapoints:
Datapoint	ESRS Reference	Required Content
E1-1	Transition plan for climate change mitigation	Paris Agreement alignment; GHG reduction levers; CapEx/OpEx allocation; timeline with milestones; locked-in emissions disclosure.
E1-2	Policies related to climate change mitigation and adaptation	Policy scope (own operations + value chain); alignment with 1.5°C; engagement with value chain actors.
E1-3	Actions and resources related to climate change policies	Specific actions taken/planned; resources allocated (€/IDR); expected outcomes; timeline.
E1-4	Targets related to climate change mitigation and adaptation	Absolute AND intensity targets; base year; target year; interim milestones; SBTi alignment status.
E1-5	Energy consumption and mix	Total energy (MWh); renewable vs non-renewable split (%); energy from fossil sources breakdown.
E1-6	Gross Scopes 1, 2, 3 and Total GHG emissions	Scope 1 + 2 + 3 in tCO2e; by country if material; methodology; significant changes from prior period.
E1-7	GHG removals and GHG mitigation projects financed through carbon credits	Removals (if any); carbon credits purchased; retirement status; registry used.
E1-8	Internal carbon pricing	Internal carbon price (if applied); scope of application; decision-making influence.
E1-9	Anticipated financial effects from material physical and transition risks	Physical risk exposure (€/IDR); transition risk exposure; opportunities; time horizons; % of assets at risk.
CSRD/ESRS-Specific Terminology:
Term	Mandatory Usage
"Double materiality"	Must appear in introduction paragraph — state that topic passes BOTH impact materiality AND financial materiality assessments
"Impact, Risk, Opportunity (IRO)"	Categorisation framework for all climate-related matters
"Value chain"	Must specify: upstream, own operations, downstream
"Transition plan"	ESRS E1-1 specific; must reference Paris Agreement
"Locked-in emissions"	Emissions from existing assets/contracts that cannot be avoided
"EU Taxonomy alignment"	If applicable; state % of revenue/CapEx/OpEx aligned
Double Materiality Assessment Statement (MUST include):
"Climate change has been assessed as material under both impact materiality 
(the institution's impact on climate through GHG emissions) and financial 
materiality (climate-related risks and opportunities affecting the institution's 
financial position, performance, and cash flows)."
IRO Categorisation Table (MUST include in E1-9):
Category	Type	Time Horizon	Likelihood	Magnitude
Physical — Acute	Flooding, extreme weather	Short-medium	[from data]	[from data]
Physical — Chronic	Sea level rise, temperature	Long-term	[from data]	[from data]
Transition — Policy	Carbon pricing, regulation	Short-medium	[from data]	[from data]
Transition — Technology	Stranded assets	Medium-long	[from data]	[from data]
Opportunity	Green finance products	Short-medium	[from data]	[from data]

5.3.4 OJK PSPK Overlay — Required Disclosures
File: prompts/overlay_ojk_pspk.txt
Category	OJK Reference	Required Content
Governance	POJK 51 Art. 4-7	Sustainability committee structure; board competence in sustainability; oversight frequency (minimum quarterly); integration with risk committee.
Strategy	POJK 51 Art. 8-12	Sustainable finance action plan (RAKB); green asset ratio; sustainable portfolio percentage; alignment with Indonesia NDC (Net Zero 2060).
Risk Management	POJK 51 Art. 13-16	Climate stress testing methodology; physical/transition risk in ICAAP; sector concentration risk for high-carbon sectors; KBMI classification context.
Environmental Metrics	SE OJK Circular	Scope 1/2/3 emissions (tCO2e); energy intensity; financed emissions (PCAF); green portfolio percentage; renewable energy usage.
Social Metrics	SE OJK Circular	Financial inclusion metrics; MSME lending ratio; diversity statistics; community investment; customer complaint resolution.
Governance Metrics	SE OJK Circular	Anti-corruption training coverage; ethics violations; ESG-linked remuneration; whistleblower cases.

OJK-Specific Table Format Mandates:
The OJK PSPK overlay MUST instruct the agent to produce tables in the following format (matching OJK Circular template):
Table Format: OJK PSPK Environmental Performance
| No. | Indicator | Unit | Current Year | Prior Year | Change (%) | Target | Achievement |
Indonesia-Specific Context (MUST inject):
Context Item	Value	Purpose
KBMI Classification	"KBMI 3" (default for POC)	Determines reporting scope requirements
NDC Reference	"Indonesia Enhanced NDC: 31.89% unconditional, 43.2% conditional by 2030"	Alignment context
Net Zero Target	"Indonesia Long-Term Strategy: Net Zero by 2060 or sooner"	Long-term framing
Grid Factor	"PLN National Grid 2023: 0.7886 kg CO2/kWh"	Local emission factor context
Regulation	"POJK No. 51/POJK.03/2017 concerning Sustainable Finance"	Citation format
Effective Date	"Mandatory for KBMI 3-4 banks from January 2027 (PSPK)"	Urgency context

Bahasa Indonesia Toggle (REQ-PROMPT-07):
IF language_toggle = "id":
    Generate all narrative in Bahasa Indonesia (formal/baku)
    Keep technical terms in English: tCO2e, PCAF, GHG Protocol, Scope 1/2/3
    Use OJK official terminology for regulatory references
ELSE (default):
    Generate in professional English
    Include Indonesian regulation names in original Bahasa (parenthetical)
OJK PSPK Style Rules:
Rule	Requirement
Numbering	Use "No." column in all tables (sequential integer)
Currency	IDR with thousand separator (.) — e.g., "IDR 1.500.000.000.000"
Percentage	Always show 2 decimal places with "%" suffix
Year reference	"Tahun Pelaporan 2025" in Bahasa mode; "Reporting Year 2025" in English
Regulation citation	Full citation on first mention: "POJK No. 51/POJK.03/2017 tentang Penerapan Keuangan Berkelanjutan bagi Lembaga Jasa Keuangan, Emiten, dan Perusahaan Publik"

5.4 Runtime Prompt Composition Rules

REQ-PROMPT-12: Composition Order
At runtime, the prompt is assembled in this exact order:
[1] SYSTEM MESSAGE:
    └── system_base.txt (full content)
    └── + "

---

"
    └── + overlay_{framework}.txt (full content)

[2] USER MESSAGE:
    └── "## DATA INPUT
"
    └── + {athena_query_result_json}
    └── + "

## RAG CONTEXT
"
    └── + {kb_retrieval_result}
    └── + "

## SECTION TEMPLATE
"
    └── + {section_template_with_placeholders_resolved}

REQ-PROMPT-13: One Overlay Per Invocation
Only ONE framework overlay is active per Claude invocation. The overlay is selected based on the framework parameter in the Step Functions input.
framework value	Overlay file loaded
GRI_305	overlay_gri305.txt
IFRS_S2	overlay_ifrs_s2.txt
CSRD_ESRS_E1	overlay_esrs_e1.txt
OJK_PSPK	overlay_ojk_pspk.txt
CON-PROMPT-01: Two or more overlays MUST NEVER be concatenated in a single invocation. This prevents conflicting disclosure requirements and keeps token budget within limits.



REQ-PROMPT-14: DATA INPUT Source Restriction
The DATA INPUT section MUST contain ONLY data from esg_aggregated zone tables. Data from raw or curated zones MUST NOT appear in the prompt.
Rationale: The aggregated zone is the single source of truth. All calculations are pre-validated. Exposing raw/curated data to the LLM creates risk of the LLM attempting its own calculations (violating DI-2).

REQ-PROMPT-15: RAG Context Token Cap
Section Type	RAG Token Cap	KB Query
Scope 1 disclosure	500 tokens	"GRI 305-1 disclosure requirements direct emissions"
Scope 2 disclosure	500 tokens	"GHG Protocol Scope 2 Guidance dual reporting location market"
PCAF financed emissions	700 tokens	"PCAF Global Standard financed emissions attribution factor data quality"
Governance	600 tokens	"IFRS S2 governance climate oversight board management"
Strategy & targets	700 tokens	"IFRS S2 strategy scenario analysis transition plan 1.5 degrees"
Executive summary	300 tokens	None (no RAG for executive summary — uses only DATA INPUT)

REQ-PROMPT-16: Multi-Framework Report Generation
When generating a multi-framework report (all 4 frameworks in one document), the Step Functions Map state iterates through sections in this order:
Iteration 1: framework=GRI_305, sections=[scope1, scope2, scope3_pcaf, intensity, reduction]
Iteration 2: framework=IFRS_S2, sections=[governance, strategy, risk_mgmt, metrics_targets]
Iteration 3: framework=CSRD_ESRS_E1, sections=[e1_1_transition, e1_5_energy, e1_6_ghg, e1_9_financial]
Iteration 4: framework=OJK_PSPK, sections=[env_metrics, social_metrics, gov_metrics]
Final: framework=NONE (no overlay), section=[executive_summary]
Executive Summary Rule: Generated LAST with no overlay, using only DATA INPUT. This ensures the summary reflects all previously generated content without framework-specific bias.

REQ-PROMPT-17: Prompt Versioning
Each prompt file MUST include a version header:
# VERSION: 1.0.0
# LAST_MODIFIED: 2025-05-29
# FRAMEWORK: {framework_name}
# TOKEN_COUNT: {approximate_tokens}
# COMPATIBLE_MODEL: anthropic.claude-3-5-sonnet-20241022-v2:0
Changes to any prompt file MUST increment the version and be logged in the Step Functions execution metadata for audit traceability.


 
6. Section Generation Prompt Templates
This section specifies the mandatory structure and required placeholder variables for each section-generation prompt template. Kiro IDE MUST generate template files in which every {placeholder} is substituted by the agent at runtime from Athena query results or Knowledge Base context. No placeholder MUST remain unresolved at invocation time.
6.1 Template: Scope 1 Direct GHG Emissions (scope1_template.txt)
This template generates the Scope 1 disclosure section. It is used for all four framework overlays with framework-specific paragraph count and table structure differences.
Placeholder Variable	Data Source	Validation Requirement
{framework}	Step Functions input	ENUM: GRI_305 | IFRS_S2 | CSRD_ESRS_E1 | OJK_PSPK. MUST match active overlay.
{section_id}	Template config	Format: {framework}_S1_{year}. Uniqueness enforced per report run.
{scope1_tco2e}	Athena aggregated	Must match scope1_tco2e in ghg_summary_annual. 3 decimal places. Unit: tCO2e.
{scope1_natgas_tco2e}	Athena aggregated	Component: scope1_natgas_tco2e from ghg_summary_annual. Sum with diesel must equal scope1_tco2e.
{scope1_diesel_tco2e}	Athena aggregated	Component: scope1_diesel_tco2e. Reconciliation rule: natgas + diesel = scope1_tco2e (tolerance: +/- 0.001 tCO2e).
{prior_year_scope1_tco2e}	Athena aggregated	From prior year record in ghg_summary_annual. NULL if reporting_year = base_year.
{yoy_scope1_change_pct}	Athena aggregated	Pre-computed yoy_change_pct. MUST match formula in REQ-ETL-25. NULL if prior year absent.
{base_year}	Step Functions input	Integer year: 2019 for this POC. Agent MUST NOT infer or modify this value.
{ef_source}	Athena aggregated	emission_factor_source value from ghg_summary_annual. Used in footnote citation.
{scope1_data_quality_score}	Athena aggregated	Integer 1-4. If >=3, agent MUST add footnote about imputed months per REQ-PROMPT-04.
{rag_context_scope1}	Bedrock KB RAG	Retrieved context from Knowledge Base for Scope 1 regulatory background. 500-token maximum.

Framework-Specific Paragraph Count
Framework	Paragraph Count	Table Required	Additional Requirements
GRI_305	4–6 paragraphs	Yes: Source breakdown table (natgas, diesel, total)	GRI Content Index entry at end
IFRS_S2	3–5 paragraphs	Yes: Cross-industry metric table	Reference IFRS S2 para 29(a)
CSRD_ESRS_E1	5–7 paragraphs	Yes: E1-6 datapoint table	Double materiality framing
OJK_PSPK	3–4 paragraphs	Yes: OJK format table (No., Indicator, Unit, Current, Prior, Change%, Target)	POJK 51 reference

Template Body Structure (REQ-TMPL-01)
## SECTION TEMPLATE: Scope 1 Direct GHG Emissions
SECTION_ID: {section_id}
FRAMEWORK: {framework}
REPORTING_YEAR: {reporting_year}

### OBJECTIVE
Generate a disclosure section reporting total Scope 1 direct GHG emissions 
for the reporting year. Include source breakdown, methodology transparency, 
base year comparison, and year-over-year trend analysis.

### DATA INPUT
{
  "scope1_tco2e": {scope1_tco2e},
  "scope1_natgas_tco2e": {scope1_natgas_tco2e},
  "scope1_diesel_tco2e": {scope1_diesel_tco2e},
  "prior_year_scope1_tco2e": {prior_year_scope1_tco2e},
  "yoy_scope1_change_pct": {yoy_scope1_change_pct},
  "base_year": {base_year},
  "ef_source": "{ef_source}",
  "data_quality_score": {scope1_data_quality_score},
  "consolidation_approach": "{consolidation_approach}"
}

### RAG CONTEXT
{rag_context_scope1}

### REQUIRED ELEMENTS
1. Opening paragraph: state total Scope 1 emissions with unit (tCO2e)
2. Source breakdown: natural gas combustion vs diesel combustion
3. Methodology paragraph: emission factors, GWP values, consolidation approach
4. Year-over-year comparison (OMIT if {yoy_scope1_change_pct} is NULL)
5. Base year comparison (OMIT if reporting_year = base_year)
6. Data quality footnote (INCLUDE ONLY if {scope1_data_quality_score} >= 3)
7. Table: emission source breakdown with values from DATA INPUT

### PARAGRAPH COUNT
{framework_paragraph_count}

### OUTPUT FORMAT
Return JSON per the contract in system_base.txt Section REQ-PROMPT-02.

6.2 Template: PCAF Financed Emissions (scope3_pcaf_template.txt)
This template generates the Scope 3 Category 15 financed emissions section. It is the most data-intensive section due to sector-level breakdown.

Placeholder Variables

Placeholder Variable	Data Source	Validation Requirement
{scope3_cat15_gross_tco2e}	Athena aggregated	SUM of gross financed emissions across all sectors. 2 decimal places.
{scope3_cat15_weighted_tco2e}	Athena aggregated	Confidence-weighted total. MUST be <= gross. MUST NOT be conflated with gross in narrative.
{total_portfolio_idr_trillion}	Athena aggregated	Total outstanding exposure in IDR trillions. 2 decimal places.
{avg_pcaf_data_quality}	Athena aggregated	Portfolio-weighted PCAF score 1.0-5.0. 2 decimal places.
{high_quality_data_pct}	Athena aggregated	Percentage of loans with PCAF score 1 or 2. 2 decimal places.
{sector_breakdown_json}	Athena curated	JSON array of top-5 sectors by financed emissions. Each object: { sector, outstanding_idr_t, gross_tco2e, pcaf_score, pct_of_portfolio }.
{rag_context_scope3_pcaf}	Bedrock KB RAG	PCAF Standard methodology context from KB. 700-token maximum for this section.

Framework-Specific Paragraph Count
Framework	Paragraph Count	Tables Required	Additional Requirements
GRI_305	5–7 paragraphs	1: Sector breakdown; 1: PCAF quality	GRI 305-3 reference; state "Category 15: Investments"
IFRS_S2	6–8 paragraphs	1: Sector breakdown; 1: SASB FN-CB-410a.3	Financial materiality framing; link to transition risk
CSRD_ESRS_E1	6–9 paragraphs	1: Sector breakdown; 1: E1-6 format	Value chain (downstream) framing; IRO categorisation
OJK_PSKP	4–6 paragraphs	1: OJK format table	POJK 51 reference; green portfolio % context

Template Body Structure (REQ-TMPL-02)
## SECTION TEMPLATE: PCAF Financed Emissions (Scope 3 Category 15)
SECTION_ID: {section_id}
FRAMEWORK: {framework}
REPORTING_YEAR: {reporting_year}

### OBJECTIVE
Generate a disclosure section reporting total financed emissions calculated 
under the PCAF Global GHG Accounting Standard. Include portfolio-level totals, 
sector breakdown (top 5 emitting sectors), data quality assessment, and 
year-over-year trend. CRITICAL: Gross and weighted figures MUST be reported 
as SEPARATE metrics. Never average or conflate them.

### DATA INPUT
{
  "scope3_cat15_gross_tco2e": {scope3_cat15_gross_tco2e},
  "scope3_cat15_weighted_tco2e": {scope3_cat15_weighted_tco2e},
  "total_portfolio_idr_trillion": {total_portfolio_idr_trillion},
  "avg_pcaf_data_quality": {avg_pcaf_data_quality},
  "high_quality_data_pct": {high_quality_data_pct},
  "portfolio_coverage_pct": {portfolio_coverage_pct},
  "prior_year_scope3_gross": {prior_year_scope3_gross},
  "yoy_scope3_change_pct": {yoy_scope3_change_pct},
  "sector_breakdown": {sector_breakdown_json}
}

### RAG CONTEXT
{rag_context_scope3_pcaf}

### REQUIRED ELEMENTS
1. Opening paragraph: state total gross financed emissions with unit
2. PCAF methodology paragraph: attribution factor formula, asset classes covered
3. Sector breakdown table: top 5 sectors by gross emissions
4. Data quality assessment: portfolio-weighted score, high-quality percentage
5. Gross vs weighted distinction paragraph (MANDATORY — VAL-NUM-06 enforced)
6. Year-over-year comparison (OMIT if {yoy_scope3_change_pct} is NULL)
7. Portfolio coverage statement
8. Data quality improvement roadmap (INCLUDE if {avg_pcaf_data_quality} > 3.5)

### PARAGRAPH COUNT
{framework_paragraph_count}

### CRITICAL CONSTRAINT
The narrative MUST clearly distinguish between:
- "Gross financed emissions" = {scope3_cat15_gross_tco2e} tCO2e
- "Confidence-weighted financed emissions" = {scope3_cat15_weighted_tco2e} tCO2e
These MUST appear as separate figures. Conflation triggers VAL-NUM-06 FAIL.

### OUTPUT FORMAT
Return JSON per the contract in system_base.txt Section REQ-PROMPT-02.

6.3 Template: GHG Emissions Intensity Section (intensity_template.txt)
This template generates the emissions intensity disclosure required by GRI 305-4, IFRS S2 Metrics, CSRD E1-6, and OJK PSPK environmental metrics.

Placeholder Variables
Placeholder Variable	Data Source	Validation Requirement
{framework}	Step Functions input	ENUM: GRI_305 | IFRS_S2 | CSRD_ESRS_E1 | OJK_PSPK.
{section_id}	Template config	Format: {framework}_INTENSITY_{year}.
{reporting_year}	Step Functions input	Integer: 2022–2035.
{intensity_tco2e_per_idr_bn}	Athena aggregated	Emission intensity per revenue. 6 decimal places. Unit: tCO2e/IDR billion.
{intensity_tco2e_per_fte}	Athena aggregated	Emission intensity per FTE. 4 decimal places. Unit: tCO2e/FTE. Scope 1+2 only.
{total_tco2e}	Athena aggregated	Numerator for revenue intensity: scope1 + scope2_market + scope3_cat15_gross.
{scope1_plus_scope2_tco2e}	Athena aggregated	Numerator for FTE intensity: scope1 + scope2_market.
{revenue_idr_billion}	Step Functions input / reference table	Denominator for revenue intensity. External financial data.
{fte_count}	Athena raw (hr_metrics)	Denominator for FTE intensity. From esg_raw.hr_metrics.fte_total.
{prior_year_intensity_revenue}	Athena aggregated	Prior year intensity per revenue. NULL if base year.
{prior_year_intensity_fte}	Athena aggregated	Prior year intensity per FTE. NULL if base year.
{yoy_intensity_revenue_change_pct}	Computed	((current - prior) / prior) × 100. Pre-computed.
{yoy_intensity_fte_change_pct}	Computed	((current - prior) / prior) × 100. Pre-computed.
{rag_context_intensity}	Bedrock KB RAG	GRI 305-4 / IFRS S2 intensity requirements. 400-token maximum.

Framework-Specific Requirements
Framework	Paragraph Count	Specific Requirements
GRI_305	3–4 paragraphs	State numerator (which scopes), denominator (revenue), and whether market-based or location-based Scope 2 is used
IFRS_S2	3–5 paragraphs	Frame as "cross-industry metric"; link to financial performance
CSRD_ESRS_E1	4–5 paragraphs	Include both revenue and FTE intensity; state value chain coverage
OJK_PSKP	2–3 paragraphs	OJK table format with Current/Prior/Change/Target columns

Template Body Structure (REQ-TMPL-03)
## SECTION TEMPLATE: GHG Emissions Intensity
SECTION_ID: {section_id}
FRAMEWORK: {framework}
REPORTING_YEAR: {reporting_year}

### OBJECTIVE
Generate a disclosure section reporting GHG emission intensity ratios. 
Two intensity metrics are required: (1) per revenue (IDR billion) using 
Scope 1+2+3, and (2) per FTE using Scope 1+2 only.

### DATA INPUT
{
  "intensity_tco2e_per_idr_bn": {intensity_tco2e_per_idr_bn},
  "intensity_tco2e_per_fte": {intensity_tco2e_per_fte},
  "total_tco2e_numerator": {total_tco2e},
  "scope1_plus_scope2_numerator": {scope1_plus_scope2_tco2e},
  "revenue_idr_billion": {revenue_idr_billion},
  "fte_count": {fte_count},
  "prior_year_intensity_revenue": {prior_year_intensity_revenue},
  "prior_year_intensity_fte": {prior_year_intensity_fte},
  "yoy_intensity_revenue_change_pct": {yoy_intensity_revenue_change_pct},
  "yoy_intensity_fte_change_pct": {yoy_intensity_fte_change_pct}
}

### RAG CONTEXT
{rag_context_intensity}

### REQUIRED ELEMENTS
1. Revenue intensity paragraph: state ratio, numerator definition, denominator
2. FTE intensity paragraph: state ratio, note Scope 1+2 only (excludes Scope 3)
3. Methodology note: state which Scope 2 method used (market-based for this POC)
4. Year-over-year comparison (OMIT if prior year values are NULL)
5. Table: Intensity metrics with current year, prior year, change %

### CRITICAL CONSTRAINTS
- Revenue intensity uses Scope 1 + Scope 2 (market) + Scope 3 Cat.15 (gross)
- FTE intensity uses Scope 1 + Scope 2 (market) ONLY — excludes Scope 3
- Agent MUST state this distinction explicitly in the narrative
- Agent MUST NOT recalculate intensity — use pre-computed values from DATA INPUT

### OUTPUT FORMAT
Return JSON per the contract in system_base.txt Section REQ-PROMPT-02.

6.4 Template: Governance and Oversight (governance_template.txt — IFRS S2 only)
This template generates the Governance section. It is primarily driven by IFRS S2 (Pillar 1) but also serves CSRD E1-1/E1-2 and OJK PSPK governance requirements. This is a qualitative section — it does NOT use numerical DATA INPUT from Athena.

Placeholder Variables
Placeholder Variable	Data Source	Validation Requirement
{framework}	Step Functions input	ENUM: IFRS_S2 | CSRD_ESRS_E1 | OJK_PSKP. (Not used for GRI 305 — GRI has no governance disclosure.)
{section_id}	Template config	Format: {framework}_GOV_{year}.
{reporting_year}	Step Functions input	Integer: 2022–2035.
{institution_name}	Step Functions input	String: institution display name for narrative.
{board_committee_name}	Step Functions input / config	Default: "Board Risk and Sustainability Committee". Configurable.
{oversight_frequency}	Step Functions input / config	Default: "quarterly". ENUM: monthly | quarterly | semi-annually.
{management_role}	Step Functions input / config	Default: "Chief Sustainability Officer (CSO)".
{erm_integration}	Step Functions input / config	Boolean: true/false. If true, state climate risk is integrated into ERM.
{rag_context_governance}	Bedrock KB RAG	IFRS S2 para 5–12 governance requirements. 600-token maximum.

Framework-Specific Requirements
Framework	Paragraph Count	Specific Requirements
IFRS_S2	5–7 paragraphs	TCFD Governance pillar; use "governing body" terminology; reference S2.6–S2.10
CSRD_ESRS_E1	4–6 paragraphs	E1-1 transition plan governance; E1-2 policy governance; double materiality assessment process
OJK_PSKP	3–5 paragraphs	POJK 51 Art. 4–7; sustainability committee; KBMI classification context

Template Body Structure (REQ-TMPL-04)
## SECTION TEMPLATE: Governance and Oversight
SECTION_ID: {section_id}
FRAMEWORK: {framework}
REPORTING_YEAR: {reporting_year}

### OBJECTIVE
Generate a governance disclosure section describing board-level and 
management-level oversight of climate-related risks and opportunities. 
This is a QUALITATIVE section — no numerical GHG data is required.

### DATA INPUT
{
  "institution_name": "{institution_name}",
  "board_committee_name": "{board_committee_name}",
  "oversight_frequency": "{oversight_frequency}",
  "management_role": "{management_role}",
  "erm_integration": {erm_integration}
}

### RAG CONTEXT
{rag_context_governance}

### REQUIRED ELEMENTS
1. Board oversight paragraph: committee name, mandate, climate competence
2. Management role paragraph: CSO/equivalent, reporting line, responsibilities
3. Monitoring frequency: how often climate matters are reviewed
4. ERM integration paragraph (INCLUDE if erm_integration = true)
5. Decision-making process: how climate considerations influence strategy

### CONSTRAINTS
- This section has NO numerical data from Athena aggregated zone
- Agent MUST NOT fabricate governance structures not in DATA INPUT
- Agent MUST NOT invent committee names, meeting frequencies, or roles
- If a governance element is not provided in DATA INPUT, state:
  "Governance arrangements for [element] are under development."

### OUTPUT FORMAT
Return JSON per the contract in system_base.txt Section REQ-PROMPT-02.

6.5 Common Template Requirements
These requirements apply to ALL section templates (REQ-TMPL-05 through REQ-TMPL-12):

REQ-TMPL-05: Placeholder Resolution Enforcement
Rule	Requirement
No unresolved placeholders	The SectionGenFn Lambda MUST verify that zero {placeholder} strings remain in the assembled prompt before invoking Bedrock. If any remain, the Lambda MUST throw UnresolvedPlaceholderError and log the placeholder name(s).
NULL handling	If a placeholder resolves to NULL (e.g., {prior_year_scope1_tco2e} for base year), the Lambda MUST substitute the literal string "NULL" and the template's REQUIRED ELEMENTS instructions handle omission logic.
Type enforcement	Numeric placeholders MUST be injected as JSON numbers (not strings). String placeholders MUST be injected as JSON strings (with quotes). Boolean placeholders MUST be true or false.

REQ-TMPL-06: Style Reference Anchor
Every template MAY include an optional {style_reference_excerpt} placeholder:
### STYLE REFERENCE (optional)
{style_reference_excerpt}
•	Source: Retrieved from KB using query "ESG report writing style financial institution"
•	Token cap: 200 tokens maximum
•	Purpose: Anchors the LLM's writing register to match audited ESG report tone
•	If KB returns no relevant style excerpt, omit this section entirely (do not inject empty string)

REQ-TMPL-07: Section Metadata Header
Every generated section JSON MUST include metadata for traceability:
{
  "metadata": {
    "section_id": "{section_id}",
    "framework": "{framework}",
    "reporting_year": {reporting_year},
    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "prompt_version": "{prompt_version}",
    "generation_timestamp": "{iso8601_timestamp}",
    "data_input_hash": "{sha256_of_data_input}",
    "rag_context_hash": "{sha256_of_rag_context}",
    "execution_id": "{step_functions_execution_arn}"
  },
  "section_id": "...",
  "title": "...",
  ...
}

REQ-TMPL-08: Imputation Footnote Trigger
If {data_quality_score} ≥ 3 for ANY section that uses GHG data, the template MUST instruct the agent to append:
"footnotes": [
  "Data quality note: {imputed_months} months of activity data for {affected_facilities} 
   facilities were estimated using facility-type monthly averages. The data quality score 
   for this reporting period is {data_quality_score}/4. The institution is implementing 
   smart meter infrastructure to improve data completeness."
]

REQ-TMPL-09: Forward-Looking Statement Qualifier
Any section template that includes targets or projections MUST instruct the agent to prefix forward-looking content with:
"This section contains forward-looking statements that are subject to risks, 
uncertainties, and assumptions. Actual results may differ materially from those 
expressed or implied."

REQ-TMPL-10: Cross-Section Consistency Rule
When multiple sections reference the same metric (e.g., scope1_tco2e appears in both Scope 1 section and Executive Summary), the DATA INPUT for both sections MUST be sourced from the SAME Athena query execution. The SectionGenFn Lambda MUST cache the Athena result and reuse it across all sections in the same Map iteration.

REQ-TMPL-11: Template File Naming Convention
Template	File Path
Scope 1	prompts/templates/scope1_template.txt
Scope 2	prompts/templates/scope2_template.txt
Scope 3 PCAF	prompts/templates/scope3_pcaf_template.txt
Intensity	prompts/templates/intensity_template.txt
Governance	prompts/templates/governance_template.txt
Strategy & Targets	prompts/templates/targets_template.txt

REQ-TMPL-12: Template Versioning
Each template file MUST include a version header (same format as prompt files):
# TEMPLATE_ID: scope1_template
# VERSION: 1.0.0
# LAST_MODIFIED: 2025-05-29
# FRAMEWORKS: GRI_305, IFRS_S2, CSRD_ESRS_E1, OJK_PSPK
# PLACEHOLDER_COUNT: 12
# PARAGRAPH_RANGE: 3-7
# DATA_DEPENDENCY: esg_aggregated.ghg_summary_annual
# RAG_DEPENDENCY: GRI 305-1, GHG Protocol Corporate Standard

 
7. Validation Rules and Numerical Tolerances
This section specifies all validation rules that the per-section validation Lambda function MUST enforce before a section may proceed to the assembly step. Validation occurs after the LLM generates a section JSON response, and before the section is added to the assembly list. Any validation failure triggers the Step Functions human review wait-for-task-token gate.
7.1 Numeric Consistency Validation Rules
Rule ID	Rule Description	Tolerance	Failure Behaviour
VAL-NUM-01	Every tCO2e value in generated paragraphs must match the corresponding DATA INPUT value	+/- 0.001 tCO2e	FAIL: section routed to human review queue with error_code NUM_MISMATCH and both values logged
VAL-NUM-02	Scope 1 component sum check: scope1_natgas + scope1_diesel must equal scope1_total	+/- 0.001 tCO2e	FAIL: ETL calculation defect. Block report assembly; alert ETL pipeline operator.
VAL-NUM-03	Percentage values in text must match pre-computed values in DATA INPUT	+/- 0.05 percentage points	FAIL: section routed to human review. Agent likely rounded independently.
VAL-NUM-04	YoY change percentage must be consistent with prior year and current year absolute values	+/- 0.1 percentage points	FAIL: validation Lambda recomputes expected value and logs delta for auditor review.
VAL-NUM-05	GHG intensity value in narrative must match intensity_tco2e_per_idr_bn from aggregated zone	+/- 0.000001 (6 dp)	FAIL: section held. Zero tolerance for misquoted intensity metrics.
VAL-NUM-06	PCAF gross and weighted financed emissions must not be conflated. Weighted must be <= gross.	Zero tolerance	FAIL: immediate section rejection. Conflation of PCAF gross/weighted is a material misstatement.
VAL-NUM-07	All tCO2e values in generated tables must match values in section JSON paragraphs	+/- 0.001 tCO2e	FAIL: internal inconsistency within the section. Section rejected and regenerated once.

REQ-VAL-01: Numeric Extraction Logic
The validation Lambda MUST implement the following numeric extraction algorithm:
ALGORITHM: extract_numeric_claims(section_json)

1. Parse section_json.paragraphs[].text for all numeric patterns:
   - Regex: r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(tCO2e|%|IDR|MWh|GJ)'
   - Also match: r'(\d+\.\d+)\s*tCO2e' (decimal without comma separator)
   
2. Parse section_json.tables[].rows[][] for all numeric cell values

3. For each extracted value:
   a. Identify the metric type (tCO2e, percentage, intensity, IDR)
   b. Map to the corresponding DATA INPUT field using label proximity
   c. Compare extracted value against DATA INPUT value
   d. Apply tolerance from VAL-NUM rules above
   e. Record: { extracted_value, expected_value, delta, rule_id, pass/fail }

4. Return validation_result: { 
     total_claims: INT, 
     passed: INT, 
     failed: INT, 
     failures: [{ rule_id, extracted, expected, delta, location }] 
   }

REQ-VAL-02: Numeric Mapping Rules
Metric Pattern in Text	Maps to DATA INPUT Field	Tolerance Rule
"X,XXX.XXX tCO2e" near "Scope 1" or "direct"	scope1_tco2e	VAL-NUM-01
"X,XXX.XXX tCO2e" near "natural gas"	scope1_natgas_tco2e	VAL-NUM-01
"X,XXX.XXX tCO2e" near "diesel"	scope1_diesel_tco2e	VAL-NUM-01
"X,XXX.XX tCO2e" near "financed" or "PCAF" or "Scope 3"	scope3_cat15_gross_tco2e	VAL-NUM-01
"X,XXX.XX tCO2e" near "weighted" or "confidence"	scope3_cat15_weighted_tco2e	VAL-NUM-06
"X.XX%" near "year-over-year" or "YoY" or "change"	yoy_change_pct	VAL-NUM-04
"X.XXXXXX tCO2e/IDR" or "X.XXXXXX per IDR billion"	intensity_tco2e_per_idr_bn	VAL-NUM-05
"X.XXXX tCO2e/FTE" or "X.XXXX per employee"	intensity_tco2e_per_fte	VAL-NUM-05

7.2 Structural Validation Rules
Rule ID	Rule Description	Failure Behaviour
VAL-STR-01	Section JSON MUST parse as valid JSON. No trailing commas, no single quotes, no comments.	RETRY: invoke SectionGenFn once more. If second attempt fails JSON parse, escalate to FAIL.
VAL-STR-02	Section JSON MUST contain all 7 required top-level keys: section_id, title, paragraphs, tables, key_metrics, footnotes, framework_references	FAIL: structural defect. Missing keys indicate prompt compliance failure.
VAL-STR-03	section_id format MUST match pattern: {FRAMEWORK}_{SECTION_TYPE}_{YEAR} (e.g., GRI_305_S1_2025)	WARN: log format deviation but allow assembly. Non-blocking.
VAL-STR-04	paragraphs array MUST contain between {min_paragraphs} and {max_paragraphs} items (per framework spec in Section 6)	WARN: paragraph count outside range. Section added with warning flag. Reviewer notified via SNS.
VAL-STR-05	Each paragraphs[].paragraph_type MUST be one of: narrative, methodology, footnote, forward_looking	FAIL: unknown paragraph type indicates prompt drift. Section rejected.
VAL-STR-06	tables array MUST contain at least 1 table for quantitative sections (Scope 1, 2, 3, Intensity). Governance section MAY have 0 tables.	FAIL for quantitative sections; PASS for governance.
VAL-STR-07	Each tables[].headers length MUST equal each tables[].rows[] length (column count consistency)	FAIL: malformed table. Section rejected and regenerated once.
VAL-STR-08	key_metrics array MUST contain at least 1 entry for quantitative sections. Each entry MUST have label, value, unit, source_column.	FAIL: missing key metrics prevents downstream validation cross-check.
VAL-STR-09	data_sources_used array MUST NOT be empty. Must reference at least one aggregated zone column name.	WARN: log for audit trail but allow assembly.

REQ-VAL-03: Structural Validation Execution Order
Structural validation MUST execute BEFORE numeric validation. Rationale: if JSON is malformed or keys are missing, numeric extraction will fail with misleading errors.
Execution Order:
1. VAL-STR-01 (JSON parse) — if FAIL → RETRY immediately, skip all other checks
2. VAL-STR-02 (required keys) — if FAIL → reject, skip numeric checks
3. VAL-STR-03 through VAL-STR-09 (structural checks)
4. VAL-NUM-01 through VAL-NUM-07 (numeric checks — only if structural passes)
5. VAL-PRH-01 through VAL-PRH-05 (prohibited content — runs in parallel with numeric)

7.3 Prohibited Content Validation Rules

Rule ID	Rule Description	Detection Method	Failure Behaviour
VAL-PRH-01	Section MUST NOT contain any number that does not exist in the DATA INPUT provided to the agent	Compare all extracted numbers against DATA INPUT value set. Any number not in the set (within tolerance) is a fabrication.	FAIL: immediate rejection. Fabricated number = hallucination. Log the fabricated value and surrounding context (±50 chars).
VAL-PRH-02	Section MUST NOT contain phrases indicating independent calculation: "calculated as", "computed by dividing", "we estimate", "approximately", "roughly"	Regex scan: `r'(calculated as	computed by
VAL-PRH-03	Section MUST NOT reference external sources not in RAG_CONTEXT: no URLs, no "according to [source not in KB]", no fabricated report titles	Regex scan for URLs: r'https?://\S+'; scan for "according to" + check if cited source exists in rag_context metadata	FAIL: fabricated citation. Log the citation text. Section rejected.
VAL-PRH-04	Section MUST NOT contain first-person pronouns: "we", "our", "us", "I", "my"	Regex: `r'\b(we	our
VAL-PRH-05	Section MUST NOT contain marketing/promotional language: "industry-leading", "best-in-class", "world-class", "cutting-edge", "pioneering"	Regex: `r'(industry.leading	best.in.class

REQ-VAL-04: Fabrication Detection Algorithm (VAL-PRH-01)
ALGORITHM: detect_fabricated_numbers(section_json, data_input)

1. Extract ALL numeric values from section_json (paragraphs + tables)
   → numeric_claims = [list of (value, unit, location)]

2. Build ALLOWED_VALUES set from data_input:
   → For each field in data_input:
     - Add the exact value
     - Add value × 1000 (for kg↔tonne conversion display)
     - Add value / 1000 (for tonne↔kilotonne display)
     - Add value × 100 (for decimal→percentage display)
   → Also add: reporting_year, base_year, paragraph counts, 
     and any integer constants (e.g., "12 months", "5 sectors")

3. For each claim in numeric_claims:
   - Check if claim.value is within tolerance of ANY value in ALLOWED_VALUES
   - Tolerance: ±0.001 for tCO2e; ±0.05 for %; ±0.000001 for intensity
   - If NO match found → flag as FABRICATED

4. Return: {
     fabricated_values: [{ value, unit, location, nearest_allowed, delta }],
     is_clean: BOOLEAN (true if fabricated_values is empty)
   }

REQ-VAL-05: Allowed Exceptions to VAL-PRH-01
The following numbers are ALWAYS allowed (not flagged as fabrication):
Allowed Value	Reason
Reporting year (e.g., 2025)	Temporal reference
Base year (e.g., 2019)	Temporal reference
Prior year (e.g., 2024)	Temporal reference
1, 2, 3 (ordinal/cardinal)	Natural language numbering
12 (months)	Standard temporal reference
1.5, 2.0 (°C scenarios)	IFRS S2 scenario analysis reference
100 (percentage base)	Mathematical constant
GWP values: 29.8, 273.0	Emission factor constants (if cited in methodology)
PCAF scores: 1, 2, 3, 4, 5	Quality tier references

7.4 Validation Outcome State Machine
Outcome	Trigger Condition	Required Action
PASS	All checks pass	Section added to assembly list. Step Functions proceeds to next section.
WARN	Paragraph count outside range; non-critical style issue	Section added with warning flag. Human reviewer is notified via SNS but assembly is not blocked.
RETRY	JSON parse error or first numeric mismatch	Section generation Lambda invoked once more with identical prompt. If second attempt passes, proceed. If fails again, escalate to FAIL.
FAIL	Numeric mismatch on retry; prohibited content detected; structural defect	Section held in SQS queue. Step Functions enters WaitForTaskToken state. Human reviewer must approve or reject via task token. Assembly is blocked until resolution.

REQ-VAL-06: State Transition Diagram

 

REQ-VAL-07: Validation Lambda Response Contract
The ValidationFn Lambda MUST return this exact JSON structure:
{
  "section_id": "GRI_305_S1_2025",
  "validation_outcome": "PASS | WARN | RETRY | FAIL",
  "structural_results": {
    "json_valid": true,
    "required_keys_present": true,
    "paragraph_count": 5,
    "paragraph_count_in_range": true,
    "table_count": 1,
    "table_columns_consistent": true
  },
  "numeric_results": {
    "total_claims_checked": 8,
    "passed": 8,
    "failed": 0,
    "failures": []
  },
  "prohibited_content_results": {
    "fabricated_numbers": [],
    "independent_calc_phrases": [],
    "fabricated_citations": [],
    "first_person_pronouns": [],
    "marketing_language": []
  },
  "warnings": [],
  "errors": [],
  "retry_count": 0,
  "timestamp": "2025-05-29T10:00:00Z",
  "execution_id": "arn:aws:states:ap-southeast-1:123456789012:execution:ESGReport:run-001"
}

REQ-VAL-08: Human Review Queue Message Format
When outcome = FAIL, the SQS message MUST contain:
{
  "task_token": "{step_functions_task_token}",
  "section_id": "GRI_305_S1_2025",
  "framework": "GRI_305",
  "reporting_year": 2025,
  "failure_reason": "VAL-NUM-01: Scope 1 value mismatch",
  "validation_details": {
    "rule_id": "VAL-NUM-01",
    "expected_value": 12456.789,
    "extracted_value": 12457.000,
    "delta": 0.211,
    "tolerance": 0.001,
    "location": "paragraphs[0].text, position 45-55"
  },
  "section_json": { ... },
  "data_input_used": { ... },
  "prompt_version": "1.0.0",
  "generation_timestamp": "2025-05-29T09:58:00Z",
  "reviewer_actions": {
    "approve": "Send TaskSuccess with output: { decision: 'approve', reviewer_id: '...' }",
    "reject": "Send TaskFailure with error: 'ReviewerRejected', cause: '...'"
  }
}

REQ-VAL-09: Timeout and Escalation
Scenario	Timeout	Escalation Action
Human review not completed	72 hours	Step Functions state times out. Section marked as TIMEOUT_EXCLUDED. Report generated WITHOUT this section. A placeholder page is inserted: "Section pending review — excluded from this version."
All sections in FAIL state	N/A	If ALL sections fail validation, the entire workflow transitions to a terminal ReportGenerationFailed state. SNS alert sent to pipeline operator with full diagnostic payload.
Retry budget exhausted	N/A	After 1 retry (total 2 attempts), no further retries. Escalate to FAIL immediately.

 
8. Assembly Style Specifications
This section specifies all typographic, layout, and style requirements for the python-docx DOCX assembly Lambda. The assembler MUST produce a document that meets all requirements below without any LLM invocation. Assembly is purely deterministic Python.
8.1 Page Setup Requirements

Property	Required Value	Notes
Page Size	A4 (210mm × 297mm)	python-docx: Inches(8.27) x Inches(11.69)
Margins (all sides)	1 inch (25.4mm)	python-docx: Inches(1.0) on top, bottom, left, right
Default Body Font	Arial, 11pt	Fallback: Calibri. Never Times New Roman for ESG reports.
Heading 1 Font	Arial Bold, 18pt, color #1B3A6B	Used for section titles (e.g., "1. Scope 1 GHG Emissions")
Heading 2 Font	Arial Bold, 14pt, color #3D6094	Used for subsection titles
Heading 3 Font	Arial Bold, 12pt, color #4A7AB5	Used for sub-subsection titles (e.g., methodology notes)
Body Text Line Spacing	1.15 (multiple)	python-docx: line_spacing_rule = WD_LINE_SPACING.MULTIPLE; line_spacing = 1.15
Paragraph Spacing After	8pt after each body paragraph	python-docx: paragraph_format.space_after = Pt(8)
Paragraph Spacing Before	0pt (no space before body paragraphs)	Headings have their own spacing rules
Header	Right-aligned: Institution Name | Reporting Year	Section-level Header; Arial 9pt, color #888888
Footer	Left: Report Title | Right: Page X of Y	Arial 9pt; page number auto-field

REQ-ASSY-01: Font Registration
The assembly Lambda MUST register Arial as the default document font. If Arial is not available in the Lambda runtime environment, Calibri MUST be used as fallback. The Lambda MUST NOT use system-default fonts (which may vary by OS).
# Required font configuration
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_LINE_SPACING

style = document.styles['Normal']
font = style.font
font.name = 'Arial'
font.size = Pt(11)

REQ-ASSY-02: Heading Style Configuration
Heading Level	Font	Size	Color (RGB)	Space Before	Space After	Keep With Next
Heading 1	Arial Bold	18pt	#1B3A6B (27, 58, 107)	24pt	12pt	True
Heading 2	Arial Bold	14pt	#3D6094 (61, 96, 148)	18pt	8pt	True
Heading 3	Arial Bold	12pt	#4A7AB5 (74, 122, 181)	12pt	6pt	True
Constraint: keep_with_next = True ensures headings are never orphaned at the bottom of a page.

8.2 Table Style Requirements
REQ-ASSY-03: Table Formatting
Property	Required Value	python-docx Implementation
Table Style	Custom "ESG_Table" (not built-in)	Create custom style programmatically
Header Row Background	#1B3A6B (dark navy)	cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255,255,255) + shading
Header Row Font	Arial Bold, 10pt, White (#FFFFFF)	Bold, white text on navy background
Body Row Font	Arial, 10pt, Black (#000000)	Standard body text
Alternating Row Shading	Even rows: #F2F6FA (light blue-grey)	Apply shading to even-indexed rows
Cell Padding	Top/Bottom: 4pt; Left/Right: 6pt	Via cell.paragraphs[0].paragraph_format
Border	0.5pt solid #D0D0D0 (light grey)	All cells, all sides
Column Alignment	Numeric columns: right-aligned; Text columns: left-aligned	Based on content type detection
Table Width	100% of available page width	table.autofit = True or set preferred width
Caption	Below table, italic, 9pt, centered	Format: "Table X: {caption text}"

REQ-ASSY-04: Table Shading Implementation
# Header row shading
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def set_cell_shading(cell, color_hex):
    """Apply background shading to a table cell."""
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), color_hex)
    shading_elm.set(qn('w:val'), 'clear')
    cell._tc.get_or_add_tcPr().append(shading_elm)

# Apply to header row
for cell in table.rows[0].cells:
    set_cell_shading(cell, '1B3A6B')

# Apply alternating row shading
for i, row in enumerate(table.rows[1:], start=1):
    if i % 2 == 0:
        for cell in row.cells:
            set_cell_shading(cell, 'F2F6FA')

REQ-ASSY-05: Numeric Formatting in Tables
Data Type	Format	Alignment	Example
tCO2e (Scope 1/2)	Comma-separated, 3 dp	Right	12,456.789
tCO2e (Scope 3)	Comma-separated, 2 dp	Right	1,234,567.89
Percentage	2 dp with % suffix	Right	-3.45%
IDR (trillions)	2 dp with "IDR" prefix	Right	IDR 45.67T
Intensity	6 dp	Right	0.123456
PCAF Score	2 dp	Center	3.25
Integer counts	Comma-separated, no dp	Right	2,145

8.3 Cover Page Requirements
REQ-ASSY-06: Cover Page Layout
The first page of the document MUST be a cover page with the following elements, in order from top to bottom:

Element	Position	Style	Content
Institution Logo Placeholder	Top-center, 2 inches from top	150×50px placeholder box	Text: "[INSTITUTION LOGO]" in grey box
Report Title	Center, 3.5 inches from top	Arial Bold, 28pt, #1B3A6B	"Environmental, Social, and Governance Report"
Subtitle (Framework)	Center, below title	Arial, 16pt, #3D6094	"{Framework Name} Disclosure"
Reporting Year	Center, below subtitle	Arial, 14pt, #666666	"Reporting Year: {reporting_year}"
Institution Name	Center, 6 inches from top	Arial Bold, 14pt, #000000	"{institution_name}"
Confidentiality Notice	Bottom-center, 9 inches from top	Arial Italic, 9pt, #888888	"CONFIDENTIAL — For internal use and regulatory submission only"
Generation Metadata	Bottom-right, 10 inches from top	Arial, 8pt, #AAAAAA	"Generated: {timestamp} | Execution: {execution_id_short}"

REQ-ASSY-07: Cover Page Section Break
After the cover page, a section break (new page) MUST be inserted. The header/footer defined in REQ-ASSY-01 starts from page 2 onwards. The cover page has NO header/footer.
from docx.enum.section import WD_ORIENT, WD_SECTION_START

# After cover page content
new_section = document.add_section(WD_SECTION_START.NEW_PAGE)
# Cover page section: no header/footer
first_section = document.sections[0]
first_section.different_first_page_header_footer = True

REQ-ASSY-08: Multi-Framework Cover Page
When generating a multi-framework report (all 4 frameworks), the subtitle MUST read:
"Multi-Framework Climate Disclosure"
"GRI 305 • IFRS S2 • CSRD/ESRS E1 • OJK PSPK"
(Two lines, second line in Arial 12pt, #666666)

8.4 Section Assembly Order Requirements

REQ-ASSY-09: Section Ordering
The assembly Lambda MUST arrange sections in the following fixed order. Sections not generated (e.g., if only one framework is selected) are simply omitted — the order of remaining sections is preserved.
Order	Section	Source Template	Page Break Before
0	Cover Page	Programmatic (REQ-ASSY-06)	N/A (first page)
1	Table of Contents	Programmatic (auto-generated)	Yes
2	Executive Summary	executive_summary section JSON	Yes
3	GRI 305-1: Scope 1 Direct Emissions	scope1_template (GRI)	Yes
4	GRI 305-2: Scope 2 Energy Indirect Emissions	scope2_template (GRI)	No (continues)
5	GRI 305-3: Scope 3 Financed Emissions (PCAF)	scope3_pcaf_template (GRI)	Yes
6	GRI 305-4: GHG Emissions Intensity	intensity_template (GRI)	No (continues)
7	GRI 305-5: Reduction of GHG Emissions	reduction_template (GRI)	No (continues)
8	IFRS S2: Governance	governance_template (IFRS)	Yes
9	IFRS S2: Strategy	strategy_template (IFRS)	No (continues)
10	IFRS S2: Risk Management	risk_mgmt_template (IFRS)	No (continues)
11	IFRS S2: Metrics and Targets	metrics_template (IFRS)	Yes
12	CSRD/ESRS E1: Transition Plan (E1-1)	transition_template (CSRD)	Yes
13	CSRD/ESRS E1: Energy & GHG (E1-5, E1-6)	energy_ghg_template (CSRD)	No (continues)
14	CSRD/ESRS E1: Financial Effects (E1-9)	financial_effects_template (CSRD)	No (continues)
15	OJK PSPK: Environmental Metrics	env_metrics_template (OJK)	Yes
16	OJK PSPK: Social Metrics	social_metrics_template (OJK)	No (continues)
17	OJK PSPK: Governance Metrics	gov_metrics_template (OJK)	No (continues)
18	Appendix A: Methodology Notes	Programmatic (from footnotes)	Yes
19	Appendix B: GRI Content Index	Programmatic (from framework_references)	No (continues)
20	Appendix C: Data Quality Statement	Programmatic (from metadata)	No (continues)

REQ-ASSY-10: Page Break Logic
# Page break insertion rule
def should_insert_page_break(section_order_index):
    """Sections marked 'Yes' in Page Break Before column."""
    page_break_sections = {1, 2, 3, 5, 8, 11, 12, 15, 18}
    return section_order_index in page_break_sections

REQ-ASSY-11: Table of Contents Generation
The Table of Contents MUST be generated programmatically using python-docx field codes:
# TOC field code insertion
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def add_table_of_contents(document):
    """Insert a TOC field that updates on document open."""
    paragraph = document.add_paragraph()
    run = paragraph.add_run()
    fldChar = OxmlElement('w:fldChar')
    fldChar.set(qn('w:fldCharType'), 'begin')
    run._r.append(fldChar)
    
    run2 = paragraph.add_run()
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = ' TOC \\o "1-3" \\h \\z \\u '
    run2._r.append(instrText)
    
    run3 = paragraph.add_run()
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')
    run3._r.append(fldChar2)
Note: The TOC will display "Update this table" placeholder until the user opens the document in Word and presses F9 or right-clicks → "Update Field". This is a known python-docx limitation.

REQ-ASSY-12: Section JSON to DOCX Mapping
For each section JSON received from the validated assembly list, the Lambda MUST map:
JSON Field	DOCX Element	Style Applied
title	Heading 1 paragraph	Heading 1 style (REQ-ASSY-02)
paragraphs[].text (type: narrative)	Body paragraph	Normal style, 11pt
paragraphs[].text (type: methodology)	Body paragraph	Normal style, 11pt, italic
paragraphs[].text (type: footnote)	Footnote paragraph	9pt, italic, #666666
paragraphs[].text (type: forward_looking)	Body paragraph with qualifier prefix	Normal style + italic qualifier
tables[]	Word table	ESG_Table custom style (REQ-ASSY-03)
tables[].caption	Paragraph below table	Italic, 9pt, centered
footnotes[]	End-of-section footnote block	9pt, italic, preceded by thin horizontal rule
framework_references[]	Inline parenthetical or footnote	9pt, format: "(Ref: GRI 305-1a)"
key_metrics[]	Not rendered directly	Used for validation cross-check only

REQ-ASSY-13: Appendix Generation Rules
Appendix	Source	Generation Logic
Methodology Notes	All footnotes[] arrays across all sections	Deduplicate; group by topic (emission factors, PCAF, data quality); number sequentially
GRI Content Index	All framework_references[] where framework = GRI_305	Build table: GRI Standard | Disclosure | Page Reference | Omission
Data Quality Statement	Section metadata: data_quality_score, imputed_months, avg_pcaf_data_quality	Programmatic paragraph stating overall data quality, assurance level, and known limitations

REQ-ASSY-14: No LLM Invocation Constraint (CON-ASSY-01)
The assembly Lambda MUST NOT invoke any LLM, foundation model, or AI service. All text in the final DOCX comes from:
1.	Section JSONs (generated earlier by SectionGenFn and validated)
2.	Programmatic strings (cover page, TOC, appendix headers)
3.	Metadata fields (timestamps, execution IDs)
Rationale: This ensures the final document is 100% deterministic and reproducible. Given the same set of validated section JSONs, the assembly Lambda MUST produce byte-identical DOCX output (excluding timestamps in metadata).

 
9. AWS Step Functions Workflow State Specifications
This section specifies all states in the ESG Report Generation Step Functions state machine. Kiro IDE MUST generate the Amazon States Language (ASL) definition satisfying every requirement below. The state machine name MUST be ESGReportGenerationStateMachine.
9.1 State Machine Overview

State Name	State Type	Resource / Integration	Purpose
ValidateInput	Task	Lambda: ValidateInputFn	Validates Step Functions input JSON against required schema: framework, reporting_year, bank_id, output_bucket. Rejects on missing or invalid fields.
TriggerGlueScope1	Task	AWS Glue: startJobRun	Starts the Scope 1 Glue ETL job with REPORTING_YEAR and S3 bucket parameters. Polls for completion via .sync integration pattern.
TriggerGlueScope3	Task	AWS Glue: startJobRun	Starts the PCAF Scope 3 Glue ETL job in parallel with Scope 1. Both Glue jobs run concurrently via Parallel state.
WaitForGlueJobs	Parallel	N/A (container)	Container state that runs TriggerGlueScope1 and TriggerGlueScope3 as parallel branches. Proceeds only when both branches succeed.
TriggerAggregation	Task	AWS Glue: startJobRun	Runs the aggregation Glue job after both curated zone jobs complete. Produces esg_aggregated.ghg_summary_annual record.
QueryAthena	Task	Lambda: AthenaQueryFn	Executes all aggregated zone queries for the reporting year. Assembles the full DATA INPUT JSON object for section generation.
GenerateSections	Map	Lambda: SectionGenFn	Iterates over section_templates array from input. Each iteration invokes SectionGenFn with one template + DATA INPUT. MaxConcurrency: 3 (Claude rate limit protection).
ValidateSection	Task	Lambda: ValidationFn	Per-section validation Lambda. Called within the Map iterator after each section is generated. Applies all rules from Section 7.
ValidationChoice	Choice	N/A	Routes on validation outcome: PASS → accumulate section; RETRY → re-invoke SectionGenFn once; FAIL → HumanReviewGate.
HumanReviewGate	Task	SQS + SNS (callback)	Publishes failed section to SQS review queue, sends SNS notification to reviewer. Enters WaitForTaskToken pause. Maximum wait: 72 hours before timeout.
AssembleDocument	Task	Lambda: AssemblyFn	Invokes python-docx assembly Lambda with all validated section JSONs. Writes output DOCX to S3 output bucket. No LLM involvement.
NotifyCompletion	Task	SNS: PublishMessage	Publishes completion notification with S3 URI of the generated DOCX. Final state before Success.

State Machine Flow Diagram

START
  │
  ▼
┌──────────────┐
│ValidateInput │ ──── FAIL ──→ ExecutionFailed (terminal)
└──────┬───────┘
       │ PASS
       ▼
┌──────────────────────────────────────┐
│         WaitForGlueJobs (Parallel)   │
│  ┌─────────────────┐ ┌────────────┐ │
│  │TriggerGlueScope1│ │TriggerGlue │ │
│  │  (Scope 1 ETL)  │ │  Scope3    │ │
│  │                 │ │ (PCAF ETL) │ │
│  └────────┬────────┘ └─────┬──────┘ │
│           └────────┬────────┘        │
└────────────────────┼─────────────────┘
                     │ Both succeed
                     ▼
          ┌─────────────────────┐
          │ TriggerAggregation  │
          │ (Aggregation ETL)   │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │    QueryAthena      │
          │ (Build DATA INPUT)  │
          └──────────┬──────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│              GenerateSections (Map)                      │
│              MaxConcurrency: 3                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │  FOR EACH section_template:                       │  │
│  │    ┌──────────────┐                               │  │
│  │    │SectionGenFn  │ (invoke Bedrock Claude)       │  │
│  │    └──────┬───────┘                               │  │
│  │           │                                       │  │
│  │           ▼                                       │  │
│  │    ┌──────────────┐                               │  │
│  │    │ValidateSection│                              │  │
│  │    └──────┬───────┘                               │  │
│  │           │                                       │  │
│  │           ▼                                       │  │
│  │    ┌──────────────────┐                           │  │
│  │    │ValidationChoice  │                           │  │
│  │    ├──────────────────┤                           │  │
│  │    │ PASS → Accumulate│                           │  │
│  │    │ RETRY → Re-invoke│ (max 1 retry)            │  │
│  │    │ FAIL → HumanReviewGate                      │  │
│  │    └──────────────────┘                           │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────────┘
                         │ All sections resolved
                         ▼
              ┌─────────────────────┐
              │  AssembleDocument   │
              │  (python-docx)     │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ NotifyCompletion    │
              │ (SNS publish)      │
              └──────────┬──────────┘
                         │
                         ▼
                      SUCCESS

9.2 State Machine Input Schema
REQ-SFN-01: Required Input Fields
The state machine execution input MUST conform to this JSON schema:
{
  "$schema": "json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["framework", "reporting_year", "bank_id", "output_bucket"],
  "properties": {
    "framework": {
      "type": "string",
      "enum": ["GRI_305", "IFRS_S2", "CSRD_ESRS_E1", "OJK_PSPK", "MULTI_FRAMEWORK"],
      "description": "Target reporting framework. MULTI_FRAMEWORK generates all four."
    },
    "reporting_year": {
      "type": "integer",
      "minimum": 2020,
      "maximum": 2035,
      "description": "Fiscal year for which the ESG report is generated."
    },
    "bank_id": {
      "type": "string",
      "pattern": "^[A-Z_]+_\\d{3}$",
      "description": "Institution identifier. Format: GENERIC_FI_001."
    },
    "output_bucket": {
      "type": "string",
      "description": "S3 bucket name for output DOCX. Must exist and be writable."
    },
    "base_year": {
      "type": "integer",
      "default": 2022,
      "description": "Base year for YoY and trend comparisons. Default: 2022."
    },
    "language": {
      "type": "string",
      "enum": ["en", "id"],
      "default": "en",
      "description": "Report language. 'id' triggers Bahasa Indonesia for OJK PSPK overlay."
    },
    "institution_name": {
      "type": "string",
      "default": "Generic Financial Institution",
      "description": "Display name for cover page and narrative."
    },
    "revenue_idr_billion": {
      "type": "number",
      "minimum": 0,
      "description": "Annual revenue in IDR billions. Required for intensity calculation."
    },
    "section_templates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["template_id", "framework"],
        "properties": {
          "template_id": {
            "type": "string",
            "enum": ["scope1", "scope2", "scope3_pcaf", "intensity", "governance", "targets"]
          },
          "framework": {
            "type": "string",
            "enum": ["GRI_305", "IFRS_S2", "CSRD_ESRS_E1", "OJK_PSPK"]
          }
        }
      },
      "description": "Array of section templates to generate. Auto-populated if framework=MULTI_FRAMEWORK."
    }
  }
}

REQ-SFN-02: MULTI_FRAMEWORK Auto-Population
When framework = "MULTI_FRAMEWORK", the ValidateInputFn Lambda MUST auto-populate the section_templates array with all sections in the order defined in Section 8.4 (REQ-ASSY-09):
[
  {"template_id": "scope1", "framework": "GRI_305"},
  {"template_id": "scope2", "framework": "GRI_305"},
  {"template_id": "scope3_pcaf", "framework": "GRI_305"},
  {"template_id": "intensity", "framework": "GRI_305"},
  {"template_id": "scope1", "framework": "IFRS_S2"},
  {"template_id": "governance", "framework": "IFRS_S2"},
  {"template_id": "targets", "framework": "IFRS_S2"},
  {"template_id": "scope1", "framework": "CSRD_ESRS_E1"},
  {"template_id": "scope3_pcaf", "framework": "CSRD_ESRS_E1"},
  {"template_id": "scope1", "framework": "OJK_PSPK"},
  {"template_id": "scope3_pcaf", "framework": "OJK_PSPK"},
  {"template_id": "intensity", "framework": "OJK_PSPK"}
]

REQ-SFN-03: Input Validation Rules
The ValidateInputFn Lambda MUST enforce:
Rule	Check	Failure Action
Required fields present	framework, reporting_year, bank_id, output_bucket all non-null	Return error: InputValidationError with missing field names
Year range	2020 <= reporting_year <= 2035	Return error: InvalidYearRange
Bank ID format	Matches regex ^[A-Z_]+_\d{3}$	Return error: InvalidBankIdFormat
Bucket exists	HEAD bucket call succeeds	Return error: BucketNotFound
Revenue provided	revenue_idr_billion > 0 if intensity section is in templates	Return error: MissingRevenueData
No duplicate templates	No two entries with same (template_id, framework) pair	Return error: DuplicateTemplate

9.3 Map State Configuration Requirements
REQ-SFN-04: Map State Parameters
Parameter	Required Value	Rationale
MaxConcurrency	3	Claude 3.5 Sonnet rate limit: 3 concurrent invocations per account in POC tier. Prevents throttling.
ItemsPath	$.section_templates	Iterates over the section_templates array from validated input.
ItemSelector	See below	Passes template config + DATA INPUT to each iteration.
ResultPath	$.generated_sections	Collects all validated section JSONs for assembly.
ToleratedFailurePercentage	25	If more than 25% of sections fail (after retry + human review timeout), the entire Map state fails.
ToleratedFailureCount	3	Maximum 3 sections can be excluded (timeout/rejected) before Map fails.

REQ-SFN-05: ItemSelector Configuration
Each Map iteration receives:
{
  "template_config.$": "$$.Map.Item.Value",
  "data_input.$": "$.athena_query_result",
  "rag_config": {
    "knowledge_base_id.$": "$.kb_id",
    "max_tokens_per_section": 700
  },
  "execution_context": {
    "execution_id.$": "$$.Execution.Id",
    "state_entered_time.$": "$$.State.EnteredTime",
    "retry_count": 0
  }
}

REQ-SFN-06: Map Iterator Internal Flow
Within each Map iteration, the states execute in this order:
┌─────────────────────────────────────────────────────────┐
│  Map Iterator (per section_template)                     │
│                                                          │
│  1. InvokeSectionGen (Task → SectionGenFn Lambda)       │
│     │                                                    │
│     ▼                                                    │
│  2. InvokeValidation (Task → ValidationFn Lambda)       │
│     │                                                    │
│     ▼                                                    │
│  3. ValidationChoice (Choice state)                      │
│     ├── PASS → AccumulateSection (Pass state)           │
│     ├── WARN → AccumulateWithWarning (Pass state)       │
│     ├── RETRY → RetryGeneration (Task → SectionGenFn)  │
│     │           │                                        │
│     │           ▼                                        │
│     │         RetryValidation (Task → ValidationFn)     │
│     │           │                                        │
│     │           ▼                                        │
│     │         RetryChoice (Choice state)                │
│     │           ├── PASS → AccumulateSection            │
│     │           └── FAIL → HumanReviewGate             │
│     │                                                    │
│     └── FAIL → HumanReviewGate (Task, WaitForTaskToken)│
│                 │                                        │
│                 ▼                                        │
│               ReviewChoice (Choice state)               │
│                 ├── APPROVED → AccumulateSection         │
│                 ├── REJECTED → ExcludeSection            │
│                 └── TIMEOUT → ExcludeSection             │
│                                                          │
│  Final: AccumulateSection OR ExcludeSection              │
└─────────────────────────────────────────────────────────┘

REQ-SFN-07: HumanReviewGate Configuration
{
  "Type": "Task",
  "Resource": "arn:aws:states:::sqs:sendMessage.waitForTaskToken",
  "Parameters": {
    "QueueUrl": "${ESGReviewQueueUrl}",
    "MessageBody": {
      "task_token.$": "$$.Task.Token",
      "section_id.$": "$.validation_result.section_id",
      "framework.$": "$.template_config.framework",
      "failure_reason.$": "$.validation_result.errors[0]",
      "section_json.$": "$.section_output",
      "data_input.$": "$.data_input"
    }
  },
  "HeartbeatSeconds": 3600,
  "TimeoutSeconds": 259200,
  "ResultPath": "$.review_decision",
  "Catch": [
    {
      "ErrorEquals": ["States.Timeout"],
      "ResultPath": "$.review_decision",
      "Next": "ExcludeSection"
    }
  ]
}

Parameter	Value	Rationale
TimeoutSeconds	259200 (72 hours)	Maximum wait for human reviewer. After 72h, section is excluded.
HeartbeatSeconds	3600 (1 hour)	Reviewer must send heartbeat every hour to keep task alive. Prevents abandoned revie

9.4 Error Handling Requirements
REQ-SFN-08: Retry Configuration per State
State	Retryable Errors	MaxAttempts	IntervalSeconds	BackoffRate	MaxDelaySeconds
TriggerGlueScope1	Glue.ConcurrentRunsExceededException	3	60	2.0	300
TriggerGlueScope3	Glue.ConcurrentRunsExceededException	3	60	2.0	300
TriggerAggregation	Glue.ConcurrentRunsExceededException	3	60	2.0	300
QueryAthena	Athena.TooManyRequestsException, Lambda.TooManyRequestsException	3	30	2.0	120
InvokeSectionGen	Bedrock.ThrottlingException, Bedrock.ModelTimeoutException, Lambda.TooManyRequestsException	2	15	3.0	120
InvokeValidation	Lambda.TooManyRequestsException	2	10	2.0	60
AssembleDocument	Lambda.TooManyRequestsException	2	10	2.0	60
NotifyCompletion	SNS.ThrottledException	3	5	2.0	30

REQ-SFN-09: Catch Configuration (Non-Retryable Errors)
State	Caught Errors	Next State	ResultPath
ValidateInput	States.ALL	ExecutionFailed	$.error_info
WaitForGlueJobs	States.ALL (after retries exhausted)	ETLPipelineFailed	$.error_info
TriggerAggregation	States.ALL	ETLPipelineFailed	$.error_info
QueryAthena	States.ALL	DataQueryFailed	$.error_info
GenerateSections (Map)	States.ALL	SectionGenerationFailed	$.error_info
AssembleDocument	States.ALL	AssemblyFailed	$.error_info
Terminal Error States
State Name	Type	Action
ExecutionFailed	Fail	Error: InputValidationError. Cause: $.error_info.message
ETLPipelineFailed	Fail	Error: ETLProcessingError. Cause: Glue job failure details. SNS alert to pipeline operator.
DataQueryFailed	Fail	Error: AthenaQueryError. Cause: Query execution failure. SNS alert.
SectionGenerationFailed	Fail	Error: SectionGenError. Cause: >25% sections failed or >3 excluded. SNS alert.
AssemblyFailed	Fail	Error: DocumentAssemblyError. Cause: python-docx failure. SNS alert.
REQ-SFN-10: Execution Timeout
Parameter	Value	Rationale
State Machine Timeout	86400 seconds (24 hours)	Accounts for Glue jobs (~30 min each) + section generation (~15 min) + potential 72h human review. If human review is active, the 24h timeout does NOT apply to the HumanReviewGate state (which has its own 72h timeout). The 24h applies to the overall execution excluding wait states.

REQ-SFN-11: CloudWatch Metrics and Alarms
Metric	Alarm Threshold	Action
ExecutionsFailed	≥ 1 in 1 hour	SNS alert to pipeline operator
ExecutionsTimedOut	≥ 1 in 24 hours	SNS alert + investigation ticket
ExecutionTime	> 3600 seconds (excluding wait states)	WARN: performance degradation
SectionsRetried (custom)	> 50% of sections in single execution	SNS alert: prompt quality issue
HumanReviewsTriggered (custom)	> 3 in single execution	SNS alert: systemic validation failure

REQ-SFN-12: Execution Tagging
Every execution MUST include these tags for traceability:
Tag Key	Tag Value	Purpose
esg:framework	{framework}	Filter executions by framework
esg:reporting_year	{reporting_year}	Filter by year
esg:bank_id	{bank_id}	Filter by institution
esg:initiated_by	{caller_identity}	Audit trail
esg:environment	poc | staging | production	Environment isolation
 
10. Amazon Bedrock Knowledge Base Configuration
This section specifies the requirements for the Bedrock Knowledge Base (KB) that provides RAG-based regulatory context to section generation prompts. The KB is a read-only reference store; it is NEVER used as a source of numeric values.
10.1 Knowledge Base Source Document Requirements
Document Category	Required Sources	Usage in Prompts
GRI Standards	GRI 305: Emissions 2016; GRI 3: Material Topics 2021	Regulatory context for Scope 1, 2, 3 disclosure requirements and GRI Content Index format.
IFRS Standards	IFRS S2 Climate-related Disclosures (June 2023); IFRS S1 General Requirements (June 2023)	Four-pillar TCFD requirements, SASB FN-CB-410 industry supplement.
CSRD/ESRS	ESRS E1 Climate Change (2023); ESRS 2 General Disclosures; EU Taxonomy Regulation 2020/852	E1 datapoint requirements, EU Taxonomy alignment criteria, double materiality guidance.
OJK / Indonesian Regs	POJK 51/POJK.03/2017 (Sustainable Finance); SEOJK Circular on Green Bond	Regulatory table formats, Bahasa Indonesia terminology equivalents, local carbon market references.
GHG Methodology	GHG Protocol Corporate Standard v2015; PCAF Standard Part A 2022; IPCC AR6 Chapter 7	Emission factor justification, methodology narrative, uncertainty quantification language.
Style Reference	3–5 sample audited ESG reports from financial institutions (anonymised); 50,000-word corpus	Writing register anchor via style_reference_excerpt placeholder in section templates.

REQ-KB-01: Document Preparation Rules
Rule	Requirement
Format	All source documents MUST be converted to PDF or plain text before ingestion. No DOCX or HTML.
Metadata tagging	Each document MUST have metadata fields: category (from table above), framework (GRI/IFRS/CSRD/OJK/GHG/STYLE), version, effective_date.
Numeric stripping	Style reference documents MUST have all numeric values redacted/replaced with [REDACTED] to prevent the KB from becoming a source of numeric claims.
Language	All documents in English. OJK documents: bilingual (English primary, Bahasa Indonesia terms in parentheses).
Copyright compliance	Only publicly available regulatory standards or properly licensed content. No copyrighted third-party reports without permission.

REQ-KB-02: Minimum Document Count
Category	Minimum Documents	Approximate Token Count
GRI Standards	2 documents	~15,000 tokens
IFRS Standards	2 documents	~20,000 tokens
CSRD/ESRS	3 documents	~25,000 tokens
OJK / Indonesian Regs	2 documents	~10,000 tokens
GHG Methodology	3 documents	~18,000 tokens
Style Reference	3–5 documents	~50,000 tokens
TOTAL	15–17 documents	~138,000 tokens




10.2 Chunking and Embedding Configuration
REQ-KB-03: Chunking Strategy
Parameter	Required Value	Rationale
Chunking strategy	Fixed-size with overlap	Ensures consistent retrieval granularity across heterogeneous documents
Chunk size	300 tokens	Optimised for regulatory paragraph-level retrieval. Larger chunks (512+) include too much irrelevant context for section-specific queries.
Chunk overlap	50 tokens	Preserves context continuity at chunk boundaries. ~17% overlap ratio.
Separator	Paragraph boundary preferred; fallback to sentence boundary	Avoids splitting mid-sentence which degrades retrieval quality
Maximum chunks per document	No limit	Allow full document indexing

REQ-KB-04: Embedding Model Configuration
Parameter	Required Value	Notes
Embedding model	Amazon Titan Embeddings V2 (amazon.titan-embed-text-v2:0)	1024-dimension vectors; multilingual support for Bahasa Indonesia terms
Vector dimensions	1024	Fixed by model; do not reduce via PCA
Distance metric	Cosine similarity	Standard for text embeddings; normalised vectors
Normalisation	L2 normalisation applied by model	No additional normalisation needed
REQ-KB-05: Vector Store Configuration (Amazon OpenSearch Serverless)
Parameter	Required Value	Notes
Collection type	VECTORSEARCH	AOSS vector search collection
Collection name	esg-regulatory-kb	Lowercase, hyphen-separated
Index name	esg-regulatory-index	Single index for all document categories
Engine	FAISS	Efficient approximate nearest neighbour search
ef_construction	512	Build-time accuracy parameter
m	16	HNSW graph connectivity parameter
Encryption	AWS-owned key (default)	Upgrade to CMK for production
Network policy	VPC endpoint only (production); Public (POC)	POC allows public for development convenience

AOSS Index Mapping:
{
  "settings": {
    "index": {
      "knn": true,
      "knn.algo_param.ef_search": 512
    }
  },
  "mappings": {
    "properties": {
      "bedrock-knowledge-base-default-vector": {
        "type": "knn_vector",
        "dimension": 1024,
        "method": {
          "engine": "faiss",
          "name": "hnsw",
          "space_type": "l2",
          "parameters": {
            "ef_construction": 512,
            "m": 16
          }
        }
      },
      "AMAZON_BEDROCK_TEXT_CHUNK": {
        "type": "text"
      },
      "AMAZON_BEDROCK_METADATA": {
        "type": "text"
      },
      "category": {
        "type": "keyword"
      },
      "framework": {
        "type": "keyword"
      },
      "version": {
        "type": "keyword"
      },
      "effective_date": {
        "type": "date"
      }
    }
  }
}




10.3 Retrieval Configuration
REQ-KB-06: Retrieval Parameters
Parameter	Required Value	Rationale
Number of results (numberOfResults)	5	Top-5 chunks provide sufficient context without exceeding token budget
Search type	HYBRID (semantic + keyword)	Combines vector similarity with BM25 keyword matching for regulatory terminology precision
Minimum relevance score	0.65	Chunks below this threshold are discarded; prevents injection of irrelevant context
Metadata filter	framework field MUST match active overlay framework	Ensures GRI queries only retrieve GRI chunks, IFRS queries only IFRS chunks, etc.

REQ-KB-07: Per-Section Retrieval Queries and Token Caps
Section Type	Retrieval Query	Framework Filter	Token Cap	Purpose
Scope 1 disclosure	"GRI 305-1 disclosure requirements direct emissions consolidation approach"	framework = active_overlay	500 tokens	Regulatory context for Scope 1 narrative
Scope 2 disclosure	"GHG Protocol Scope 2 Guidance dual reporting location-based market-based contractual instruments"	framework IN (GRI, IFRS, CSRD)	500 tokens	Dual reporting methodology context
PCAF financed emissions	"PCAF Global Standard financed emissions attribution factor data quality score methodology"	framework IN (GRI, IFRS, CSRD, GHG)	700 tokens	PCAF methodology and quality tier definitions
Governance	"IFRS S2 governance climate oversight board management responsibilities"	framework = active_overlay	600 tokens	Governance disclosure requirements
Strategy & targets	"IFRS S2 strategy scenario analysis transition plan 1.5 degrees climate targets"	framework = active_overlay	700 tokens	Strategy and target-setting context
Intensity	"GRI 305-4 GHG emissions intensity ratio denominator definition"	framework = active_overlay	400 tokens	Intensity metric requirements
Executive summary	N/A (no RAG retrieval)	N/A	0 tokens	Executive summary uses only DATA INPUT

REQ-KB-08: Token Cap Enforcement
The SectionGenFn Lambda MUST enforce token caps on retrieved context:
def enforce_token_cap(retrieval_results, max_tokens):
    """
    Truncate retrieved chunks to fit within token budget.
    Uses tiktoken cl100k_base tokenizer for approximation.
    """
    accumulated_tokens = 0
    capped_chunks = []
    
    for result in retrieval_results:
        chunk_tokens = count_tokens(result['text'])
        if accumulated_tokens + chunk_tokens <= max_tokens:
            capped_chunks.append(result['text'])
            accumulated_tokens += chunk_tokens
        else:
            # Truncate last chunk to fit remaining budget
            remaining = max_tokens - accumulated_tokens
            if remaining > 50:  # Only include if meaningful (>50 tokens)
                truncated = truncate_to_tokens(result['text'], remaining)
                capped_chunks.append(truncated)
            break
    
    return "
---
".join(capped_chunks)

REQ-KB-09: Retrieval Metadata Logging
Every KB retrieval MUST log the following to CloudWatch for audit:
Log Field	Value	Purpose
execution_id	Step Functions execution ARN	Links retrieval to workflow
section_id	Target section being generated	Maps context to output
query_text	The retrieval query string	Reproducibility
results_count	Number of chunks returned (before cap)	Quality monitoring
results_used	Number of chunks after token cap	Actual context injected
total_tokens_injected	Token count of final RAG context	Budget compliance
min_relevance_score	Lowest score among used chunks	Quality threshold monitoring
framework_filter	Active metadata filter	Audit trail

REQ-KB-10: Knowledge Base Sync Schedule
Environment	Sync Frequency	Trigger
POC	Manual (on-demand)	Developer triggers via console or CLI after adding new documents
Staging	Weekly (Sunday 02:00 UTC+7)	EventBridge scheduled rule
Production	On document upload + weekly full sync	S3 event notification + scheduled rule

REQ-KB-11: KB Data Source S3 Structure
s3://{KB_SOURCE_BUCKET}/
├── gri/
│   ├── GRI_305_Emissions_2016.pdf
│   └── GRI_3_Material_Topics_2021.pdf
├── ifrs/
│   ├── IFRS_S2_Climate_Disclosures_2023.pdf
│   └── IFRS_S1_General_Requirements_2023.pdf
├── csrd/
│   ├── ESRS_E1_Climate_Change_2023.pdf
│   ├── ESRS_2_General_Disclosures_2023.pdf
│   └── EU_Taxonomy_Regulation_2020_852.pdf
├── ojk/
│   ├── POJK_51_2017_Sustainable_Finance.pdf
│   └── SEOJK_Circular_Green_Bond.pdf
├── ghg_methodology/
│   ├── GHG_Protocol_Corporate_Standard_v2015.pdf
│   ├── PCAF_Standard_Part_A_2022.pdf
│   └── IPCC_AR6_Chapter7_GWP.pdf
└── style_reference/
    ├── sample_esg_report_bank_A_anonymised.pdf
    ├── sample_esg_report_bank_B_anonymised.pdf
    └── sample_esg_report_bank_C_anonymised.pdf

REQ-KB-12: Metadata Schema per Document
Each document uploaded to the KB S3 source MUST have an accompanying .metadata.json file:
{
  "metadataAttributes": {
    "category": "gri",
    "framework": "GRI_305",
    "version": "2016",
    "effective_date": "2016-01-01",
    "document_title": "GRI 305: Emissions 2016",
    "language": "en",
    "contains_numeric_data": false
  }
}
Critical: contains_numeric_data MUST be false for all style reference documents. If true, the retrieval filter MUST exclude these chunks from any section that uses numeric DATA INPUT (prevents numeric contamination from sample reports).

 
11. Component Integration Matrix
11.1 Full Integration Matrix
From Component	To Component	Trigger Mechanism	Input Contract	Output Contract	Required IAM Permissions
EventBridge / Manual	Step Functions	API / Scheduled Rule	Execution input JSON (REQ-SFN-01)	Execution ARN	states:StartExecution on ESGReportGenerationStateMachine
Step Functions	Glue Scope 1 Job	Step Functions .sync	{ JobName, Arguments: { REPORTING_YEAR, S3_RAW_BUCKET, S3_CURATED_BUCKET } }	Job run success/fail status	glue:StartJobRun, glue:GetJobRun, glue:BatchStopJobRun
Step Functions	Glue PCAF Job	Step Functions .sync	{ JobName, Arguments: { REPORTING_YEAR, S3_RAW_BUCKET, S3_CURATED_BUCKET } }	Job run success/fail status	glue:StartJobRun, glue:GetJobRun (separate job name)
Glue ETL Jobs	S3 Curated Bucket	PySpark write.parquet()	PySpark DataFrame matching curated zone schema	Parquet files in s3://curated/zone/year=YYYY/	s3:PutObject, s3:GetObject on curated bucket prefix; kms:GenerateDataKey for SSE
Step Functions	Lambda AthenaQueryFn	Task state invoke	{ reporting_year, bank_id, framework }	DATA_INPUT JSON object with all aggregated zone fields	lambda:InvokeFunction; athena:StartQueryExecution, athena:GetQueryResults; s3:GetObject on aggregated prefix
Lambda AthenaQueryFn	Athena	boto3 athena client	SQL query strings + workgroup config	QueryExecutionId; CSV result via S3	athena:StartQueryExecution, athena:GetQueryExecution, athena:GetQueryResults, s3:PutObject on Athena results bucket
Lambda SectionGenFn	Bedrock Claude 3.5 Sonnet	boto3 bedrock-runtime converse API	{ system: hybrid_prompt, messages: [{ role: user, content: DATA_INPUT + RAG_CONTEXT }] }	JSON string: section_id, title, paragraphs, tables, footnotes	bedrock:InvokeModel on arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-*
Lambda SectionGenFn	Bedrock KB	boto3 bedrock-agent-runtime retrieve	{ knowledgeBaseId, retrievalQuery, retrievalConfiguration: { numberOfResults: 5, filter } }	RetrievalResults array with text + metadata	bedrock:Retrieve on Knowledge Base ARN
Lambda ValidationFn	SQS Review Queue	boto3 sqs send_message	{ section_id, validation_errors, section_json, task_token }	MessageId confirming queue receipt	sqs:SendMessage on review queue ARN
Lambda ValidationFn	SNS Notification Topic	boto3 sns publish	{ subject, message: validation_failure_summary }	SNS MessageId	sns:Publish on reviewer notification topic ARN
Human Reviewer	Step Functions Callback	API Gateway or console: SendTaskSuccess / SendTaskFailure	`{ taskToken, output: { decision: approve	reject, reviewer_id } }`	Execution resumes from HumanReviewGate state
Lambda AssemblyFn	S3 Output Bucket	python-docx + boto3 put_object	All section JSONs + metadata + assembly config	DOCX byte stream at reports/year=YYYY/framework/ESG_Report_{framework}_{year}_{timestamp}.docx	s3:PutObject, s3:GetObject on output bucket; kms:GenerateDataKey
Step Functions	SNS Completion Topic	Task state: SNS PublishMessage	{ framework, reporting_year, s3_uri, section_count, execution_arn }	SNS MessageId	sns:Publish on completion topic ARN
________________________________________
11.2 IAM Least-Privilege Requirements

REQ-IAM-01: One Role Per Lambda Function
Each Lambda function MUST have its own dedicated IAM execution role. Shared roles are PROHIBITED.
Lambda Function	Role Name	Trust Policy
ValidateInputFn	ESG-ValidateInput-ExecutionRole	Lambda service principal
AthenaQueryFn	ESG-AthenaQuery-ExecutionRole	Lambda service principal
SectionGenFn	ESG-SectionGen-ExecutionRole	Lambda service principal
ValidationFn	ESG-Validation-ExecutionRole	Lambda service principal
AssemblyFn	ESG-Assembly-ExecutionRole	Lambda service principal

Trust Policy (common to all Lambda roles):
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}

REQ-IAM-02: Scoped Resource ARNs
All IAM policies MUST use specific resource ARNs — never "Resource": "*".
Permission	Scoped Resource ARN Pattern
s3:GetObject (raw)	arn:aws:s3:::${RAW_BUCKET}/esg_raw/*
s3:GetObject (curated)	arn:aws:s3:::${CURATED_BUCKET}/esg_curated/*
s3:GetObject (aggregated)	arn:aws:s3:::${AGGREGATED_BUCKET}/esg_aggregated/*
s3:PutObject (curated)	arn:aws:s3:::${CURATED_BUCKET}/esg_curated/*
s3:PutObject (output)	arn:aws:s3:::${OUTPUT_BUCKET}/reports/*
s3:PutObject (Athena results)	arn:aws:s3:::${ATHENA_RESULTS_BUCKET}/esg-workgroup/*
bedrock:InvokeModel	arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0
bedrock:Retrieve	arn:aws:bedrock:${REGION}:${ACCOUNT}:knowledge-base/${KB_ID}
athena:StartQueryExecution	arn:aws:athena:${REGION}:${ACCOUNT}:workgroup/esg-reporting-workgroup
glue:StartJobRun	arn:aws:glue:${REGION}:${ACCOUNT}:job/esg-scope1-* and arn:aws:glue:${REGION}:${ACCOUNT}:job/esg-scope3-*
sqs:SendMessage	arn:aws:sqs:${REGION}:${ACCOUNT}:esg-review-queue
sns:Publish	arn:aws:sns:${REGION}:${ACCOUNT}:esg-*-topic
states:SendTaskSuccess	arn:aws:states:${REGION}:${ACCOUNT}:stateMachine:ESGReportGenerationStateMachine

REQ-IAM-03: Per-Lambda Policy Specifications
ValidateInputFn Policy:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3BucketCheck",
      "Effect": "Allow",
      "Action": ["s3:HeadBucket", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::${OUTPUT_BUCKET}"]
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:${REGION}:${ACCOUNT}:log-group:/aws/lambda/ESG-ValidateInputFn:*"
    }
  ]
}

AthenaQueryFn Policy:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AthenaExecution",
      "Effect": "Allow",
      "Action": ["athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults", "athena:StopQueryExecution"],
      "Resource": "arn:aws:athena:${REGION}:${ACCOUNT}:workgroup/esg-reporting-workgroup"
    },
    {
      "Sid": "S3ReadAggregated",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetBucketLocation"],
      "Resource": ["arn:aws:s3:::${AGGREGATED_BUCKET}", "arn:aws:s3:::${AGGREGATED_BUCKET}/esg_aggregated/*"]
    },
    {
      "Sid": "S3WriteAthenaResults",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:AbortMultipartUpload"],
      "Resource": "arn:aws:s3:::${ATHENA_RESULTS_BUCKET}/esg-workgroup/*"
    },
    {
      "Sid": "GlueCatalogRead",
      "Effect": "Allow",
      "Action": ["glue:GetTable", "glue:GetPartitions", "glue:GetDatabase"],
      "Resource": [
        "arn:aws:glue:${REGION}:${ACCOUNT}:catalog",
        "arn:aws:glue:${REGION}:${ACCOUNT}:database/esg_aggregated",
        "arn:aws:glue:${REGION}:${ACCOUNT}:table/esg_aggregated/*"
      ]
    },
    {
      "Sid": "KMSDecrypt",
      "Effect": "Allow",
      "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "arn:aws:kms:${REGION}:${ACCOUNT}:key/${KMS_KEY_ID}"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:${REGION}:${ACCOUNT}:log-group:/aws/lambda/ESG-AthenaQueryFn:*"
    }
  ]
}

SectionGenFn Policy:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvoke",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
    },
    {
      "Sid": "BedrockKBRetrieve",
      "Effect": "Allow",
      "Action": ["bedrock:Retrieve"],
      "Resource": "arn:aws:bedrock:${REGION}:${ACCOUNT}:knowledge-base/${KB_ID}"
    },
    {
      "Sid": "S3ReadPrompts",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::${CONFIG_BUCKET}/prompts/*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:${REGION}:${ACCOUNT}:log-group:/aws/lambda/ESG-SectionGenFn:*"
    }
  ]
}

ValidationFn Policy:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SQSSendMessage",
      "Effect": "Allow",
      "Action": ["sqs:SendMessage"],
      "Resource": "arn:aws:sqs:${REGION}:${ACCOUNT}:esg-review-queue"
    },
    {
      "Sid": "SNSPublish",
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "arn:aws:sns:${REGION}:${ACCOUNT}:esg-reviewer-notification-topic"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:${REGION}:${ACCOUNT}:log-group:/aws/lambda/ESG-ValidationFn:*"
    }
  ]
}

AssemblyFn Policy:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3WriteOutput",
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::${OUTPUT_BUCKET}/reports/*"
    },
    {
      "Sid": "S3ReadSections",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::${STAGING_BUCKET}/sections/*"
    },
    {
      "Sid": "KMSEncrypt",
      "Effect": "Allow",
      "Action": ["kms:GenerateDataKey", "kms:Encrypt"],
      "Resource": "arn:aws:kms:${REGION}:${ACCOUNT}:key/${KMS_KEY_ID}"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:${REGION}:${ACCOUNT}:log-group:/aws/lambda/ESG-AssemblyFn:*"
    }
  ]
}

REQ-IAM-04: Step Functions Execution Role
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeLambdas",
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": [
        "arn:aws:lambda:${REGION}:${ACCOUNT}:function:ESG-ValidateInputFn",
        "arn:aws:lambda:${REGION}:${ACCOUNT}:function:ESG-AthenaQueryFn",
        "arn:aws:lambda:${REGION}:${ACCOUNT}:function:ESG-SectionGenFn",
        "arn:aws:lambda:${REGION}:${ACCOUNT}:function:ESG-ValidationFn",
        "arn:aws:lambda:${REGION}:${ACCOUNT}:function:ESG-AssemblyFn"
      ]
    },
    {
      "Sid": "GlueJobRun",
      "Effect": "Allow",
      "Action": ["glue:StartJobRun", "glue:GetJobRun", "glue:BatchStopJobRun"],
      "Resource": [
        "arn:aws:glue:${REGION}:${ACCOUNT}:job/esg-scope1-ghg-etl",
        "arn:aws:glue:${REGION}:${ACCOUNT}:job/esg-scope3-pcaf-etl",
        "arn:aws:glue:${REGION}:${ACCOUNT}:job/esg-aggregation-etl"
      ]
    },
    {
      "Sid": "SQSSendForReview",
      "Effect": "Allow",
      "Action": ["sqs:SendMessage"],
      "Resource": "arn:aws:sqs:${REGION}:${ACCOUNT}:esg-review-queue"
    },
    {
      "Sid": "SNSPublish",
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": [
        "arn:aws:sns:${REGION}:${ACCOUNT}:esg-reviewer-notification-topic",
        "arn:aws:sns:${REGION}:${ACCOUNT}:esg-completion-topic"
      ]
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:${REGION}:${ACCOUNT}:log-group:/aws/states/ESGReportGenerationStateMachine:*"
    },
    {
      "Sid": "XRayTracing",
      "Effect": "Allow",
      "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
      "Resource": "*"
    }
  ]
}

Trust Policy for Step Functions Role:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "states.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "${ACCOUNT}"
        }
      }
    }
  ]
}
________________________________________
11.3 Data Flow Traceability Requirements
REQ-TRACE-01: Athena Query Tagging
Every Athena query executed by AthenaQueryFn MUST include execution context tags:
athena_client.start_query_execution(
    QueryString=sql,
    WorkGroup='esg-reporting-workgroup',
    QueryExecutionContext={
        'Database': 'esg_aggregated',
        'Catalog': 'AwsDataCatalog'
    },
    ResultConfiguration={
        'OutputLocation': f's3://{ATHENA_RESULTS_BUCKET}/esg-workgroup/{execution_id}/'
    },
    ExecutionParameters=[],
    ResultReuseConfiguration={
        'ResultReuseByAgeConfiguration': {
            'Enabled': True,
            'MaxAgeInMinutes': 60
        }
    }
)

Tag Requirements:
Tag Key	Tag Value	Purpose
esg:execution_id	Step Functions execution ARN	Links query to workflow
esg:reporting_year	Reporting year integer	Partition filter verification
esg:query_purpose	data_input_assembly | validation_recheck	Distinguishes primary vs validation queries
esg:timestamp	ISO 8601 UTC	Temporal ordering

REQ-TRACE-02: DOCX Execution ARN Property
The final DOCX file MUST contain a custom document property linking it to the Step Functions execution:
from docx.opc.constants import RELATIONSHIP_TYPE as RT

# Add custom properties to DOCX
core_properties = document.core_properties
core_properties.author = institution_name
core_properties.title = f"ESG Report {framework} {reporting_year}"
core_properties.subject = "AI-Generated ESG Disclosure"
core_properties.keywords = f"{framework};{reporting_year};{bank_id}"
core_properties.comments = f"Generated by ESGReportGenerationStateMachine. Execution: {execution_arn}"
core_properties.category = "ESG Reporting"
core_properties.revision = "1"

# Custom properties via XML manipulation
custom_props = {
    "execution_arn": execution_arn,
    "generation_timestamp": iso_timestamp,
    "framework": framework,
    "reporting_year": str(reporting_year),
    "bank_id": bank_id,
    "section_count": str(section_count),
    "validation_warnings": str(warning_count),
    "prompt_version": prompt_version,
    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

REQ-TRACE-03: Section JSON Generation Metadata
Every section JSON stored in the staging bucket MUST include generation metadata (as specified in REQ-TMPL-07):
{
  "metadata": {
    "section_id": "GRI_305_S1_2025",
    "framework": "GRI_305",
    "reporting_year": 2025,
    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "prompt_version": "1.0.0",
    "generation_timestamp": "2025-05-29T10:00:00Z",
    "data_input_hash": "sha256:a1b2c3d4e5f6...",
    "rag_context_hash": "sha256:f6e5d4c3b2a1...",
    "execution_id": "arn:aws:states:ap-southeast-1:123456789012:execution:ESGReport:run-001",
    "athena_query_execution_id": "abc-123-def-456",
    "kb_retrieval_session_id": "sess-789-xyz",
    "validation_outcome": "PASS",
    "validation_warnings": [],
    "retry_count": 0,
    "total_input_tokens": 3200,
    "total_output_tokens": 2800,
    "latency_ms": 4500
  },
  "section_id": "GRI_305_S1_2025",
  "title": "...",
  "paragraphs": [...],
  "tables": [...],
  "key_metrics": [...],
  "footnotes": [...],
  "framework_references": [...],
  "data_sources_used": [...]
}

REQ-TRACE-04: End-to-End Audit Trail
The complete audit trail for any generated report MUST be reconstructable from:
Artefact	Location	Retention
Step Functions execution history	AWS Console / API	90 days (default)
Glue job run logs	CloudWatch Logs /aws/glue/jobs/esg-*	90 days
Athena query results	s3://${ATHENA_RESULTS_BUCKET}/esg-workgroup/{execution_id}/	30 days
Section JSONs (all versions)	s3://${STAGING_BUCKET}/sections/{execution_id}/	365 days
Validation results	CloudWatch Logs /aws/lambda/ESG-ValidationFn	90 days
Human review decisions	SQS DLQ + CloudWatch Logs	365 days
Final DOCX	s3://${OUTPUT_BUCKET}/reports/year=YYYY/framework/	Indefinite
KB retrieval logs	CloudWatch Logs /aws/lambda/ESG-SectionGenFn	90 days


REQ-TRACE-05: S3 Object Tagging for Output DOCX
The final DOCX S3 object MUST have these S3 object tags:
Tag Key	Tag Value
esg:framework	Framework name
esg:reporting_year	Year integer
esg:bank_id	Institution ID
esg:execution_arn	Full execution ARN
esg:section_count	Number of sections assembled
esg:generation_date	ISO 8601 date
esg:validation_status	all_pass | with_warnings | with_exclusions
esg:prompt_version	Prompt version used

 
12. Kiro IDE Generation Instructions and Artefact Checklist

This section summarises the complete set of artefacts that Kiro IDE MUST generate when consuming this specification document. Each artefact is listed with its type, the specification section driving it, and the required file naming convention.
________________________________________
12.1 Artefact Generation Table
#	Artefact	Type	Driven by Section	Required File Name / Convention
1	Raw zone DDL (energy_consumption)	SQL	Secs 2.1, 4	sql/ddl/esg_raw_energy_consumption.sql
2	Raw zone DDL (loan_portfolio)	SQL	Secs 2.2, 4	sql/ddl/esg_raw_loan_portfolio.sql
3	Raw zone DDL (hr_metrics)	SQL	Secs 2.3, 4	sql/ddl/esg_raw_hr_metrics.sql
4	Curated zone DDL (ghg_scope1)	SQL	Secs 2.4, 4	sql/ddl/esg_curated_ghg_scope1.sql
5	Curated zone DDL (ghg_scope3_financed)	SQL	Secs 2.5, 4	sql/ddl/esg_curated_ghg_scope3.sql
6	Aggregated zone DDL (ghg_summary_annual)	SQL	Secs 2.6, 4	sql/ddl/esg_aggregated_ghg_summary.sql
7	Glue Scope 1 ETL Job	Python (PySpark)	Secs 3.1–3.3	glue_jobs/glue_job_scope1_ghg.py — must include all emission factor constants and imputation logic
8	Glue Scope 3 PCAF ETL Job	Python (PySpark)	Secs 3.4–3.5	glue_jobs/glue_job_scope3_pcaf.py — must include all 3 validation gates and confidence map
9	Aggregation Glue Job	Python (PySpark)	Sec 3.5	glue_jobs/glue_job_aggregation.py — computes intensity, YoY, base year comparisons
10	Synthetic Data Generator (energy)	Python	Sec 2.1	data_generation/generate_energy_consumption.py — outputs Parquet to data/raw/energy_consumption/
11	Synthetic Data Generator (loan portfolio)	Python	Sec 2.2	data_generation/generate_loan_portfolio.py — outputs Parquet to data/raw/loan_portfolio/
12	Synthetic Data Generator (hr_metrics)	Python	Sec 2.3	data_generation/generate_hr_metrics.py — outputs Parquet to data/raw/hr_metrics/
13	Base System Prompt	Text	Sec 5.2	prompts/system_base.txt — must contain 5 DATA INTEGRITY RULES and output JSON contract
14	GRI 305 Overlay	Text	Sec 5.3.1	prompts/overlay_gri305.txt — must cover GRI 305-1 through 305-5 disclosures
15	IFRS S2 Overlay	Text	Sec 5.3.2	prompts/overlay_ifrs_s2.txt — must include all four TCFD pillar requirements
16	CSRD/ESRS E1 Overlay	Text	Sec 5.3.3	prompts/overlay_esrs_e1.txt — must cover all 9 E1 datapoints and double materiality
17	OJK PSPK Overlay	Text	Sec 5.3.4	prompts/overlay_ojk_pspk.txt — must include POJK 51 table formats and Bahasa toggle
18	Scope 1 Section Template	Text	Sec 6.1	prompts/templates/scope1_template.txt
19	Scope 2 Section Template	Text	Sec 6.1 (variant)	prompts/templates/scope2_template.txt
20	Scope 3 PCAF Section Template	Text	Sec 6.2	prompts/templates/scope3_pcaf_template.txt
21	Intensity Section Template	Text	Sec 6.3	prompts/templates/intensity_template.txt
22	Governance Section Template	Text	Sec 6.4	prompts/templates/governance_template.txt
23	Strategy & Targets Template	Text	Sec 6.5	prompts/templates/targets_template.txt
24	Validation Lambda	Python	Sec 7	lambda/validation_fn/handler.py — must implement all VAL-NUM, VAL-STR, and VAL-PRH checks
25	Validation Lambda requirements	Text	Sec 7	lambda/validation_fn/requirements.txt
26	Section Generation Lambda	Python	Secs 5, 6, 10	lambda/section_gen_fn/handler.py — must handle prompt composition, KB retrieval, Bedrock invoke
27	Section Gen Lambda requirements	Text	Secs 5, 6, 10	lambda/section_gen_fn/requirements.txt
28	Assembly Lambda	Python	Sec 8	lambda/assembly_fn/handler.py — python-docx assembler; no LLM calls (CON-ASSY-01)
29	Assembly Lambda requirements	Text	Sec 8	lambda/assembly_fn/requirements.txt — must include python-docx>=1.1.0
30	Athena Query Lambda	Python	Secs 4.4, 9	lambda/athena_query_fn/handler.py — executes aggregated zone queries, builds DATA INPUT JSON
31	Athena Query Lambda requirements	Text	Sec 4.4	lambda/athena_query_fn/requirements.txt
32	Input Validation Lambda	Python	Sec 9.2	lambda/validate_input_fn/handler.py — validates execution input against REQ-SFN-01 schema
33	Step Functions ASL	JSON (ASL)	Sec 9	state_machines/esg_report_generation.asl.json — must include all 12 states from Section 9.1
34	IAM Policies (per Lambda)	JSON	Secs 11.1–11.2	iam/policies/{function_name}_policy.json — one file per Lambda execution role
35	IAM Trust Policies	JSON	Sec 11.2	iam/trust_policies/{role_name}_trust.json — Lambda and Step Functions trust policies
36	Step Functions Execution Role Policy	JSON	Sec 11.2	iam/policies/step_functions_execution_policy.json
37	KB Configuration	JSON	Sec 10	infra/bedrock_kb_config.json — chunk size, embedding model, AOSS index config, metadata schema
38	AOSS Index Mapping	JSON	Sec 10.2	infra/aoss_index_mapping.json — vector search index definition
39	KB Metadata Schema	JSON	Sec 10.3	infra/kb_metadata_schema.json — per-document metadata template
40	CDK Stack (main)	Python CDK	All sections	infra/esg_reporting_stack.py — deploys all Lambda, Glue, Step Functions, S3, KB resources
41	CDK App Entry	Python CDK	All sections	infra/app.py — CDK app entry point
42	Project README	Markdown	All sections	README.md — setup instructions, architecture overview, deployment steps
43	Configuration File	YAML	All sections	config/esg_config.yaml — environment-specific variables (bucket names, KB ID, region)
________________________________________
12.2 Kiro IDE Generation Rules (REQ-KIRO-01 through REQ-KIRO-08)

REQ-KIRO-01: Requirements as Acceptance Criteria
Every REQ-* identifier in this document MUST be treated as an acceptance criterion. Generated code MUST satisfy the requirement or the artefact is considered non-compliant. Kiro IDE SHOULD embed REQ-* identifiers as code comments at the point of implementation:

# REQ-ETL-02: Natural gas Scope 1 formula
scope1_natgas_tco2e = (
    natgas_gj * EF_NATGAS_KGCO2_PER_GJ +
    natgas_gj * EF_NATGAS_KGCH4_PER_GJ * GWP_CH4 +
    natgas_gj * EF_NATGAS_KGN2O_PER_GJ * GWP_N2O
) / 1000

REQ-KIRO-02: Prohibited Patterns (CON-*)
Every CON-* identifier defines a pattern that MUST NOT appear in generated code:
CON ID	Prohibited Pattern	Rationale
CON-ASSY-01	LLM invocation in assembly Lambda	Assembly must be deterministic
CON-PROMPT-01	Hard-coded numeric values in prompts	All numbers from DATA INPUT only
CON-ETL-01	Inline emission factor values (not from named constants)	Maintainability; single source of truth
CON-IAM-01	"Resource": "*" in any IAM policy	Least-privilege violation
CON-SFN-01	Unbounded retry without MaxAttempts	Infinite loop risk
CON-VAL-01	Skipping validation for any section type	All sections must be validated
CON-KB-01	Numeric values sourced from KB retrieval results	KB is for regulatory context only

REQ-KIRO-03: No Magic Numbers
All numeric constants (emission factors, GWP values, tolerances, token caps, timeouts) MUST be declared as named constants at module level or in a configuration file. Inline numeric literals are prohibited except for:
•	Mathematical constants (0, 1, 100, 1000)
•	Array indices
•	Loop counters

REQ-KIRO-04: No TODOs or Placeholders
Generated code MUST NOT contain:
•	# TODO comments
•	pass statements in non-abstract methods
•	NotImplementedError raises (except in abstract base classes)
•	Placeholder strings like "REPLACE_ME", "YOUR_VALUE_HERE", "xxx"
•	Empty function bodies
•	Commented-out code blocks

REQ-KIRO-05: Type Hints and Docstrings
All Python functions MUST include:
•	Full type hints (parameters and return type)
•	Google-style docstrings with Args, Returns, and Raises sections
•	Example:
def calculate_scope1_natgas(natgas_gj: float) -> float:
    """Calculate Scope 1 GHG emissions from natural gas combustion.
    
    Implements REQ-ETL-02: CO2 + CH4×GWP + N2O×GWP per GJ input.
    
    Args:
        natgas_gj: Natural gas consumption in gigajoules for the period.
        
    Returns:
        Scope 1 emissions from natural gas in tCO2e (metric tonnes).
        
    Raises:
        ValueError: If natgas_gj is negative.
    """

REQ-KIRO-06: Error Handling Standards
All Lambda handlers MUST implement:
•	Structured exception handling with specific exception types (not bare except:)
•	CloudWatch-compatible JSON logging with execution_id, section_id, error_type
•	Graceful degradation where specified (e.g., NULL handling for base year)
•	No silent failures — every caught exception must be logged

REQ-KIRO-07: Test File Generation
For each Lambda function, Kiro IDE SHOULD generate a corresponding test file:
Lambda	Test File	Minimum Test Cases
ValidateInputFn	tests/test_validate_input.py	Valid input; missing required field; invalid year range; invalid bank_id format
AthenaQueryFn	tests/test_athena_query.py	Successful query; empty result; timeout handling
SectionGenFn	tests/test_section_gen.py	Successful generation; Bedrock throttle retry; KB retrieval empty
ValidationFn	tests/test_validation.py	PASS case; NUM_MISMATCH; fabricated number; JSON parse error; PCAF conflation
AssemblyFn	tests/test_assembly.py	Single section; multi-section; cover page; table formatting

REQ-KIRO-08: Project Structure
The complete generated project MUST follow this directory structure:
esg-reporting-poc/
├── README.md
├── config/
│   └── esg_config.yaml
├── data_generation/
│   ├── generate_energy_consumption.py
│   ├── generate_loan_portfolio.py
│   └── generate_hr_metrics.py
├── sql/
│   └── ddl/
│       ├── esg_raw_energy_consumption.sql
│       ├── esg_raw_loan_portfolio.sql
│       ├── esg_raw_hr_metrics.sql
│       ├── esg_curated_ghg_scope1.sql
│       ├── esg_curated_ghg_scope3.sql
│       └── esg_aggregated_ghg_summary.sql
├── glue_jobs/
│   ├── glue_job_scope1_ghg.py
│   ├── glue_job_scope3_pcaf.py
│   └── glue_job_aggregation.py
├── prompts/
│   ├── system_base.txt
│   ├── overlay_gri305.txt
│   ├── overlay_ifrs_s2.txt
│   ├── overlay_esrs_e1.txt
│   ├── overlay_ojk_pspk.txt
│   └── templates/
│       ├── scope1_template.txt
│       ├── scope2_template.txt
│       ├── scope3_pcaf_template.txt
│       ├── intensity_template.txt
│       ├── governance_template.txt
│       └── targets_template.txt
├── lambda/
│   ├── validate_input_fn/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── athena_query_fn/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── section_gen_fn/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── validation_fn/
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── assembly_fn/
│       ├── handler.py
│       └── requirements.txt
├── state_machines/
│   └── esg_report_generation.asl.json
├── iam/
│   ├── policies/
│   │   ├── validate_input_fn_policy.json
│   │   ├── athena_query_fn_policy.json
│   │   ├── section_gen_fn_policy.json
│   │   ├── validation_fn_policy.json
│   │   ├── assembly_fn_policy.json
│   │   └── step_functions_execution_policy.json
│   └── trust_policies/
│       ├── lambda_trust_policy.json
│       └── step_functions_trust_policy.json
├── infra/
│   ├── app.py
│   ├── esg_reporting_stack.py
│   ├── bedrock_kb_config.json
│   ├── aoss_index_mapping.json
│   └── kb_metadata_schema.json
└── tests/
    ├── test_validate_input.py
    ├── test_athena_query.py
    ├── test_section_gen.py
    ├── test_validation.py
    └── test_assembly.py
