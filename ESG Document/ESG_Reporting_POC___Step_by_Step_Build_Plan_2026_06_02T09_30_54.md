
# ESG Reporting POC — Step-by-Step Build Plan

## Prerequisites (Before Day 1)
- [v] AWS Account active (us-east-1 N. Virginia enabled)
- [v] AWS CLI configured with appropriate IAM user/role
- [v] Python 3.11+ installed locally
- [v] Kiro IDE installed & configured
- [v] 3 DOCX specs ready (Architecture, Technical Spec, Kiro Requirements)
- [v] ESG Knowledge Base Space di Quick sudah setup + agent configured

---

## W1: Foundation — Data Layer & Infrastructure

### D1: AWS Account Setup & IAM
- [v] Create IAM roles:
  - `ESGGlueRole` (Glue → S3 read/write, CloudWatch logs)
  - `ESGLambdaRole` (Lambda → S3, Athena, Bedrock, DynamoDB, CloudWatch)
  - `ESGStepFunctionsRole` (StepFunctions → Lambda invoke, SNS publish)
- [v] Create S3 buckets (us-east-1, account 061039769766):
  - `esg-data-raw-061039769766` ✅ created 2026-06-03
  - `esg-data-curated-061039769766` ✅ created 2026-06-03
  - `esg-data-aggregated-061039769766` ✅ created 2026-06-03
  - `esg-output-reports-061039769766` ✅ created 2026-06-03
- [v] Enable bucket versioning on all buckets (+ lifecycle: keep 1 noncurrent version only)
- [v] Create folder structure: `/{reporting_year}/{data_domain}/`
  - Years: `2023/`, `2024/`
  - Domains: `emissions/`, `energy/`, `water/`, `waste/`, `social/`, `governance/`
- [v] Tag all resources: `Project=ESG, Env=POC, Team=Sustainability`

### D2: Synthetic Data Generation
- [v] Open Kiro → feed ESG_Kiro_Requirements_Spec.docx Section 2.1–2.2
- [v] Generate Python script: `generate_energy_data.py`
  - 200+ facilities, 2 reporting years (2023, 2024)
  - Natural gas (GJ) + Diesel (litres) + Electricity (kWh)
  - Monthly granularity
- [v] Generate Python script: `generate_loan_portfolio.py`
  - 2,000+ borrowers
  - PCAF scores distribution: {1.0:5%, 1.5:5%, 2.0:10%, 3.0:30%, 4.0:35%, 5.0:15%}
  - Sector NACE codes, outstanding amounts, borrower emissions
- [v] Run scripts → output as Parquet files
- [v] Upload Parquet to S3 raw bucket: `s3://esg-data-raw-061039769766/2024/energy/` and `s3://esg-data-raw-061039769766/2024/loans/`
- [v] Verify: `aws s3 ls` confirm files exist

### D3: Athena DDL Setup
- [v] Create Athena workgroup: `esg-reporting-workgroup`
- [v] Create Glue databases: `esg_raw`, `esg_curated`, `esg_aggregated`
- [v] Run DDL from Spec Section 4.1 (Raw zone tables):
  - `esg_raw.energy_consumption`
  - `esg_raw.loan_portfolio`
- [v] Run DDL from Spec Section 4.2 (Curated zone tables):
  - `esg_curated.ghg_scope1`
  - `esg_curated.ghg_scope2`
  - `esg_curated.ghg_scope3_financed`
- [v] Run DDL from Spec Section 4.3 (Aggregated zone tables):
  - `esg_aggregated.ghg_summary_annual`
  - `esg_aggregated.pcaf_sector_summary`
- [v] Verify: Run `SELECT * FROM esg_raw.energy_consumption LIMIT 10` — confirm data readable

### D4: Glue ETL — Scope 1
- [v] Open Kiro → feed Spec Section 3.2 (REQ-ETL-01 to REQ-ETL-08)
- [v] Generate PySpark script: `glue_job_scope1_ghg.py`
  - Natural gas: `consumption_gj × 56.10` + CH4/N2O with GWP
  - Diesel: `liters × 2.53763` + CH4/N2O with GWP (DEFRA 2025, per §3.1)
  - Monthly aggregation → annual rollup
  - Output: Parquet to `s3://esg-data-curated-061039769766/{year}/ghg_scope1/`
- [v] Create Glue job: `esg-etl-scope1-direct`
- [v] Run job → verify output in Athena: `SELECT * FROM esg_curated.ghg_scope1 LIMIT 10`
- [v] Validate: `scope1_total = scope1_natural_gas + scope1_diesel` (GATE-S1-03 ±0.0001)

#### Implementation Additions (beyond spec):
- [v] **Schema Governance Gate** — validates all 12 expected columns present + type check before processing. Job fails immediately if source schema deviates from DDL contract.
- [v] **ENUM Validation Gate** — validates `ef_source` & `record_status` contain only spec-allowed values before any processing. Fail fast on dirty data.
- [v] **Configurable `ACCOUNT_ID` + path templates** — single variable change to recreate in any environment. No hardcoded paths in business logic.
- [v] **Rounding order: components first, recompute total** — round `scope1_natgas_tco2e` and `scope1_diesel_tco2e` to 4dp FIRST, then recompute `scope1_tco2e = rounded_natgas + rounded_diesel`. Guarantees GATE-S1-03 always passes.
- [v] **Error partition** — excluded facilities (>5 imputed months) written to `s3://{CURATED_BUCKET}/errors/ghg_scope1_errors/` for audit trail.
- [v] **Summary stats logging** — total records, total tCO2e, averages logged to CloudWatch at end of job.
- [v] **S3 direct read** (not Glue Catalog `from_catalog()`) — Glue Spark doesn't support Athena partition projection. Direct S3 read is reliable and reproducible; schema governance gate compensates for loss of Catalog-level enforcement.

### D5: Glue ETL — Scope 2 + Scope 3 PCAF
- [v] Generate PySpark: `glue_job_scope2_electricity.py`
  - Formula: `electricity_kwh × 0.7886 / 1000` → tCO2e
  - Output: `s3://esg-data-curated-061039769766/{year}/ghg_scope2/`
- [v] Generate PySpark: `glue_job_scope3_pcaf.py`
  - Attribution factor: `outstanding / (equity + debt)`
  - Gross: `attribution × borrower_emissions`
  - Weighted: `gross × PCAF_CONFIDENCE[score]`
  - Sector aggregation
  - Output: `s3://esg-data-curated-061039769766/{year}/ghg_scope3_financed/`
- [v] Create & run both Glue jobs
- [v] Validate: `weighted ≤ gross` for ALL rows (VAL-NUM-06)

#### Implementation Additions (beyond spec) — Scope 3 PCAF:
- [v] **Schema Governance Gate** — validates loan_portfolio columns match DDL contract before processing.
- [v] **ENUM Validation Gate** — validates `sector_nace`, `loan_type`, `record_status` values.
- [v] **Error partition** — rejected/invalid loans written to `s3://{CURATED_BUCKET}/errors/ghg_scope3_errors/` for audit trail.
- [v] **Summary stats logging** — sector count, total financed emissions, avg PCAF score logged to CloudWatch.
- [v] **S3 direct read** — same ADR as Scope 1; partition projection not supported in Glue Spark.
- [v] **Configurable `ACCOUNT_ID` + path templates** — environment-agnostic config.

### D6: Glue ETL — Aggregation Layer
- [v] Generate PySpark: `glue_job_aggregation.py`
  - Join Scope 1 + 2 + 3 → `ghg_summary_annual`
  - Compute: total, YoY%, intensity ratio, portfolio PCAF score
  - Output: `s3://esg-data-aggregated-061039769766/{year}/ghg_summary_annual/`
- [v] Create & run Glue job
- [v] Validate in Athena:
  - `total_tco2e = scope1 + scope2 + scope3_gross` ✓
  - `yoy_change_pct` = `(2024 - 2023) / 2023 × 100` ✓
  - `portfolio_weighted_pcaf_score` between 1.0–5.0 ✓

#### Implementation Additions (beyond spec) — Aggregation:
- [v] **Schema Governance Gate** — validates curated zone input tables match expected schemas before join.
- [v] **Summary stats logging** — total tCO2e per scope, YoY, intensity ratios logged to CloudWatch.
- [v] **S3 direct read** — reads curated parquets from `/{year}/ghg_scope1/`, `/{year}/ghg_scope2/`, `/{year}/ghg_scope3_financed/`.
- [v] **Configurable `ACCOUNT_ID` + path templates** — environment-agnostic config.

### D7: Data Layer Checkpoint
- [v] Run full pipeline end-to-end: Raw → Curated → Aggregated
- [v] Document any issues/deviations from spec
  - Scope 1 row count lower than 220 (100-110 per year) due to generator creating sporadic 0.0 values for branches that should be all-null — cosmetic, not blocking
  - Emission factors use §3.1 constants (authoritative) not §3.2 table values where they differ
- [v] Screenshot Athena query results for each table
- [ ] Commit all scripts to Git repo
- [v] ✅ **Milestone: Data layer complete — all metrics queryable via Athena**

---

### Cross-Cutting Implementation Standards (applies to ALL components)

The following patterns MUST be applied universally across all Glue jobs, Lambda functions, and Step Functions:

| # | Standard | Applies To | Rationale | Status |
|---|----------|------------|-----------|--------|
| 1 | **Schema Governance Gate** | All Glue jobs (Scope1, Scope2, Scope3 PCAF, Aggregation) | Validate source columns match DDL contract before processing. Fail fast on schema drift. | ✅ Implemented |
| 2 | **Config Externalization** (`ACCOUNT_ID` + path templates) | All Glue jobs + Lambda + Step Functions | Single variable change to recreate in any environment. Zero hardcoded paths in business logic. | ✅ Implemented (Glue jobs) |
| 3 | **Error Partition Path** | Scope1, Scope3 PCAF jobs | Excluded/rejected records written to `/curated/errors/{job_name}/` for audit trail and traceability. | ✅ Implemented |
| 4 | **Summary Stats Logging** | All Glue jobs + Lambda | Every job logs key metrics (row counts, totals, durations) to CloudWatch at completion. | ✅ Implemented (Glue jobs) |
| 5 | **S3 Direct Read (ADR)** | All Glue jobs | Glue Spark does not support Athena partition projection. Direct S3 read with schema governance gate is the reliable alternative. | ✅ Implemented |
| 6 | **Rounding Order** | All Glue jobs with multi-component sums | Round components FIRST, then recompute totals from rounded values. Prevents floating-point tolerance failures in validation gates. | ✅ Implemented |

---

## W2: AI Generation Layer & Orchestration

### D8: Bedrock Knowledge Base Setup (us-east-1)
- [v] Create S3 bucket in us-east-1: `esg-kb-documents-061039769766`
- [v] Upload framework documents:
  - GRI 305 standard PDF
  - IFRS S2 standard PDF
  - CSRD/ESRS E1 guidance PDF
  - OJK PSPK regulation PDF
- [v] Create Bedrock Knowledge Base:
  - Data source: S3 bucket above
  - Embedding model: Titan Embeddings V2
  - Vector store: OpenSearch Serverless
  - Chunking: Fixed 512 tokens, 20% overlap
- [v] Sync KB → verify document count matches
- [v] Test: Query KB with "What are GRI 305-1 disclosure requirements?" → confirm relevant chunks returned

### D9: Prompt Engineering — Base + Overlays
- [v] Create prompt files locally (from Spec Section 5):
  - `prompts/base_prompt.txt` — universal rules
  - `prompts/overlay_gri305.txt` — GRI-specific
  - `prompts/overlay_ifrs_s2.txt` — IFRS-specific
  - `prompts/overlay_csrd_e1.txt` — CSRD-specific
  - `prompts/overlay_ojk_pspk.txt` — OJK-specific
- [v] Create section templates (from Spec Section 6):
  - `prompts/section_scope1.txt`
  - `prompts/section_scope2.txt`
  - `prompts/section_pcaf.txt`
  - `prompts/section_summary.txt`
- [v] Store all prompts in S3: `s3://esg-kb-documents-061039769766/prompts/`
- [v] Test prompt composition manually in Bedrock console:
  - Combine: base + GRI overlay + scope1 template
  - Feed sample Athena data as context
  - Verify output format matches spec

### D10: Lambda #1 — ValidateInput
- [v] Generate via Kiro (Spec Section 9.1):
  - Input: `{reporting_year, frameworks[], s3_paths{}}`
  - Logic: Check S3 files exist, check freshness (< 24h), check completeness
  - Output: `{status: "PASS"|"FAIL", metadata: {...}, errors: [...]}`
- [v] Deploy Lambda (Python 3.11, 256MB, 30s timeout)
- [v] Test with valid + invalid inputs
- [v] Add CloudWatch logging

### D11: Lambda #2 — AthenaQuery
- [v] Generate via Kiro (Spec Section 9.1):
  - Input: `{section_id, framework, reporting_year}`
  - Logic: Map section_id → pre-defined Athena query → execute → return JSON
  - Pre-defined queries stored in DynamoDB or hardcoded dict
  - Output: `{metrics: {scope1_tco2e: 1234.56, yoy_pct: -5.2, ...}}`
- [v] Deploy Lambda (Python 3.11, 512MB, 60s timeout)
- [v] Test: Query for "scope1_gri305_2024" → verify JSON matches Athena data

### D12: Lambda #3 — SectionGen
- [v] Generate via Kiro (Spec Section 9.1):
  - Input: `{section_id, framework, metrics_json, kb_id}`
  - Logic:
    1. Load base_prompt + framework_overlay + section_template
    2. Inject metrics_json into template placeholders
    3. Query KB for regulatory context (RAG)
    4. Call Bedrock (Claude 3.5 Sonnet) with composed prompt
    5. Return generated section text
  - Output: `{section_id, content_markdown, model_id, token_usage}`
- [v] Deploy Lambda (Python 3.11, 1024MB, 120s timeout)
- [v] ~~Configure VPC + VPC Endpoint to Bedrock~~ — N/A (all resources in us-east-1, no cross-region needed)
- [v] Test: Generate Scope 1 section for GRI 305 → review output quality

### D13: Lambda #4 — Validation
- [v] Generate via Kiro (Spec Section 7):
  - Input: `{section_content, source_metrics, framework}`
  - Logic: Apply all 21 validation rules:
    - Extract numbers from narrative → compare against source_metrics
    - Check totals = sum of components
    - Check YoY matches pre-computed
    - Check no prohibited content (hallucinated refs, future dates)
    - Check structural requirements (headings, order)
  - Output: `{status: "PASS"|"FAIL", violations: [{rule, detail, severity}]}`
- [v] Deploy Lambda (Python 3.11, 512MB, 60s timeout)
- [v] Test with intentionally wrong narrative → confirm violations caught

### D14: Lambda #5 — AssemblyDoc + Integration Test
- [v] Generate via Kiro (Spec Section 8):
  - Input: `{sections: [{id, content, framework}], style_config}`
  - Logic: python-docx assembly
    - Create DOCX with styles (fonts, headings, margins per Spec 8.1–8.4)
    - Insert sections in correct order per framework
    - Add TOC, headers/footers, page numbers
    - Save to S3 output bucket
  - Output: `{s3_path, page_count, file_size_kb}`
- [v] Deploy Lambda (Python 3.11, 1024MB, 120s timeout, /tmp for file write)
- [v] Layer: python-docx as Lambda layer (`esg-python-docx:1`)
- [v] Test: Feed 2 sample sections → verify DOCX output opens correctly in Word

---

## W3: Orchestration, End-to-End Testing & Polish

### D15: Step Functions State Machine
- [v] Create state machine definition (ASL JSON) from Spec Section 9:
  - StartAt: ValidateInputState
  - Parallel state for Glue ETL (Scope 1 + 2 + 3 concurrent)
  - Aggregation after all curated done
  - AthenaQuery (single call, full DATA INPUT)
  - Map state for multi-section generation (MaxConcurrency: 3)
  - Retry logic: max 1 explicit retry on SectionGen failure
  - ValidationChoice: PASS/WARN/RETRY/FAIL_NO_RETRY routing
  - Auto-approve on FAIL (SNS notification + proceed)
  - FilterSections Lambda (workaround for JSONPath limitation)
  - Final: AssemblyDoc → NotifyComplete (SNS)
- [v] Deploy state machine (`ESGReportGenerationStateMachine`)
- [v] Create SNS topics: `ESG-HumanReview`, `ESG-ReportComplete`
- [v] Create `esg-filter-sections` Lambda
- [v] Create `esg-review-handler` Lambda + Function URL (blocked by SCP — documented)
- [v] Create manual review ASL variant (`esg_orchestrator_human_review_manual.asl.json`)
- [v] Test with single section (Scope 1 GRI_305) → execution completes ✅
- [v] Test human review flow → CloudShell `send-task-success` works ✅
- [v] Switch to auto-approve mode (no waitForTaskToken)

#### Implementation Additions (beyond spec) — Step Functions:
- [v] **Auto-approve mode** — SNS notifies reviewer but proceeds automatically. Manual review version preserved as documentation.
- [v] **FilterSections Lambda** — Step Functions doesn't support JSONPath filter expressions. Separate Lambda filters Map output.
- [v] **Glue job parameters** — `--REPORTING_YEAR` passed via `States.Format` to all ETL jobs.
- [v] **SNS stringify** — `States.JsonToString()` for Message parameter (must be string).
- [v] **ASL deployment via S3** — Windows CLI can't use `file://` due to encoding. Upload to S3 → deploy from CloudShell.
- [v] **Template key resolution** — `_resolve_template_key()` in SectionGenFn handles full section IDs from Step Functions.

### D16: End-to-End Test — Single Framework (GRI 305)
- [v] Trigger Step Functions with:
  ```json
  {
    "reporting_year": 2024,
    "framework": "GRI_305",
    "bank_id": "GENERIC_FI_001",
    "output_bucket": "esg-output-reports-061039769766",
    "revenue_idr_billion": 92000.0,
    "kb_id": "WVREXI1LEI",
    "section_templates": [
      {"template_id": "scope1", "framework": "GRI_305"},
      {"template_id": "scope2", "framework": "GRI_305"},
      {"template_id": "scope3_pcaf", "framework": "GRI_305"},
      {"template_id": "summary", "framework": "NONE"}
    ]
  }
  ```
- [v] Monitor execution in Step Functions console
- [v] Verify each Lambda completes successfully
- [v] Download output DOCX → manual review:
  - [v] Numbers match Athena data? (with known VAL-NUM-01 minor deviations due to LLM interpretation)
  - [v] Format matches GRI 305 structure? ✅
  - [v] No hallucinated content? ✅ (validation catches most)
  - [v] Validation passed all rules? (WARN/auto-approved on minor percentage mismatches)

### D17: End-to-End Test — Multi-Framework
- [v] Run with all 4 frameworks: `"framework": "MULTI_FRAMEWORK"` (14 sections)
- [v] Verify each framework generates correct sections
- [v] Verify DOCX has proper section separation per framework
- [v] Compare output against sample reports (if available)
- [v] Document: execution time, token usage, cost per run


### optional #######
### D18: Guardrails + Error Handling
- [ ] Create Bedrock Guardrail:
  - Content filter: Block fabricated statistics
  - Automated Reasoning: Verify numerical claims
  - Topic filter: Block off-topic content
- [ ] Attach guardrail to SectionGen Lambda
- [ ] Test: Intentionally feed wrong data → confirm guardrail blocks
- [ ] Add DLQ (Dead Letter Queue) to SQS for failed executions
- [v] Add SNS notification on: completion, failure, human-review-needed

### D19: Monitoring & Observability
- [ ] Create CloudWatch dashboard:
  - Lambda duration per function
  - Step Functions execution success/fail rate
  - Bedrock token usage & latency
  - Glue job duration
  - S3 storage metrics
- [ ] Set up alarms:
  - Lambda error rate > 5%
  - Step Functions execution time > 10 min
  - Bedrock throttling
- [ ] Enable X-Ray tracing on all Lambdas
- [ ] Verify end-to-end trace visible in X-Ray service map


### optional #######

### D20: Documentation & Demo Prep
- [ ] Write README.md:
  - Architecture overview
  - How to run (trigger Step Functions)
  - How to add new framework
  - Cost breakdown per execution
- [ ] Record demo video or prepare live demo:
  - Show: trigger → execution → output DOCX
  - Show: validation catching errors
  - Show: monitoring dashboard
- [ ] Create cost analysis:
  - Per-report cost breakdown
  - Monthly projection (10 reports/month)
- [ ] ✅ **Milestone: POC complete — demo-ready**

---

## W4: Chat UI + Bedrock Agent (AWS Summit Demo)

### Purpose
Provide a conversational UI for the AWS Summit presentation. User chats naturally ("Generate ESG report for 2024, GRI 305"), agent triggers existing Step Functions pipeline, returns status + download link. **Pipeline unchanged — agent is a frontend layer only.**

### Architecture
```
User (browser) → Amplify React App → Bedrock Agent
    → Tool: generate_report → Lambda → stepfunctions.start_execution()
    → Tool: check_status → Lambda → stepfunctions.describe_execution()
    → Tool: download_report → Returns S3 presigned URL
```

### D21: Bedrock Agent Setup
- [v] Create Bedrock Agent:
  - Name: `ESGReportAgent`
  - Model: Claude Sonnet 4.5 (or latest)
  - Instructions:
    ```
    You help users generate ESG sustainability reports.
    
    CONVERSATION FLOW:
    1. Ask: "Which reporting year? (Available: 2023, 2024)"
       - If user says anything other than 2023 or 2024: respond "Data not available for that year. Currently only 2023 and 2024 have data."
    2. Ask: "Which framework? (GRI 305, IFRS S2, CSRD ESRS E1, OJK PSPK, or All Frameworks)"
       - If user says something outside these options: respond "That framework is not available. Please choose from: GRI 305, IFRS S2, CSRD ESRS E1, OJK PSPK, or All Frameworks."
    3. Ask: "Revenue in IDR billion? (Default: 92,000 = IDR 92 Trillion. Format: number in billions)"
       - If user says "default" or skips: use 92000
       - If user provides a number: use that value
    4. Confirm all parameters before triggering generation.
    5. After triggering: inform user estimated time (3-5 minutes for single framework, 8-12 for all).
    6. When user asks status: check and report.
    7. When complete: provide download link.
    
    GUARDRAILS:
    - Only years 2023, 2024 are available. Other years = "Data not available."
    - Only frameworks: GRI_305, IFRS_S2, CSRD_ESRS_E1, OJK_PSPK, MULTI_FRAMEWORK. Others = "Not available."
    - Revenue must be > 0. If 0 or negative: "Revenue must be a positive number in IDR billions."
    - Never fabricate report content. You only trigger generation and report status.
    ```
- [v] Define Action Group: `ESGReportActions`
  - Tool 1: `generate_report`
    - Params: `reporting_year` (int), `framework` (enum: GRI_305|IFRS_S2|CSRD_ESRS_E1|OJK_PSPK|MULTI_FRAMEWORK)
    - Lambda: triggers Step Functions with constructed input
    - Returns: execution ARN + estimated time
  - Tool 2: `check_status`
    - Params: `execution_arn` (string)
    - Lambda: calls `describe_execution`
    - Returns: status (RUNNING|SUCCEEDED|FAILED) + duration
  - Tool 3: `download_report`
    - Params: `execution_arn` (string)
    - Lambda: gets output from execution → generates S3 presigned URL (1 hour expiry)
    - Returns: download URL
  - Tool 4: `list_available_data`
    - Params: none
    - Lambda: queries Athena for available reporting_years
    - Returns: list of years with data
- [v] Create Lambda: `esg-agent-tools` (single Lambda, routes by tool name)
- [v] Test agent in Bedrock console chat

### D22: Frontend (Amplify React Chat)
- [ ] Create Amplify app:
  - React + Amplify UI components
  - Chat interface (message input + response display)
  - Backend: Bedrock Agent `invoke_agent` API
- [ ] Add authentication (Cognito — optional for demo, can skip)
- [ ] Add "typing indicator" while agent processes
- [ ] Add download button when report ready
- [ ] Deploy to Amplify hosting (HTTPS URL for demo)

### D23: Agent Tool Lambda
- [v] Create `esg-agent-tools` Lambda:
  ```python
  def lambda_handler(event, context):
      tool_name = event["actionGroup"]  # or extract from event
      if tool_name == "generate_report":
          # Construct Step Functions input from params
          # Call stepfunctions.start_execution()
          # Return execution ARN
      elif tool_name == "check_status":
          # Call stepfunctions.describe_execution()
          # Return status + output path if done
      elif tool_name == "download_report":
          # Get S3 path from execution output
          # Generate presigned URL
          # Return URL
  ```
- [v] IAM: Agent role needs `stepfunctions:StartExecution`, `stepfunctions:DescribeExecution`, `s3:GetObject`
- [v] Deploy + test

### D24: Integration Test + Demo Prep
- [ ] End-to-end flow:
  1. Open Amplify URL in browser
  2. Chat: "Generate ESG report for 2024, all frameworks"
  3. Agent asks: "Confirm: MULTI_FRAMEWORK for year 2024?"
  4. User: "Yes"
  5. Agent: "Report generation started. This takes 3-5 minutes..."
  6. User: "Check status"
  7. Agent: "Complete! 14 sections generated. [Download Report]"
  8. Click download → DOCX opens in Word
- [ ] Prepare demo script (talking points for AWS Summit)
- [ ] Backup: if agent fails, demo from Step Functions console directly
- [ ] ✅ **Milestone: AWS Summit demo-ready with chat UI**

### Alternative (simpler, no Amplify):
If time is tight, use **Bedrock Agent console chat** directly for demo — no frontend needed. Agent + tools still work the same, just demo in AWS console instead of custom URL.

---

## Post-POC: Optional Enhancements (W5+)

- [ ] Add Bedrock AgentCore (full agentic orchestration replacing Step Functions triggers)
- [ ] Add human-in-the-loop review UI (simple web app via ALB)
- [ ] Add scheduling (EventBridge rule → monthly auto-generation)
- [ ] Add multi-year comparison (2022 vs 2023 vs 2024)
- [ ] Add PDF export option (DOCX → PDF conversion)
- [ ] Performance optimization (parallel Athena queries, Lambda concurrency)
- [ ] Security hardening (VPC endpoints, KMS encryption, least-privilege audit)


### ANOTHER IMPORVEMENT FOR RECOMENDATION BY BEDROCK AGENTCORE


# ESG Advisory Layer — Requirements Specification
## Two-Pass Architecture: Pipeline 2 (Recommendations Engine)
### Version: 1.0 | Date: 05/06/2026

---

## 1. Overview & Objective

### 1.1 Purpose
Add an AI-powered **Advisory/Recommendations Layer** (Pipeline 2) to the existing ESG Report Generation System. This layer analyzes the factual report output (Pipeline 1) and generates **contextualized, framework-aligned recommendations** based on emission performance, regulatory guidance, and industry benchmarks.

### 1.2 Design Principle: Two-Pass Architecture

Pipeline 1 (EXISTING — no changes): Input → Validate → ETL → Athena → SectionGen → Validate → Assembly Output: Factual Report DOCX (auditable, deterministic)

Pipeline 2 (NEW — this spec): Input: Pipeline 1 metrics summary + report sections → Advisory Agent (Bedrock AgentCore) → Recommendations generation (framework-aware) → Append to DOCX OR separate advisory document Output: Recommendations Annex / Executive Advisory


### 1.3 Key Constraint
- Pipeline 1 output = **FACTUAL** (numbers, disclosures, methodology) → auditable
- Pipeline 2 output = **ADVISORY** (recommendations, gap analysis, benchmarking) → clearly labeled as AI-generated insights
- These MUST be visually and structurally separated in the final document

---

## 2. Functional Requirements

### 2.1 Input Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| ADV-INP-01 | Accept metrics summary JSON from Pipeline 1 (all scope totals, YoY, intensity, PCAF scores) | Lambda #2 output or Athena direct |
| ADV-INP-02 | Accept reporting_year and framework list | Step Functions input |
| ADV-INP-03 | Accept optional client-specific context (targets, commitments, sector) | Manual input or config |
| ADV-INP-04 | Access to Knowledge Base (framework guidance, best practices, benchmarks, reduction strategies) | KB ID: WVREXI1LEI |

### 2.2 Output Requirements

| ID | Requirement | Detail |
|----|-------------|--------|
| ADV-OUT-01 | Generate Executive Advisory Summary | 1-2 paragraphs, key findings + priority actions |
| ADV-OUT-02 | Generate Framework-Specific Recommendations | Per framework (GRI/IFRS/CSRD/OJK), aligned recommendations |
| ADV-OUT-03 | Generate Gap Analysis | Current performance vs framework expectations/targets |
| ADV-OUT-04 | Generate Prioritized Action Plan | Short-term (< 1yr), Medium-term (1-3yr), Long-term (3-5yr) |
| ADV-OUT-05 | Generate Benchmark Comparison | vs industry average, vs SBTi pathway, vs national targets |
| ADV-OUT-06 | Output as structured JSON (for DOCX assembly) OR markdown | Compatible with Lambda #5 AssemblyDoc |
| ADV-OUT-07 | All recommendations MUST cite framework clause/article | e.g., "Per GRI 305-5, organizations should..." |

### 2.3 Recommendation Categories

| Category | Trigger Condition | Example Output |
|----------|-------------------|----------------|
| **Emission Reduction** | YoY increase detected | "Scope 1 increased 2.36%. Consider: fleet electrification, renewable energy procurement..." |
| **Data Quality Improvement** | PCAF score > 2.5 | "Portfolio PCAF score is 3.27. Target: improve 20% of loans to Score 2 via direct engagement..." |
| **Portfolio Transition** | High-carbon sector > 40% | "Oil & Gas represents 43.56% of financed emissions. Develop sector transition policy per PCAF..." |
| **Target Setting** | No reduction target detected | "Per IFRS S2 para 33, disclose Scope 1+2 reduction target. Recommend SBTi 1.5°C alignment..." |
| **Disclosure Enhancement** | Missing optional disclosures | "Consider adding Scope 3 Category 1-14 per GRI 305-3 for comprehensive reporting..." |
| **Governance** | No climate governance mentioned | "Per CSRD ESRS E1 DR E1-1, disclose transition plan with board oversight..." |

### 2.4 Framework-Specific Guidance Mapping

| Framework | Relevant Clauses for Recommendations | Focus Area |
|-----------|--------------------------------------|------------|
| GRI 305 | 305-5 (Reduction), 305-1/2/3 (Completeness) | Reduction initiatives, boundary completeness |
| IFRS S2 | Para 29-33 (Metrics & Targets), Para 13-22 (Strategy) | Climate targets, transition plans, scenario analysis |
| CSRD/ESRS E1 | DR E1-1 (Transition Plan), DR E1-4 (Targets), DR E1-8 (Internal Carbon Pricing) | Transition plan, SBTi targets, carbon pricing |
| OJK PSPK | Bab III (Rencana Aksi), Bab IV (Target Penurunan) | Action plan, reduction targets, green portfolio ratio |

---

## 3. Technical Architecture

### 3.1 Component Overview

┌─────────────────────────────────────────────────────────────────┐ │ Step Functions (Extended) │ │ │ │ [Pipeline 1: Report Gen] ──→ [Pipeline 2: Advisory Gen] │ │ │ │ │ ┌────────┴────────┐ │ │ │ Lambda: Advisory │ │ │ │ Orchestrator │ │ │ └────────┬────────┘ │ │ │ │ │ ┌────────┴────────┐ │ │ │ Bedrock Agent │ │ │ │ (AgentCore) │ │ │ └────────┬────────┘ │ │ │ │ │ ┌──────────────────┼──────────────────┐ │ │ │ │ │ │ │ ┌─────┴─────┐ ┌──────┴──────┐ ┌──────┴─────┐ │ │ │ Tool: KB │ │ Tool: Athena │ │ Tool: Bench│ │ │ │ Retrieve │ │ Query │ │ mark Data │ │ │ └───────────┘ └─────────────┘ └────────────┘ │ └─────────────────────────────────────────────────────────────────┘


### 3.2 Bedrock AgentCore Configuration

| Setting | Value |
|---------|-------|
| **Agent Name** | `esg-advisory-agent` |
| **Foundation Model** | Claude Sonnet 4.5 (via inference profile) |
| **Instruction Length** | Long (advisory requires detailed reasoning) |
| **Session TTL** | 300 seconds |
| **Guardrails** | Content filter + denied topics (investment advice, legal advice) |
| **Action Groups** | 3 (see §3.3) |

### 3.3 Action Groups (Tools)

#### Tool 1: `search_framework_guidance`
```json
{
  "name": "search_framework_guidance",
  "description": "Search ESG framework standards for specific guidance on targets, reductions, and disclosure requirements",
  "parameters": {
    "query": "string - what guidance to search for",
    "framework_filter": "string - GRI_305|IFRS_S2|CSRD_ESRS_E1|OJK_PSPK|ALL"
  },
  "implementation": "Bedrock KB Retrieve (KB ID: WVREXI1LEI) with metadata filter"
}
Tool 2: get_emission_metrics

{
  "name": "get_emission_metrics",
  "description": "Get current and historical emission metrics for analysis",
  "parameters": {
    "reporting_year": "int",
    "metric_type": "string - scope1|scope2|scope3|intensity|all",
    "include_yoy": "boolean"
  },
  "implementation": "Athena query against esg_aggregated tables"
}

Tool 3: get_benchmark_data
{
  "name": "get_benchmark_data",
  "description": "Get industry benchmarks, SBTi pathways, and national targets for comparison",
  "parameters": {
    "sector": "string - financial_institution|energy|manufacturing|all",
    "benchmark_type": "string - sbti_pathway|industry_average|national_target|paris_aligned"
  },
  "implementation": "KB Retrieve from benchmark documents OR hardcoded reference data"
}

3.4 Agent Instructions (Base Prompt)
You are an ESG Advisory Agent for financial institutions. Your role is to 
analyze GHG emission data and provide actionable, framework-aligned 
recommendations.

RULES:
1. Every recommendation MUST cite a specific framework clause (e.g., "GRI 305-5", "IFRS S2 para 33")
2. Recommendations must be ACTIONABLE — include specific steps, not generic advice
3. Prioritize by impact: largest emission sources first
4. Consider feasibility for Indonesian financial institution context
5. Distinguish between: regulatory requirement vs. best practice vs. stretch goal
6. NEVER provide specific investment advice or legal advice
7. ALWAYS caveat: "These recommendations are AI-generated advisory insights and should be reviewed by qualified ESG professionals"
8. Use data from tools — do not fabricate benchmarks or targets

OUTPUT FORMAT:
Return structured JSON with sections:
- executive_summary (1-2 paragraphs)
- gap_analysis (array of gaps with severity)
- recommendations (array with: category, priority, framework_reference, action, rationale, timeline)
- benchmark_comparison (current vs targets)

3.5 Lambda: Advisory Orchestrator (esg-advisory-orchestrator)
| Setting | Value |
|---------|-------|
| **Runtime** | Python 3.11 |
| **Memory** | 512 MB |
| **Timeout** | 180 seconds |
| **Purpose** | Invoke AgentCore agent, parse response, format for assembly |

logic:

def handler(event, context):
    # 1. Extract metrics summary from Pipeline 1 output
    metrics = event['pipeline1_metrics']
    frameworks = event['frameworks']
    reporting_year = event['reporting_year']
    
    # 2. Build agent input prompt
    agent_prompt = build_advisory_prompt(metrics, frameworks, reporting_year)
    
    # 3. Invoke AgentCore
    response = bedrock_agent.invoke_agent(
        agentId=ADVISORY_AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        sessionId=str(uuid4()),
        inputText=agent_prompt
    )
    
    # 4. Parse structured response
    advisory_sections = parse_advisory_response(response)
    
    # 5. Return for assembly
    return {
        'status': 'SUCCESS',
        'advisory_sections': advisory_sections
    }


4. Knowledge Base Expansion
4.1 New Documents to Add to KB
| Document | Category | Purpose |
|----------|----------|---------|
| `SBTi_Financial_Sector_Guidance_2024.pdf` | benchmark | Science-Based Targets for FIs |
| `PCAF_Recommendations_Best_Practices.pdf` | best_practice | PCAF implementation guidance |
| `Indonesia_NDC_Enhanced_2022.pdf` | benchmark | National reduction targets |
| `IEA_Net_Zero_2050_Financial_Sector.pdf` | benchmark | Net zero pathway for FIs |
| `ESG_Reduction_Strategies_FI.pdf` | best_practice | Proven reduction strategies |
| `Climate_Risk_Management_OJK.pdf` | regulatory | OJK climate risk guidance |
| `GFANZ_Transition_Plan_Framework.pdf` | best_practice | Transition planning guidance |

4.2 Metadata Schema Extension
json

{
  "metadataAttributes": {
    "category": "benchmark|best_practice|regulatory|ghg_methodology|style_reference",
    "framework": "GRI_305|PCAF|IFRS_S2|CSRD_ESRS_E1|OJK_PSPK|SBTi|GFANZ",
    "document_type": "standard|methodology|style_reference|guidance|benchmark",
    "content_type": "factual|advisory",
    "version": "2022|2024|2025",
    "language": "en|id",
    "contains_numeric_data": "true|false"
  }
}

5. Step Functions Integration
5.1 Extended State Machine Flow
[Pipeline 1: Existing]
  ValidateInput → ETL → QueryAthena → GenerateSections → ValidateSections 
  → FilterSections → AssembleReport
                                          ↓
[Pipeline 2: Advisory — NEW]
  → ExtractMetricsSummary (Lambda)
  → InvokeAdvisoryAgent (Lambda → AgentCore)
  → ValidateAdvisory (basic checks — no numeric validation needed)
  → AppendToDocument (Lambda #5 extended) OR GenerateSeparateDoc
  → NotifyComplete


5.2 State Machine ASL Addition (Conceptual)
json

{
  "AdvisoryGeneration": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:us-east-1:061039769766:function:esg-advisory-orchestrator",
    "Parameters": {
      "pipeline1_metrics.$": "$.athena_results",
      "frameworks.$": "$.input.framework",
      "reporting_year.$": "$.input.reporting_year",
      "bank_id.$": "$.input.bank_id"
    },
    "ResultPath": "$.advisory_output",
    "Next": "ValidateAdvisory",
    "Retry": [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 1}]
  }
}

5.3 Conditional Advisory (Optional)
json

{
  "CheckAdvisoryEnabled": {
    "Type": "Choice",
    "Choices": [{
      "Variable": "$.input.include_advisory",
      "BooleanEquals": true,
      "Next": "AdvisoryGeneration"
    }],
    "Default": "SkipAdvisory"
  }
}

Input format becomes:

json

{
  "reporting_year": 2024,
  "framework": "MULTI_FRAMEWORK",
  "include_advisory": true,
  "advisory_config": {
    "focus_areas": ["emission_reduction", "data_quality", "target_setting"],
    "benchmark_against": ["sbti_15c", "industry_average"],
    "language": "en"
  }
}

6. Output Document Structure
6.1 Integrated Report (Single DOCX)
EXISTING SECTIONS (Pipeline 1):
├── Cover Page
├── Table of Contents
├── Executive Summary (factual)
├── GRI 305 Disclosures
│   ├── Scope 1
│   ├── Scope 2
│   ├── Scope 3 / PCAF
│   └── Intensity
├── IFRS S2 Disclosures
├── CSRD/ESRS E1 Disclosures
├── OJK PSPK Disclosures
├── Data Quality & Methodology
└── Appendices

NEW SECTIONS (Pipeline 2):
├── ══════════════════════════════════════
├── ADVISORY SECTION (clearly demarcated)
├── ══════════════════════════════════════
├── Disclaimer Banner:
│   "The following recommendations are AI-generated advisory insights
│    based on reported data and framework guidance. They should be
│    reviewed and validated by qualified ESG professionals before
│    implementation."
├── Executive Advisory Summary
├── Performance Gap Analysis
│   ├── Current vs Framework Requirements
│   ├── Current vs Industry Benchmarks
│   └── Current vs Science-Based Targets
├── Framework-Specific Recommendations
│   ├── GRI 305-5 Aligned Actions
│   ├── IFRS S2 Strategy & Targets
│   ├── CSRD/ESRS E1 Transition Plan Elements
│   └── OJK PSPK Action Plan (Rencana Aksi)
├── Prioritized Action Plan
│   ├── Immediate (0-6 months)
│   ├── Short-term (6-12 months)
│   ├── Medium-term (1-3 years)
│   └── Long-term (3-5 years)
└── Benchmark Comparison Table
6.2 Advisory Section JSON Schema (for Assembly)
json
{
  "advisory_sections": [
    {
      "section_type": "disclaimer",
      "content": "string — standard disclaimer text"
    },
    {
      "section_type": "executive_advisory",
      "title": "Executive Advisory Summary",
      "paragraphs": ["string"]
    },
    {
      "section_type": "gap_analysis",
      "title": "Performance Gap Analysis",
      "gaps": [
        {
          "area": "Scope 1 Reduction",
          "current": "+2.36% YoY increase",
          "target": "-4.2% per year (SBTi 1.5°C)",
          "gap": "-6.56% deviation",
          "severity": "HIGH",
          "framework_ref": "GRI 305-5, IFRS S2 para 33(a)"
        }
      ]
    },
    {
      "section_type": "recommendations",
      "title": "Recommendations",
      "items": [
        {
          "id": "REC-001",
          "category": "emission_reduction",
          "priority": "HIGH",
          "title": "Fleet Electrification Program",
          "rationale": "Diesel accounts for 64.7% of Scope 1...",
          "action_steps": ["Step 1...", "Step 2..."],
          "expected_impact": "Reduce Scope 1 by 30-40% over 3 years",
          "timeline": "medium_term",
          "framework_reference": "GRI 305-5(a), OJK PSPK Bab III",
          "investment_level": "MEDIUM"
        }
      ]
    },
    {
      "section_type": "action_plan",
      "title": "Prioritized Action Plan",
      "immediate": ["..."],
      "short_term": ["..."],
      "medium_term": ["..."],
      "long_term": ["..."]
    },
    {
      "section_type": "benchmark_table",
      "title": "Benchmark Comparison",
      "columns": ["Metric", "Current", "Industry Avg", "SBTi Target", "Gap"],
      "rows": ["..."]
    }
  ]
}

7. Validation Rules (Advisory-Specific)

| Rule | Check | Action |
|------|-------|--------|
| ADV-VAL-01 | Every recommendation has framework_reference | FAIL if missing |
| ADV-VAL-02 | No investment/legal advice language | FAIL if detected |
| ADV-VAL-03 | Disclaimer section present | FAIL if missing |
| ADV-VAL-04 | Numbers referenced match Pipeline 1 metrics | WARN if mismatch |
| ADV-VAL-05 | At least 3 recommendations generated | WARN if fewer |
| ADV-VAL-06 | All priority levels covered (HIGH/MEDIUM/LOW) | WARN if missing |
| ADV-VAL-07 | Timeline distribution reasonable | WARN if all same timeline |
| ADV-VAL-08 | No fabricated benchmark numbers | FAIL if benchmark not from KB |

8. Guardrails Configuration
8.1 Denied Topics
Specific investment recommendations ("buy X stock", "divest from Y")
Legal advice ("you must comply with...", "you are in violation of...")
Guarantee of outcomes ("this will definitely reduce...")
Comparison to specific named competitors
8.2 Required Caveats
Every advisory output MUST include disclaimer
Benchmark data MUST cite source
Reduction estimates MUST include range (not single number)
Timeline MUST be indicative ("typically 1-3 years", not "exactly 18 months")

9. IAM Permissions (New)
9.1 Advisory Orchestrator Lambda Role
json

{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeAgent",
    "bedrock:GetAgent"
  ],
  "Resource": "arn:aws:bedrock:us-east-1:061039769766:agent/*"
}

9.2 AgentCore Execution Role
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:Retrieve",
    "athena:StartQueryExecution",
    "athena:GetQueryExecution",
    "athena:GetQueryResults",
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": [
    "arn:aws:bedrock:us-east-1:061039769766:knowledge-base/WVREXI1LEI",
    "arn:aws:bedrock:us-east-1:*:inference-profile/*",
    "arn:aws:athena:us-east-1:061039769766:workgroup/esg-reporting-workgroup",
    "arn:aws:s3:::esg-aggregated-data-061039769766/*",
    "arn:aws:s3:::esg-kb-documents-061039769766/*"
  ]
}
