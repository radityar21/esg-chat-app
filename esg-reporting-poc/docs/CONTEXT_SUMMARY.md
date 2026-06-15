# Context Summary — ESG Reporting POC

> **Purpose:** Paste this into a new chat session so the AI has full context without re-reading everything.
> **Last Updated:** 2026-06-05

---

## Project Overview

AI-powered ESG sustainability report generator. Takes raw ESG data (energy, loans, HR) → ETL calculates GHG emissions → AI generates formatted DOCX reports compliant with 4 international frameworks.

**AWS Account:** `061039769766`, Region: `us-east-1`

---

## Architecture

```
User (Amplify Chat) → API Gateway → Lambda (proxy) → Bedrock Agent
    → Agent Tools Lambda → Step Functions (orchestrator)
        → Glue ETL (Scope 1/2/3 + Aggregation)
        → Athena Query (fetch aggregated data)
        → SectionGen Lambda (Bedrock Claude + KB RAG)
        → Validation Lambda (21 rules)
        → Assembly Lambda (python-docx → DOCX)
        → S3 Output → Presigned URL → User downloads
```

---

## Key Reference Files (READ THESE FIRST in new session)

| File | Purpose | Location |
|------|---------|----------|
| **ESG_kiro_Requirement_Spec.md** | Original spec (authoritative, unchanged) | `esg-reporting-poc/ESG_kiro_Requirement_Spec.md` |
| **INFRASTRUCTURE_REFERENCE.md** | All deployed resources, configs, deploy commands | `esg-reporting-poc/docs/INFRASTRUCTURE_REFERENCE.md` |
| **SPEC_AMENDMENTS.md** | Tracked deviations from spec (AMD-001 to AMD-003, 64 items) | `esg-reporting-poc/docs/SPEC_AMENDMENTS.md` |
| **IMPLEMENTATION_CHANGELOG.md** | Full diff: spec vs actual implementation | `esg-reporting-poc/docs/IMPLEMENTATION_CHANGELOG.md` |
| **VALIDATION_FALSE_POSITIVES.md** | Known validation issues (not bugs, calibration needed) | `esg-reporting-poc/docs/VALIDATION_FALSE_POSITIVES.md` |
| **Build Plan** | Step-by-step progress (D1-D24) | `ESG Document/ESG_Reporting_POC___Step_by_Step_Build_Plan_2026_06_02T09_30_54.md` |

---

## Current State (what's working)

- ✅ Full pipeline: Raw → Curated → Aggregated → Report (DOCX)
- ✅ 4 frameworks: GRI_305, IFRS_S2, CSRD_ESRS_E1, OJK_PSPK, MULTI_FRAMEWORK
- ✅ Bedrock Agent chat interface (Amplify hosted)
- ✅ Step Functions orchestration with auto-approve
- ✅ Knowledge Base (semantic chunking, HYBRID search)
- ✅ Validation (21 rules, false positive rate documented)
- ⚠️ Download URL: presigned URL works but agent sometimes corrupts with markdown formatting
- ⚠️ Validation false positives: LLM-derived percentages flagged (see VALIDATION_FALSE_POSITIVES.md)

---

## Key Resources

| Resource | Name/ARN |
|----------|----------|
| State Machine | `ESGReportGenerationStateMachine` |
| Agent ID | `MBERNIQMBG` |
| Agent Alias | `QIXEJW2TN6` |
| KB ID | `WVREXI1LEI` |
| Bedrock Model (SectionGen) | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| Amplify App | `d337jqli3ubqmk` → `https://main.d337jqli3ubqmk.amplifyapp.com` |
| API Gateway | `olj4tuggm1` → `https://olj4tuggm1.execute-api.us-east-1.amazonaws.com/prod` |

### S3 Buckets

| Bucket | Purpose |
|--------|---------|
| `esg-data-raw-061039769766` | Raw data + scripts + lambda code |
| `esg-data-curated-061039769766` | ETL-computed GHG emissions |
| `esg-data-aggregated-061039769766` | Report-ready metrics |
| `esg-output-reports-061039769766` | Generated DOCX reports |
| `esg-kb-documents-061039769766` | KB docs + prompts + templates |
| `esg-athena-results-061039769766` | Athena query results |

### Lambda Functions

| Function | Purpose |
|----------|---------|
| `esg-validate-input` | Step Functions input validation |
| `esg-athena-query` | Fetch all aggregated data |
| `esg-section-gen` | AI section generation (Bedrock + KB) |
| `esg-validation` | 21-rule output validation |
| `esg-assembly-doc` | DOCX assembly (python-docx) |
| `esg-filter-sections` | Filter Map output (JSONPath workaround) |
| `esg-agent-tools` | Bedrock Agent tool handler |
| `esg-chat-proxy` | API GW → Bedrock Agent proxy |
| `esg-review-handler` | Human review (blocked by SCP) |

### Glue Jobs

| Job | Input | Output |
|-----|-------|--------|
| `esg-etl-scope1-direct` | Raw energy → Scope 1 | Curated ghg_scope1 |
| `esg-etl-scope2-indirect` | Raw energy → Scope 2 | Curated ghg_scope2 |
| `esg-etl-scope3-pcaf` | Raw loans → Scope 3 PCAF | Curated ghg_scope3_financed |
| `esg-etl-aggregation` | All curated → Summary | Aggregated ghg_summary_annual + pcaf_by_sector + scope1_by_facility |

---

## S3 Path Convention (REQ-DDL-05)

```
Raw:        s3://{bucket}/raw/{table}/reporting_year={Y}/[reporting_month={M}/]
Curated:    s3://{bucket}/curated/{table}/reporting_year={Y}/
Aggregated: s3://{bucket}/aggregated/{table}/reporting_year={Y}/
Prompts:    s3://esg-kb-documents-*/prompts/{file}.txt
Templates:  s3://esg-kb-documents-*/prompts/templates/{name}_template.txt
```

---

## Key Design Decisions

1. Step Functions (not AgentCore) as orchestrator — deterministic, testable
2. Bedrock Agent as chat frontend only — doesn't control pipeline logic
3. Auto-approve mode (no waitForTaskToken) — SCP blocks public Lambda URLs
4. S3 direct read in Glue (not from_catalog) — partition projection incompatible
5. Single Lambda role (`ESGLambdaRole`) for all functions — POC simplification
6. Semantic chunking for KB (not fixed-size) — preserves regulatory clause boundaries
7. Rounding: components first, then recompute totals

---

## Known Issues / Pending

1. Download URL corruption by agent markdown formatting
2. Validation false positives (LLM-derived percentages, table↔paragraph mismatch)
3. Scope 1 facility count: 100-110 instead of 220 (generator edge case)
4. ~~Missing: Social (S) section (HR data exists, section template needed)~~ ✅ Implemented (2026-06-09)
5. Missing: Governance section data (qualitative — hardcoded defaults)
6. Templates `methodology` exists locally but not in TEMPLATE_MAP

---

## How to Trigger Report Generation

**From Bedrock Agent console or Amplify chat:**
```
"Generate ESG report for 2024, all frameworks"
```

**From CLI:**
```bash
aws stepfunctions start-execution --state-machine-arn arn:aws:states:us-east-1:061039769766:stateMachine:ESGReportGenerationStateMachine --input '{"reporting_year":2024,"framework":"GRI_305","bank_id":"GENERIC_FI_001","output_bucket":"esg-output-reports-061039769766","revenue_idr_billion":92000.0,"kb_id":"WVREXI1LEI","section_templates":[{"template_id":"scope1","framework":"GRI_305"},{"template_id":"scope2","framework":"GRI_305"},{"template_id":"scope3_pcaf","framework":"GRI_305"},{"template_id":"summary","framework":"NONE"}]}' --region us-east-1
```

**Download report:**
```bash
aws s3 presign "s3://esg-output-reports-061039769766/reports/year=2024/..." --expires-in 3600 --region us-east-1
```
