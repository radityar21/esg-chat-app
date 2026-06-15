
# ESG Reporting System — Quick Reference Card
## (Upload this as Reference Document in Agent config)

---

## Architecture Overview

```
External Sources → S3 Raw → Glue ETL → S3 Curated → S3 Aggregated → Athena
                                                                        ↓
Step Functions → Lambda(Validate) → Lambda(Query) → Lambda(SectionGen) → Lambda(Validate) → Lambda(Assembly)
                                                          ↓                                        ↓
                                                   Bedrock AgentCore                        python-docx
                                                   + Knowledge Base                         (Final DOCX)
                                                   + Guardrails
```

---

## Lambda Functions (5 Total)

| # | Lambda | Purpose | Input | Output |
|---|--------|---------|-------|--------|
| 1 | ValidateInput | Check data freshness & completeness | S3 paths, framework list | Pass/fail + metadata |
| 2 | AthenaQuery | Run pre-defined queries | Framework + section ID | JSON metrics payload |
| 3 | SectionGen | Invoke Bedrock for narrative | Metrics + prompt template | Section markdown |
| 4 | Validation | Apply 21 rules to generated section | Section text + source data | Pass/fail + violations |
| 5 | AssemblyDoc | Merge all sections into DOCX | All validated sections | Final .docx in S3 |

---

## Validation Rules (Critical)

| Rule | Check | Tolerance |
|------|-------|-----------|
| VAL-NUM-01 | All numbers in narrative exist in source | 0% tolerance |
| VAL-NUM-02 | GHG total = Scope1 + Scope2 + Scope3 | ±0.01 tCO2e |
| VAL-NUM-03 | YoY% matches pre-computed value | ±0.1% |
| VAL-NUM-04 | Intensity ratio = emissions/revenue | ±0.0001 |
| VAL-NUM-05 | Unit consistency (tCO2e, not kgCO2e in report) | 0% tolerance |
| VAL-NUM-06 | Weighted ≤ Gross (PCAF) | 0% tolerance, ZERO RETRY |
| VAL-STRUCT-01 | Required sections present | All mandatory |
| VAL-STRUCT-02 | Section order matches framework | Exact match |
| VAL-PROHIB-01 | No hallucinated references | 0% tolerance |
| VAL-PROHIB-02 | No future-dated claims | 0% tolerance |

---

## Emission Factor Constants

### Scope 1 — Natural Gas
- CO2: 56.10 kg/GJ
- CH4: 0.001 kg/GJ → ×29.8 GWP = 0.0298 kgCO2e/GJ
- N2O: 0.0001 kg/GJ → ×273.0 GWP = 0.0273 kgCO2e/GJ

### Scope 1 — Diesel
- CO2: 2.6710 kg/L
- CH4: 0.00029 kgCO2e/L (DEFRA 2025, pre-multiplied)
- N2O: 0.03308 kgCO2e/L (DEFRA 2025, pre-multiplied)

### Scope 2 — Grid Electricity
- PLN 2023: 0.7886 kg CO2/kWh

### PCAF Confidence Factors
- Score 1.0 (Verified): 1.00
- Score 1.5 (Unverified): 0.95
- Score 2.0 (Physical activity): 0.90
- Score 3.0 (EEIO + revenue): 0.75
- Score 4.0 (EEIO + assets): 0.60
- Score 5.0 (Sector average): 0.45

---

## Prompt Architecture (Hybrid)

```
FINAL_PROMPT = BASE_PROMPT + FRAMEWORK_OVERLAY[framework] + SECTION_TEMPLATE[section_id]
```

### Base Prompt (Universal)
- Role: "ESG report writer for financial institutions"
- Rules: No fabrication, cite data sources, use pre-computed metrics only
- Format: Markdown with specific heading structure

### Framework Overlays
- GRI 305: Disclosure 305-1 through 305-5 structure
- IFRS S2: Climate-related metrics & targets format
- CSRD/ESRS E1: DR E1-1 through E1-9
- OJK PSPK: Indonesian regulation specific disclosures

### Section Templates
- Include: data placeholders, required narrative elements, prohibited content
- Each template specifies which Athena query to run

---

## Data Schema (Aggregated Zone — Source of Truth)

### esg_aggregated.ghg_summary_annual
| Column | Type | Description |
|--------|------|-------------|
| reporting_year | INT | 2023, 2024 |
| scope1_tco2e | DOUBLE | Total Scope 1 |
| scope2_tco2e | DOUBLE | Total Scope 2 (location-based) |
| scope3_financed_gross_tco2e | DOUBLE | PCAF gross |
| scope3_financed_weighted_tco2e | DOUBLE | PCAF confidence-weighted |
| total_tco2e | DOUBLE | Scope1 + 2 + 3 |
| yoy_change_pct | DOUBLE | Pre-computed YoY |
| intensity_tco2e_per_billion_idr | DOUBLE | Emissions intensity |
| portfolio_weighted_pcaf_score | DOUBLE | 1.0–5.0 |
| data_quality_coverage_pct | DOUBLE | % loans with score ≤ 3 |

---

## Step Functions State Machine Flow

```
StartExecution
  → ValidateInputState (Lambda #1)
  → ParallelSectionGeneration
      → [For each section]:
          → AthenaQueryState (Lambda #2)
          → SectionGenState (Lambda #3)
          → ValidationState (Lambda #4)
              → If PASS: next section
              → If FAIL (retryable): retry SectionGen (max 2)
              → If FAIL (VAL-NUM-06): → HumanReviewState (HALT)
  → AssemblyState (Lambda #5)
  → OutputArchiveState (S3 put)
  → NotifyComplete (SNS)
```

---

## Kiro Prompt Template (for generating artefacts)

```
Generate [ARTEFACT_TYPE] for the ESG Reporting System.

Context:
- Spec document: ESG_Kiro_Requirements_Spec.docx
- Section: [SECTION_NUMBER]
- Requirement IDs: [REQ-IDs]

Constraints:
- Production-grade code, no placeholders
- Follow exact schema from spec Section 2
- Use emission factors from spec Section 3.1
- Output format: [Python/PySpark/SQL/JSON]
- Include error handling and logging
- Add inline comments referencing requirement IDs

Expected output:
[DESCRIPTION OF WHAT THE CODE SHOULD DO]
```
