
# [Outline] ESG Report Generation POC — Spec-Driven Requirements for Kiro

## Sources
- AI_Powered_ESG_Reporting_Architecture.docx — Reference architecture, data contract, validation rules
- ESG_Technical_Specification.docx — Code examples, schema definitions, prompt architecture
- Conversation context — All technical decisions (hybrid prompt, multi-framework, no context limit)

## Core Thesis
This document provides **specification-only requirements** (not code) that serve as a definitive "pakem" for Kiro IDE to generate all production code — including data generation scripts, ETL jobs, agent logic, and report assembly. Every spec references back to the two preceding architecture documents.

## [Draft] 1. Document Purpose

This document is a **Spec-Driven Requirement** — a structured set of specifications for each component in the ESG Report Generation pipeline. It is designed to be consumed by AI-assisted code generation tools (e.g., Kiro IDE) to produce production-ready implementations.

**How to use this document:**
- Each component section defines WHAT to build (not HOW)
- Schemas define exact column names, types, units, and constraints
- Business logic is described as rules and formulas
- Feed each section to Kiro as a generation prompt
- Validate generated code against the specs herein

**Relationship to preceding documents:**
- Architecture Guide → defines the WHY and WHERE
- Technical Specification → provides reference code examples
- This Document (Specs) → defines the WHAT for code generation

## [Outline] 2. System Overview & Component Map

- Component dependency diagram (text-based)
- Execution order: Data Gen → Upload S3 → Glue ETL → Athena → Agent → Validate → Assemble
- Per-component: name, purpose, input, output, AWS service, trigger

## [Draft] 3. Data Generation Specifications

### 3.1 Component: Energy Consumption Generator

**Purpose:** Generate synthetic energy consumption records in Parquet format for Scope 1 & 2 source data.

**Output:** `s3://esg-datalake/raw/energy_consumption/reporting_year={year}/reporting_month={month}/`

**Output Format:** Apache Parquet, SNAPPY compression, partitioned by year + month

**Output Schema:**

| Column | Type | Unit | Nullable | Constraints |
|--------|------|------|----------|-------------|
| record_id | STRING | — | No | UUID v4, unique |
| bank_id | STRING | — | No | Constant per institution |
| facility_id | STRING | — | No | Pattern: FAC-XXXX |
| facility_type | STRING | — | No | ENUM: head_office, regional_office, branch, data_center, warehouse, atm_center |
| region | STRING | — | No | Indonesian province name |
| business_unit | STRING | — | No | Same as facility_type |
| source_type | STRING | — | No | ENUM: electricity, natural_gas, diesel_generator, diesel_fleet, petrol_fleet, lpg |
| scope | INT | — | No | 1 or 2 |
| quantity | DOUBLE | varies | No | > 0, see value ranges below |
| unit | STRING | — | No | kWh, m3, liters, or kg (matches source_type) |
| period_start | DATE | — | No | First day of month |
| period_end | DATE | — | No | Last day of month |
| data_source | STRING | — | No | ENUM: utility_bill, meter_reading, estimate |
| meter_id | STRING | — | No | Pattern: MTR-{facility_id}-{source_prefix} |
| reporting_year | INT | — | No | Partition key |
| reporting_month | INT | — | No | Partition key, 1-12 |
| ingestion_timestamp | STRING | — | No | ISO 8601 |

**Value Ranges (per month, by facility size):**

| source_type | Unit | Large (min-max) | Medium (min-max) | Small (min-max) |
|-------------|------|-----------------|------------------|-----------------|
| electricity | kWh | 80,000 – 250,000 | 15,000 – 60,000 | 3,000 – 12,000 |
| natural_gas | m3 | 500 – 3,000 | 100 – 800 | 0 – 50 |
| diesel_generator | liters | 200 – 2,000 | 50 – 500 | 10 – 150 |
| diesel_fleet | liters | 1,000 – 8,000 | 200 – 2,000 | 0 – 300 |
| petrol_fleet | liters | 500 – 5,000 | 100 – 1,500 | 0 – 200 |
| lpg | kg | 50 – 300 | 10 – 80 | 0 – 20 |

**Facility Size Mapping:**

| facility_type | size_category | count |
|---------------|--------------|-------|
| head_office | large | 2 |
| regional_office | medium | 18 |
| branch | small | 150 |
| data_center | large | 5 |
| warehouse | medium | 10 |
| atm_center | small | 15 |

**Generation Rules:**
- Total facilities: 200
- Reporting years: 2022, 2023, 2024, 2025
- Months per year: 12
- YoY reduction factors: 2022=1.00, 2023=0.97, 2024=0.94, 2025=0.90
- Seasonal multiplier: Jun-Sep=1.15 (dry/hot), Dec-Feb=0.95
- Random noise: ±10% per record
- Data source distribution: utility_bill=60%, meter_reading=25%, estimate=15%
- Skip records where quantity=0

**Relationships:**
- facility_id → referenced by curated.ghg_scope1.facility_id
- source_type + scope → determines which Glue ETL job processes it

---

### 3.2 Component: Loan Portfolio Generator

**Purpose:** Generate synthetic loan portfolio & borrower emissions for PCAF Scope 3 Cat.15

**Output Files:**
- `s3://esg-datalake/raw/loan_portfolio/reporting_year={year}/`
- `s3://esg-datalake/raw/borrower_emissions/reporting_year={year}/`

**Loan Portfolio Schema:**

| Column | Type | Unit | Nullable | Constraints |
|--------|------|------|----------|-------------|
| loan_id | STRING | — | No | Pattern: LN-{borrower_id}-{year} |
| borrower_id | STRING | — | No | Pattern: BRW-XXXXX |
| borrower_name | STRING | — | No | Generated name |
| sector_code | STRING | — | No | ENUM: see Sector table below |
| sector_name | STRING | — | No | Display name of sector |
| asset_class | STRING | — | No | ENUM: corporate_loan, project_finance, commercial_real_estate, mortgage, motor_vehicle |
| country_code | STRING | — | No | "ID" (Indonesia) |
| outstanding_amount_idr | DOUBLE | IDR | No | See ranges below |
| total_equity_idr | DOUBLE | IDR | No | > 0 |
| total_debt_idr | DOUBLE | IDR | No | > 0 |
| borrower_revenue_idr | DOUBLE | IDR | Yes | > 0 |
| pcaf_data_quality_tier | INT | — | No | 1-5 |
| ef_source | STRING | — | No | Matches tier (see mapping) |
| is_green_loan | BOOLEAN | — | No | 12% true |
| snapshot_date | DATE | — | No | Year-end: {year}-12-31 |
| reporting_year | INT | — | No | Partition key |
| currency | STRING | — | No | "IDR" |
| bank_id | STRING | — | No | Institution ID |

**Outstanding Amount Ranges by Asset Class:**

| asset_class | Weight | Min (IDR) | Max (IDR) |
|-------------|--------|-----------|-----------|
| corporate_loan | 40% | 5,000,000,000 | 2,000,000,000,000 |
| project_finance | 15% | 50,000,000,000 | 5,000,000,000,000 |
| commercial_real_estate | 20% | 10,000,000,000 | 1,000,000,000,000 |
| mortgage | 15% | 500,000,000 | 10,000,000,000 |
| motor_vehicle | 10% | 100,000,000 | 2,000,000,000 |

**Sector Definitions with Emission Intensity:**

| sector_code | Weight | Intensity (tCO2e/IDR Bn) min-max | Equity Ratio |
|-------------|--------|-----------------------------------|--------------|
| palm_oil | 12% | 800 – 2,500 | 0.35 |
| coal_mining | 5% | 2,000 – 8,000 | 0.30 |
| oil_gas | 8% | 1,500 – 5,000 | 0.40 |
| manufacturing | 15% | 200 – 1,200 | 0.40 |
| transportation | 10% | 300 – 1,500 | 0.35 |
| real_estate | 12% | 50 – 300 | 0.45 |
| agriculture | 10% | 400 – 1,800 | 0.30 |
| telecommunications | 8% | 20 – 150 | 0.50 |
| financial_services | 10% | 5 – 50 | 0.55 |
| retail_consumer | 10% | 30 – 200 | 0.45 |

**PCAF Tier Distribution:**

| Tier | % | Description | EF Source |
|------|---|-------------|-----------|
| 1 | 5% | Verified reported | Borrower CDP/Annual Report (verified) |
| 2 | 15% | Reported unverified | Borrower Annual Report (unverified) |
| 3 | 30% | Physical activity | PCAF Physical Activity Database |
| 4 | 35% | Economic activity | PCAF Economic Activity EF |
| 5 | 15% | Asset class proxy | PCAF Asset Class Proxy |

**Borrower Emissions Schema:**

| Column | Type | Unit | Nullable | Constraints |
|--------|------|------|----------|-------------|
| borrower_id | STRING | — | No | FK to loan_portfolio |
| reporting_year | INT | — | No | Partition key |
| scope1_emissions_tco2e | DOUBLE | tCO2e | No | ≥ 0 |
| scope2_emissions_tco2e | DOUBLE | tCO2e | No | ≥ 0 |
| scope3_emissions_tco2e | DOUBLE | tCO2e | No | ≥ 0 |
| total_emissions_tco2e | DOUBLE | tCO2e | No | = scope1 + scope2 + scope3 |
| emission_unit | STRING | — | No | "tCO2e" |
| gas_type | STRING | — | No | "CO2e" |
| emission_factor_used | DOUBLE | tCO2e/IDR Bn | No | Within sector intensity range |
| ef_source | STRING | — | No | Matches PCAF tier |
| pcaf_data_quality_tier | INT | — | No | 1-5, same as loan |
| verification_status | STRING | — | No | "verified" if tier=1, else "unverified" |
| methodology | STRING | — | No | "GHG Protocol Corporate Standard" |

**Generation Rules:**
- Total borrowers: 2,000
- Reporting years: 2022, 2023, 2024, 2025
- Portfolio growth: 2022=1.00, 2023=+8%, 2024=+12%, 2025=+15%
- Emission reduction: 2022=1.00, 2023=-3%, 2024=-6%, 2025=-10%
- Scope split per borrower: S1=20-50%, S2=10-30%, S3=remainder
- Outstanding noise: ±15% per year
- Constraint: total_emissions = scope1 + scope2 + scope3 (exact)

**Relationships:**
- borrower_id in loan_portfolio = borrower_id in borrower_emissions (1:1 per year)
- pcaf_data_quality_tier must match between both tables

## [Draft] 4. ETL Specifications (Glue Jobs)

### 4.1 Component: Scope 1 Direct Emissions ETL

**Job Name:** `esg-etl-scope1-direct`
**Runtime:** AWS Glue 4.0, PySpark, G.1X, 10 DPU
**Trigger:** EventBridge schedule (monthly) or on-demand
**Input:** `esg_raw.energy_consumption` WHERE scope = 1
**Output:** `s3://esg-datalake/curated/ghg_scope1/reporting_year={year}/`

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| REPORTING_YEAR | INT | Fiscal year to process |
| BANK_ID | STRING | Institution identifier |
| RAW_BUCKET | STRING | S3 bucket for raw zone |
| CURATED_BUCKET | STRING | S3 bucket for curated zone |

**Business Logic — Emission Factors (IPCC AR6 / DEFRA 2025):**

| source_type | Factor | Unit | Gas | GWP (AR6) |
|-------------|--------|------|-----|-----------|
| natural_gas | 0.00202 | tCO2e/m3 | CO2 | 1.0 |
| diesel_generator | 0.002676 | tCO2e/liter | CO2 | 1.0 |
| diesel_fleet | 0.002680 | tCO2e/liter | CO2 | 1.0 |
| petrol_fleet | 0.002310 | tCO2e/liter | CO2 | 1.0 |
| lpg | 0.00151 | tCO2e/kg | CO2 | 1.0 |

**Calculation Formula:**
```
emissions_tco2e = quantity × emission_factor
```

**Emission Source Classification:**

| source_type | emission_source |
|-------------|----------------|
| natural_gas, lpg, diesel_generator | stationary_combustion |
| diesel_fleet, petrol_fleet | mobile_combustion |

**Data Quality Scoring:**

| data_source | quality_score |
|-------------|--------------|
| meter_reading | 1 |
| utility_bill | 2 |
| estimate | 4 |

**Validation Gates (pre-output):**
1. No null emissions_tco2e
2. All emissions_tco2e > 0
3. Sum of output emissions = sum of (input quantity × EF) ± 0.01% tolerance
4. Record count output ≤ record count input (filtered only)

**Output Schema:** Reference `esg_curated.ghg_scope1` in Athena DDL (Section 5)

---

### 4.2 Component: Scope 2 Energy Indirect Emissions ETL

**Job Name:** `esg-etl-scope2-indirect`
**Runtime:** AWS Glue 4.0, PySpark, G.1X, 10 DPU
**Input:** `esg_raw.energy_consumption` WHERE source_type = 'electricity'
**Output:** `s3://esg-datalake/curated/ghg_scope2/reporting_year={year}/`

**Business Logic — Grid Emission Factors:**

| Grid Region | EF Location (tCO2e/MWh) | Source |
|-------------|--------------------------|--------|
| Indonesia (PLN national) | 0.760 | RUPTL/PLN 2024 |
| Java-Bali grid | 0.725 | PLN regional |
| Sumatra grid | 0.802 | PLN regional |
| Kalimantan grid | 0.845 | PLN regional |
| Sulawesi grid | 0.790 | PLN regional |

**Dual Reporting Requirement (GHG Protocol Scope 2 Guidance):**

| Method | Formula | When to Use |
|--------|---------|-------------|
| Location-based | (kWh / 1000) × grid_ef | Always required |
| Market-based | (kWh / 1000) × supplier_ef | If has_rec=true → 0; if has_ppa=true → PPA factor; else → residual mix |

**Calculation Rules:**
```
consumption_mwh = quantity_kwh / 1000
emissions_location_tco2e = consumption_mwh × ef_location_tco2e_per_mwh
emissions_market_tco2e = 
    IF has_rec THEN 0
    ELIF has_ppa THEN consumption_mwh × ppa_ef
    ELSE consumption_mwh × residual_mix_ef
```

**Output Schema:** Reference `esg_curated.ghg_scope2` in Athena DDL

---

### 4.3 Component: Scope 3 Category 15 PCAF Financed Emissions ETL

**Job Name:** `esg-etl-scope3-pcaf`
**Runtime:** AWS Glue 4.0, PySpark, G.2X, 20 DPU (larger dataset)
**Input:** `esg_raw.loan_portfolio` JOIN `esg_raw.borrower_emissions`
**Output:** `s3://esg-datalake/curated/ghg_scope3_financed/reporting_year={year}/`

**Business Logic — PCAF Formula:**
```
attribution_factor = outstanding_amount / (total_equity + total_debt)
financed_emissions = attribution_factor × borrower_total_emissions
weighted_quality_score = (outstanding_amount × pcaf_tier) / SUM(all outstanding)
```

**Validation Gates:**
1. attribution_factor must be between 0 and 1 (cap at 1.0 if exceeds)
2. financed_emissions ≥ 0
3. total_equity + total_debt > 0 (no division by zero)
4. SUM(financed_emissions) per sector = aggregated sector total ± 0.01%

**PCAF Data Quality Weighted Score (portfolio-level):**
```
portfolio_quality = SUM(outstanding_i × tier_i) / SUM(outstanding_i)
```

**Output Schema:** Reference `esg_curated.ghg_scope3_financed` in Athena DDL

---

### 4.4 Component: Annual Aggregation ETL

**Job Name:** `esg-etl-aggregation`
**Runtime:** AWS Glue 4.0, PySpark, G.1X, 5 DPU
**Input:** All curated tables (scope1, scope2, scope3)
**Output:**
- `s3://esg-datalake/aggregated/ghg_summary_annual/`
- `s3://esg-datalake/aggregated/pcaf_by_sector/`

**Business Logic — GHG Summary:**
```
scope1_tco2e = SUM(curated.ghg_scope1.emissions_tco2e) WHERE year = X
scope2_location = SUM(curated.ghg_scope2.emissions_location_tco2e) WHERE year = X
scope2_market = SUM(curated.ghg_scope2.emissions_market_tco2e) WHERE year = X
scope3_cat15 = SUM(curated.ghg_scope3_financed.financed_emissions_tco2e) WHERE year = X
total_tco2e = scope1 + scope2_market + scope3_cat15
yoy_change_pct = ((current_year_total - previous_year_total) / previous_year_total) × 100
vs_base_year_pct = ((current_year_total - base_year_total) / base_year_total) × 100
intensity_per_revenue = total_tco2e / revenue_idr_billion
intensity_per_fte = total_tco2e / fte_count
```

**Critical Constraint:** `total_tco2e` MUST equal `scope1 + scope2_market + scope3_cat15` exactly. This is validation rule R2.

**Output Schema:** Reference `esg_aggregated.ghg_summary_annual` and `esg_aggregated.pcaf_by_sector` in Athena DDL

## [Draft] 5. Athena DDL Specifications

- Reference full DDL from ESG_Technical_Specification.docx Section 3
- Include: all 9 tables (3 raw, 3 curated, 3 aggregated)
- Include: partition projection configuration
- Include: 4 analytical queries used by Agent tools

## [Draft] 6. Agent Prompt Specifications (Hybrid Architecture)

### 6.1 Base System Prompt — Specification

**File:** `prompts/system_prompt_base.txt`
**Purpose:** Shared rules applied to ALL framework generations
**Injected:** Every Claude invocation as system prompt prefix

**Required Sections in Base Prompt:**

| Section | Purpose | Key Rules |
|---------|---------|-----------|
| ROLE | Define agent persona | "You are an ESG Reporting Specialist for a financial institution" |
| DATA_INTEGRITY | Prevent hallucination | "NEVER generate, fabricate, or estimate numerical values" |
| NUMBER_RULES | Enforce data source | "ALL numbers MUST come from the provided DATA INPUT section" |
| STYLE | Output consistency | "Use formal professional English, active voice, third person" |
| STRUCTURE | Section format | "Each section must contain: opening context, data presentation, analysis, forward-looking statement" |
| CITATIONS | Source attribution | "Cite methodology as (GHG Protocol, YYYY) or (PCAF, YYYY)" |
| FORMATTING | Output contract | "Return JSON with keys: title, narrative, tables, key_metrics" |
| CONSTRAINTS | Boundary rules | "Do NOT provide recommendations unless specifically asked. Do NOT compare to competitors. Do NOT reference data not in DATA INPUT." |

**Anti-Hallucination Rules (MANDATORY in base prompt):**
1. Every number in narrative MUST exist verbatim in DATA INPUT
2. Never round, estimate, or derive numbers not provided
3. If data is missing, state "Data not available for this reporting period"
4. Percentages must match pre-computed values (do not recalculate)
5. Year-over-year changes must use provided yoy_change_pct (not self-computed)

**Output JSON Contract:**
```json
{
  "section_id": "string — matches template section ID",
  "title": "string — section heading",
  "narrative": "string — full section text, markdown formatted",
  "tables": [
    {
      "caption": "string",
      "headers": ["col1", "col2"],
      "rows": [["val1", "val2"]]
    }
  ],
  "key_metrics": [
    {"label": "string", "value": "number", "unit": "string", "source_column": "string"}
  ],
  "framework_references": ["GRI 305-1a", "IFRS S2 para 29a"],
  "data_sources_used": ["ghg_summary_annual.scope1_tco2e"]
}
```

---

### 6.2 Framework Overlay — GRI 305

**File:** `prompts/overlay_gri_305.txt`
**Injected:** When generating GRI 305 sections

**Specification:**

| Attribute | Requirement |
|-----------|-------------|
| Disclosure IDs | 305-1 (Scope 1), 305-2 (Scope 2), 305-3 (Scope 3), 305-4 (Intensity), 305-5 (Reduction) |
| Mandatory fields per disclosure | See GRI 305 requirements table below |
| Tone | Factual, concise, disclosure-oriented |
| Structure | One heading per disclosure ID, subpoints for each requirement |

**GRI 305 Required Disclosures:**

| Disclosure | Required Data Points |
|------------|---------------------|
| 305-1a | Gross Scope 1 in tCO2e |
| 305-1b | Gases included (CO2, CH4, N2O, HFCs, PFCs, SF6, NF3) |
| 305-1c | Biogenic emissions (separate) |
| 305-1d | Base year, rationale, emissions, context for change |
| 305-1e | Source of emission factors and GWP rates |
| 305-1f | Consolidation approach |
| 305-1g | Standards, methodologies, assumptions |
| 305-2a | Gross Scope 2 location-based (tCO2e) |
| 305-2b | Gross Scope 2 market-based (tCO2e) |
| 305-3a | Gross Scope 3 (tCO2e) |
| 305-3b | Categories included |
| 305-4a | Intensity ratio, numerator, denominator |
| 305-5a | Reductions achieved (tCO2e), gases, scope, base year |

**Style Rules (GRI-specific):**
- Use "The organization" as subject (not company name in every sentence)
- Report both location-based AND market-based for Scope 2
- Explicitly state all gases included even if only CO2 is material
- State base year rationale

---

### 6.3 Framework Overlay — IFRS S2

**File:** `prompts/overlay_ifrs_s2.txt`
**Injected:** When generating IFRS S2 sections

**Specification:**

| Attribute | Requirement |
|-----------|-------------|
| Pillar Structure | Governance → Strategy → Risk Management → Metrics & Targets |
| Paragraph references | IFRS S2 para 5-12 (Governance), 13-22 (Strategy), 23-28 (Risk Mgmt), 29-36 (Metrics) |
| Tone | Investor-focused, financial materiality, forward-looking |
| Climate scenarios | Must reference at least 2 scenarios (e.g., 1.5°C aligned, >2°C) |

**Required Content per Pillar:**

| Pillar | Key Requirements |
|--------|-----------------|
| Governance | Board oversight, management role, climate competence, monitoring frequency |
| Strategy | Climate risks/opportunities identified, business model impact, transition plan, scenario analysis |
| Risk Management | Identification process, assessment criteria, integration with ERM |
| Metrics & Targets | Scope 1/2/3, cross-industry metrics (Table B), industry-specific, targets vs progress |

**IFRS S2 Cross-Industry Metrics (Table B) — Must Include:**
- GHG emissions (Scope 1, 2, 3) absolute
- Transition risks amount
- Physical risks amount  
- Climate-related opportunities amount
- Capital deployment toward climate
- Internal carbon price (if used)
- Remuneration linked to climate

**Style Rules (IFRS-specific):**
- Frame in terms of financial impact ("This represents X% of total assets at risk")
- Use "climate-related financial disclosures" terminology
- Reference specific IFRS S2 paragraphs
- Forward-looking statements require qualifiers

---

### 6.4 Framework Overlay — CSRD/ESRS E1

**File:** `prompts/overlay_csrd_esrs.txt`
**Injected:** When generating CSRD sections

**Specification:**

| Attribute | Requirement |
|-----------|-------------|
| Standard reference | ESRS E1 Climate Change |
| Disclosure requirements | E1-1 through E1-9 |
| Double materiality | Must address both impact materiality AND financial materiality |
| Transition plan | ESRS E1-1 requires detailed transition plan aligned with Paris Agreement |

**ESRS E1 Disclosure Requirements:**

| DR | Title | Key Content |
|----|-------|-------------|
| E1-1 | Transition plan for climate change mitigation | Paris-aligned targets, actions, resources, timeline |
| E1-2 | Policies related to climate change | Policies adopted, scope, engagement processes |
| E1-3 | Actions and resources | CapEx/OpEx allocated, timeline |
| E1-4 | Targets related to climate | Absolute & intensity targets, base year, progress |
| E1-5 | Energy consumption and mix | Total MWh, renewable %, fossil breakdown |
| E1-6 | Gross Scope 1/2/3 and Total | By country/scope, methodology, changes |
| E1-7 | GHG removals and carbon credits | If applicable |
| E1-8 | Internal carbon pricing | If applicable |
| E1-9 | Anticipated financial effects | Physical risks €, transition risks €, opportunities € |

**Style Rules (ESRS-specific):**
- Use "double materiality" framing explicitly
- State whether topic passes both impact and financial materiality tests
- Include value chain coverage (upstream, own operations, downstream)
- Reference ESRS paragraph numbers

---

### 6.5 Framework Overlay — OJK PSPK

**File:** `prompts/overlay_ojk_pspk.txt`
**Injected:** When generating OJK PSPK sections

**Specification:**

| Attribute | Requirement |
|-----------|-------------|
| Regulation | POJK No. 14/2023 (PSPK) + SE OJK Circular |
| Effective | Mandatory January 2027 for KBMI 3-4 banks |
| Language consideration | Formal English (for this POC); production may need Bahasa |
| Structure | Follows PSPK Annex structure |

**OJK PSPK Required Disclosures for Banks:**

| Category | Specific Requirements |
|----------|----------------------|
| Governance | Sustainability committee, board competence, oversight frequency |
| Strategy | Sustainable finance portfolio %, green asset ratio, transition plan |
| Risk Management | Climate stress testing, physical/transition risk in ICAAP |
| Metrics — Environment | Scope 1/2/3 emissions, energy intensity, financed emissions (PCAF), green portfolio % |
| Metrics — Social | Financial inclusion metrics, diversity, community investment |
| Metrics — Governance | Anti-corruption, ethics violations, ESG-linked remuneration |

**Indonesia-Specific Context (inject into prompt):**
- Reference OJK KBMI classification
- Mention Indonesia NDC (Net Zero 2060)
- Reference national grid factor (PLN)
- Cite PSPK regulation number explicitly

**Style Rules (PSPK-specific):**
- Formal regulatory tone
- Reference specific PSPK annex items
- Include both Indonesian regulation context AND international alignment
- State KBMI category applicability

## [Draft] 7. Section Generation Prompt Specifications

### 7.1 Prompt Template Structure

Every section generation prompt follows this structure:

```
[BASE SYSTEM PROMPT]
+
[FRAMEWORK OVERLAY]
+
[SECTION-SPECIFIC PROMPT]
    ├── SECTION_ID: unique identifier
    ├── SECTION_TITLE: heading text
    ├── OBJECTIVE: what this section must achieve
    ├── DATA_INPUT: pre-fetched data (from Athena query result)
    ├── RAG_CONTEXT: retrieved regulatory text (from Knowledge Base)
    ├── REQUIRED_ELEMENTS: checklist of mandatory content
    ├── WORD_COUNT: target length
    └── OUTPUT_FORMAT: JSON structure (from base prompt contract)
```

### 7.2 Section Prompt Definitions

**Section: scope1_disclosure**
- Objective: "Disclose total Scope 1 direct GHG emissions with full methodology transparency"
- Data query: `SELECT * FROM esg_aggregated.ghg_summary_annual WHERE year = {year}`
- RAG query: "GRI 305-1 disclosure requirements" + "IFRS S2 paragraph 29"
- Required elements: gross emissions, gas breakdown, emission sources, EF source, GWP version, consolidation approach, base year comparison, YoY change
- Word count: 400-600

**Section: scope2_disclosure**
- Objective: "Disclose Scope 2 energy indirect emissions using dual reporting"
- Data query: Same as scope1 (ghg_summary_annual)
- RAG query: "GHG Protocol Scope 2 Guidance dual reporting" + "GRI 305-2"
- Required elements: location-based total, market-based total, grid region, EF source, REC/PPA status, difference explanation
- Word count: 300-500

**Section: pcaf_financed_emissions**
- Objective: "Disclose PCAF Scope 3 Category 15 financed emissions by sector"
- Data query: `SELECT * FROM esg_aggregated.pcaf_by_sector WHERE year = {year} ORDER BY total_financed_emissions DESC`
- RAG query: "PCAF Global GHG Accounting Standard" + "PCAF data quality scoring"
- Required elements: total financed emissions, top 5 sectors, attribution methodology, data quality score, asset class coverage, portfolio coverage %
- Word count: 500-800

**Section: governance**
- Objective: "Describe board-level governance of climate-related risks and opportunities"
- Data query: None (qualitative — from RAG + template)
- RAG query: "IFRS S2 governance pillar para 5-12" + "ESRS E1-1"
- Required elements: board oversight, management role, committee structure, monitoring frequency, competence
- Word count: 400-600

**Section: strategy_and_targets**
- Objective: "Describe climate strategy, scenario analysis results, and emission reduction targets"
- Data query: Multi-year trend from ghg_summary_annual
- RAG query: "IFRS S2 strategy pillar" + "SBTi financial sector guidance"
- Required elements: identified risks/opportunities, scenario analysis, transition plan, targets (absolute/intensity), progress vs target
- Word count: 600-900

**Section: executive_summary**
- Objective: "Provide high-level overview of all ESG performance for the reporting year"
- Data query: Full ghg_summary_annual for current year + previous year
- RAG query: None
- Required elements: headline metrics, key achievements, material changes, forward-looking statement
- Word count: 300-400
- IMPORTANT: Generate this section LAST (after all others) to ensure consistency

## [Draft] 8. Validation Specifications

### 8.1 Validation Rules

| Rule ID | Name | Logic | Failure Action |
|---------|------|-------|----------------|
| R1 | Number Source Check | Every number in narrative text MUST exist in DATA_INPUT | Regenerate section |
| R2 | Sum Consistency | scope1 + scope2_market + scope3_cat15 = total_tco2e (±0.01%) | Fail pipeline |
| R3 | YoY Accuracy | Stated YoY % = pre-computed yoy_change_pct (±0.1 ppt) | Regenerate section |
| R4 | Intensity Accuracy | Stated intensity = pre-computed intensity_per_revenue (±0.01) | Regenerate section |
| R5 | Required Phrases | Framework-specific mandatory terms present in output | Regenerate section |

### 8.2 Per-Rule Specification

**R1 — Number Source Check:**
- Extract all numbers from generated narrative (regex: decimals, integers, percentages)
- For each extracted number, verify it exists in the DATA_INPUT provided to that section
- Tolerance: integers exact match; decimals ±0.01; percentages ±0.1
- Exception: years (2022-2030) and framework references (e.g., "305-1") are excluded

**R2 — Sum Consistency:**
- Query: scope1_tco2e + scope2_market_tco2e + scope3_cat15_tco2e vs total_tco2e
- Tolerance: ±0.01% of total
- Applies to: both data AND narrative claims about total

**R3 — YoY Accuracy:**
- If narrative states "X% decrease/increase year-over-year"
- Compare X to ghg_summary_annual.yoy_change_pct
- Tolerance: ±0.1 percentage point

**R4 — Intensity Accuracy:**
- If narrative states intensity ratio
- Compare to ghg_summary_annual.intensity_tco2e_per_idr_bn
- Tolerance: ±0.01

**R5 — Required Phrases (per framework):**

| Framework | Required Phrases (at least 1 from each group) |
|-----------|----------------------------------------------|
| GRI 305 | ["operational control" OR "equity share"], ["tCO2e"], ["base year"] |
| IFRS S2 | ["climate-related"], ["financial"], ["Scope 1", "Scope 2", "Scope 3"] |
| CSRD | ["double materiality"], ["transition plan"], ["ESRS"] |
| OJK PSPK | ["PSPK" OR "POJK"], ["financed emissions"], ["PCAF"] |

### 8.3 Validation Execution Flow

```
For each generated section:
  1. Run R1 (Number Source Check)
  2. Run R2 (Sum Consistency) — only for sections with GHG totals
  3. Run R3 (YoY Accuracy) — only for sections mentioning YoY
  4. Run R4 (Intensity Accuracy) — only for sections mentioning intensity
  5. Run R5 (Required Phrases) — based on target framework

  IF any rule fails:
    - Log failure details
    - Regenerate section (max 3 retries)
    - IF still fails after 3 retries → flag for human review
```

## [Draft] 9. Report Assembly Specifications

### 9.1 Component: DOCX Assembler

**Purpose:** Combine all generated section JSONs into final Word document
**Key Principle:** This is PURE CODE — no LLM involved — therefore NO context window limit

**Input:** List of section JSON objects (output from Claude per section)
**Output:** `s3://esg-datalake/output/reports/{year}/{framework}_{timestamp}.docx`

**Assembly Logic:**
```
1. Create Document object (python-docx)
2. Add cover page (title, date, institution, framework)
3. Add Table of Contents placeholder
4. For each section in ordered template:
   a. Add heading (level based on section hierarchy)
   b. Add narrative paragraphs
   c. Add tables (from section JSON)
   d. Add page break between major sections
5. Add appendix (methodology notes, data quality statement)
6. Save to S3
```

**Style Specifications:**

| Element | Font | Size | Spacing |
|---------|------|------|---------|
| Title | Calibri Bold | 24pt | 24pt after |
| Heading 1 | Calibri Bold | 16pt | 18pt before, 6pt after |
| Heading 2 | Calibri Bold | 13pt | 12pt before, 4pt after |
| Body text | Calibri | 11pt | 6pt after, 1.15 line spacing |
| Table header | Calibri Bold | 10pt | Gray background (#F2F2F2) |
| Table body | Calibri | 10pt | — |
| Footer | Calibri | 8pt | "Confidential — {institution_name}" |

**Section Order (default for multi-framework report):**
1. Cover Page
2. Table of Contents
3. Executive Summary
4. Governance
5. Strategy & Scenario Analysis
6. Risk Management
7. Scope 1 Direct Emissions
8. Scope 2 Energy Indirect Emissions
9. Scope 3 PCAF Financed Emissions
10. Emission Intensity & Trends
11. Targets & Progress
12. Appendix: Methodology & Data Quality

## [Draft] 10. Step Functions Workflow Specification

**State Machine Name:** `esg-report-generation-workflow`

**States:**

| State | Type | Purpose | Next |
|-------|------|---------|------|
| ReadConfig | Task | Load report template JSON from S3 | ValidateData |
| ValidateData | Task | Run Athena queries to verify data exists | FetchSharedContext |
| FetchSharedContext | Task | Query ghg_summary_annual for shared metrics | GenerateSections |
| GenerateSections | Map | Parallel generate all sections (MaxConcurrency: 5) | CrossValidate |
| → FetchSectionData | Task | Run section-specific Athena query | QueryKB |
| → QueryKB | Task | Retrieve RAG context from KB | InvokeModel |
| → InvokeModel | Task | Call Claude with base+overlay+section prompt | ValidateSection |
| → ValidateSection | Task | Run R1-R5 validation rules | SectionGate |
| → SectionGate | Choice | Pass → next; Fail → RetryOrFlag | — |
| CrossValidate | Task | Check consistency across all sections | AssemblyGate |
| AssemblyGate | Choice | All pass → Assemble; Any fail → HumanReview | — |
| HumanReview | Task (callback) | SNS notification, wait for approval | Assemble |
| Assemble | Task | Lambda: python-docx assembly | Publish |
| Publish | Task | Write to S3, send SNS notification | End |

**Error Handling:**
- Each Task has Retry with exponential backoff (max 3 attempts)
- Catch → ErrorHandler state → log to CloudWatch → SNS alert

**Timeout:** Overall workflow = 30 minutes max

## [Draft] 11. Knowledge Base Specification

### 11.1 Component: Bedrock Knowledge Base

**KB Name:** `esg-regulatory-knowledge-base`
**Embedding Model:** Amazon Titan Embeddings v2
**Vector Store:** OpenSearch Serverless
**Chunking:** Hierarchical (parent: 1500 tokens, child: 300 tokens)

**Documents to Ingest:**

| Document | Size | Purpose |
|----------|------|---------|
| GRI 305 (2016) | ~30 pages | Emission disclosure requirements |
| IFRS S2 (2023) | ~50 pages | Climate-related financial disclosures |
| ESRS E1 (2023) | ~40 pages | EU climate change standard |
| OJK PSPK Circular | ~60 pages | Indonesia sustainability reporting |
| PCAF Global Standard (2022) | ~120 pages | Financed emissions methodology |
| GHG Protocol Corporate Standard | ~100 pages | GHG accounting methodology |
| Sample IFRS S2 Bank Report | ~80 pages | Style and structure reference |

**Retrieval Configuration:**
- Top-K: 5 chunks per query
- Score threshold: 0.7
- Reranking: enabled (Bedrock Reranker)

**Storage:** `s3://esg-datalake/knowledge-base/standards/`

## [Draft] 12. Integration Matrix

| Component | AWS Service | Input | Output | Trigger |
|-----------|-------------|-------|--------|---------|
| Data Generation | Local/EC2 | Config params | Parquet files in S3 raw/ | Manual (POC) |
| ETL Scope 1 | Glue | raw.energy_consumption | curated.ghg_scope1 | EventBridge/Manual |
| ETL Scope 2 | Glue | raw.energy_consumption | curated.ghg_scope2 | EventBridge/Manual |
| ETL Scope 3 | Glue | raw.loan_portfolio + raw.borrower_emissions | curated.ghg_scope3_financed | EventBridge/Manual |
| ETL Aggregation | Glue | All curated tables | aggregated zone | After ETL 1-3 complete |
| Data Query | Athena | aggregated tables | Query results (JSON) | On-demand from Agent |
| RAG Retrieval | Bedrock KB | Natural language query | Relevant chunks | On-demand from Agent |
| Section Generation | Bedrock (Claude) | System+Overlay+Section prompt + Data + RAG | Section JSON | Step Functions |
| Validation | Lambda | Section JSON + Source data | Pass/Fail + details | Step Functions |
| Assembly | Lambda | All validated section JSONs | Final DOCX | Step Functions |
| Orchestration | Step Functions | Report config | End-to-end coordination | Manual/Scheduled |
