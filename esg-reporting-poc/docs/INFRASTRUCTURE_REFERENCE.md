# ESG Reporting POC — Infrastructure & Configuration Reference

> Generated: 2026-06-03
> Last Updated: 2026-06-05
> Status: D1-D15 + W4 (Bedrock Agent + Chat UI Operational)

---

## AWS Account

| Property | Value |
|----------|-------|
| Account ID | `061039769766` |
| Region | `us-east-1` (N. Virginia) |
| Environment | POC |
| Tags | `Project=ESG`, `Env=POC`, `Team=Sustainability` |

---

## IAM Roles

| Role Name | Trust Principal | Key Permissions |
|-----------|-----------------|-----------------|
| `ESGGlueRole` | `glue.amazonaws.com` | S3 read/write (raw, curated, aggregated), CloudWatch Logs, AWSGlueServiceRole |
| `ESGLambdaRole` | `lambda.amazonaws.com` | S3 (all 4 buckets), Athena, Bedrock (invoke + KB), DynamoDB (ESG*), CloudWatch Logs |
| `ESGStepFunctionsRole` | `states.amazonaws.com` | Lambda invoke (esg-*), SNS publish (ESG*), CloudWatch Logs |

---

## S3 Buckets

| Bucket Name | Purpose | Created |
|-------------|---------|---------|
| `esg-data-raw-061039769766` | Raw zone — source data as ingested | 2026-06-03 |
| `esg-data-curated-061039769766` | Curated zone — ETL-computed GHG calculations | 2026-06-03 |
| `esg-data-aggregated-061039769766` | Aggregated zone — report-ready metrics | 2026-06-03 |
| `esg-output-reports-061039769766` | Output — generated DOCX/PDF reports | 2026-06-03 |

### Bucket Configuration

- **Versioning:** Enabled (all buckets)
- **Lifecycle:** Keep 1 noncurrent version, delete older after 1 day
- **Public Access:** Blocked (all 4 settings)
- **Region:** us-east-1

### Folder Structure

```
{bucket}/
├── 2023/
│   ├── emissions/
│   ├── energy/
│   ├── water/
│   ├── waste/
│   ├── social/
│   └── governance/
└── 2024/
    ├── emissions/
    ├── energy/
    ├── water/
    ├── waste/
    ├── social/
    └── governance/
```

---

## S3 Data Locations (Uploaded)

| Dataset | S3 Path | Size | Rows |
|---------|---------|------|------|
| Energy 2023 | `s3://esg-data-raw-061039769766/2023/energy/energy_consumption.parquet` | 58 KB | 2,640 |
| Energy 2024 | `s3://esg-data-raw-061039769766/2024/energy/energy_consumption.parquet` | 59 KB | 2,640 |
| Loans 2023 | `s3://esg-data-raw-061039769766/2023/loans/loan_portfolio.parquet` | 131 KB | 2,200 |
| Loans 2024 | `s3://esg-data-raw-061039769766/2024/loans/loan_portfolio.parquet` | 132 KB | 2,200 |
| HR 2023 | `s3://esg-data-raw-061039769766/2023/social/hr_metrics.parquet` | 6 KB | 1 |
| HR 2024 | `s3://esg-data-raw-061039769766/2024/social/hr_metrics.parquet` | 6 KB | 1 |

---

## Athena Configuration

| Property | Value |
|----------|-------|
| Workgroup | `esg-reporting-workgroup` |
| Region | `us-east-1` |
| Result Location | (configured in workgroup) |

### Databases

| Database | Purpose | S3 Location |
|----------|---------|-------------|
| `esg_raw` | Source data as ingested | `s3://esg-data-raw-061039769766/` |
| `esg_curated` | ETL-computed GHG emissions | `s3://esg-data-curated-061039769766/` |
| `esg_aggregated` | Report-ready annual metrics (AgentCore reads ONLY from here) | `s3://esg-data-aggregated-061039769766/` |

### Tables

| Database | Table | Partition Key(s) | S3 Location Template |
|----------|-------|------------------|----------------------|
| esg_raw | energy_consumption | reporting_year | `s3://esg-data-raw-061039769766/energy_consumption/reporting_year=${reporting_year}` |
| esg_raw | loan_portfolio | reporting_year | `s3://esg-data-raw-061039769766/loan_portfolio/reporting_year=${reporting_year}` |
| esg_raw | hr_metrics | reporting_year | `s3://esg-data-raw-061039769766/hr_metrics/reporting_year=${reporting_year}` |
| esg_curated | ghg_scope1 | reporting_year | `s3://esg-data-curated-061039769766/ghg_scope1/reporting_year=${reporting_year}` |
| esg_curated | ghg_scope2 | reporting_year | `s3://esg-data-curated-061039769766/ghg_scope2/reporting_year=${reporting_year}` |
| esg_curated | ghg_scope3_financed | reporting_year | `s3://esg-data-curated-061039769766/ghg_scope3_financed/reporting_year=${reporting_year}` |
| esg_aggregated | ghg_summary_annual | reporting_year | `s3://esg-data-aggregated-061039769766/ghg_summary_annual/reporting_year=${reporting_year}` |
| esg_aggregated | pcaf_by_sector | reporting_year | `s3://esg-data-aggregated-061039769766/pcaf_by_sector/reporting_year=${reporting_year}` |

### Partition Projection (All Tables)

```
projection.enabled = true
projection.reporting_year.type = integer
projection.reporting_year.range = 2020,2035
parquet.compress = SNAPPY
classification = parquet
```

---

## Synthetic Data Summary

### energy_consumption (220 facilities × 2 years × 12 months = 5,280 rows)

| Facility Type | Count | Electricity (kWh) | Gas (GJ) | Diesel (L) |
|---------------|-------|--------------------|-----------|-------------|
| branch | 150 | 1,500–25,000 | none | none |
| regional_office | 30 | 15,000–55,000 | 5–40 | 100–1,500 |
| data_centre | 15 | 50,000–85,000 | none | 500–3,500 |
| headquarters | 5 | 60,000–85,000 | 50–120 | 1,000–3,500 |
| warehouse | 20 | 5,000–35,000 | 10–60 | 200–2,000 |

- EF Source: PLN_Grid_Average_2023 (85.8%), DEFRA_2025 (9.1%), IPCC_AR6_CH4_GWP100 (5.1%)
- Record Status: complete (97.4%), excluded (2.0%), missing_primary (0.6%)

### loan_portfolio (2,200 borrowers × 2 years = 4,400 rows)

| PCAF Score | Target % | Actual % |
|------------|----------|----------|
| 1.0 | 3.5% | 4.2% |
| 1.5 | 1.5% | 2.0% |
| 2.0 | 15.0% | 14.9% |
| 3.0 | 30.0% | 30.2% |
| 4.0 | 35.0% | 34.5% |
| 5.0 | 15.0% | 14.2% |

- Outstanding (IDR) mean: 790.7B, median: 500.0B
- Emissions (tCO2e) mean: 178,054, median: 19,498
- Record Status: validated (88.4%), pending (7.3%), rejected (4.3%)

### hr_metrics (1 row per year = 2 rows)

| Metric | 2023 | 2024 |
|--------|------|------|
| FTE Total | 24,500 | 24,997 |
| Female % | 46.2% | 42.3% |
| Female Mgmt % | 28.4% | 26.7% |
| New Hires | 3,169 | 2,595 |
| Voluntary Turnover | 14.2% | 8.4% |
| Training Hours/FTE | 64.1 | 49.3 |
| Discrimination Cases | 3 | 2 |

---

## Emission Factor Constants (from Spec §3.1)

| Constant | Value | Unit | Source |
|----------|-------|------|--------|
| GWP_CH4 | 29.8 | kg CO2e/kg CH4 | IPCC AR6 GWP100 |
| GWP_N2O | 273.0 | kg CO2e/kg N2O | IPCC AR6 GWP100 |
| EF_NATGAS_KGCO2_PER_GJ | 56.10 | kg CO2/GJ | IPCC 2006 Table 2.2 |
| EF_NATGAS_KGCH4_PER_GJ | 0.001 | kg CH4/GJ | IPCC 2006 Vol 2 Table 2.3 |
| EF_NATGAS_KGN2O_PER_GJ | 0.0001 | kg N2O/GJ | IPCC 2006 Vol 2 Table 2.3 |
| EF_DIESEL_KGCO2_PER_L | 2.53763 | kg CO2/L | DEFRA 2025 Annex 3 |
| EF_DIESEL_KGCH4_PER_L | 0.0000097 | kg CH4/L | DEFRA 2025 |
| EF_DIESEL_KGN2O_PER_L | 0.000121 | kg N2O/L | DEFRA 2025 |
| GRID_EF_PLN_2023 | 0.7886 | kg CO2/kWh | PLN National Grid 2023 |

### PCAF Confidence Factors

| PCAF Tier | Factor | Description |
|-----------|--------|-------------|
| 1 | 1.00 | Verified CDP/equivalent |
| 2 | 0.90 | Reported, unverified |
| 3 | 0.75 | EEIO + revenue-based |
| 4 | 0.60 | EEIO + asset-based |
| 5 | 0.45 | Sector-average proxy |

---

## Glue Jobs

| Job Name | Script | Input | Output | Status |
|----------|--------|-------|--------|--------|
| `esg-etl-scope1-direct` | `glue_job_scope1_ghg.py` | `s3://{RAW}/energy/` (record_status='complete') | `s3://{CURATED}/{year}/ghg_scope1/` | ✅ Complete (D4) |
| `esg-etl-scope2-indirect` | `glue_job_scope2_electricity.py` | `s3://{RAW}/energy/` (record_status='complete') | `s3://{CURATED}/{year}/ghg_scope2/` | ✅ Complete (D5) |
| `esg-etl-scope3-pcaf` | `glue_job_scope3_pcaf.py` | `s3://{RAW}/loans/` (record_status='validated') | `s3://{CURATED}/{year}/ghg_scope3_financed/` | ✅ Complete (D5) |
| `esg-etl-aggregation` | `glue_job_aggregation.py` | All curated tables | `s3://{AGG}/{year}/ghg_summary_annual/` + `pcaf_by_sector/` | ⏳ Pending (D6) |

### Glue Job Configuration (all jobs)

| Property | Value |
|----------|-------|
| Glue Version | 4.0 |
| Worker Type | G.1X |
| Number of Workers | 2 |
| Python Version | 3 |
| `--enable-glue-datacatalog` | true |
| `--enable-job-insights` | true |
| Role | ESGGlueRole |
| Scripts Location | `s3://esg-data-raw-061039769766/scripts/` |

### Glue Job Output Verification (2024)

**Scope 1 (`esg_curated.ghg_scope1`):**
- Rows per year: ~220 (1 per facility)
- All validation gates passed (GATE-S1-01 to S1-05)

**Scope 2 (`esg_curated.ghg_scope2`):**
- Rows per year: ~220 (1 per facility)
- Dual reporting: location-based + market-based
- All validation gates passed (GATE-S2-01 to S2-05)

**Scope 3 PCAF (`esg_curated.ghg_scope3_financed` — 2024 data):**

| Sector | Loans | Gross (tCO2e) | Weighted (tCO2e) | Avg PCAF |
|--------|-------|---------------|------------------|----------|
| energy_oil_gas | 135 | 9,573,144 | 6,753,949 | 3.32 |
| manufacturing_cement | 161 | 5,813,831 | 4,168,058 | 3.40 |
| manufacturing_steel | 122 | 3,499,463 | 2,228,740 | 3.35 |
| transportation_road | 189 | 1,227,020 | 864,356 | 3.36 |
| manufacturing_food | 206 | 936,111 | 653,414 | 3.35 |
| agriculture | 163 | 288,493 | 183,548 | 3.41 |
| real_estate_commercial | 290 | 231,235 | 158,419 | 3.27 |
| retail_trade | 209 | 226,341 | 140,813 | 3.21 |
| real_estate_residential | 223 | 107,465 | 79,159 | 3.32 |
| financial_services | 257 | 73,694 | 49,718 | 3.42 |

- Total gross: ~21.98M tCO2e
- weighted ≤ gross: ✅ for all sectors (REQ-ETL-23)
- avg_pcaf_score range: 3.21–3.43 ✅

---

## Lambda Functions (Deployed)

| Function | Runtime | Memory | Timeout | Purpose | Layer |
|----------|---------|--------|---------|---------|-------|
| `esg-validate-input` | Python 3.11 | 256 MB | 30s | Input validation (REQ-SFN-03) | — |
| `esg-athena-query` | Python 3.11 | 512 MB | 60s | Single-call Athena data fetch (REQ-DDL-11) | — |
| `esg-section-gen` | Python 3.11 | 1024 MB | 120s | AI section generation (Bedrock + KB RAG) | — |
| `esg-validation` | Python 3.11 | 512 MB | 60s | 21-rule output validation (§7) | — |
| `esg-assembly-doc` | Python 3.11 | 1024 MB | 120s | DOCX assembly (§8) | `esg-python-docx:2` |

### Lambda Layer: `esg-python-docx`

| Property | Value |
|----------|-------|
| Layer Name | `esg-python-docx` |
| Current Version | `:2` |
| Compatible Runtime | python3.11 |
| Contents | `python-docx` + `lxml` (Linux x86_64 binaries) |
| S3 Location | `s3://esg-data-raw-061039769766/lambda-layers/python-docx-layer.zip` |

**⚠️ CRITICAL: Layer MUST be built on Linux (CloudShell), not Windows.**

`lxml` has C extensions that require Linux-compiled binaries. Building on Windows produces incompatible `.pyd` files.

**Build command (run in CloudShell us-east-1):**
```bash
mkdir -p /tmp/layer/python
pip install python-docx -t /tmp/layer/python --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.11 --implementation cp
cd /tmp/layer
zip -r /tmp/python-docx-layer.zip python/
aws s3 cp /tmp/python-docx-layer.zip s3://esg-data-raw-061039769766/lambda-layers/python-docx-layer.zip
aws lambda publish-layer-version --layer-name esg-python-docx --description "python-docx for Lambda (Linux x86_64)" --content S3Bucket=esg-data-raw-061039769766,S3Key=lambda-layers/python-docx-layer.zip --compatible-runtimes python3.11 --region us-east-1
```

### Lambda Deployment (from `bedrock-agentcore-solution\`)

**Package (Windows — handler only, no dependencies):**
```cmd
mkdir deploy
powershell Compress-Archive -Path esg-reporting-poc\lambda\{function}\handler.py -DestinationPath deploy\{function}.zip -Force
```

**Upload + Create:**
```cmd
aws s3 cp deploy\{function}.zip s3://esg-data-raw-061039769766/lambda-code/{function}.zip
aws lambda create-function --function-name esg-{name} --runtime python3.11 --handler handler.lambda_handler --role arn:aws:iam::061039769766:role/ESGLambdaRole --code S3Bucket=esg-data-raw-061039769766,S3Key=lambda-code/{function}.zip --timeout {T} --memory-size {M} --region us-east-1
```

**Update existing:**
```cmd
aws lambda update-function-code --function-name esg-{name} --s3-bucket esg-data-raw-061039769766 --s3-key lambda-code/{function}.zip --region us-east-1
```

### Lambda IAM Role: `ESGLambdaRole`

Single role for all 5 functions (POC). Policy `ESGLambdaAccess` includes:
- S3: 6 buckets (GetObject, PutObject, ListBucket, GetBucketLocation, PutObjectTagging)
- Athena: StartQueryExecution, GetQueryExecution, GetQueryResults, StopQueryExecution
- Glue: GetTable, GetTables, GetDatabase, GetDatabases, GetPartitions
- Bedrock: InvokeModel, InvokeModelWithResponseStream (all regions, inference profiles)
- Bedrock KB: Retrieve, RetrieveAndGenerate
- DynamoDB: PutItem, GetItem, UpdateItem, Query, Scan (ESG* tables)

### Bedrock Model

| Property | Value |
|----------|-------|
| Model ID | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| Type | Cross-region inference profile |
| Region | us-east-1 |

**Check available models:**
```bash
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[?contains(modelId, 'claude')].modelId" --output table
aws bedrock list-inference-profiles --region us-east-1 --query "inferenceProfileSummaries[?contains(inferenceProfileName, 'Claude')].[inferenceProfileId,inferenceProfileName]" --output table
```

### Knowledge Base

| Property | Value |
|----------|-------|
| KB ID | `WVREXI1LEI` |
| Region | us-east-1 |
| Documents Bucket | `esg-kb-documents-061039769766` |
| Embedding Model | Titan Embeddings V2 |
| Vector Store | OpenSearch Serverless |
| Chunking Strategy | **Semantic** |
| Max Sentences per Chunk | 1 |
| Token Size | 700 |
| Similarity Percentile Threshold | 90 |
| Foundation Model (KB) | Claude Sonnet 4.6 |
| Min Relevance Score (retrieval) | 0.40 |

### Lessons Learned (Lambda Deployment)

1. **Layer must be Linux-built:** Windows `pip install` produces incompatible binaries for `lxml`. Always build layers in CloudShell or Docker.
2. **KB bucket not in original IAM policy:** `esg-kb-documents-*` was missing from S3Access. Added manually.
3. **`s3:GetBucketLocation` required:** Athena needs this to verify output bucket. Not obvious from error message.
4. **`s3:PutObjectTagging` required:** AssemblyDoc uploads with S3 object tags (REQ-TRACE-05).
5. **Model ID deprecation:** `anthropic.claude-3-5-sonnet-20241022-v2:0` reached end-of-life. Use inference profile ID or latest model.
6. **Prompts path mismatch:** Templates must be at `prompts/templates/{name}_template.txt` in S3 (not flat in `prompts/`). Overlay for CSRD must be named `overlay_esrs_e1.txt`.

---

## Key Decisions & Notes

1. **Single Region:** All resources in `us-east-1` — no cross-region, no VPC endpoints needed.
2. **Partition Projection:** Used in Athena DDL (per REQ-DDL-04, CON-DDL-01). Glue Spark reads S3 directly.
3. **S3 Path Convention:** `s3://{bucket}/{zone}/{table}/reporting_year={Y}/[reporting_month={M}/]` — Hive-style per REQ-DDL-05.
4. **S3 Direct Read (ADR):** All Glue jobs + Lambda read from S3 directly. Schema governance gate compensates.
5. **PCAF Score Type:** DOUBLE (supports 1.5 half-scores).
6. **Rounding Order:** Components first, then recompute totals.
7. **Bedrock Model:** `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (inference profile).
8. **Knowledge Base:** ID `WVREXI1LEI`, bucket `esg-kb-documents-061039769766`.
9. **Single Lambda Role:** `ESGLambdaRole` for all 5 functions (POC simplification; spec requires 5 separate roles for prod).
10. **Layer build constraint:** Must use CloudShell/Linux for python-docx layer (lxml C extension).

---

## Step Functions

| Property | Value |
|----------|-------|
| State Machine Name | `ESGReportGenerationStateMachine` |
| ARN | `arn:aws:states:us-east-1:061039769766:stateMachine:ESGReportGenerationStateMachine` |
| Type | STANDARD |
| Role | `ESGStepFunctionsRole` |
| ASL File (active) | `step_functions/esg_orchestrator.asl.json` (auto-approve) |
| ASL File (manual review) | `step_functions/esg_orchestrator_human_review_manual.asl.json` |

### State Machine Flow

```
ValidateInput → WaitForGlueJobs (Parallel: Scope1+2+3)
  → TriggerAggregation → QueryAthena
  → GenerateSections (Map, MaxConcurrency:3)
      [per section: SectionGen → Validation → Choice]
        PASS → Accumulate
        WARN → AccumulateWithWarning
        RETRY → Re-gen once → Re-validate
        FAIL → Auto-Approve (SNS notification) → AccumulateWithWarning
  → FilterSections → AssembleDocument → NotifyCompletion → Success
```

### How to Start Execution

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:061039769766:stateMachine:ESGReportGenerationStateMachine \
  --input '{
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
  }' --region us-east-1
```

For multi-framework (all 4): use `"framework": "MULTI_FRAMEWORK"` with full 14-section template list.

### How to Update State Machine

```bash
# From Windows CMD — upload to S3 first (encoding issues with file://)
aws s3 cp esg-reporting-poc\step_functions\esg_orchestrator.asl.json s3://esg-data-raw-061039769766/scripts/esg_orchestrator.asl.json

# From CloudShell — download and deploy
aws s3 cp s3://esg-data-raw-061039769766/scripts/esg_orchestrator.asl.json /tmp/esg_orchestrator.asl.json
aws stepfunctions update-state-machine --state-machine-arn arn:aws:states:us-east-1:061039769766:stateMachine:ESGReportGenerationStateMachine --definition file:///tmp/esg_orchestrator.asl.json --region us-east-1
```

---

## SNS Topics

| Topic | ARN | Purpose |
|-------|-----|---------|
| `ESG-HumanReview` | `arn:aws:sns:us-east-1:061039769766:ESG-HumanReview` | Validation failure notifications (auto-approve mode: info only) |
| `ESG-ReportComplete` | `arn:aws:sns:us-east-1:061039769766:ESG-ReportComplete` | Report generation completion with S3 path |

---

## Review Handler (Human Review Infrastructure)

| Property | Value |
|----------|-------|
| Lambda | `esg-review-handler` |
| Function URL | `https://vel6mq7yhaty24wx2b4virsxze0qdskl.lambda-url.us-east-1.on.aws/` |
| Auth Type | NONE |
| Status | ⚠️ Blocked by Organization SCP (Function URL returns Forbidden from browser) |
| Workaround | Use CloudShell `send-task-success` or auto-approve mode |

---

## Full Deployment Procedure (from scratch)

### Prerequisites
- AWS CLI configured with appropriate credentials
- Python 3.11+ installed locally
- CloudShell access (us-east-1) for Linux-dependent operations

### Step-by-step

```
1. IAM Roles:        scripts/setup_account.sh (run in CloudShell)
2. S3 Buckets:       scripts/setup_account.sh
3. Generate Data:    python scripts/generate_energy_data.py (+ loan + hr)
4. Upload Data:      scripts/upload_to_s3.bat (or aws s3 cp commands)
5. Athena DDL:       Run sql/ddl/00_drop_all_tables.sql → 01 → 02 → 03 → 04 (one per execution)
6. Glue Scripts:     aws s3 cp glue_jobs/*.py s3://esg-data-raw-061039769766/scripts/
7. Glue Jobs:        Create via CLI (see deploy commands below)
8. Run Glue ETL:     Start scope1+2+3 → then aggregation
9. KB Documents:     python scripts/setup_kb_documents.py → aws s3 cp commands
10. KB Metadata:     Upload .metadata.json files
11. Prompts to S3:   aws s3 cp prompts/ + templates/ to s3://esg-kb-documents-*/prompts/
12. Lambda Layer:    Build in CloudShell (python-docx + lxml for Linux)
13. Package Lambda:  powershell Compress-Archive for each handler
14. Deploy Lambda:   aws lambda create-function (5 functions + filter + review handler)
15. SNS Topics:      aws sns create-topic (2 topics)
16. Step Functions:  aws stepfunctions create-state-machine (via CloudShell)
17. Test:            Start execution from console or CLI
```

---

## Bedrock Agent (Chat Interface)

| Property | Value |
|----------|-------|
| Agent Name | `ESGReportAgent` |
| Agent ID | `MBERNIQMBG` |
| Alias ID | `QIXEJW2TN6` (esg-report-agent-v2) |
| Model | Claude Sonnet 4.5 (inference profile) |
| Action Group | `ESGReportActions` |
| Tools Lambda | `esg-agent-tools` |
| Instructions | `agent/agent_instructions.txt` |
| OpenAPI Schema | `agent/openapi_schema.json` |

### Agent Tools

| Tool | Purpose | Backend |
|------|---------|---------|
| `generate_report` | Triggers Step Functions pipeline | `sfn.start_execution()` |
| `check_status` | Checks execution status | `sfn.describe_execution()` |
| `download_report` | Generates presigned S3 URL | `s3.generate_presigned_url()` |
| `list_available_data` | Returns available years/frameworks | Static response |

---

## Chat App (Frontend)

| Property | Value |
|----------|-------|
| App Name | `ESG-Chat` |
| Amplify App ID | `d337jqli3ubqmk` |
| URL | `https://main.d337jqli3ubqmk.amplifyapp.com` |
| Backend API | `https://olj4tuggm1.execute-api.us-east-1.amazonaws.com/prod` |
| Proxy Lambda | `esg-chat-proxy` |
| Source | `esg-chat-app/frontend/index.html` |

### Chat App Architecture

```
Browser (Amplify) → API Gateway (POST /chat) → Lambda (esg-chat-proxy) → Bedrock Agent
    → Agent calls tools → Lambda (esg-agent-tools) → Step Functions / S3
```

### Redeploy Frontend

```cmd
powershell Compress-Archive -Path esg-chat-app\frontend\* -DestinationPath deploy\frontend.zip -Force
aws amplify create-deployment --app-id d337jqli3ubqmk --branch-name main --region us-east-1
REM Then: curl -T deploy\frontend.zip "UPLOAD_URL" && aws amplify start-deployment ...
```

---

## Progress Tracker

| Day | Task | Status |
|-----|------|--------|
| D1 | AWS Account Setup & IAM | ✅ Complete |
| D2 | Synthetic Data Generation | ✅ Complete |
| D3 | Athena DDL Setup | ✅ Complete |
| D4 | Glue ETL — Scope 1 | ✅ Complete |
| D5 | Glue ETL — Scope 2 + Scope 3 | ✅ Complete |
| D6 | Glue ETL — Aggregation | ✅ Complete |
| D7 | Data Layer Checkpoint | ✅ Complete |
| D8 | Bedrock Knowledge Base | ✅ Complete |
| D9 | Prompt Engineering | ✅ Complete |
| D10 | Lambda #1 — ValidateInput | ✅ Deployed |
| D11 | Lambda #2 — AthenaQuery | ✅ Deployed |
| D12 | Lambda #3 — SectionGen | ✅ Deployed |
| D13 | Lambda #4 — Validation | ✅ Deployed |
| D14 | Lambda #5 — AssemblyDoc | ✅ Deployed |
| D15 | Step Functions | ✅ Deployed |
| D21 | Bedrock Agent Setup | ✅ Complete |
| D22 | Amplify Chat Frontend | ✅ Deployed |
| D23 | Agent Tools Lambda | ✅ Deployed |
| D24 | Integration Test | ✅ Working (download URL fix pending) |
| D7 | Data Layer Checkpoint | ⏳ Pending |
