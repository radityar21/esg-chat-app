# ESG Reporting System - Infrastructure Specification

**Tokaicom Mitra Indonesia (Tokai Group)**  
**Version:** 1.1  
**Last Updated:** June 15, 2026  
**Region:** us-east-1 (N. Virginia) — current POC deployment  
**Crosschecked against:** IMPLEMENTATION_CHANGELOG (91 deviations), INFRASTRUCTURE_REFERENCE, SPEC_AMENDMENTS (76 items), VALIDATION_FALSE_POSITIVES

---

## 📋 Table of Contents

1. [Infrastructure Overview](#infrastructure-overview)
2. [IAM Roles & Policies](#iam-roles--policies)
3. [Lambda Functions](#lambda-functions)
4. [Step Functions](#step-functions)
5. [API Gateway](#api-gateway)
6. [Amazon Bedrock](#amazon-bedrock)
7. [S3 Buckets](#s3-buckets)
8. [Glue & Athena](#glue--athena)
9. [AWS Amplify](#aws-amplify)
10. [Network & Security](#network--security)
11. [Monitoring & Logging](#monitoring--logging)
12. [Cost Analysis](#cost-analysis)
13. [Known Issues & Validation False Positives](#known-issues--validation-false-positives)
14. [Disaster Recovery](#disaster-recovery)
15. [Performance Benchmarks](#performance-benchmarks)

---

## Infrastructure Overview

### AWS Account

| Property | Value |
|----------|-------|
| Account ID | `061039769766` |
| Region | `us-east-1` (N. Virginia) |
| Environment | POC |
| Tags | `Project=ESG`, `Env=POC`, `Team=Sustainability` |

### Region Decision

| Option | Region | Status | Notes |
|--------|--------|--------|-------|
| Current (POC) | us-east-1 | ✅ Active | CloudShell available, all Bedrock models accessible |
| Target (Prod) | ap-southeast-1 | 🔄 Future | Low latency for Indonesia, data residency compliance |
| Original Spec | ap-southeast-3 (Jakarta) | ❌ Rejected | CloudShell unavailable, limited Bedrock models |

### Complete Resource List

| Resource Type | Name | Purpose | Dependencies |
|--------------|------|---------|--------------|
| **IAM Role** | ESGGlueRole | Glue ETL jobs | - |
| **IAM Role** | ESGLambdaRole | All Lambda functions (single role, POC) | - |
| **IAM Role** | ESGStepFunctionsRole | Step Functions execution | - |
| **S3 Bucket** | esg-data-raw-061039769766 | Raw zone — source data as ingested | - |
| **S3 Bucket** | esg-data-curated-061039769766 | Curated zone — ETL-computed GHG | - |
| **S3 Bucket** | esg-data-aggregated-061039769766 | Aggregated zone — report-ready metrics | - |
| **S3 Bucket** | esg-output-reports-061039769766 | Generated DOCX reports | - |
| **S3 Bucket** | esg-kb-documents-061039769766 | Knowledge Base documents + prompts | - |
| **S3 Bucket** | esg-athena-results-061039769766 | Athena query results | - |
| **Lambda** | esg-validate-input | Input validation (REQ-SFN-03) | ESGLambdaRole |
| **Lambda** | esg-athena-query | Single-call Athena data fetch (incl. HR) | ESGLambdaRole, Athena |
| **Lambda** | esg-section-gen | AI section generation (Bedrock + KB RAG) | ESGLambdaRole, Bedrock, KB |
| **Lambda** | esg-filter-sections | Section filtering (SFN JSONPath workaround) | ESGLambdaRole |
| **Lambda** | esg-validation | 21-rule output validation (§7) | ESGLambdaRole |
| **Lambda** | esg-review-handler | Human review callback (blocked by SCP) | ESGLambdaRole |
| **Lambda** | esg-assembly-doc | DOCX assembly (§8) | ESGLambdaRole, Layer |
| **Lambda** | esg-status-check | Execution status API | ESGLambdaRole, SFN |
| **Lambda** | esg-history | Execution history API | ESGLambdaRole, SFN |
| **Lambda** | esg-dashboard-data | Analytics dashboard data (S3 cache + Athena) | ESGLambdaRole, Athena |
| **Lambda** | esg-agent-tools | Bedrock Agent action group (4 tools) | ESGLambdaRole, SFN, S3 |
| **Lambda** | esg-chat-proxy | API GW → Bedrock Agent proxy | ESGLambdaRole, Bedrock |
| **Lambda Layer** | esg-python-docx:2 | python-docx + lxml (Linux x86_64) | - |
| **Step Functions** | ESGReportGenerationStateMachine | Report generation orchestration | ESGStepFunctionsRole |
| **API Gateway** | ESG-Chat-API (olj4tuggm1) | REST API (4 endpoints) | Lambdas |
| **Bedrock Agent** | ESGReportAgent (MBERNIQMBG) | Chat assistant | ESGBedrockAgentRole |
| **Bedrock KB** | ESG-Framework-KB (WVREXI1LEI) | ESG framework docs (RAG) | S3, OpenSearch Serverless |
| **SNS Topic** | ESG-HumanReview | Validation failure notifications | - |
| **SNS Topic** | ESG-ReportComplete | Report completion notifications | - |
| **Glue Job** | esg-etl-scope1-direct | Scope 1 GHG calculation | ESGGlueRole, S3 |
| **Glue Job** | esg-etl-scope2-indirect | Scope 2 GHG calculation | ESGGlueRole, S3 |
| **Glue Job** | esg-etl-scope3-pcaf | Scope 3 PCAF calculation | ESGGlueRole, S3 |
| **Glue Job** | esg-etl-aggregation | Annual aggregation | ESGGlueRole, S3 |
| **Glue Database** | esg_raw | Raw data tables | - |
| **Glue Database** | esg_curated | ETL-processed data | - |
| **Glue Database** | esg_aggregated | Report-ready aggregations | - |
| **Amplify App** | esg-reporting-dashboard (d337jqli3ubqmk) | React frontend | API Gateway |

**Total Resources:** ~40

---

## IAM Roles & Policies

> Note: POC uses single `ESGLambdaRole` for all functions. Production should use separate roles per function (per spec §11).

### 1. ESGLambdaRole (Single Role for All Lambdas — POC)

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**Managed Policies:**
- `arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole`

**Inline Policy — ESGLambdaAccess:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "s3:DeleteObject",
        "s3:GetBucketLocation",
        "s3:PutObjectTagging"
      ],
      "Resource": [
        "arn:aws:s3:::esg-data-raw-061039769766",
        "arn:aws:s3:::esg-data-raw-061039769766/*",
        "arn:aws:s3:::esg-data-curated-061039769766",
        "arn:aws:s3:::esg-data-curated-061039769766/*",
        "arn:aws:s3:::esg-data-aggregated-061039769766",
        "arn:aws:s3:::esg-data-aggregated-061039769766/*",
        "arn:aws:s3:::esg-output-reports-061039769766",
        "arn:aws:s3:::esg-output-reports-061039769766/*",
        "arn:aws:s3:::esg-kb-documents-061039769766",
        "arn:aws:s3:::esg-kb-documents-061039769766/*",
        "arn:aws:s3:::esg-athena-results-061039769766",
        "arn:aws:s3:::esg-athena-results-061039769766/*"
      ]
    },
    {
      "Sid": "BedrockInvokeModel",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:*::inference-profile/*"
      ]
    },
    {
      "Sid": "BedrockKnowledgeBase",
      "Effect": "Allow",
      "Action": [
        "bedrock:Retrieve",
        "bedrock:RetrieveAndGenerate"
      ],
      "Resource": "arn:aws:bedrock:us-east-1:061039769766:knowledge-base/*"
    },
    {
      "Sid": "BedrockAgent",
      "Effect": "Allow",
      "Action": "bedrock:InvokeAgent",
      "Resource": "arn:aws:bedrock:us-east-1:061039769766:agent-alias/*"
    },
    {
      "Sid": "AthenaAccess",
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:StopQueryExecution"
      ],
      "Resource": "arn:aws:athena:us-east-1:061039769766:workgroup/esg-reporting-workgroup"
    },
    {
      "Sid": "GlueDataCatalog",
      "Effect": "Allow",
      "Action": [
        "glue:GetTable",
        "glue:GetTables",
        "glue:GetDatabase",
        "glue:GetDatabases",
        "glue:GetPartitions"
      ],
      "Resource": [
        "arn:aws:glue:us-east-1:061039769766:catalog",
        "arn:aws:glue:us-east-1:061039769766:database/esg_raw",
        "arn:aws:glue:us-east-1:061039769766:database/esg_curated",
        "arn:aws:glue:us-east-1:061039769766:database/esg_aggregated",
        "arn:aws:glue:us-east-1:061039769766:table/esg_raw/*",
        "arn:aws:glue:us-east-1:061039769766:table/esg_curated/*",
        "arn:aws:glue:us-east-1:061039769766:table/esg_aggregated/*"
      ]
    },
    {
      "Sid": "StepFunctionsAccess",
      "Effect": "Allow",
      "Action": [
        "states:StartExecution",
        "states:DescribeExecution",
        "states:GetExecutionHistory",
        "states:ListExecutions"
      ],
      "Resource": [
        "arn:aws:states:us-east-1:061039769766:stateMachine:ESGReportGenerationStateMachine",
        "arn:aws:states:us-east-1:061039769766:execution:ESGReportGenerationStateMachine:*"
      ]
    },
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:061039769766:table/ESG*"
    }
  ]
}
```

---

### 2. ESGStepFunctionsRole

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "states.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**Inline Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaInvoke",
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-east-1:061039769766:function:esg-*"
    },
    {
      "Sid": "SNSPublish",
      "Effect": "Allow",
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:061039769766:ESG-*"
    },
    {
      "Sid": "GlueJobs",
      "Effect": "Allow",
      "Action": [
        "glue:StartJobRun",
        "glue:GetJobRun"
      ],
      "Resource": "arn:aws:glue:us-east-1:061039769766:job/esg-*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogDelivery",
        "logs:GetLogDelivery",
        "logs:UpdateLogDelivery",
        "logs:DeleteLogDelivery",
        "logs:ListLogDeliveries",
        "logs:PutResourcePolicy",
        "logs:DescribeResourcePolicies",
        "logs:DescribeLogGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

---

### 3. ESGGlueRole

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "glue.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**Managed Policies:**
- `arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole`

**Inline Policy — S3 access for raw, curated, aggregated buckets + CloudWatch Logs**

---

## Lambda Functions

### Function Specifications (Actual Deployed)

| Function Name | Runtime | Memory | Timeout | Layer | Key Dependencies |
|--------------|---------|--------|---------|-------|-----------------|
| esg-validate-input | Python 3.11 | 256 MB | 30s | No | — |
| esg-athena-query | Python 3.11 | 512 MB | 60s | No | Athena (5 queries incl. HR metrics) |
| esg-section-gen | Python 3.11 | 1024 MB | 120s | No | Bedrock Claude 4.5, KB RAG |
| esg-filter-sections | Python 3.11 | 256 MB | 30s | No | — |
| esg-validation | Python 3.11 | 512 MB | 60s | No | 21 validation rules |
| esg-review-handler | Python 3.11 | 256 MB | 30s | No | Function URL (blocked by SCP) |
| esg-assembly-doc | Python 3.11 | 1024 MB | 120s | esg-python-docx:2 | python-docx, lxml |
| esg-status-check | Python 3.11 | 256 MB | 30s | No | Step Functions API |
| esg-history | Python 3.11 | 256 MB | 30s | No | Step Functions API |
| esg-dashboard-data | Python 3.11 | 512 MB | 60s | No | Athena + S3 cache |
| esg-agent-tools | Python 3.11 | 256 MB | 30s | No | SFN + S3 presigned URLs |
| esg-chat-proxy | Python 3.11 | 256 MB | 30s | No | bedrock:InvokeAgent |

### Key Lambda Details

#### esg-athena-query (Data Layer)

Executes 5 Athena queries and returns consolidated data:

| Query | Source Table | Purpose |
|-------|-------------|---------|
| QUERY_GHG_SUMMARY | esg_aggregated.ghg_summary_annual | Scope 1/2/3 totals, intensity, natgas/diesel breakdown |
| QUERY_PRIOR_YEAR | esg_aggregated.ghg_summary_annual | Prior year for YoY comparison |
| QUERY_PCAF_SECTORS | esg_aggregated.pcaf_by_sector | Financed emissions by sector |
| QUERY_SCOPE1_FACILITIES | esg_aggregated.scope1_by_facility | Top 10 emitting facilities |
| QUERY_HR_METRICS | esg_raw.hr_metrics | Workforce data (Social pillar) |

**HR Metrics pre-computation:**
- `hiring_rate_pct` = new_hires / fte_total × 100
- `female_headcount` = fte_total × female_pct / 100
- `male_headcount` = fte_total - female_headcount
- YoY changes: headcount, turnover, training hours, female %, mgmt female %

#### esg-section-gen (Report Generation)

**Model:** `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (cross-region inference profile)

**TEMPLATE_MAP (8 sections):**
| Template Key | Template File | RAG Query |
|-------------|---------------|-----------|
| scope1 | templates/scope1_template.txt | GRI 305-1 direct Scope 1 emissions |
| scope2 | templates/scope2_template.txt | GRI 305-2 indirect Scope 2 emissions |
| scope3_pcaf | templates/scope3_pcaf_template.txt | Scope 3 PCAF financed emissions |
| intensity | templates/intensity_template.txt | GHG emission intensity |
| methodology | templates/methodology_template.txt | GHG accounting methodology |
| summary | templates/summary_template.txt | Executive summary |
| social | templates/social_template.txt | **[W5]** GRI 2-7, 401-1, 404-1, 405-1, 406-1 |
| (framework-specific) | Various overlays | CSRD ESRS E1, OJK PSPK, etc. |

**Knowledge Base RAG:**
- KB ID: `WVREXI1LEI`
- Filter: `orAll` for cross-framework sections (e.g., scope3_pcaf → GRI_305 + PCAF)
- Token cap: 700 chars
- Min relevance: 0.40

#### esg-assembly-doc (Document Generation)

**SECTION_ORDER per framework:**
- GRI_305: scope1, scope2, scope3_pcaf, intensity, **social**, methodology, summary
- IFRS_S2: governance, strategy_risks, metrics, pcaf, intensity, **social**, summary
- CSRD_ESRS_E1: climate_strategy, metrics, pcaf, intensity, **social**, methodology, summary
- OJK_PSPK: ghg_inventory, pcaf, intensity, **social**, methodology, summary
- MULTI_FRAMEWORK: All sections from all frameworks

**Document styling:**
- Font: Arial 11pt body, Arial Bold headings
- Colors: H1=#1B3A6B, H2=#3D6094
- Paper: A4 (8.27×11.69 inches)
- Alignment: Justified
- KMS encryption on S3 upload
- 8 S3 object tags per REQ-TRACE-05
- GRI Content Index: 10 rows (5 environmental + 5 social)

#### esg-dashboard-data (Analytics)

**Endpoint:** `GET /dashboard-data` (optional `?refresh=true`)
- Default: Read from S3 cache (`dashboard-cache/latest.json`) — $0 cost
- Refresh: Query Athena → update S3 → return fresh data — ~$0.01
- 5 queries: GHG summary, prior year, PCAF sectors, Scope 1 facilities, HR metrics
- Response: `{reporting_year, last_updated, ghg_summary, prior_year_summary, pcaf_sectors, scope1_facilities, hr_metrics}`

### Lambda Layer: esg-python-docx

| Property | Value |
|----------|-------|
| Layer Name | `esg-python-docx` |
| Current Version | `:2` |
| Compatible Runtime | python3.11 |
| Contents | python-docx + lxml (Linux x86_64 binaries) |
| S3 Location | `s3://esg-data-raw-061039769766/lambda-layers/python-docx-layer.zip` |

**⚠️ CRITICAL:** Must be built on Linux (CloudShell). Windows produces incompatible `.pyd` files.

```bash
# Build in CloudShell (us-east-1)
mkdir -p /tmp/layer/python
pip install python-docx -t /tmp/layer/python \
  --platform manylinux2014_x86_64 --only-binary=:all: \
  --python-version 3.11 --implementation cp
cd /tmp/layer && zip -r /tmp/python-docx-layer.zip python/
aws s3 cp /tmp/python-docx-layer.zip s3://esg-data-raw-061039769766/lambda-layers/
aws lambda publish-layer-version --layer-name esg-python-docx \
  --content S3Bucket=esg-data-raw-061039769766,S3Key=lambda-layers/python-docx-layer.zip \
  --compatible-runtimes python3.11 --region us-east-1
```

---

## Step Functions

### State Machine: ESGReportGenerationStateMachine

| Property | Value |
|----------|-------|
| ARN | `arn:aws:states:us-east-1:061039769766:stateMachine:ESGReportGenerationStateMachine` |
| Type | STANDARD |
| Role | ESGStepFunctionsRole |
| Active ASL | `esg_orchestrator.asl.json` (auto-approve mode) |
| Manual Review ASL | `esg_orchestrator_human_review_manual.asl.json` |

### State Machine Flow

```
ValidateInput → WaitForGlueJobs (Parallel: Scope1+2+3)
  → TriggerAggregation → QueryAthena (GHG + PCAF + HR metrics)
  → GenerateSections (Map, MaxConcurrency:3)
      [per section: SectionGen → Validation → Choice]
        PASS → Accumulate
        WARN → AccumulateWithWarning
        RETRY → Re-gen once → Re-validate
        FAIL_NO_RETRY → Auto-Approve (SNS notify) → AccumulateWithWarning
  → FilterSections (esg-filter-sections Lambda)
  → AssembleDocument → NotifyCompletion (ResultPath: $.sns_result)
  → Success (Pass type, outputs $.assembly_result)
```

**Key Design Decisions:**
- `esg-filter-sections` Lambda exists because Step Functions doesn't support JSONPath filter expressions
- Success state is a `Pass` type (not `Succeed`) to output `assembly_result` for agent's `download_report` tool
- `NotifyCompletion` uses `ResultPath: "$.sns_result"` to preserve assembly_result in state
- Glue parameters passed via `States.Format` with `--REPORTING_YEAR`
- SNS Message uses `States.JsonToString()` (SNS requires string, not JSON object)
- ASL deployed via S3 (Windows `file://` encoding incompatible)

### Execution Times

| Framework | Sections | Avg Time | Max Time |
|-----------|----------|----------|----------|
| GRI_305 | 7 (incl. Social) | 3-5 min | 5 min |
| IFRS_S2 | 7 | 4 min | 6 min |
| CSRD_ESRS_E1 | 7 | 4 min | 6 min |
| OJK_PSPK | 6 | 4 min | 6 min |
| MULTI_FRAMEWORK | 15 | 8-12 min | 15 min |

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
      {"template_id": "intensity", "framework": "GRI_305"},
      {"template_id": "social", "framework": "GRI_305"},
      {"template_id": "methodology", "framework": "GRI_305"},
      {"template_id": "summary", "framework": "NONE"}
    ]
  }' --region us-east-1
```

---

## API Gateway

### REST API: ESG-Chat-API

| Property | Value |
|----------|-------|
| API ID | `olj4tuggm1` |
| Endpoint | `https://olj4tuggm1.execute-api.us-east-1.amazonaws.com/prod` |
| Type | REGIONAL |
| Stage | prod |

### Endpoints (5 total)

| Method | Path | Integration | Purpose |
|--------|------|-------------|---------|
| POST | /chat | Lambda: esg-chat-proxy → Bedrock Agent | Chat with ESG assistant |
| GET | /status | Lambda: esg-status-check | Check report generation status |
| GET | /history | Lambda: esg-history | List all executions |
| GET | /dashboard-data | Lambda: esg-dashboard-data | Get analytics dashboard data |
| OPTIONS | (all) | MOCK | CORS preflight |

### CORS Configuration

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token
```

### Endpoint Response Examples

#### GET /dashboard-data

```json
{
  "reporting_year": 2024,
  "last_updated": "2026-06-15T03:00:00Z",
  "ghg_summary": {
    "scope1_tco2e": 3402.99,
    "scope1_natgas_tco2e": 1199.79,
    "scope1_diesel_tco2e": 2203.20,
    "scope2_location_tco2e": 73451.23,
    "scope2_market_tco2e": 73451.23,
    "scope3_cat15_gross_tco2e": 21976797.30,
    "scope3_cat15_weighted_tco2e": 15280174.00,
    "total_scope123_tco2e": 22053651.52,
    "intensity_per_idr_bn": 239.71,
    "intensity_per_fte": 882.55
  },
  "prior_year_summary": { ... },
  "pcaf_sectors": [ ... ],
  "scope1_facilities": [ ... ],
  "hr_metrics": {
    "fte_total": 24997,
    "female_pct": 42.3,
    "female_mgmt_pct": 26.7,
    "hiring_rate_pct": 10.38,
    "voluntary_turnover_pct": 8.4,
    "training_hours_per_fte": 49.3,
    "discrimination_cases": 2,
    "prior_year": { ... },
    "yoy_changes": {
      "headcount_change_pct": 2.03,
      "turnover_change_pct": -40.66,
      "training_change_pct": -23.13,
      "female_pct_change_pp": -3.88,
      "mgmt_female_pct_change_pp": -1.78
    }
  }
}
```

---

## Amazon Bedrock

### Bedrock Agent: ESGReportAgent

| Property | Value |
|----------|-------|
| Agent Name | ESGReportAgent |
| Agent ID | `MBERNIQMBG` |
| Alias ID | `QIXEJW2TN6` (esg-report-agent-v2) |
| Foundation Model | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (inference profile) |
| Action Group | ESGReportActions |
| Tools Lambda | esg-agent-tools |
| Instructions | `agent/agent_instructions.txt` |
| OpenAPI Schema | `agent/openapi_schema.json` |

### Agent Tools (4 Actions)

| Tool | Method | Parameters | Backend |
|------|--------|------------|---------|
| `generate_report` | POST | reporting_year, framework, revenue_idr_billion | `sfn.start_execution()` |
| `check_status` | POST | execution_arn | `sfn.describe_execution()` |
| `download_report` | POST | execution_arn | `s3.generate_presigned_url()` (1hr, s3v4 sig) |
| `list_available_data` | GET | — | Static response (years, frameworks) |

**Section Templates per Framework (from agent_tools):**

| Framework | Sections |
|-----------|----------|
| GRI_305 | scope1, scope2, scope3_pcaf, intensity, social, methodology, summary |
| IFRS_S2 | governance, strategy_risks, metrics, pcaf, intensity, social, summary |
| CSRD_ESRS_E1 | climate_strategy, metrics, pcaf, intensity, social, methodology, summary |
| OJK_PSPK | ghg_inventory, pcaf, intensity, social, methodology, summary |
| MULTI_FRAMEWORK | All 15 sections across all frameworks |

### Bedrock Knowledge Base: ESG-Framework-KB

| Property | Value |
|----------|-------|
| KB ID | `WVREXI1LEI` |
| Region | us-east-1 |
| Documents Bucket | `esg-kb-documents-061039769766` |
| Embedding Model | Amazon Titan Embeddings V2 (1024 dimensions, floating) |
| Vector Store | OpenSearch Serverless (Quick Create) |
| Active Replicas | Disabled |
| Standby Replicas | Disabled |
| **Chunking Strategy** | **Semantic** |
| Max Sentences per Chunk | 1 |
| Token Size | 700 |
| Similarity Percentile Threshold | 90% |
| Foundation Model (parser) | Claude Sonnet 4.5 |
| Min Relevance Score (retrieval) | **0.40** |

> Note: Semantic chunking produces lower similarity scores than fixed-size chunking. The 0.40 threshold is intentionally lower than the typical 0.65 — setting it higher filters out valid regulatory content.

**KB Filter Logic:** Uses `orAll` filter for cross-framework sections (e.g., `scope3_pcaf` → GRI_305 + PCAF filter).

---

## S3 Buckets

### Bucket Inventory (6 Buckets)

| Bucket Name | Purpose | Versioning | Encryption |
|-------------|---------|------------|-----------|
| `esg-data-raw-061039769766` | Raw zone — source data, scripts, layers | Enabled | AES-256 |
| `esg-data-curated-061039769766` | ETL-computed GHG calculations | Enabled | AES-256 |
| `esg-data-aggregated-061039769766` | Report-ready annual metrics + dashboard cache | Enabled | AES-256 |
| `esg-output-reports-061039769766` | Generated DOCX reports | Enabled | KMS |
| `esg-kb-documents-061039769766` | KB docs + prompts + templates | Enabled | AES-256 |
| `esg-athena-results-061039769766` | Athena query results | Enabled | AES-256 |

### S3 Path Convention

```
s3://{bucket}/{zone}/{table}/reporting_year={YYYY}/[reporting_month={MM}/]
```

Hive-style partitioning per REQ-DDL-05.

### Key S3 Locations

| Path | Content |
|------|---------|
| `s3://esg-data-raw-*/energy_consumption/reporting_year=2024/` | Energy data (2,640 rows) |
| `s3://esg-data-raw-*/loan_portfolio/reporting_year=2024/` | Loan data (2,200 rows) |
| `s3://esg-data-raw-*/hr_metrics/reporting_year=2024/` | HR metrics (1 row) |
| `s3://esg-data-raw-*/scripts/` | Glue ETL scripts |
| `s3://esg-data-raw-*/lambda-layers/` | Lambda layer zip |
| `s3://esg-data-raw-*/lambda-code/` | Lambda function zips |
| `s3://esg-data-aggregated-*/dashboard-cache/latest.json` | Dashboard cache |
| `s3://esg-output-reports-*/reports/year=2024/{framework}/` | Generated reports |
| `s3://esg-kb-documents-*/prompts/templates/` | Section templates |

---

## Glue & Athena

### Glue Jobs (4 ETL Jobs)

| Job Name | Script | Input | Output | Status |
|----------|--------|-------|--------|--------|
| esg-etl-scope1-direct | glue_job_scope1_ghg.py | esg_raw/energy (complete) | esg_curated/ghg_scope1 | ✅ |
| esg-etl-scope2-indirect | glue_job_scope2_electricity.py | esg_raw/energy (complete) | esg_curated/ghg_scope2 | ✅ |
| esg-etl-scope3-pcaf | glue_job_scope3_pcaf.py | esg_raw/loans (validated) | esg_curated/ghg_scope3_financed | ✅ |
| esg-etl-aggregation | glue_job_aggregation.py | All curated | esg_aggregated/* | ✅ |

**Glue Job Config:** Glue 4.0, G.1X workers × 2, Python 3, `--enable-glue-datacatalog`

**Important:** Glue jobs read S3 directly (`spark.read.parquet` with `basePath`), NOT from Glue Catalog. Schema governance gate validates before processing.

### Athena Configuration

| Property | Value |
|----------|-------|
| Workgroup | `esg-reporting-workgroup` |
| Engine | Athena SQL (Engine v3) |
| Result Location | `s3://esg-athena-results-061039769766/query-results/` |
| Authentication | IAM only |

### Databases & Tables (12 Tables across 3 Databases)

| Database | Table | Partition Key | Description |
|----------|-------|---------------|-------------|
| esg_raw | energy_consumption | reporting_year | 220 facilities × 12 months |
| esg_raw | loan_portfolio | reporting_year | 2,200 borrowers |
| esg_raw | hr_metrics | reporting_year | 1 row per year |
| esg_curated | ghg_scope1 | reporting_year | Per-facility Scope 1 |
| esg_curated | ghg_scope2 | reporting_year | Per-facility Scope 2 |
| esg_curated | ghg_scope3_financed | reporting_year | Per-borrower PCAF |
| esg_aggregated | ghg_summary_annual | reporting_year | Annual totals (14 columns incl. natgas/diesel) |
| esg_aggregated | pcaf_by_sector | reporting_year | PCAF emissions by sector |
| esg_aggregated | scope1_by_facility | reporting_year | Top 10 emitters per year |

**All tables use Partition Projection:**
```
projection.enabled = true
projection.reporting_year.type = integer
projection.reporting_year.range = 2020,2035
parquet.compress = SNAPPY
classification = parquet
```

### Emission Factor Constants

| Constant | Value | Unit | Source |
|----------|-------|------|--------|
| GWP_CH4 | 29.8 | kg CO2e/kg CH4 | IPCC AR6 GWP100 |
| GWP_N2O | 273.0 | kg CO2e/kg N2O | IPCC AR6 GWP100 |
| EF_NATGAS_KGCO2_PER_GJ | 56.10 | kg CO2/GJ | IPCC 2006 |
| EF_DIESEL_KGCO2_PER_L | 2.53763 | kg CO2/L | DEFRA 2025 |
| GRID_EF_PLN_2023 | 0.7886 | kg CO2/kWh | PLN National Grid 2023 |

---

## AWS Amplify

### App: esg-reporting-dashboard

| Property | Value |
|----------|-------|
| App ID | `d337jqli3ubqmk` |
| URL | `https://main.d337jqli3ubqmk.amplifyapp.com` |
| Repository | `https://github.com/radityar21/esg-chat-app` |
| Branch | main |
| Framework | React 18 + Vite 5 + Tailwind CSS 3 + Recharts 2.15 |
| Build Time | 2-3 minutes |
| Deploy Trigger | Push to `main` (auto-deploy) |

### Frontend Pages (5)

| Page | Content |
|------|---------|
| Overview | Stats, recent reports |
| Analytics | 14 charts + 6 KPI cards (10 Environmental, 4 Social) |
| Chat | Bedrock Agent conversation (with auto-polling) |
| Reports | Report history list |
| Reference | Framework documentation |

### Design System

| Element | Value |
|---------|-------|
| Theme | Dark mode (navy #0f172a) |
| Glassmorphism | backdrop-blur-xl, bg-white/[0.02] |
| Accent Colors | Blue (#4f8cf7), Teal (#06d6a0), Purple (#7c5cfc) |
| Typography | Inter font |
| Logo | "Tokaicom Mitra Indonesia (Tokai Group)" |

### Build Configuration (amplify.yml)

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd esg-chat-app-react
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: esg-chat-app-react/dist
    files:
      - '**/*'
  cache:
    paths:
      - esg-chat-app-react/node_modules/**/*
```

### Silent Polling (Chat Feature)

| Feature | Implementation |
|---------|----------------|
| Execution ID detection | Regex: `/Execution ID:\s*([a-f0-9\-]+)/i` |
| Poll interval | 30 seconds |
| Max attempts | 30 (15 min timeout) |
| Status detection | String match: SUCCEEDED/complete → done |
| Download URL | Silent agent call → regex extract URL |
| Indicator | CSS pulse animation + elapsed time |

---

## Network & Security

### Encryption

| Resource | Type | Key |
|----------|------|-----|
| S3 Buckets (5) | Server-side | AES-256 (SSE-S3) |
| S3 Output Reports | Server-side | **KMS** (requires s3v4 signature for presigned URLs) |
| Lambda Env Variables | At rest | AWS-managed key |
| OpenSearch (KB) | At rest | AWS-managed key |

### IAM Design (POC vs Production)

| POC (Current) | Production (Recommended) |
|---------------|--------------------------|
| 1 shared ESGLambdaRole | 5+ separate roles per function |
| Wildcard Bedrock model access | Specific model ARN only |
| All S3 buckets in one policy | Least-privilege per function |

---

## Monitoring & Logging

### CloudWatch Log Groups

| Log Group | Retention |
|-----------|-----------|
| /aws/lambda/esg-validate-input | 7 days |
| /aws/lambda/esg-athena-query | 7 days |
| /aws/lambda/esg-section-gen | 30 days |
| /aws/lambda/esg-filter-sections | 7 days |
| /aws/lambda/esg-validation | 7 days |
| /aws/lambda/esg-review-handler | 7 days |
| /aws/lambda/esg-assembly-doc | 7 days |
| /aws/lambda/esg-status-check | 7 days |
| /aws/lambda/esg-history | 7 days |
| /aws/lambda/esg-dashboard-data | 7 days |
| /aws/lambda/esg-agent-tools | 7 days |
| /aws/lambda/esg-chat-proxy | 7 days |
| /aws/vendedlogs/states/ESGReportGeneration | 30 days |
| /aws/apigateway/esg-chat-api | 7 days |

### CloudWatch Alarms

| Alarm | Metric | Threshold | Action |
|-------|--------|-----------|--------|
| ESG-Lambda-Errors | Lambda Errors | > 5 in 5 min | SNS |
| ESG-StepFunctions-Failed | ExecutionsFailed | > 3 in 1 hour | SNS |
| ESG-API-5XX | 5XXError | > 10 in 5 min | SNS |
| ESG-Section-Gen-Timeout | Duration | > 110s | SNS |

---

## Cost Analysis

### Monthly Cost Breakdown (100 reports/month)

| Service | Usage | Monthly Cost |
|---------|-------|-------------|
| **OpenSearch Serverless (KB)** | 1 OCU × 720 hrs × $0.24 | **$172.80** |
| **Bedrock API** | 100 reports × 8 sections × 12K tokens | **$12.96** |
| **Lambda Compute** | All functions combined | **$2.00** |
| **S3 Storage** | ~500 MB total | **$0.01** |
| **Step Functions** | 100 exec × 15 transitions | **$0.04** |
| **API Gateway** | ~10,000 requests | **$0.04** |
| **Athena** | 10 refreshes × 50MB | **$0.003** |
| **CloudWatch Logs** | 5 GB ingested | **$2.50** |
| **Amplify Hosting** | Free tier | **$0.00** |
| **Glue ETL** | Sporadic runs | **~$1.00** |
| **Total** | | **~$191/month** |

### Cost Optimization

| Strategy | Savings | New Total |
|----------|---------|-----------|
| Switch KB to Aurora Serverless | -$150 | ~$41/month |
| Disable KB entirely (templates only) | -$173 | ~$18/month |
| Reduce CloudWatch retention | -$1.50 | Minimal |
| Aggressive S3 lifecycle (Glacier 90d) | -$0.01 | Minimal |

---

## Known Issues & Validation False Positives

### Validation Layer Issues

> These are calibration issues, NOT data errors. Auto-approve mode is the correct approach for POC.

| Issue ID | Description | Root Cause | Impact | Fix Effort |
|----------|-------------|-----------|--------|------------|
| VAL-NUM-01 | Scientific notation mismatch | Regex extracts `2.19E7` vs float `21976797.3` | LOW | 30 min |
| VAL-NUM-01/03 | LLM-derived percentages flagged | Model calculates `component/total × 100` correctly but result not in source data | LOW | 1 hr |
| VAL-NUM-07 | Table values not in paragraphs | Narrative summarizes, doesn't repeat every table value | LOW | 15 min |
| VAL-NUM-01 | Sector values not in allowed set | `pcaf_sectors` not passed to ValidationFn as source_metrics | MEDIUM | 30 min |

**DI-2 Compliance Note:** Spec rule says "model MUST NOT perform arithmetic." LLM technically derives percentages, but they're mathematically correct and improve report readability. For production: pre-compute all common percentages in aggregation layer.

### Infrastructure Limitations

| Issue | Status | Workaround |
|-------|--------|-----------|
| Human Review Function URL blocked by Org SCP | ⚠️ Blocked | Use auto-approve ASL mode |
| Agent markdown corrupts presigned URLs | ⚠️ Known | Frontend regex strips trailing `)` / `]` |
| Windows `file://` encoding breaks ASL deploy | ⚠️ Known | Upload to S3, deploy from CloudShell |
| Model `claude-3-5-sonnet-20241022-v2:0` deprecated | ✅ Fixed | Migrated to `us.anthropic.claude-sonnet-4-5-20250929-v1:0` |

---

## Disaster Recovery

### Backup Strategy

| Resource | Method | Frequency |
|----------|--------|-----------|
| S3 Buckets | Versioning (enabled on all) | Continuous |
| Lambda Code | Git repository + S3 zips | Per deployment |
| Step Functions ASL | Git repository + S3 | Per update |
| KB Documents | S3 versioning | Continuous |
| Athena DDL | Git-tracked SQL files | Per schema change |

### RTO/RPO

| Scenario | RTO | RPO |
|----------|-----|-----|
| Lambda code corruption | 10 min (redeploy from S3) | Last deployment |
| S3 data loss | 0 min (versioning) | 0 (continuous) |
| Full infrastructure rebuild | 1-2 hours (manual) or 20 min (CDK) | Last Git commit |

---

## Performance Benchmarks

### Latency Targets

| Operation | Target | Actual (P95) |
|-----------|--------|--------------|
| API Gateway → Lambda | < 100ms | 45ms |
| Report Generation (GRI 305, 7 sections) | < 5 min | 3-5 min |
| Report Generation (MULTI, 15 sections) | < 15 min | 8-12 min |
| Dashboard Load (cached) | < 500ms | 200-500ms |
| Dashboard Load (refresh) | < 15s | 8-15s |
| Chat Response (no KB) | < 3s | 2s |
| Chat Response (with KB) | < 5s | 4s |

### Throughput

| Metric | Value |
|--------|-------|
| Concurrent report generations | 10 (Lambda concurrency) |
| API requests/sec | 1,000 (API Gateway limit) |
| Max reports/hour | 60 |
| Frontend bundle size | 593 KB JS (174 KB gzipped) |
| First Contentful Paint | < 1s |

---

## 📚 References

| Document | Purpose |
|----------|---------|
| DEPLOYMENT_GUIDE.md | Step-by-step deployment instructions |
| DEPLOYMENT_SUMMARY.md | Quick reference guide |
| esg-reporting-poc/docs/IMPLEMENTATION_CHANGELOG.md | 91 spec deviations (W1-W6) |
| esg-reporting-poc/docs/INFRASTRUCTURE_REFERENCE.md | Current deployed resource configs |
| esg-reporting-poc/docs/SPEC_AMENDMENTS.md | 76 tracked amendments |
| esg-reporting-poc/docs/VALIDATION_FALSE_POSITIVES.md | Validator calibration issues |

---

**Document Version:** 1.1  
**Last Updated:** June 15, 2026  
**Maintained by:** Tokaicom Mitra Indonesia (Tokai Group)
