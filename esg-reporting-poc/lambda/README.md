# Lambda Functions Reference

This directory contains all AWS Lambda functions for the ESG Reporting POC backend system.

---

## 📦 Function Overview

| Function | Purpose | Trigger | Runtime | Timeout |
|---------|---------|---------|---------|---------|
| **validate_input** | Validates report generation requests | Step Functions | Python 3.12 | 10s |
| **section_gen** | Generates ESG report sections using Bedrock | Step Functions (Map) | Python 3.12 | 600s |
| **filter_sections** | Filters sections for double materiality | Step Functions | Python 3.12 | 30s |
| **assembly_doc** | Assembles DOCX + PPTX reports | Step Functions | Python 3.12 | 300s |
| **validation** | Validates final report structure | Step Functions | Python 3.12 | 30s |
| **review_handler** | Human review callback (not implemented) | Step Functions | Python 3.12 | 10s |
| **status_check** | Returns report generation status | API Gateway | Python 3.12 | 10s |
| **history** | Returns report generation history | API Gateway | Python 3.12 | 10s |
| **athena_query** | Executes Athena queries on ESG data | API Gateway | Python 3.12 | 60s |
| **dashboard_data** | Returns analytics dashboard data | API Gateway | Python 3.12 | 30s |

---

## 🔧 Function Details

### 1. validate_input

**Path:** `validate_input/handler.py`

**Purpose:** Validates incoming report generation requests before starting Step Functions execution.

**Input:**
```json
{
  "reporting_year": 2024,
  "framework": "GRI_305",
  "revenue_idr_billion": 92000
}
```

**Output:** Same payload (passes through if valid), or raises error if invalid.

**Validation Rules:**
- `reporting_year` must be 2023 or 2024
- `framework` must be one of: `GRI_305`, `IFRS_S2`, `CSRD_ESRS_E1`, `OJK_PSPK`, `MULTI_FRAMEWORK`
- `revenue_idr_billion` must be positive number

**Deployment:**
```bash
cd validate_input
zip -r ../../../deploy/validate_input.zip handler.py
aws lambda update-function-code --function-name esg-validate-input --zip-file fileb://../../deploy/validate_input.zip --region ap-southeast-1
```

---

### 2. section_gen

**Path:** `section_gen/handler.py`

**Purpose:** Generates individual ESG report sections using Amazon Bedrock (Claude 3.5 Sonnet).

**Step Functions Map State:** Processes 9 sections in parallel (or 10 if double materiality included).

**Input:**
```json
{
  "section_id": "GRI_305_SCOPE1",
  "reporting_year": 2024,
  "framework": "GRI_305",
  "revenue_idr_billion": 92000
}
```

**Output:**
```json
{
  "section_id": "GRI_305_SCOPE1",
  "section_content": "# GRI 305-1: Direct (Scope 1) GHG Emissions\n\n...",
  "metadata": {
    "tokens_used": 1234,
    "generation_time_seconds": 45.2
  }
}
```

**Sections Generated:**
- **GRI_305:** SCOPE1, SCOPE2, SCOPE3, INTENSITY, METHODOLOGY
- **IFRS_S2:** STRATEGY_RISKS, GOVERNANCE, METRICS, PCAF_FINANCED_EMISSIONS
- **CSRD_ESRS_E1:** CLIMATE_STRATEGY, EMISSION_TARGETS, SCOPE1_2, SCOPE3_FINANCED
- **OJK_PSKP:** CLIMATE_RISK_GOVERNANCE, GHG_INVENTORY, FINANCED_EMISSIONS_FI
- **MULTI_FRAMEWORK:** All 9 sections above
- **DOUBLE_MATERIALITY:** (Optional) Added when framework = MULTI_FRAMEWORK

**Deployment:**
```bash
cd section_gen
zip -r ../../../deploy/section_gen.zip handler.py
aws lambda update-function-code --function-name esg-section-gen --zip-file fileb://../../deploy/section_gen.zip --region ap-southeast-1
```

---

### 3. filter_sections

**Path:** `filter_sections/handler.py`

**Purpose:** Filters generated sections based on double materiality analysis (currently returns all sections).

**Input:**
```json
{
  "sections": [
    {"section_id": "GRI_305_SCOPE1", "section_content": "..."},
    {"section_id": "IFRS_S2_STRATEGY_RISKS", "section_content": "..."}
  ],
  "reporting_year": 2024
}
```

**Output:** Same array of sections (no filtering logic yet).

**Deployment:**
```bash
cd filter_sections
zip -r ../../../deploy/filter_sections.zip handler.py
aws lambda update-function-code --function-name esg-filter-sections --zip-file fileb://../../deploy/filter_sections.zip --region ap-southeast-1
```

---

### 4. assembly_doc

**Path:** `assembly_doc/handler.py`

**Purpose:** Assembles final DOCX and PPTX reports from generated sections.

**Input:**
```json
{
  "sections": [...],
  "framework": "MULTI_FRAMEWORK",
  "reporting_year": 2024,
  "revenue_idr_billion": 92000,
  "execution_id": "exec_abc123"
}
```

**Output:**
```json
{
  "docx_s3_key": "reports/MULTI_FRAMEWORK_2024_exec_abc123.docx",
  "pptx_s3_key": "reports/MULTI_FRAMEWORK_2024_exec_abc123.pptx",
  "bucket": "esg-reporting-output-bucket",
  "download_url": "https://...",
  "download_url_pptx": "https://..."
}
```

**DOCX Structure:**
- Title page with institution logo
- Executive summary
- Table of contents
- All sections (unified formatting)
- OJK regulatory table (for OJK_PSPK framework)
- Management sign-off page

**PPTX Structure (MULTI_FRAMEWORK only):**
- 4 slides with template-based design
- Scope 1/2/3 emissions summary
- PCAF financed emissions breakdown
- Key metrics visualization

**Dependencies:** Requires Lambda layer with `python-docx`, `python-pptx`, `matplotlib`

**Deployment:**
```bash
cd assembly_doc
zip -r ../../../deploy/assembly_doc.zip handler.py
aws lambda update-function-code --function-name esg-assembly-doc --zip-file fileb://../../deploy/assembly_doc.zip --region ap-southeast-1
```

---

### 5. validation

**Path:** `validation/handler.py`

**Purpose:** Validates final report structure and content quality.

**Input:**
```json
{
  "docx_s3_key": "reports/...",
  "pptx_s3_key": "reports/...",
  "sections": [...]
}
```

**Output:**
```json
{
  "validation_status": "PASSED",
  "issues": [],
  "report_metadata": {
    "total_sections": 9,
    "total_pages": 42,
    "word_count": 8500
  }
}
```

**Validation Checks:**
- All required sections present
- DOCX file readable
- PPTX file readable (if exists)
- No empty sections

**Deployment:**
```bash
cd validation
zip -r ../../../deploy/validation.zip handler.py
aws lambda update-function-code --function-name esg-validation --zip-file fileb://../../deploy/validation.zip --region ap-southeast-1
```

---

### 6. review_handler

**Path:** `review_handler/handler.py`

**Purpose:** Placeholder for human review callback (not implemented yet).

**Deployment:**
```bash
cd review_handler
zip -r ../../../deploy/review_handler.zip handler.py
aws lambda update-function-code --function-name esg-review-handler --zip-file fileb://../../deploy/review_handler.zip --region ap-southeast-1
```

---

### 7. status_check

**Path:** `status_check/handler.py`

**Purpose:** Returns status of Step Functions execution for report generation.

**API Endpoint:** `GET /status?execution_id=<id>`

**Response:**
```json
{
  "status": "SUCCEEDED",
  "execution_id": "exec_abc123",
  "start_time": "2024-06-15T03:00:00Z",
  "end_time": "2024-06-15T03:08:23Z",
  "output": {
    "download_url": "https://...",
    "download_url_pptx": "https://...",
    "framework": "MULTI_FRAMEWORK",
    "reporting_year": 2024
  }
}
```

**Status Values:**
- `RUNNING` — Report generation in progress
- `SUCCEEDED` — Report completed, download URLs available
- `FAILED` — Generation failed, check error message

**Deployment:**
```bash
cd status_check
zip -r ../../../deploy/status_check.zip handler.py
aws lambda update-function-code --function-name esg-status-check --zip-file fileb://../../deploy/status_check.zip --region ap-southeast-1
```

---

### 8. history

**Path:** `history/handler.py`

**Purpose:** Returns list of all report generation executions (last 30 days).

**API Endpoint:** `GET /history`

**Response:**
```json
{
  "executions": [
    {
      "execution_id": "exec_abc123",
      "status": "SUCCEEDED",
      "framework": "MULTI_FRAMEWORK",
      "reporting_year": 2024,
      "start_time": "2024-06-15T03:00:00Z"
    }
  ]
}
```

**Deployment:**
```bash
cd history
zip -r ../../../deploy/history.zip handler.py
aws lambda update-function-code --function-name esg-history --zip-file fileb://../../deploy/history.zip --region ap-southeast-1
```

---

### 9. athena_query

**Path:** `athena_query/handler.py`

**Purpose:** Executes Athena queries on ESG data tables (emissions, portfolio, social metrics).

**API Endpoint:** `POST /athena/query`

**Input:**
```json
{
  "query": "SELECT * FROM esg_emissions WHERE year = 2024",
  "database": "esg_reporting_db"
}
```

**Response:**
```json
{
  "query_execution_id": "q123...",
  "status": "SUCCEEDED",
  "results": [
    {"scope": 1, "emissions_tco2e": 1234.5},
    {"scope": 2, "emissions_tco2e": 5678.9}
  ]
}
```

**Deployment:**
```bash
cd athena_query
zip -r ../../../deploy/athena_query.zip handler.py
aws lambda update-function-code --function-name esg-athena-query --zip-file fileb://../../deploy/athena_query.zip --region ap-southeast-1
```

---

### 10. dashboard_data

**Path:** `dashboard_data/handler.py`

**Purpose:** Returns pre-aggregated analytics data for dashboard (14 charts + 6 KPIs).

**API Endpoint:** `GET /dashboard-data?refresh=false`

**Query Parameters:**
- `refresh=true` — Force Athena refresh (costs ~$0.01 per query)
- `refresh=false` (default) — Use S3 cached results (free)

**Response:**
```json
{
  "kpis": {
    "total_scope1": 1234.5,
    "total_scope2": 5678.9,
    "total_scope3": 987654.3,
    "portfolio_size_billion": 125000,
    "emission_intensity": 7.9,
    "pcaf_avg_score": 4.2
  },
  "charts": {
    "emissions_by_scope": [...],
    "intensity_trends": [...],
    "pcaf_distribution": [...],
    "financed_by_sector": [...],
    "gender_diversity": [...],
    "training_hours": [...]
  }
}
```

**Data Sources:**
1. S3 cache: `s3://esg-athena-results/dashboard-cache/latest.json`
2. Athena refresh: Queries 6 tables (emissions, portfolio, social, sectors, etc.)

**Deployment:**
```bash
cd dashboard_data
zip -r ../../../deploy/dashboard_data.zip handler.py
aws lambda update-function-code --function-name esg-dashboard-data --zip-file fileb://../../deploy/dashboard_data.zip --region ap-southeast-1
```

---

## 🏗️ Lambda Layer

All functions requiring document generation use a shared Lambda layer.

**Layer Contents:**
- `python-docx` (DOCX generation)
- `python-pptx` (PPTX generation)
- `matplotlib` (Chart rendering in PPTX)
- `Pillow` (Image handling)

**Build Layer:**
```bash
cd ../deploy/layer
pip install -t python python-docx python-pptx matplotlib pillow
zip -r ../layer.zip python/
```

**Deploy Layer:**
```bash
aws lambda publish-layer-version --layer-name esg-reporting-layer --zip-file fileb://deploy/layer.zip --compatible-runtimes python3.12 --region ap-southeast-1
```

**Attach to Functions:**
```bash
aws lambda update-function-configuration --function-name esg-assembly-doc --layers arn:aws:lambda:ap-southeast-1:123456789012:layer:esg-reporting-layer:1
```

---

## 🔐 IAM Permissions

All Lambda functions require the following base permissions:

```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": [
    "arn:aws:logs:ap-southeast-1:*:*",
    "arn:aws:s3:::esg-reporting-output-bucket/*",
    "arn:aws:s3:::esg-athena-results/*"
  ]
}
```

**Additional permissions by function:**

| Function | Additional Permissions |
|---------|----------------------|
| **section_gen** | `bedrock:InvokeModel` on Claude 3.5 Sonnet |
| **status_check** | `states:DescribeExecution`, `states:GetExecutionHistory` |
| **history** | `states:ListExecutions` |
| **athena_query** | `athena:StartQueryExecution`, `athena:GetQueryExecution`, `athena:GetQueryResults`, `glue:GetTable`, `glue:GetPartitions` |
| **dashboard_data** | Same as `athena_query` |

---

## 🧪 Testing

### Test Locally (Docker Lambda Runtime)

```bash
docker run --rm -v $(pwd):/var/task amazon/aws-lambda-python:3.12 python handler.py
```

### Test in AWS (CLI)

```bash
aws lambda invoke --function-name esg-section-gen --payload file://test_payload.json --region ap-southeast-1 output.json
cat output.json
```

### Example Test Payload (`test_payload.json`)

```json
{
  "section_id": "GRI_305_SCOPE1",
  "reporting_year": 2024,
  "framework": "GRI_305",
  "revenue_idr_billion": 92000
}
```

---

## 📊 Cost Estimates (per report generation)

| Function | Avg Duration | Memory | Cost per Invocation | Invocations | Total |
|---------|-------------|--------|---------------------|-------------|-------|
| validate_input | 0.5s | 128 MB | $0.000001 | 1 | $0.000001 |
| section_gen | 45s | 512 MB | $0.0015 | 9 | $0.0135 |
| filter_sections | 1s | 256 MB | $0.000002 | 1 | $0.000002 |
| assembly_doc | 30s | 1024 MB | $0.005 | 1 | $0.005 |
| validation | 2s | 256 MB | $0.000004 | 1 | $0.000004 |
| **Total Lambda Cost** | | | | | **~$0.02** |

*Note: Bedrock API costs (~$0.10 per report) dominate Lambda costs.*

---

## 🔗 Related Documentation

- **Backend Architecture:** `../README.md`
- **Agent Setup:** `../agent/README.md`
- **Frontend:** `../../esg-chat-app-react/README.md`
- **Root README:** `../../README.md`

---

**Maintained by:** Tokaicom Mitra Indonesia (Tokai Group)  
**Last Updated:** June 15, 2026
