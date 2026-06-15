# ESG Reporting System - Complete Deployment Guide

**Tokaicom Mitra Indonesia (Tokai Group)**  
**Version:** 1.1  
**Last Updated:** June 15, 2026  
**Crosschecked against:** IMPLEMENTATION_CHANGELOG, INFRASTRUCTURE_REFERENCE, SPEC_AMENDMENTS, VALIDATION_FALSE_POSITIVES

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Deployment Sequence](#deployment-sequence)
4. [Option A: Automated Deployment (IaC with CDK)](#option-a-automated-deployment-iac-with-cdk)
5. [Option B: Manual Deployment (AWS CLI)](#option-b-manual-deployment-aws-cli)
6. [Post-Deployment Configuration](#post-deployment-configuration)
7. [Verification & Testing](#verification--testing)
8. [Troubleshooting](#troubleshooting)
9. [Known Validation Issues (False Positives)](#known-validation-issues-false-positives)
10. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Required Tools

| Tool | Version | Purpose | Installation |
|------|---------|---------|--------------|
| **AWS CLI** | 2.x | Infrastructure deployment | `aws --version` |
| **Node.js** | 18+ | Frontend build | `node --version` |
| **npm** | 9+ | Package management | `npm --version` |
| **Python** | 3.11 | Lambda runtime | `python --version` |
| **Git** | 2.x | Version control | `git --version` |
| **AWS CDK** (optional) | 2.x | IaC deployment | `npm install -g aws-cdk` |
| **AWS CloudShell** | N/A | Linux-dependent builds (Layer) | Available in AWS Console |

### AWS Account Requirements

- **AWS Account ID:** `061039769766` (current POC)
- **IAM User/Role** with these managed policies:
  - `AdministratorAccess` (for initial setup) OR
  - Custom policy with: IAM, Lambda, S3, Step Functions, Bedrock, API Gateway, Amplify, Glue, Athena, SNS, DynamoDB permissions
- **AWS Region:** `us-east-1` (N. Virginia) — current deployment
  - *Note: Original spec targeted `ap-southeast-1` (Singapore), but CloudShell availability and Bedrock model access led to us-east-1*
- **Bedrock Model Access:** Enable `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (cross-region inference profile) in target region

### Region Decision

| Option | Region | Pros | Cons |
|--------|--------|------|------|
| **Current (POC)** | us-east-1 | All services available, CloudShell works, models available | Latency from Indonesia |
| **Target (Prod)** | ap-southeast-1 | Low latency, data residency compliance | Must verify Bedrock model availability |

> ⚠️ **All commands in this guide use the variable `$REGION`. Set it to your target region before running commands.**

```bash
# Set region (choose one)
export REGION="us-east-1"        # Current POC deployment
# export REGION="ap-southeast-1" # Future production target
export ACCOUNT_ID="061039769766"
```

### Cost Estimate

| Component | Setup Cost | Monthly Cost (100 reports) |
|-----------|-----------|---------------------------|
| OpenSearch Serverless (KB) | $0 | ~$173 |
| Bedrock API (Claude 4.5 Sonnet) | $0 | ~$13 |
| Lambda (11 functions) | $0 | ~$2 |
| S3 Storage (6 buckets) | $0 | ~$5 |
| Step Functions | $0 | ~$2.50 |
| API Gateway | $0 | ~$3.50 |
| Athena | $0 | ~$1 |
| Amplify Hosting | $0 | Free tier |
| CloudWatch Logs | $0 | ~$2.50 |
| **Total** | **$0** | **~$190/month** |
| **Optimized (no OpenSearch)** | $0 | **~$30/month** |

---

## Architecture Overview

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────────────────────────────┐
│  Frontend (React + Amplify)                         │
│  Pages: Overview, Analytics, Chat, Reports, Ref    │
│  Stack: React 18 + Vite 5 + Tailwind + Recharts   │
└──────┬──────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────────────┐
│  API Gateway (REST) - ESG-Chat-API                 │
│  /chat (POST), /status (GET), /history (GET),      │
│  /dashboard-data (GET)                             │
└──────┬──────────────────────────────────────────────┘
       │
   ┌───┴────┬──────────────┬────────────┐
   │        │              │            │
   ↓        ↓              ↓            ↓
┌────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐
│Bedrock │ │ Lambda   │ │  Step    │ │Lambda       │
│ Agent  │ │(status,  │ │Functions │ │(dashboard)  │
│(chat-  │ │ history) │ │          │ │             │
│ proxy) │ └──────────┘ └─────┬────┘ └─────────────┘
└───┬────┘                     │
    │           ┌──────────────┼──────────────────────┐
    ↓           │              │                      │
┌────────┐      ↓              ↓                      ↓
│Agent   │ ┌─────────┐   ┌──────────┐          ┌──────────┐
│Tools   │ │validate │   │ section_ │          │ assembly │
│Lambda  │ │ _input  │   │   gen    │          │   _doc   │
└────────┘ └─────────┘   └────┬─────┘          └────┬─────┘
                               │                     │
                    ┌──────────┴──────────┐          │
                    ↓                    ↓           │
              ┌──────────┐         ┌──────────┐     │
              │ Bedrock  │         │ validation│     │
              │ Claude   │         │  Lambda   │     │
              │ Sonnet   │         └──────────┘     │
              │ 4.5      │                          │
              └────┬─────┘                          ↓
                   │                          ┌──────────────┐
                   ↓                          │   S3 Buckets │
              ┌──────────┐                    │  - Raw       │
              │ Knowledge│                    │  - Curated   │
              │   Base   │                    │  - Aggregated│
              │ (RAG)    │                    │  - Output    │
              └──────────┘                    │  - KB Docs   │
                                              │  - Athena    │
                                              └──────────────┘
```

**Key Components:**
- 11 Lambda functions + 1 chat proxy = 12 Lambda functions total
- 1 Step Functions State Machine (ESGReportGenerationStateMachine)
- 1 API Gateway REST API (ESG-Chat-API)
- 1 Bedrock Agent (ESGReportAgent) with 4 tools
- 1 Bedrock Knowledge Base (WVREXI1LEI) with OpenSearch Serverless
- 6 S3 Buckets (raw, curated, aggregated, output, KB docs, Athena results)
- 4 Glue ETL Jobs (Scope 1, 2, 3, Aggregation)
- 3 Athena Databases (esg_raw, esg_curated, esg_aggregated)
- 2 SNS Topics (ESG-HumanReview, ESG-ReportComplete)
- 5 pages React frontend on Amplify

**Supported Report Sections:**
- Environment (E): Scope 1, Scope 2, Scope 3/PCAF, Intensity, Methodology, Summary
- Social (S): Workforce (GRI 2-7), Employment (GRI 401-1), Training (GRI 404-1), Diversity (GRI 405-1), Non-Discrimination (GRI 406-1)

**Deployment Time:** ~30-45 minutes (manual) or ~15-20 minutes (CDK)

---

## Deployment Sequence

**CRITICAL:** Follow this exact order to avoid dependency issues.

```
 1. IAM Roles & Policies (3 roles: ESGGlueRole, ESGLambdaRole, ESGStepFunctionsRole)
 2. S3 Buckets (6 buckets with account-ID suffix)
 3. Glue Data Catalog (3 databases + 12 tables with partition projection)
 4. Glue ETL Scripts (upload to S3)
 5. Run Glue ETL Jobs (Scope 1 → Scope 2 → Scope 3 → Aggregation)
 6. Lambda Layer (python-docx + lxml, MUST build on Linux/CloudShell)
 7. Lambda Functions (11 functions)
 8. SNS Topics (2 topics)
 9. Step Functions State Machine
10. API Gateway (4 endpoints + CORS)
11. Bedrock Knowledge Base (15 documents + semantic chunking)
12. Bedrock Agent (4 tools + action group)
13. Chat Proxy Lambda + API integration
14. Frontend (Amplify + GitHub auto-deploy)
```

---

## Option A: Automated Deployment (IaC with CDK)

### Step 1: Setup CDK Environment

```bash
# Navigate to infrastructure folder
cd esg-reporting-poc/infra

# Install CDK dependencies
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap aws://$ACCOUNT_ID/$REGION
```

### Step 2: Configure Parameters

Edit `esg-reporting-poc/infra/cdk.json`:

```json
{
  "context": {
    "account_id": "061039769766",
    "region": "us-east-1",
    "project_name": "esg-reporting",
    "bedrock_model_id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "kb_id": "WVREXI1LEI"
  }
}
```

### Step 3: Deploy All Infrastructure

```bash
# Deploy everything (15-20 min)
cdk deploy ESGInfraStack --require-approval never

# Output will show:
# - Lambda ARNs
# - Step Functions ARN
# - API Gateway URL
# - S3 bucket names
```

### Step 4: Deploy Frontend

```bash
# Push to GitHub (Amplify auto-deploys)
cd ../../esg-chat-app-react
git add .
git commit -m "deploy: initial frontend"
git push origin main
```

**✅ Done!** Skip to [Post-Deployment Configuration](#post-deployment-configuration)

---

## Option B: Manual Deployment (AWS CLI)

### 🔧 Step 1: Setup IAM Roles & S3 Buckets

Run the automated setup script (in CloudShell for Linux compatibility):

```bash
cd esg-reporting-poc/scripts
chmod +x setup_account.sh
./setup_account.sh
```

**What it creates:**

| Resource | Name | Purpose |
|----------|------|---------|
| IAM Role | `ESGGlueRole` | Glue ETL jobs (S3 read/write, CloudWatch) |
| IAM Role | `ESGLambdaRole` | All Lambda functions (S3, Athena, Bedrock, DynamoDB, Glue) |
| IAM Role | `ESGStepFunctionsRole` | Step Functions (Lambda invoke, SNS, Glue, CloudWatch) |
| S3 Bucket | `esg-data-raw-{ACCOUNT_ID}` | Source data as ingested |
| S3 Bucket | `esg-data-curated-{ACCOUNT_ID}` | ETL-computed GHG calculations |
| S3 Bucket | `esg-data-aggregated-{ACCOUNT_ID}` | Report-ready annual metrics |
| S3 Bucket | `esg-output-reports-{ACCOUNT_ID}` | Generated DOCX/PDF reports |
| S3 Bucket | `esg-kb-documents-{ACCOUNT_ID}` | Knowledge Base documents |
| S3 Bucket | `esg-athena-results-{ACCOUNT_ID}` | Athena query results |
| Glue DB | `esg_raw` | Raw data tables |
| Glue DB | `esg_curated` | ETL-processed data |
| Glue DB | `esg_aggregated` | Report-ready aggregations |

**Verify:**
```bash
aws iam get-role --role-name ESGLambdaRole --region $REGION
aws iam get-role --role-name ESGStepFunctionsRole --region $REGION
aws s3 ls | grep esg
```

**Key IAM permissions (ESGLambdaRole):**
- S3: GetObject, PutObject, ListBucket, GetBucketLocation, PutObjectTagging (6 buckets)
- Athena: StartQueryExecution, GetQueryExecution, GetQueryResults, StopQueryExecution
- Glue: GetTable, GetTables, GetDatabase, GetDatabases, GetPartitions
- Bedrock: InvokeModel, InvokeModelWithResponseStream (foundation-model/* + inference-profile/*)
- Bedrock KB: Retrieve, RetrieveAndGenerate
- DynamoDB: PutItem, GetItem, UpdateItem, Query, Scan (ESG* tables)
- States: StartExecution, DescribeExecution
- CloudWatch Logs

---

### 📊 Step 2: Setup Data Layer (Glue + Athena)

#### 2.1 Upload Synthetic Data

```bash
# Generate synthetic data (if not already done)
python scripts/generate_energy_data.py
python scripts/generate_loan_data.py
python scripts/generate_hr_data.py

# Upload to S3
aws s3 cp data/energy/ s3://esg-data-raw-$ACCOUNT_ID/energy_consumption/ --recursive
aws s3 cp data/loans/ s3://esg-data-raw-$ACCOUNT_ID/loan_portfolio/ --recursive
aws s3 cp data/hr/ s3://esg-data-raw-$ACCOUNT_ID/hr_metrics/ --recursive
```

#### 2.2 Create Athena Tables

Run DDL statements in Athena console or via CLI. All tables use **partition projection**:

```bash
# Create tables (run each SQL file in Athena)
aws athena start-query-execution \
  --query-string "$(cat sql/ddl/01_raw_tables.sql)" \
  --work-group esg-reporting-workgroup \
  --region $REGION

aws athena start-query-execution \
  --query-string "$(cat sql/ddl/02_curated_tables.sql)" \
  --work-group esg-reporting-workgroup \
  --region $REGION

aws athena start-query-execution \
  --query-string "$(cat sql/ddl/03_aggregated_tables.sql)" \
  --work-group esg-reporting-workgroup \
  --region $REGION
```

**Tables created (12 total):**

| Database | Table | Partition Keys |
|----------|-------|----------------|
| esg_raw | energy_consumption | reporting_year |
| esg_raw | loan_portfolio | reporting_year |
| esg_raw | hr_metrics | reporting_year |
| esg_curated | ghg_scope1 | reporting_year |
| esg_curated | ghg_scope2 | reporting_year |
| esg_curated | ghg_scope3_financed | reporting_year |
| esg_aggregated | ghg_summary_annual | reporting_year |
| esg_aggregated | pcaf_by_sector | reporting_year |
| esg_aggregated | scope1_by_facility | reporting_year |

#### 2.3 Run Glue ETL Jobs

```bash
# Upload Glue scripts
aws s3 cp glue_jobs/glue_job_scope1_ghg.py s3://esg-data-raw-$ACCOUNT_ID/scripts/
aws s3 cp glue_jobs/glue_job_scope2_electricity.py s3://esg-data-raw-$ACCOUNT_ID/scripts/
aws s3 cp glue_jobs/glue_job_scope3_pcaf.py s3://esg-data-raw-$ACCOUNT_ID/scripts/
aws s3 cp glue_jobs/glue_job_aggregation.py s3://esg-data-raw-$ACCOUNT_ID/scripts/

# Create & run jobs (Scope 1 → 2 → 3 → Aggregation)
aws glue create-job --name esg-etl-scope1-direct \
  --role ESGGlueRole \
  --command '{"Name":"glueetl","ScriptLocation":"s3://esg-data-raw-'$ACCOUNT_ID'/scripts/glue_job_scope1_ghg.py","PythonVersion":"3"}' \
  --default-arguments '{"--enable-glue-datacatalog":"true","--enable-job-insights":"true"}' \
  --glue-version 4.0 --number-of-workers 2 --worker-type G.1X \
  --region $REGION

# Start ETL (sequential)
aws glue start-job-run --job-name esg-etl-scope1-direct --arguments '{"--REPORTING_YEAR":"2024"}' --region $REGION
# Wait for completion, then:
aws glue start-job-run --job-name esg-etl-scope2-indirect --arguments '{"--REPORTING_YEAR":"2024"}' --region $REGION
aws glue start-job-run --job-name esg-etl-scope3-pcaf --arguments '{"--REPORTING_YEAR":"2024"}' --region $REGION
aws glue start-job-run --job-name esg-etl-aggregation --arguments '{"--REPORTING_YEAR":"2024"}' --region $REGION
```

---

### 📦 Step 3: Build & Deploy Lambda Layer

> ⚠️ **CRITICAL:** Layer MUST be built on Linux (CloudShell). Windows `pip install` produces incompatible `.pyd` files for `lxml` C extensions.

**Build in CloudShell (us-east-1):**

```bash
mkdir -p /tmp/layer/python
pip install python-docx -t /tmp/layer/python \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --python-version 3.11 \
  --implementation cp

cd /tmp/layer
zip -r /tmp/python-docx-layer.zip python/

# Upload and publish
aws s3 cp /tmp/python-docx-layer.zip s3://esg-data-raw-$ACCOUNT_ID/lambda-layers/python-docx-layer.zip

aws lambda publish-layer-version \
  --layer-name esg-python-docx \
  --description "python-docx for Lambda (Linux x86_64)" \
  --content S3Bucket=esg-data-raw-$ACCOUNT_ID,S3Key=lambda-layers/python-docx-layer.zip \
  --compatible-runtimes python3.11 \
  --region $REGION
```

**Output:** Note the `LayerVersionArn` — needed for `esg-assembly-doc`

---

### ⚡ Step 4: Deploy Lambda Functions

**Packaging (from Windows CMD):**

```cmd
REM Package each Lambda (handler.py only, no dependencies)
powershell Compress-Archive -Path esg-reporting-poc\lambda\validate_input\handler.py -DestinationPath deploy\validate_input.zip -Force
powershell Compress-Archive -Path esg-reporting-poc\lambda\section_gen\handler.py -DestinationPath deploy\section_gen.zip -Force
powershell Compress-Archive -Path esg-reporting-poc\lambda\filter_sections\handler.py -DestinationPath deploy\filter_sections.zip -Force
powershell Compress-Archive -Path esg-reporting-poc\lambda\assembly_doc\handler.py -DestinationPath deploy\assembly_doc.zip -Force
powershell Compress-Archive -Path esg-reporting-poc\lambda\validation\handler.py -DestinationPath deploy\validation.zip -Force
powershell Compress-Archive -Path esg-reporting-poc\lambda\review_handler\handler.py -DestinationPath deploy\review_handler.zip -Force
powershell Compress-Archive -Path esg-reporting-poc\lambda\status_check\handler.py -DestinationPath deploy\status_check.zip -Force
powershell Compress-Archive -Path esg-reporting-poc\lambda\history\handler.py -DestinationPath deploy\history.zip -Force
powershell Compress-Archive -Path esg-reporting-poc\lambda\athena_query\handler.py -DestinationPath deploy\athena_query.zip -Force
powershell Compress-Archive -Path esg-reporting-poc\lambda\dashboard_data\handler.py -DestinationPath deploy\dashboard_data.zip -Force
powershell Compress-Archive -Path esg-reporting-poc\agent\lambda_agent_tools\handler.py -DestinationPath deploy\agent_tools.zip -Force
```

**Upload to S3:**

```bash
for fn in validate_input section_gen filter_sections assembly_doc validation review_handler status_check history athena_query dashboard_data agent_tools; do
  aws s3 cp deploy/${fn}.zip s3://esg-data-raw-$ACCOUNT_ID/lambda-code/${fn}.zip
done
```

**Create functions:**

```bash
# 1. esg-validate-input
aws lambda create-function --function-name esg-validate-input \
  --runtime python3.11 --handler handler.lambda_handler \
  --role arn:aws:iam::$ACCOUNT_ID:role/ESGLambdaRole \
  --code S3Bucket=esg-data-raw-$ACCOUNT_ID,S3Key=lambda-code/validate_input.zip \
  --timeout 30 --memory-size 256 --region $REGION

# 2. esg-section-gen (largest — Bedrock + KB RAG)
aws lambda create-function --function-name esg-section-gen \
  --runtime python3.11 --handler handler.lambda_handler \
  --role arn:aws:iam::$ACCOUNT_ID:role/ESGLambdaRole \
  --code S3Bucket=esg-data-raw-$ACCOUNT_ID,S3Key=lambda-code/section_gen.zip \
  --timeout 120 --memory-size 1024 --region $REGION

# 3. esg-filter-sections (Step Functions JSONPath workaround)
aws lambda create-function --function-name esg-filter-sections \
  --runtime python3.11 --handler handler.lambda_handler \
  --role arn:aws:iam::$ACCOUNT_ID:role/ESGLambdaRole \
  --code S3Bucket=esg-data-raw-$ACCOUNT_ID,S3Key=lambda-code/filter_sections.zip \
  --timeout 30 --memory-size 256 --region $REGION

# 4. esg-assembly-doc (needs Lambda Layer)
aws lambda create-function --function-name esg-assembly-doc \
  --runtime python3.11 --handler handler.lambda_handler \
  --role arn:aws:iam::$ACCOUNT_ID:role/ESGLambdaRole \
  --code S3Bucket=esg-data-raw-$ACCOUNT_ID,S3Key=lambda-code/assembly_doc.zip \
  --timeout 120 --memory-size 1024 \
  --layers arn:aws:lambda:$REGION:$ACCOUNT_ID:layer:esg-python-docx:2 \
  --region $REGION

# 5. esg-validation (21-rule output validation)
aws lambda create-function --function-name esg-validation \
  --runtime python3.11 --handler handler.lambda_handler \
  --role arn:aws:iam::$ACCOUNT_ID:role/ESGLambdaRole \
  --code S3Bucket=esg-data-raw-$ACCOUNT_ID,S3Key=lambda-code/validation.zip \
  --timeout 60 --memory-size 512 --region $REGION

# 6. esg-review-handler (human review callback)
aws lambda create-function --function-name esg-review-handler \
  --runtime python3.11 --handler handler.lambda_handler \
  --role arn:aws:iam::$ACCOUNT_ID:role/ESGLambdaRole \
  --code S3Bucket=esg-data-raw-$ACCOUNT_ID,S3Key=lambda-code/review_handler.zip \
  --timeout 30 --memory-size 256 --region $REGION

# 7. esg-status-check
aws lambda create-function --function-name esg-status-check \
  --runtime python3.11 --handler handler.lambda_handler \
  --role arn:aws:iam::$ACCOUNT_ID:role/ESGLambdaRole \
  --code S3Bucket=esg-data-raw-$ACCOUNT_ID,S3Key=lambda-code/status_check.zip \
  --timeout 30 --memory-size 256 --region $REGION

# 8. esg-history
aws lambda create-function --function-name esg-history \
  --runtime python3.11 --handler handler.lambda_handler \
  --role arn:aws:iam::$ACCOUNT_ID:role/ESGLambdaRole \
  --code S3Bucket=esg-data-raw-$ACCOUNT_ID,S3Key=lambda-code/history.zip \
  --timeout 30 --memory-size 256 --region $REGION

# 9. esg-athena-query (data fetch for SectionGen, includes HR metrics)
aws lambda create-function --function-name esg-athena-query \
  --runtime python3.11 --handler handler.lambda_handler \
  --role arn:aws:iam::$ACCOUNT_ID:role/ESGLambdaRole \
  --code S3Bucket=esg-data-raw-$ACCOUNT_ID,S3Key=lambda-code/athena_query.zip \
  --timeout 60 --memory-size 512 --region $REGION

# 10. esg-dashboard-data (Analytics page - hybrid S3 cache + Athena refresh)
aws lambda create-function --function-name esg-dashboard-data \
  --runtime python3.11 --handler handler.lambda_handler \
  --role arn:aws:iam::$ACCOUNT_ID:role/ESGLambdaRole \
  --code S3Bucket=esg-data-raw-$ACCOUNT_ID,S3Key=lambda-code/dashboard_data.zip \
  --timeout 60 --memory-size 512 --region $REGION

# 11. esg-agent-tools (Bedrock Agent action group handler)
aws lambda create-function --function-name esg-agent-tools \
  --runtime python3.11 --handler handler.lambda_handler \
  --role arn:aws:iam::$ACCOUNT_ID:role/ESGLambdaRole \
  --code S3Bucket=esg-data-raw-$ACCOUNT_ID,S3Key=lambda-code/agent_tools.zip \
  --timeout 30 --memory-size 256 --region $REGION
```

**Verify all 11 functions:**
```bash
aws lambda list-functions --region $REGION \
  --query "Functions[?starts_with(FunctionName, 'esg-')].{Name:FunctionName,Runtime:Runtime,Memory:MemorySize,Timeout:Timeout}" \
  --output table
```

---

### 📢 Step 5: Create SNS Topics

```bash
# Human Review notifications (info only in auto-approve mode)
aws sns create-topic --name ESG-HumanReview --region $REGION

# Report completion notifications
aws sns create-topic --name ESG-ReportComplete --region $REGION
```

---

### 🔄 Step 6: Deploy Step Functions

**Upload ASL to S3 first (Windows encoding workaround):**

```bash
aws s3 cp esg-reporting-poc/step_functions/esg_orchestrator.asl.json \
  s3://esg-data-raw-$ACCOUNT_ID/scripts/esg_orchestrator.asl.json
```

**Create state machine (from CloudShell):**

```bash
# Download ASL from S3
aws s3 cp s3://esg-data-raw-$ACCOUNT_ID/scripts/esg_orchestrator.asl.json /tmp/esg_orchestrator.asl.json

# Create state machine
aws stepfunctions create-state-machine \
  --name ESGReportGenerationStateMachine \
  --definition file:///tmp/esg_orchestrator.asl.json \
  --role-arn arn:aws:iam::$ACCOUNT_ID:role/ESGStepFunctionsRole \
  --type STANDARD \
  --region $REGION
```

**State Machine Flow:**
```
ValidateInput → WaitForGlueJobs (Parallel: Scope1+2+3)
  → TriggerAggregation → QueryAthena (including HR metrics for Social)
  → GenerateSections (Map, MaxConcurrency:3)
      [per section: SectionGen → Validation → Choice]
        PASS → Accumulate
        WARN → AccumulateWithWarning
        RETRY → Re-gen once → Re-validate
        FAIL_NO_RETRY → Auto-Approve → AccumulateWithWarning
  → FilterSections → AssembleDocument → NotifyCompletion → Success (outputs assembly_result)
```

**Verify:**
```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:$REGION:$ACCOUNT_ID:stateMachine:ESGReportGenerationStateMachine \
  --region $REGION
```

---

### 🌐 Step 7: Deploy API Gateway

#### 7.1 Create REST API

```bash
API_ID=$(aws apigateway create-rest-api \
  --name "ESG-Chat-API" \
  --description "ESG Report Generation API" \
  --endpoint-configuration types=REGIONAL \
  --region $REGION \
  --query 'id' --output text)

echo "API ID: $API_ID"

ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id $API_ID --region $REGION \
  --query 'items[0].id' --output text)
```

#### 7.2 Create Resources & Methods

```bash
# /chat (POST) — proxied to Bedrock Agent via esg-chat-proxy
CHAT_ID=$(aws apigateway create-resource --rest-api-id $API_ID --parent-id $ROOT_ID --path-part chat --region $REGION --query 'id' --output text)
aws apigateway put-method --rest-api-id $API_ID --resource-id $CHAT_ID --http-method POST --authorization-type NONE --region $REGION

# /status (GET)
STATUS_ID=$(aws apigateway create-resource --rest-api-id $API_ID --parent-id $ROOT_ID --path-part status --region $REGION --query 'id' --output text)
aws apigateway put-method --rest-api-id $API_ID --resource-id $STATUS_ID --http-method GET --authorization-type NONE --region $REGION

# /history (GET)
HISTORY_ID=$(aws apigateway create-resource --rest-api-id $API_ID --parent-id $ROOT_ID --path-part history --region $REGION --query 'id' --output text)
aws apigateway put-method --rest-api-id $API_ID --resource-id $HISTORY_ID --http-method GET --authorization-type NONE --region $REGION

# /dashboard-data (GET)
DASHBOARD_ID=$(aws apigateway create-resource --rest-api-id $API_ID --parent-id $ROOT_ID --path-part dashboard-data --region $REGION --query 'id' --output text)
aws apigateway put-method --rest-api-id $API_ID --resource-id $DASHBOARD_ID --http-method GET --authorization-type NONE --region $REGION
```

#### 7.3 Lambda Integrations & Permissions

```bash
# Integrate each endpoint with its Lambda (AWS_PROXY type)
for resource in "chat:esg-chat-proxy:POST:$CHAT_ID" "status:esg-status-check:GET:$STATUS_ID" "history:esg-history:GET:$HISTORY_ID" "dashboard-data:esg-dashboard-data:GET:$DASHBOARD_ID"; do
  IFS=':' read -r path fn method rid <<< "$resource"
  
  aws apigateway put-integration --rest-api-id $API_ID --resource-id $rid \
    --http-method $method --type AWS_PROXY --integration-http-method POST \
    --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$fn/invocations" \
    --region $REGION

  aws lambda add-permission --function-name $fn \
    --statement-id apigateway-invoke --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*" \
    --region $REGION
done
```

#### 7.4 Enable CORS

```bash
for RESOURCE_ID in $CHAT_ID $STATUS_ID $HISTORY_ID $DASHBOARD_ID; do
  aws apigateway put-method --rest-api-id $API_ID --resource-id $RESOURCE_ID \
    --http-method OPTIONS --authorization-type NONE --region $REGION

  aws apigateway put-integration --rest-api-id $API_ID --resource-id $RESOURCE_ID \
    --http-method OPTIONS --type MOCK \
    --request-templates '{"application/json":"{\"statusCode\": 200}"}' --region $REGION

  aws apigateway put-method-response --rest-api-id $API_ID --resource-id $RESOURCE_ID \
    --http-method OPTIONS --status-code 200 \
    --response-parameters '{"method.response.header.Access-Control-Allow-Headers":true,"method.response.header.Access-Control-Allow-Methods":true,"method.response.header.Access-Control-Allow-Origin":true}' \
    --region $REGION

  aws apigateway put-integration-response --rest-api-id $API_ID --resource-id $RESOURCE_ID \
    --http-method OPTIONS --status-code 200 \
    --response-parameters '{"method.response.header.Access-Control-Allow-Headers":"'\''Content-Type,X-Amz-Date,Authorization,X-Api-Key'\''","method.response.header.Access-Control-Allow-Methods":"'\''GET,POST,OPTIONS'\''","method.response.header.Access-Control-Allow-Origin":"'\''*'\''"}'  \
    --region $REGION
done
```

#### 7.5 Deploy API

```bash
aws apigateway create-deployment --rest-api-id $API_ID --stage-name prod \
  --description "Production deployment" --region $REGION

echo "API URL: https://$API_ID.execute-api.$REGION.amazonaws.com/prod"
```

---

### 🤖 Step 8: Deploy Bedrock Agent & Knowledge Base

#### 8.1 Upload Knowledge Base Documents

```bash
# Upload ESG framework PDFs and reference documents
aws s3 cp esg-reporting-poc/data/kb_docs/ s3://esg-kb-documents-$ACCOUNT_ID/ --recursive

# Upload prompts and templates
aws s3 cp esg-reporting-poc/prompts/ s3://esg-kb-documents-$ACCOUNT_ID/prompts/ --recursive
```

**Knowledge Base Documents (~15 files):**
- GRI 305 Emissions Standard
- IFRS S2 Climate Disclosures
- CSRD/ESRS E1 Climate Change
- OJK POJK 51/2017 Sustainable Finance
- PCAF Global GHG Accounting Standard
- Sample ESG reports (BCA, BRI, DBS, Mandiri, OCBC)
- Section templates (scope1, scope2, scope3_pcaf, intensity, methodology, summary, social)
- Overlay file: `overlay_esrs_e1.txt`

#### 8.2 Create Knowledge Base (Console recommended)

**Configuration:**
| Setting | Value |
|---------|-------|
| Name | ESG-Framework-KB |
| Data Source | S3 (`s3://esg-kb-documents-{ACCOUNT_ID}/`) |
| Chunking Strategy | **Semantic** |
| Max Sentences per Chunk | 1 |
| Token Size | 700 |
| Similarity Percentile Threshold | 90% |
| Embedding Model | Amazon Titan Embeddings V2 (1024 dimensions) |
| Vector Store | OpenSearch Serverless (Quick Create) |
| Foundation Model (parser) | Claude Sonnet 4.5 |
| Min Relevance Score | **0.40** |

> Note: Semantic chunking preserves regulatory clause boundaries. The 0.40 threshold is lower than typical (0.65) because semantic chunking produces different score distributions.

#### 8.3 Create Bedrock Agent

```bash
# Create agent
AGENT_ID=$(aws bedrock-agent create-agent \
  --agent-name ESGReportAgent \
  --foundation-model "us.anthropic.claude-sonnet-4-5-20250929-v1:0" \
  --instruction "$(cat esg-reporting-poc/agent/agent_instructions.txt)" \
  --agent-resource-role-arn arn:aws:iam::$ACCOUNT_ID:role/ESGBedrockAgentRole \
  --region $REGION \
  --query 'agent.agentId' --output text)

# Add action group (4 tools)
aws bedrock-agent create-agent-action-group \
  --agent-id $AGENT_ID --agent-version DRAFT \
  --action-group-name ESGReportActions \
  --action-group-executor lambda=arn:aws:lambda:$REGION:$ACCOUNT_ID:function:esg-agent-tools \
  --api-schema '{"payload":"'$(base64 -w0 esg-reporting-poc/agent/openapi_schema.json)'"}' \
  --region $REGION

# Grant Bedrock permission to invoke Lambda
aws lambda add-permission --function-name esg-agent-tools \
  --statement-id bedrock-agent-invoke --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:$REGION:$ACCOUNT_ID:agent/$AGENT_ID" \
  --region $REGION

# Associate Knowledge Base
aws bedrock-agent associate-agent-knowledge-base \
  --agent-id $AGENT_ID --agent-version DRAFT \
  --knowledge-base-id $KB_ID \
  --description "ESG Framework Documentation (GRI, IFRS, CSRD, OJK, PCAF)" \
  --region $REGION

# Prepare and create alias
aws bedrock-agent prepare-agent --agent-id $AGENT_ID --region $REGION
sleep 30  # Wait for preparation

AGENT_ALIAS_ID=$(aws bedrock-agent create-agent-alias \
  --agent-id $AGENT_ID --agent-alias-name esg-report-agent-v2 \
  --region $REGION --query 'agentAlias.agentAliasId' --output text)

echo "Agent ID: $AGENT_ID"
echo "Agent Alias: $AGENT_ALIAS_ID"
```

**Agent Tools:**
| Tool | Purpose | Backend |
|------|---------|---------|
| `generate_report` | Triggers Step Functions pipeline | `sfn.start_execution()` |
| `check_status` | Checks execution status | `sfn.describe_execution()` |
| `download_report` | Generates presigned S3 URL (1hr expiry) | `s3.generate_presigned_url()` |
| `list_available_data` | Returns available years/frameworks | Static response |

---

### 🎨 Step 9: Deploy Frontend (Amplify)

#### 9.1 Update API URL

Edit `esg-chat-app-react/src/api.js`:

```javascript
export const API_BASE_URL = `https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod`
```

#### 9.2 Deploy via GitHub + Amplify

```bash
cd esg-chat-app-react
git add .
git commit -m "config: update API endpoint for production"
git push origin main
```

**Amplify Console Setup:**
1. AWS Console → Amplify → New app → Host web app
2. Select GitHub → Authorize → Select `radityar21/esg-chat-app`
3. Branch: `main`
4. Amplify auto-detects `amplify.yml` at repo root
5. Deploy (5-10 min build)

**Build configuration (amplify.yml):**
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

---

## Post-Deployment Configuration

### 1. Upload Section Templates to S3

```bash
aws s3 cp esg-reporting-poc/templates/ \
  s3://esg-kb-documents-$ACCOUNT_ID/prompts/templates/ --recursive
```

**Templates (8 total):**
- `scope1_template.txt` — GRI 305-1 Scope 1 emissions
- `scope2_template.txt` — GRI 305-2 Scope 2 emissions
- `scope3_pcaf_template.txt` — Scope 3 PCAF financed emissions
- `intensity_template.txt` — Emission intensity
- `methodology_template.txt` — GHG methodology
- `summary_template.txt` — Executive summary
- `social_template.txt` — Social (S) pillar (GRI 2-7, 401-1, 404-1, 405-1, 406-1) **[NEW W5]**
- `overlay_esrs_e1.txt` — CSRD/ESRS E1 overlay

### 2. Sync Knowledge Base

```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DATA_SOURCE_ID \
  --region $REGION
```

### 3. Test Complete Pipeline

```bash
# Start execution with Social section
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:$REGION:$ACCOUNT_ID:stateMachine:ESGReportGenerationStateMachine \
  --input '{
    "reporting_year": 2024,
    "framework": "GRI_305",
    "bank_id": "GENERIC_FI_001",
    "output_bucket": "esg-output-reports-'$ACCOUNT_ID'",
    "revenue_idr_billion": 92000.0,
    "kb_id": "'$KB_ID'",
    "section_templates": [
      {"template_id": "scope1", "framework": "GRI_305"},
      {"template_id": "scope2", "framework": "GRI_305"},
      {"template_id": "scope3_pcaf", "framework": "GRI_305"},
      {"template_id": "intensity", "framework": "GRI_305"},
      {"template_id": "social", "framework": "GRI_305"},
      {"template_id": "summary", "framework": "NONE"}
    ]
  }' --region $REGION
```

---

## Verification & Testing

### End-to-End Test

1. **Open Frontend:** Navigate to Amplify URL
2. **Go to Chat page**
3. **Send message:** "Generate a GRI 305 report for 2024 with revenue 92000 billion IDR"
4. **Agent responds** with execution ID
5. **Auto-polling starts** (30s intervals, up to 15 minutes)
6. **Report generates** (3-5 minutes for single framework)
7. **Download button appears** with presigned URL
8. **Verify DOCX:** Open in Word — check sections include Social (S) pillar

### Health Checks

```bash
# All Lambdas
aws lambda list-functions --region $REGION \
  --query "Functions[?starts_with(FunctionName, 'esg-')].{Name:FunctionName,State:State}" --output table

# Step Functions
aws stepfunctions list-state-machines --region $REGION

# Recent executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:$REGION:$ACCOUNT_ID:stateMachine:ESGReportGenerationStateMachine \
  --max-results 5 --region $REGION

# API Gateway
aws apigateway get-rest-apis --region $REGION --query "items[?name=='ESG-Chat-API']"

# S3 buckets
aws s3 ls | grep esg

# Dashboard endpoint
curl "https://$API_ID.execute-api.$REGION.amazonaws.com/prod/dashboard-data"
```

---

## Troubleshooting

### Lambda Errors

**Issue:** `Runtime.ImportModuleError: Unable to import module 'handler'`
```bash
# Verify zip contains handler.py at root (not nested in folder)
unzip -l deploy/function_name.zip
# Fix: re-zip with correct structure
```

**Issue:** `lxml` import error in esg-assembly-doc
```bash
# Layer was built on Windows — must rebuild on Linux
# See Step 3 (CloudShell build commands)
```

**Issue:** `AccessDeniedException: User is not authorized to perform bedrock:InvokeModel`
```bash
# ESGLambdaRole needs inference-profile/* permissions (not just foundation-model/*)
# Verify IAM policy includes both ARN patterns:
#   arn:aws:bedrock:*::foundation-model/*
#   arn:aws:bedrock:*::inference-profile/*
```

### Step Functions Issues

**Issue:** `file://` encoding error when deploying ASL from Windows
```bash
# Solution: Upload to S3 first, then download in CloudShell
aws s3 cp esg_orchestrator.asl.json s3://esg-data-raw-$ACCOUNT_ID/scripts/
# In CloudShell:
aws s3 cp s3://esg-data-raw-$ACCOUNT_ID/scripts/esg_orchestrator.asl.json /tmp/
aws stepfunctions update-state-machine --state-machine-arn $SFN_ARN --definition file:///tmp/esg_orchestrator.asl.json
```

**Issue:** Step Functions output doesn't contain `assembly_result`
```bash
# The Success state must be a Pass type that outputs $.assembly_result
# NotifyCompletion must use ResultPath: "$.sns_result" to preserve state
```

### Bedrock Agent Issues

**Issue:** Agent formats URLs with markdown that corrupts presigned URLs
```
# Known issue: Agent adds []() formatting around S3 presigned URLs
# Frontend handles this: regex strips trailing ) and ] from URLs
# No backend fix needed — frontend regex handles it
```

**Issue:** `ThrottlingException: Rate exceeded`
```bash
# Request quota increase via Service Quotas
aws service-quotas request-service-quota-increase \
  --service-code bedrock --quota-code L-xxx --desired-value 100 --region $REGION
```

### Presigned URL Issues

**Issue:** Presigned URL returns `SignatureDoesNotMatch`
```bash
# KMS-encrypted S3 objects require signature_version='s3v4'
# Verify agent_tools Lambda uses:
#   config = Config(signature_version='s3v4')
#   s3_client = boto3.client('s3', config=config)
```

### API Gateway CORS

**Issue:** `No 'Access-Control-Allow-Origin' header`
```bash
# Re-run CORS setup (Step 7.4) or verify OPTIONS method exists on each resource
```

### Frontend Deployment

**Issue:** 404 on assets after Amplify deploy
```bash
# Verify amplify.yml baseDirectory: esg-chat-app-react/dist
# Verify public/_redirects exists with: /* /index.html 200
```

**Issue:** White page on load
```bash
# Missing _redirects file for SPA routing
echo "/* /index.html 200" > esg-chat-app-react/public/_redirects
git add . && git commit -m "fix: add SPA redirects" && git push
```

---

## Known Validation Issues (False Positives)

> These are calibration issues in the validation layer, NOT data errors. Auto-approve is the correct approach for POC/demo.

### VAL-NUM-01: Scientific Notation Mismatch

**Symptom:** Validator flags correct numbers (e.g., `21,976,797.30 tCO2e` vs `2.19767973E7`)

**Root Cause:** Regex extraction produces scientific notation string. Float comparison would be equal but string matching fails.

**Impact:** LOW — numbers are correct

**Fix:** Normalize both sides to float before comparison, or add `round(val, 2)` variants to allowed set.

### VAL-NUM-01/03: LLM-Derived Percentages

**Symptom:** "35.3% not in source" flagged as fabricated

**Root Cause:** LLM calculates `1199.79 / 3402.99 × 100 = 35.3%`. Mathematically correct but not verbatim in DATA INPUT (only totals sent, not percentages).

**Impact:** LOW — calculation is correct

**DI-2 Tradeoff:** Spec says "model MUST NOT perform arithmetic" but derived percentages make reports more readable. For production: pre-compute all common percentages in aggregation layer.

### VAL-NUM-07: Table Values Not in Paragraphs

**Symptom:** "Table value 131.4422 not found in paragraphs"

**Root Cause:** LLM generates detailed tables (10 rows × multiple columns). Narrative summarizes, doesn't repeat every value.

**Impact:** LOW — values from Athena source, table is correct

**Fix:** Downgrade VAL-NUM-07 to informational only.

### Sector Values Not in Allowed Set

**Symptom:** Sector-level PCAF data flagged as fabricated

**Root Cause:** `source_metrics` passed to ValidationFn only contains `ghg_summary` (aggregated totals). Sector breakdown (`pcaf_sectors`) is sent to SectionGenFn but NOT to ValidationFn.

**Impact:** MEDIUM — causes unnecessary validation failures

**Fix:** Pass full `athena_query_result` (including `pcaf_sectors` + `scope1_facilities`) to ValidationFn.

---

## Rollback Procedures

### Delete All Infrastructure

```bash
# Delete Lambda functions
for fn in esg-validate-input esg-section-gen esg-filter-sections esg-assembly-doc esg-validation esg-review-handler esg-status-check esg-history esg-athena-query esg-dashboard-data esg-agent-tools esg-chat-proxy; do
  aws lambda delete-function --function-name $fn --region $REGION 2>/dev/null
done

# Delete Step Functions
aws stepfunctions delete-state-machine \
  --state-machine-arn arn:aws:states:$REGION:$ACCOUNT_ID:stateMachine:ESGReportGenerationStateMachine \
  --region $REGION

# Delete API Gateway
aws apigateway delete-rest-api --rest-api-id $API_ID --region $REGION

# Delete SNS Topics
aws sns delete-topic --topic-arn arn:aws:sns:$REGION:$ACCOUNT_ID:ESG-HumanReview
aws sns delete-topic --topic-arn arn:aws:sns:$REGION:$ACCOUNT_ID:ESG-ReportComplete

# Delete S3 buckets (WARNING: deletes all data — irreversible)
for bucket in esg-data-raw esg-data-curated esg-data-aggregated esg-output-reports esg-kb-documents esg-athena-results; do
  aws s3 rb s3://${bucket}-$ACCOUNT_ID --force 2>/dev/null
done

# Delete IAM roles (must detach policies first)
for role in ESGLambdaRole ESGStepFunctionsRole ESGGlueRole; do
  aws iam delete-role --role-name $role 2>/dev/null
done
```

---

## 📚 Additional Resources

| Document | Purpose | Location |
|----------|---------|----------|
| Architecture Diagrams | Visual system design | `architecture/README.md` |
| Lambda Functions Ref | All 11 Lambda details | `esg-reporting-poc/lambda/README.md` |
| Agent Setup | Bedrock Agent config | `esg-reporting-poc/agent/README.md` |
| Frontend Guide | React/Vite development | `esg-chat-app-react/README.md` |
| Infrastructure Spec | Complete resource spec | `INFRASTRUCTURE_SPEC.md` |
| Implementation Changelog | 91 spec deviations (W1-W6) | `esg-reporting-poc/docs/IMPLEMENTATION_CHANGELOG.md` |
| Spec Amendments | 76 tracked amendments | `esg-reporting-poc/docs/SPEC_AMENDMENTS.md` |
| Validation False Positives | Known validator issues | `esg-reporting-poc/docs/VALIDATION_FALSE_POSITIVES.md` |
| Infrastructure Reference | Current deployed configs | `esg-reporting-poc/docs/INFRASTRUCTURE_REFERENCE.md` |

---

**Deployment complete!** 🎉

For live log monitoring:
```bash
aws logs tail /aws/lambda/esg-section-gen --follow --region $REGION
```
