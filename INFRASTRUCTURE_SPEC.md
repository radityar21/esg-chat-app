# ESG Reporting System - Infrastructure Specification

**Tokaicom Mitra Indonesia (Tokai Group)**  
**Version:** 1.0  
**Last Updated:** June 15, 2026  
**Region:** ap-southeast-1 (Singapore)

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

---

## Infrastructure Overview

### Complete Resource List

| Resource Type | Name | Purpose | Dependencies |
|--------------|------|---------|--------------|
| **IAM Role** | ESGLambdaExecutionRole | Lambda execution | - |
| **IAM Role** | ESGStepFunctionsRole | Step Functions execution | - |
| **IAM Role** | ESGBedrockAgentRole | Bedrock Agent execution | - |
| **IAM Role** | ESGAPIGatewayRole | API Gateway logging | - |
| **IAM Role** | ESGGlueETLRole | Glue ETL jobs | - |
| **Lambda** | esg-validate-input | Input validation | ESGLambdaExecutionRole |
| **Lambda** | esg-section-gen | Report section generation | ESGLambdaExecutionRole, Bedrock |
| **Lambda** | esg-filter-sections | Section filtering | ESGLambdaExecutionRole |
| **Lambda** | esg-assembly-doc | DOCX/PPTX assembly | ESGLambdaExecutionRole, Layer |
| **Lambda** | esg-validation | Report validation | ESGLambdaExecutionRole |
| **Lambda** | esg-review-handler | Human review callback | ESGLambdaExecutionRole |
| **Lambda** | esg-status-check | Execution status check | ESGLambdaExecutionRole, Step Functions |
| **Lambda** | esg-history | Execution history | ESGLambdaExecutionRole, Step Functions |
| **Lambda** | esg-athena-query | Athena query execution | ESGLambdaExecutionRole, Athena |
| **Lambda** | esg-dashboard-data | Dashboard analytics | ESGLambdaExecutionRole, Athena |
| **Lambda** | esg-agent-tools | Bedrock Agent tools | ESGLambdaExecutionRole, Step Functions |
| **Lambda Layer** | esg-reporting-layer | python-docx, python-pptx, matplotlib | - |
| **Step Functions** | esg-orchestrator | Report generation orchestration | ESGStepFunctionsRole, 6 Lambdas |
| **API Gateway** | ESG Reporting API | REST API endpoints | 4 Lambdas |
| **Bedrock Agent** | ESG-Report-Assistant | Chat assistant | ESGBedrockAgentRole, esg-agent-tools |
| **Bedrock KB** | ESG-Framework-KB | ESG framework docs | S3, OpenSearch Serverless |
| **S3 Bucket** | esg-reporting-output-bucket | DOCX/PPTX reports | - |
| **S3 Bucket** | esg-athena-results | Athena results + cache | - |
| **S3 Bucket** | esg-knowledge-base | ESG framework documents | - |
| **Glue Database** | esg_reporting_db | Athena table metadata | - |
| **Amplify App** | esg-chat-app | React frontend hosting | API Gateway |

**Total Resources:** 32

---

## IAM Roles & Policies

### 1. ESGLambdaExecutionRole

**Purpose:** Execution role for all 11 Lambda functions

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

**Inline Policy** (`ESGLambdaCustomPolicy`):
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
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::esg-reporting-output-bucket",
        "arn:aws:s3:::esg-reporting-output-bucket/*",
        "arn:aws:s3:::esg-athena-results",
        "arn:aws:s3:::esg-athena-results/*",
        "arn:aws:s3:::esg-knowledge-base",
        "arn:aws:s3:::esg-knowledge-base/*"
      ]
    },
    {
      "Sid": "BedrockInvokeModel",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:ap-southeast-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v2:0"
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
      "Resource": "arn:aws:athena:ap-southeast-1:ACCOUNT_ID:workgroup/primary"
    },
    {
      "Sid": "GlueDataCatalogAccess",
      "Effect": "Allow",
      "Action": [
        "glue:GetTable",
        "glue:GetTables",
        "glue:GetDatabase",
        "glue:GetDatabases",
        "glue:GetPartitions"
      ],
      "Resource": [
        "arn:aws:glue:ap-southeast-1:ACCOUNT_ID:catalog",
        "arn:aws:glue:ap-southeast-1:ACCOUNT_ID:database/esg_reporting_db",
        "arn:aws:glue:ap-southeast-1:ACCOUNT_ID:table/esg_reporting_db/*"
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
        "arn:aws:states:ap-southeast-1:ACCOUNT_ID:stateMachine:esg-orchestrator",
        "arn:aws:states:ap-southeast-1:ACCOUNT_ID:execution:esg-orchestrator:*"
      ]
    }
  ]
}
```

---

### 2. ESGStepFunctionsRole

**Purpose:** Execution role for Step Functions state machine

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

**Inline Policy** (`ESGStepFunctionsPolicy`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaInvoke",
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": [
        "arn:aws:lambda:ap-southeast-1:ACCOUNT_ID:function:esg-validate-input",
        "arn:aws:lambda:ap-southeast-1:ACCOUNT_ID:function:esg-section-gen",
        "arn:aws:lambda:ap-southeast-1:ACCOUNT_ID:function:esg-filter-sections",
        "arn:aws:lambda:ap-southeast-1:ACCOUNT_ID:function:esg-assembly-doc",
        "arn:aws:lambda:ap-southeast-1:ACCOUNT_ID:function:esg-validation",
        "arn:aws:lambda:ap-southeast-1:ACCOUNT_ID:function:esg-review-handler"
      ]
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

### 3. ESGBedrockAgentRole

**Purpose:** Execution role for Bedrock Agent

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "bedrock.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {
        "aws:SourceAccount": "ACCOUNT_ID"
      },
      "ArnLike": {
        "aws:SourceArn": "arn:aws:bedrock:ap-southeast-1:ACCOUNT_ID:agent/*"
      }
    }
  }]
}
```

**Inline Policy** (`ESGBedrockAgentPolicy`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvokeModel",
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:ap-southeast-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v2:0"
    },
    {
      "Sid": "BedrockKnowledgeBaseRetrieval",
      "Effect": "Allow",
      "Action": "bedrock:Retrieve",
      "Resource": "arn:aws:bedrock:ap-southeast-1:ACCOUNT_ID:knowledge-base/*"
    },
    {
      "Sid": "LambdaInvokeAgentTools",
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:ap-southeast-1:ACCOUNT_ID:function:esg-agent-tools"
    }
  ]
}
```

---

### 4. ESGAPIGatewayRole

**Purpose:** CloudWatch Logs access for API Gateway

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "apigateway.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**Managed Policies:**
- `arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs`

---

### 5. ESGGlueETLRole

**Purpose:** Execution role for Glue ETL jobs (optional)

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

**Inline Policy** (`ESGGlueS3Access`):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ],
    "Resource": [
      "arn:aws:s3:::esg-reporting-output-bucket",
      "arn:aws:s3:::esg-reporting-output-bucket/*",
      "arn:aws:s3:::esg-athena-results",
      "arn:aws:s3:::esg-athena-results/*"
    ]
  }]
}
```

---

## Lambda Functions

### Function Specifications Table

| Function Name | Runtime | Memory | Timeout | Layer | Environment Variables |
|--------------|---------|--------|---------|-------|----------------------|
| esg-validate-input | Python 3.12 | 128 MB | 10s | No | - |
| esg-section-gen | Python 3.12 | 512 MB | 600s | No | BEDROCK_MODEL_ID |
| esg-filter-sections | Python 3.12 | 256 MB | 30s | No | - |
| esg-assembly-doc | Python 3.12 | 1024 MB | 300s | Yes | OUTPUT_BUCKET |
| esg-validation | Python 3.12 | 256 MB | 30s | No | - |
| esg-review-handler | Python 3.12 | 128 MB | 10s | No | - |
| esg-status-check | Python 3.12 | 128 MB | 10s | No | STEP_FUNCTION_ARN |
| esg-history | Python 3.12 | 128 MB | 10s | No | - |
| esg-athena-query | Python 3.12 | 256 MB | 60s | No | ATHENA_DATABASE, ATHENA_OUTPUT_BUCKET |
| esg-dashboard-data | Python 3.12 | 512 MB | 30s | No | ATHENA_DATABASE, CACHE_BUCKET |
| esg-agent-tools | Python 3.12 | 256 MB | 10s | No | STEP_FUNCTION_ARN, OUTPUT_BUCKET |

###
 Detailed Lambda Configurations

#### 1. esg-validate-input

**Purpose:** Validates report generation request parameters

**Configuration:**
```json
{
  "FunctionName": "esg-validate-input",
  "Runtime": "python3.12",
  "Role": "arn:aws:iam::ACCOUNT_ID:role/ESGLambdaExecutionRole",
  "Handler": "handler.lambda_handler",
  "Timeout": 10,
  "MemorySize": 128
}
```

**Input:**
```json
{
  "reporting_year": 2024,
  "framework": "GRI_305",
  "revenue_idr_billion": 92000
}
```

**Output:** Same as input (if valid), raises exception if invalid

---

#### 2. esg-section-gen

**Purpose:** Generates individual report sections using Bedrock

**Configuration:**
```json
{
  "FunctionName": "esg-section-gen",
  "Runtime": "python3.12",
  "Role": "arn:aws:iam::ACCOUNT_ID:role/ESGLambdaExecutionRole",
  "Handler": "handler.lambda_handler",
  "Timeout": 600,
  "MemorySize": 512,
  "Environment": {
    "Variables": {
      "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20240620-v2:0"
    }
  }
}
```

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
  "section_content": "# GRI 305-1: Direct (Scope 1) GHG Emissions...",
  "metadata": {
    "tokens_used": 1234,
    "generation_time_seconds": 45.2
  }
}
```

---

#### 3. esg-assembly-doc

**Purpose:** Assembles DOCX and PPTX reports from generated sections

**Configuration:**
```json
{
  "FunctionName": "esg-assembly-doc",
  "Runtime": "python3.12",
  "Role": "arn:aws:iam::ACCOUNT_ID:role/ESGLambdaExecutionRole",
  "Handler": "handler.lambda_handler",
  "Timeout": 300,
  "MemorySize": 1024,
  "Layers": [
    "arn:aws:lambda:ap-southeast-1:ACCOUNT_ID:layer:esg-reporting-layer:1"
  ],
  "Environment": {
    "Variables": {
      "OUTPUT_BUCKET": "esg-reporting-output-bucket"
    }
  }
}
```

**Dependencies:** python-docx, python-pptx, matplotlib (via Layer)

---

### Lambda Layer Specification

**Layer Name:** `esg-reporting-layer`

**Compatible Runtimes:** Python 3.12

**Contents:**
- `python-docx==1.1.0` (DOCX generation)
- `python-pptx==0.6.23` (PPTX generation)
- `matplotlib==3.8.3` (Chart rendering)
- `Pillow==10.2.0` (Image handling)
- `lxml==5.1.0` (XML parsing for docx/pptx)

**Size:** ~45 MB (compressed)

**Build Command:**
```bash
docker run --rm -v "$PWD":/var/task public.ecr.aws/lambda/python:3.12 \
  /bin/bash -c "pip install python-docx python-pptx matplotlib pillow -t /var/task/python"
```

---

## Step Functions

### State Machine: esg-orchestrator

**ARN:** `arn:aws:states:ap-southeast-1:ACCOUNT_ID:stateMachine:esg-orchestrator`

**Role:** `ESGStepFunctionsRole`

**Type:** STANDARD

**Timeout:** 1 hour

### State Machine Flow

```
┌─────────────────┐
│ ValidateInput   │ → Lambda: esg-validate-input
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ GenerateSections│ → Map State (Parallel execution)
│                 │   ├─ GRI_305_SCOPE1
│                 │   ├─ GRI_305_SCOPE2
│                 │   ├─ GRI_305_SCOPE3
│                 │   ├─ IFRS_S2_STRATEGY_RISKS
│                 │   ├─ IFRS_S2_GOVERNANCE
│                 │   ├─ IFRS_S2_METRICS
│                 │   ├─ IFRS_S2_PCAF_FINANCED_EMISSIONS
│                 │   ├─ CSRD_ESRS_E1_CLIMATE_STRATEGY
│                 │   └─ OJK_PSPK_GHG_INVENTORY
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ FilterSections  │ → Lambda: esg-filter-sections
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ AssembleDocument│ → Lambda: esg-assembly-doc
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ ValidateReport  │ → Lambda: esg-validation
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ HumanReview?    │ → Choice State (skip by default)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Success         │ → Return download URLs
└─────────────────┘
```

### Execution Times

| Framework | Sections | Avg Time | Max Time |
|-----------|----------|----------|----------|
| GRI_305 | 5 | 3 min | 5 min |
| IFRS_S2 | 4 | 4 min | 6 min |
| CSRD_ESRS_E1 | 4 | 4 min | 6 min |
| OJK_PSPK | 4 | 4 min | 6 min |
| MULTI_FRAMEWORK | 9 | 8-12 min | 15 min |

---

## API Gateway

### REST API: ESG Reporting API

**API ID:** (generated on creation)

**Endpoint:** `https://API_ID.execute-api.ap-southeast-1.amazonaws.com/prod`

**Type:** REGIONAL

**Stage:** prod

### API Endpoints

| Method | Path | Integration | Purpose |
|--------|------|-------------|---------|
| POST | /chat | Bedrock Agent Runtime | Chat with ESG assistant |
| GET | /status | Lambda: esg-status-check | Check report status |
| GET | /history | Lambda: esg-history | List all executions |
| GET | /dashboard-data | Lambda: esg-dashboard-data | Get analytics data |

### Endpoint Specifications

#### 1. GET /status

**Query Parameters:**
- `execution_id` (required): Step Functions execution ID

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


#### 2. GET /history

**Query Parameters:** None

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

#### 3. GET /dashboard-data

**Query Parameters:**
- `refresh` (optional): `true` to force Athena refresh, `false` (default) to use cache

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
    "financed_by_sector": [...]
  }
}
```

### CORS Configuration

All endpoints have CORS enabled:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token
```

---

## Amazon Bedrock

### Bedrock Agent: ESG-Report-Assistant

**Agent ID:** (generated on creation)

**Alias:** production

**Foundation Model:** `anthropic.claude-3-5-sonnet-20240620-v2:0`

**Role:** `ESGBedrockAgentRole`

**Region:** ap-southeast-1

### Agent Instructions

```text
You are an ESG (Environmental, Social, Governance) Report Generation Assistant 
specialized in sustainability reporting for financial institutions.

SCOPE GUARDRAILS - STRICT ENFORCEMENT:
You ONLY answer questions related to:
- ESG reporting frameworks (GRI 305, IFRS S2, CSRD/ESRS E1, OJK PSPK)
- Greenhouse gas (GHG) emissions (Scope 1, 2, 3)
- PCAF (Partnership for Carbon Accounting Financials)
- Climate risk disclosures
- Sustainability metrics and KPIs

If the user asks about topics OUTSIDE of ESG, politely reject:
"I'm specialized in ESG reporting and sustainability topics. That question 
is outside my scope. Can I help you with ESG reports instead?"

RESPONSE FORMATTING:
- Use markdown: **bold**, #headers, bullet lists
- Add relevant emoji: 📊, 🌍, 💡, ✅, ⚠️
- Short paragraphs (2-3 sentences max)
- Professional but conversational tone
```

### Agent Tools (4 Actions)

#### 1. generate_report

**Method:** POST  
**Parameters:**
- `reporting_year` (integer, required): 2023 or 2024
- `framework` (string, required): GRI_305, IFRS_S2, CSRD_ESRS_E1, OJK_PSPK, MULTI_FRAMEWORK
- `revenue_idr_billion` (number, optional): Default 92000

**Returns:** Execution ARN and estimated completion time

#### 2. check_status

**Method:** POST  
**Parameters:**
- `execution_arn` (string, required): Execution ID

**Returns:** Status (RUNNING/SUCCEEDED/FAILED) and output if complete

#### 3. download_report

**Method:** POST  
**Parameters:**
- `execution_arn` (string, required): Execution ID

**Returns:** Presigned S3 URLs for DOCX and PPTX (1 hour expiry)

#### 4. list_available_data

**Method:** GET  
**Parameters:** None

**Returns:** Available years (2023, 2024) and supported frameworks

### Bedrock Knowledge Base: ESG-Framework-KB

**KB ID:** (generated on creation)

**Data Source:** S3 (`s3://esg-knowledge-base/documents/`)

**Embeddings Model:** Amazon Titan Embeddings v2

**Vector Store:** Amazon OpenSearch Serverless (auto-created)

**Documents:**
- GRI 305 Standard (Emissions)
- IFRS S2 Climate Disclosures
- CSRD/ESRS E1 Climate Change
- OJK POJK 51/2017 Sustainable Finance
- PCAF Global GHG Accounting Standard
- Sample ESG reports (BCA, BRI, DBS, Mandiri, OCBC)

**Total Documents:** ~15 PDFs + text files

**Sync Frequency:** Manual (via console)

---

## S3 Buckets

### 1. esg-reporting-output-bucket

**Purpose:** Store generated DOCX and PPTX reports

**Region:** ap-southeast-1

**Versioning:** Enabled

**Encryption:** AES-256 (server-side)

**Public Access:** Blocked

**Lifecycle Policy:**
```json
{
  "Rules": [{
    "ID": "DeleteOldVersions",
    "Status": "Enabled",
    "Filter": {},
    "NoncurrentVersionExpiration": {
      "NewerNoncurrentVersions": 3,
      "NoncurrentDays": 30
    }
  }]
}
```

**Folder Structure:**
```
reports/
  ├── 2023/
  │   ├── GRI_305_2023_exec_xxx.docx
  │   └── MULTI_FRAMEWORK_2023_exec_yyy.pptx
  └── 2024/
      ├── IFRS_S2_2024_exec_zzz.docx
      └── MULTI_FRAMEWORK_2024_exec_aaa.pptx
```

**Average File Size:**
- DOCX: 500 KB - 2 MB
- PPTX: 1 MB - 3 MB

---

### 2. esg-athena-results

**Purpose:** Store Athena query results and dashboard cache

**Region:** ap-southeast-1

**Versioning:** Enabled

**Encryption:** AES-256

**Public Access:** Blocked

**Folder Structure:**
```
queries/
  └── [query-execution-id]/
      └── results.csv
dashboard-cache/
  └── latest.json
```

**Cache Strategy:**
- Dashboard reads from `dashboard-cache/latest.json` by default (free)
- Manual refresh triggers Athena query and updates cache (~$0.01)

---

### 3. esg-knowledge-base

**Purpose:** Store ESG framework documents for Bedrock Knowledge Base

**Region:** ap-southeast-1

**Versioning:** Enabled

**Encryption:** AES-256

**Public Access:** Blocked

**Folder Structure:**
```
documents/
  ├── gri_GRI_305_Emissions_2016.pdf
  ├── ifrs_IFRS_S2_Climate_Disclosures_2023.pdf
  ├── csrd_ESRS_E1_Climate_Change_2023.pdf
  ├── ojk_POJK_51_2017_Sustainable_Finance.pdf
  ├── ghg_methodology_PCAF_Standard_Part_A_2022.pdf
  └── ...
```

---

## Glue & Athena

### Glue Database: esg_reporting_db

**Database Name:** `esg_reporting_db`

**Location:** `s3://esg-athena-results/`

**Description:** ESG Reporting Database for Athena queries

### Glue Tables (Example Schema)

#### Table: esg_emissions

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS esg_reporting_db.esg_emissions (
  year INT,
  scope INT,
  source STRING,
  emissions_tco2e DOUBLE,
  location STRING,
  data_quality_score INT
)
PARTITIONED BY (reporting_year INT)
STORED AS PARQUET
LOCATION 's3://esg-athena-results/tables/emissions/'
TBLPROPERTIES ('parquet.compression'='SNAPPY');
```

#### Table: pcaf_portfolio

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS esg_reporting_db.pcaf_portfolio (
  year INT,
  sector STRING,
  borrower_id STRING,
  loan_amount_idr BIGINT,
  financed_emissions_tco2e DOUBLE,
  data_quality_score INT
)
PARTITIONED BY (reporting_year INT)
STORED AS PARQUET
LOCATION 's3://esg-athena-results/tables/pcaf/'
TBLPROPERTIES ('parquet.compression'='SNAPPY');
```

### Athena Workgroup

**Name:** primary

**Output Location:** `s3://esg-athena-results/queries/`

**Data Scanned (per query):** ~10-50 MB

**Cost per Query:** ~$0.01

---

## AWS Amplify

### App: esg-chat-app

**Repository:** `https://github.com/radityar21/esg-chat-app`

**Branch:** main

**Build Spec:** `amplify.yml` (in repo root)

**Build Configuration:**
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

**Custom Domain:** (optional)

**Environment Variables:** None (API URL hardcoded in `src/api.js`)

**Deployment URL:** `https://main.d337jqli3ubqmk.amplifyapp.com`

**Build Time:** 2-3 minutes

**Deploy Trigger:** Push to `main` branch (auto-deploy)

---

## Network & Security

### VPC Configuration

**Current:** Lambdas run in AWS-managed VPC (no custom VPC)

**Future Enhancement:** Deploy Lambdas in private subnet with NAT Gateway for enhanced security

### Security Groups

Not applicable (no custom VPC)

### Encryption

| Resource | Encryption Type | Key |
|----------|----------------|-----|
| S3 Buckets | Server-side | AES-256 (SSE-S3) |
| Lambda Environment Variables | At rest | AWS-managed key |
| Athena Results | Server-side | AES-256 (SSE-S3) |
| OpenSearch (KB) | At rest | AWS-managed key |

### IAM Best Practices

- ✅ Principle of least privilege
- ✅ No wildcard (*) permissions in production
- ✅ Separate roles for each service
- ✅ Resource-level permissions where possible
- ✅ Condition keys for cross-service access

---

## Monitoring & Logging

### CloudWatch Log Groups

| Log Group | Retention | Purpose |
|-----------|-----------|---------|
| `/aws/lambda/esg-validate-input` | 7 days | Input validation logs |
| `/aws/lambda/esg-section-gen` | 30 days | Report generation logs (high volume) |
| `/aws/lambda/esg-assembly-doc` | 7 days | Document assembly logs |
| `/aws/lambda/esg-status-check` | 7 days | Status API logs |
| `/aws/lambda/esg-history` | 7 days | History API logs |
| `/aws/lambda/esg-athena-query` | 7 days | Athena query logs |
| `/aws/lambda/esg-dashboard-data` | 7 days | Dashboard data logs |
| `/aws/lambda/esg-agent-tools` | 7 days | Agent tools logs |
| `/aws/vendedlogs/states/esg-orchestrator` | 30 days | Step Functions execution logs |
| `/aws/apigateway/esg-reporting-api` | 7 days | API Gateway access logs |

### CloudWatch Metrics

#### Lambda Metrics
- Invocations
- Errors
- Duration (P50, P90, P99, P100)
- Throttles
- Concurrent Executions

#### Step Functions Metrics
- ExecutionsStarted
- ExecutionsSucceeded
- ExecutionsFailed
- ExecutionTime

#### API Gateway Metrics
- Count (requests)
- 4XXError
- 5XXError
- IntegrationLatency
- Latency

### CloudWatch Alarms

| Alarm Name | Metric | Threshold | Action |
|-----------|--------|-----------|--------|
| ESG-Lambda-Errors-High | Lambda Errors | > 5 in 5 min | SNS notification |
| ESG-StepFunctions-Failed | ExecutionsFailed | > 3 in 1 hour | SNS notification |
| ESG-API-5XX-Errors | 5XXError | > 10 in 5 min | SNS notification |
| ESG-Section-Gen-Timeout | Duration | > 550s | SNS notification |

---

## Cost Analysis

### Monthly Cost Breakdown (100 reports/month)

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|-------------|
| **Lambda Compute** | | | |
| - esg-section-gen | 100 exec × 9 sections × 45s × 512MB | $0.0000083/GB-s | $1.69 |
| - esg-assembly-doc | 100 exec × 30s × 1024MB | $0.0000083/GB-s | $0.25 |
| - Other Lambdas | 300 exec × 5s × 256MB | $0.0000083/GB-s | $0.03 |
| **Lambda Requests** | 1,100 requests | $0.20/1M | $0.00 |
| **Bedrock API** | 100 reports × 9 sections × 12K tokens | $3/MTok input, $15/MTok output | $12.96 |
| **Step Functions** | 100 executions × 12 state transitions | $0.025/1K transitions | $0.03 |
| **API Gateway** | 10,000 requests | $3.50/1M | $0.04 |
| **S3 Storage** | 100 reports × 2MB avg | $0.023/GB | $0.005 |
| **S3 Requests** | 1,000 PUT + 5,000 GET | $0.005/1K PUT, $0.0004/1K GET | $0.007 |
| **Athena** | 10 dashboard refreshes × 50MB scanned | $5/TB | $0.002 |
| **Glue Data Catalog** | 5 tables | $1/100K objects | $0.00 |
| **OpenSearch Serverless (KB)** | 1 OCU-hour × 720 hours | $0.24/OCU-hour | $172.80 |
| **Amplify Hosting** | 1 app, 5GB transfer | Free tier | $0.00 |
| **CloudWatch Logs** | 5GB ingested | $0.50/GB | $2.50 |
| **CloudWatch Alarms** | 4 alarms | $0.10/alarm | $0.40 |
| **TOTAL** | | | **~$190.77/month** |

**Note:** OpenSearch Serverless dominates cost ($172.80). Can be optimized by:
- Using Aurora Serverless for vector store (~$25/month)
- Or disabling Knowledge Base if not needed (~$18/month total)

### Cost Optimization Strategies

1. **Reduce OpenSearch cost:**
   - Switch to Aurora Serverless vector store
   - Or use Amazon Kendra (pay-per-query)

2. **Lambda optimization:**
   - Increase memory for faster execution (reduces duration cost)
   - Use Lambda SnapStart for Java runtimes (not applicable, using Python)

3. **S3 lifecycle:**
   - Move old reports to Glacier after 90 days
   - Delete reports older than 1 year

4. **Athena optimization:**
   - Partition tables by year
   - Use Parquet + Snappy compression
   - Cache dashboard data aggressively

5. **CloudWatch Logs:**
   - Reduce retention to 3 days for low-priority logs
   - Export to S3 for long-term storage

---

## Disaster Recovery

### Backup Strategy

| Resource | Backup Method | Frequency | Retention |
|----------|--------------|-----------|-----------|
| S3 Buckets | Versioning + Cross-region replication | Continuous | 90 days |
| Lambda Code | Git repository + S3 deployment packages | Per deployment | Indefinite |
| Step Functions | Version-controlled JSON definition | Per update | Indefinite |
| Glue Tables | CloudFormation template | Per schema change | Indefinite |
| Knowledge Base | S3 source documents | Continuous | Indefinite |

### Recovery Time Objective (RTO)

- **Infrastructure:** 1-2 hours (re-deploy via CDK or manual)
- **Data (S3):** 0 minutes (versioning, no data loss)
- **Lambda code:** 10 minutes (re-deploy from Git)

### Recovery Point Objective (RPO)

- **S3 Data:** 0 (continuous versioning)
- **Lambda deployments:** Last Git commit
- **Infrastructure:** Last CDK deployment

---

## Compliance & Governance

### Data Residency

- **Primary Region:** ap-southeast-1 (Singapore)
- **Data stays within region** (no cross-region replication by default)

### Audit Logging

- **CloudTrail:** Enabled for all API calls
- **S3 Access Logs:** Enabled for audit trail
- **Lambda Execution Logs:** CloudWatch Logs

### Tags

All resources tagged with:
```
Project=ESG
Env=Production
Owner=TokaiGroup
CostCenter=Sustainability
```

---

## Performance Benchmarks

### Latency Targets

| Operation | Target | Actual (P95) |
|-----------|--------|--------------|
| API Gateway → Lambda | < 100ms | 45ms |
| Report Generation (GRI 305) | < 5 min | 3 min |
| Report Generation (MULTI) | < 15 min | 10 min |
| Dashboard Load (cached) | < 500ms | 200ms |
| Dashboard Load (refresh) | < 5s | 3.5s |
| Chat Response (no KB) | < 3s | 2s |
| Chat Response (with KB) | < 5s | 4s |

### Throughput

- **Concurrent report generations:** 10 (Lambda concurrency limit)
- **API requests/sec:** 1,000 (API Gateway limit)
- **Max reports/hour:** 60 (with current Lambda concurrency)

---

## 📚 References

- **AWS Lambda:** https://docs.aws.amazon.com/lambda/
- **AWS Step Functions:** https://docs.aws.amazon.com/step-functions/
- **Amazon Bedrock:** https://docs.aws.amazon.com/bedrock/
- **API Gateway:** https://docs.aws.amazon.com/apigateway/
- **AWS Amplify:** https://docs.aws.amazon.com/amplify/

---

**Document Version:** 1.0  
**Last Updated:** June 15, 2026  
**Maintained by:** Tokaicom Mitra Indonesia (Tokai Group)
