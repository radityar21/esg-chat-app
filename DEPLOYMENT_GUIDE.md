# ESG Reporting System - Complete Deployment Guide

**Tokaicom Mitra Indonesia (Tokai Group)**  
**Version:** 1.0  
**Last Updated:** June 15, 2026

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
9. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Required Tools

| Tool | Version | Purpose | Installation |
|------|---------|---------|--------------|
| **AWS CLI** | 2.x | Infrastructure deployment | `aws --version` |
| **Node.js** | 18+ | Frontend build | `node --version` |
| **npm** | 9+ | Package management | `npm --version` |
| **Python** | 3.12 | Lambda runtime | `python --version` |
| **Git** | 2.x | Version control | `git --version` |
| **AWS CDK** (optional) | 2.x | IaC deployment | `npm install -g aws-cdk` |

### AWS Account Requirements

- **AWS Account ID** with appropriate permissions
- **IAM User/Role** with these managed policies:
  - `AdministratorAccess` (for initial setup) OR
  - Custom policy with: IAM, Lambda, S3, Step Functions, Bedrock, API Gateway, Amplify, Glue, Athena permissions
- **AWS Region:** `ap-southeast-1` (Singapore) - can be changed
- **Bedrock Model Access:** Claude 3.5 Sonnet v2 enabled in target region

### Cost Estimate

| Component | Setup Cost | Monthly Cost (100 reports) |
|-----------|-----------|---------------------------|
| S3 Storage | Free | ~$5 |
| Lambda | Free | ~$2 |
| Bedrock API | $0 | ~$15 |
| Step Functions | Free | ~$2.50 |
| API Gateway | Free | ~$3.50 |
| Athena | Free | ~$1 |
| Amplify Hosting | Free | $0 (free tier) |
| **Total** | **$0** | **~$29/month** |

---

## Architecture Overview

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────────────────────────┐
│  Frontend (React + Amplify)                     │
│  - Overview, Analytics, Chat, Reports          │
└──────┬──────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────────┐
│  API Gateway (REST)                             │
│  /chat, /status, /history, /dashboard-data    │
└──────┬──────────────────────────────────────────┘
       │
   ┌───┴────┬──────────────┬────────────┐
   │        │              │            │
   ↓        ↓              ↓            ↓
┌────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐
│Bedrock │ │ Lambda   │ │  Step    │ │Lambda       │
│ Agent  │ │(status,  │ │Functions │ │(dashboard)  │
│        │ │ history) │ │          │ │             │
└────────┘ └──────────┘ └─────┬────┘ └─────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ↓              ↓              ↓
          ┌─────────┐    ┌──────────┐  ┌──────────┐
          │ Lambda  │    │  Lambda  │  │  Lambda  │
          │validate │    │ section_ │  │ assembly │
          │         │    │   gen    │  │   _doc   │
          └─────────┘    └────┬─────┘  └────┬─────┘
                               │             │
                               ↓             ↓
                          ┌─────────────────────┐
                          │   Amazon Bedrock    │
                          │ (Claude 3.5 Sonnet) │
                          └─────────────────────┘
                                    │
                                    ↓
                          ┌──────────────────────┐
                          │  S3 Buckets          │
                          │  - Reports (DOCX)    │
                          │  - Athena Results   │
                          │  - Knowledge Base   │
                          └──────────────────────┘
```

**Key Components:** 11 Lambda functions, 1 Step Functions, 1 API Gateway, 1 Bedrock Agent, 3 S3 buckets, Glue/Athena for analytics

**Deployment Time:** ~30-45 minutes (manual) or ~15-20 minutes (CDK)

---

## Deployment Sequence

**CRITICAL:** Follow this exact order to avoid dependency issues.

```
1. IAM Roles & Policies ✅
2. S3 Buckets ✅
3. Glue Data Catalog ✅
4. Lambda Layer (python-docx, python-pptx) ✅
5. Lambda Functions (10 functions) ✅
6. Step Functions State Machine ✅
7. API Gateway ✅
8. Bedrock Agent ✅
9. Bedrock Knowledge Base ✅
10. Frontend (Amplify) ✅
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
cdk bootstrap aws://YOUR_ACCOUNT_ID/ap-southeast-1
```

### Step 2: Configure Parameters

Edit `esg-reporting-poc/infra/cdk.json`:

```json
{
  "context": {
    "account_id": "YOUR_ACCOUNT_ID",
    "region": "ap-southeast-1",
    "project_name": "esg-reporting"
  }
}
```

### Step 3: Deploy All Infrastructure

```bash
# Deploy everything (30-45 min)
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

### 🔧 Step 1: Setup IAM Roles

Run the automated setup script:

```bash
cd esg-reporting-poc/scripts
chmod +x setup_account.sh
./setup_account.sh
```

**What it creates:**
- ✅ `ESGLambdaExecutionRole`
- ✅ `ESGStepFunctionsRole`
- ✅ `ESGBedrockAgentRole`
- ✅ `ESGAPIGatewayRole`
- ✅ `ESGGlueETLRole`
- ✅ 3 S3 buckets
- ✅ Glue database

**Verify:**
```bash
aws iam get-role --role-name ESGLambdaExecutionRole
aws s3 ls | grep esg
```

---

### 📦 Step 2: Build & Deploy Lambda Layer


The Lambda layer contains python-docx, python-pptx, and matplotlib for document generation.

```bash
cd esg-reporting-poc/deploy/layer

# Build layer (Linux packages for Lambda)
docker run --rm -v "$PWD":/var/task public.ecr.aws/lambda/python:3.12 /bin/bash -c "pip install python-docx python-pptx matplotlib pillow -t /var/task/python"

# Create zip
zip -r ../layer.zip python/

# Upload to Lambda
aws lambda publish-layer-version \
  --layer-name esg-reporting-layer \
  --zip-file fileb://../layer.zip \
  --compatible-runtimes python3.12 \
  --region ap-southeast-1
```

**Output:** Note the `LayerVersionArn` (needed for Lambda functions)

**Alternative (if Docker not available):** Use pre-built layer in `deploy/layer.zip`

---

### ⚡ Step 3: Deploy Lambda Functions

Deploy all 11 Lambda functions in correct order:

#### 3.1 Core Step Functions Lambdas

```bash
cd ../lambda

# 1. validate_input
cd validate_input
zip -r ../../../deploy/validate_input.zip handler.py
aws lambda create-function \
  --function-name esg-validate-input \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGLambdaExecutionRole \
  --handler handler.lambda_handler \
  --zip-file fileb://../../deploy/validate_input.zip \
  --timeout 10 \
  --memory-size 128 \
  --region ap-southeast-1

# 2. section_gen (MOST IMPORTANT - generates report content)
cd ../section_gen
zip -r ../../../deploy/section_gen.zip handler.py
aws lambda create-function \
  --function-name esg-section-gen \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGLambdaExecutionRole \
  --handler handler.lambda_handler \
  --zip-file fileb://../../deploy/section_gen.zip \
  --timeout 600 \
  --memory-size 512 \
  --region ap-southeast-1 \
  --environment Variables="{BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v2:0}"

# 3. filter_sections
cd ../filter_sections
zip -r ../../../deploy/filter_sections.zip handler.py
aws lambda create-function \
  --function-name esg-filter-sections \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGLambdaExecutionRole \
  --handler handler.lambda_handler \
  --zip-file fileb://../../deploy/filter_sections.zip \
  --timeout 30 \
  --memory-size 256 \
  --region ap-southeast-1

# 4. assembly_doc (needs Lambda layer for docx/pptx)
cd ../assembly_doc
zip -r ../../../deploy/assembly_doc.zip handler.py
aws lambda create-function \
  --function-name esg-assembly-doc \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGLambdaExecutionRole \
  --handler handler.lambda_handler \
  --zip-file fileb://../../deploy/assembly_doc.zip \
  --timeout 300 \
  --memory-size 1024 \
  --layers arn:aws:lambda:ap-southeast-1:YOUR_ACCOUNT_ID:layer:esg-reporting-layer:1 \
  --region ap-southeast-1 \
  --environment Variables="{OUTPUT_BUCKET=esg-reporting-output-bucket}"

# 5. validation
cd ../validation
zip -r ../../../deploy/validation.zip handler.py
aws lambda create-function \
  --function-name esg-validation \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGLambdaExecutionRole \
  --handler handler.lambda_handler \
  --zip-file fileb://../../deploy/validation.zip \
  --timeout 30 \
  --memory-size 256 \
  --region ap-southeast-1

# 6. review_handler
cd ../review_handler
zip -r ../../../deploy/review_handler.zip handler.py
aws lambda create-function \
  --function-name esg-review-handler \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGLambdaExecutionRole \
  --handler handler.lambda_handler \
  --zip-file fileb://../../deploy/review_handler.zip \
  --timeout 10 \
  --memory-size 128 \
  --region ap-southeast-1
```

#### 3.2 API Gateway Lambdas

```bash
# 7. status_check
cd ../status_check
zip -r ../../../deploy/status_check.zip handler.py
aws lambda create-function \
  --function-name esg-status-check \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGLambdaExecutionRole \
  --handler handler.lambda_handler \
  --zip-file fileb://../../deploy/status_check.zip \
  --timeout 10 \
  --memory-size 128 \
  --region ap-southeast-1 \
  --environment Variables="{STEP_FUNCTION_ARN=arn:aws:states:ap-southeast-1:YOUR_ACCOUNT_ID:stateMachine:esg-orchestrator}"

# 8. history
cd ../history
zip -r ../../../deploy/history.zip handler.py
aws lambda create-function \
  --function-name esg-history \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGLambdaExecutionRole \
  --handler handler.lambda_handler \
  --zip-file fileb://../../deploy/history.zip \
  --timeout 10 \
  --memory-size 128 \
  --region ap-southeast-1

# 9. athena_query
cd ../athena_query
zip -r ../../../deploy/athena_query.zip handler.py
aws lambda create-function \
  --function-name esg-athena-query \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGLambdaExecutionRole \
  --handler handler.lambda_handler \
  --zip-file fileb://../../deploy/athena_query.zip \
  --timeout 60 \
  --memory-size 256 \
  --region ap-southeast-1 \
  --environment Variables="{ATHENA_DATABASE=esg_reporting_db,ATHENA_OUTPUT_BUCKET=esg-athena-results}"

# 10. dashboard_data
cd ../dashboard_data
zip -r ../../../deploy/dashboard_data.zip handler.py
aws lambda create-function \
  --function-name esg-dashboard-data \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGLambdaExecutionRole \
  --handler handler.lambda_handler \
  --zip-file fileb://../../deploy/dashboard_data.zip \
  --timeout 30 \
  --memory-size 512 \
  --region ap-southeast-1 \
  --environment Variables="{ATHENA_DATABASE=esg_reporting_db,CACHE_BUCKET=esg-athena-results}"
```

#### 3.3 Bedrock Agent Lambda

```bash
# 11. agent_tools (for Bedrock Agent)
cd ../../agent/lambda_agent_tools
zip -r ../../../deploy/agent_tools.zip handler.py
aws lambda create-function \
  --function-name esg-agent-tools \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGLambdaExecutionRole \
  --handler handler.lambda_handler \
  --zip-file fileb://../../deploy/agent_tools.zip \
  --timeout 10 \
  --memory-size 256 \
  --region ap-southeast-1 \
  --environment Variables="{STEP_FUNCTION_ARN=arn:aws:states:ap-southeast-1:YOUR_ACCOUNT_ID:stateMachine:esg-orchestrator,OUTPUT_BUCKET=esg-reporting-output-bucket}"
```

**Verify all 11 functions:**
```bash
aws lambda list-functions --region ap-southeast-1 --query "Functions[?starts_with(FunctionName, 'esg-')].FunctionName"
```

---

### 🔄 Step 4: Deploy Step Functions

```bash
cd ../../step_functions

# Create state machine
aws stepfunctions create-state-machine \
  --name esg-orchestrator \
  --definition file://esg_orchestrator.asl.json \
  --role-arn arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGStepFunctionsRole \
  --region ap-southeast-1
```

**Verify:**
```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:ap-southeast-1:YOUR_ACCOUNT_ID:stateMachine:esg-orchestrator \
  --region ap-southeast-1
```

---

### 🌐 Step 5: Deploy API Gateway


#### 5.1 Create REST API

```bash
# Create API
API_ID=$(aws apigateway create-rest-api \
  --name "ESG Reporting API" \
  --description "API for ESG Report Generation System" \
  --endpoint-configuration types=REGIONAL \
  --region ap-southeast-1 \
  --query 'id' \
  --output text)

echo "API ID: $API_ID"

# Get root resource ID
ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id $API_ID \
  --region ap-southeast-1 \
  --query 'items[0].id' \
  --output text)
```

#### 5.2 Create Resources & Methods

```bash
# /chat endpoint
CHAT_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part chat \
  --region ap-southeast-1 \
  --query 'id' \
  --output text)

aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $CHAT_ID \
  --http-method POST \
  --authorization-type NONE \
  --region ap-southeast-1

# /status endpoint
STATUS_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part status \
  --region ap-southeast-1 \
  --query 'id' \
  --output text)

aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $STATUS_ID \
  --http-method GET \
  --authorization-type NONE \
  --region ap-southeast-1 \
  --request-parameters method.request.querystring.execution_id=true

# /history endpoint
HISTORY_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part history \
  --region ap-southeast-1 \
  --query 'id' \
  --output text)

aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $HISTORY_ID \
  --http-method GET \
  --authorization-type NONE \
  --region ap-southeast-1

# /dashboard-data endpoint
DASHBOARD_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part dashboard-data \
  --region ap-southeast-1 \
  --query 'id' \
  --output text)

aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $DASHBOARD_ID \
  --http-method GET \
  --authorization-type NONE \
  --region ap-southeast-1
```

#### 5.3 Create Lambda Integrations

```bash
# Get Lambda ARNs
STATUS_ARN="arn:aws:lambda:ap-southeast-1:YOUR_ACCOUNT_ID:function:esg-status-check"
HISTORY_ARN="arn:aws:lambda:ap-southeast-1:YOUR_ACCOUNT_ID:function:esg-history"
DASHBOARD_ARN="arn:aws:lambda:ap-southeast-1:YOUR_ACCOUNT_ID:function:esg-dashboard-data"

# Integrate /status with Lambda
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $STATUS_ID \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:ap-southeast-1:lambda:path/2015-03-31/functions/$STATUS_ARN/invocations \
  --region ap-southeast-1

# Integrate /history with Lambda
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $HISTORY_ID \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:ap-southeast-1:lambda:path/2015-03-31/functions/$HISTORY_ARN/invocations \
  --region ap-southeast-1

# Integrate /dashboard-data with Lambda
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $DASHBOARD_ID \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:ap-southeast-1:lambda:path/2015-03-31/functions/$DASHBOARD_ARN/invocations \
  --region ap-southeast-1

# Grant API Gateway permission to invoke Lambdas
aws lambda add-permission \
  --function-name esg-status-check \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:ap-southeast-1:YOUR_ACCOUNT_ID:$API_ID/*" \
  --region ap-southeast-1

aws lambda add-permission \
  --function-name esg-history \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:ap-southeast-1:YOUR_ACCOUNT_ID:$API_ID/*" \
  --region ap-southeast-1

aws lambda add-permission \
  --function-name esg-dashboard-data \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:ap-southeast-1:YOUR_ACCOUNT_ID:$API_ID/*" \
  --region ap-southeast-1
```

#### 5.4 Enable CORS

```bash
# Enable CORS for all endpoints (required for React frontend)
for RESOURCE_ID in $STATUS_ID $HISTORY_ID $DASHBOARD_ID; do
  aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method OPTIONS \
    --authorization-type NONE \
    --region ap-southeast-1

  aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method OPTIONS \
    --type MOCK \
    --request-templates '{"application/json":"{\"statusCode\": 200}"}' \
    --region ap-southeast-1

  aws apigateway put-integration-response \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters '{"method.response.header.Access-Control-Allow-Headers":"'\''Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'\''","method.response.header.Access-Control-Allow-Methods":"'\''GET,POST,OPTIONS'\''","method.response.header.Access-Control-Allow-Origin":"'\''*'\''"}'  \
    --region ap-southeast-1

  aws apigateway put-method-response \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters '{"method.response.header.Access-Control-Allow-Headers":true,"method.response.header.Access-Control-Allow-Methods":true,"method.response.header.Access-Control-Allow-Origin":true}' \
    --region ap-southeast-1
done
```

#### 5.5 Deploy API

```bash
# Deploy to 'prod' stage
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --description "Production deployment" \
  --region ap-southeast-1

# Get invoke URL
echo "API URL: https://$API_ID.execute-api.ap-southeast-1.amazonaws.com/prod"
```

**Save this URL** - needed for frontend configuration!

---

### 🤖 Step 6: Deploy Bedrock Agent

#### 6.1 Create Agent

```bash
# Create agent (via AWS Console or CLI)
AGENT_ID=$(aws bedrock-agent create-agent \
  --agent-name ESG-Report-Assistant \
  --foundation-model anthropic.claude-3-5-sonnet-20240620-v2:0 \
  --instruction file://../agent/agent_instructions.txt \
  --agent-resource-role-arn arn:aws:iam::YOUR_ACCOUNT_ID:role/ESGBedrockAgentRole \
  --region ap-southeast-1 \
  --query 'agent.agentId' \
  --output text)

echo "Agent ID: $AGENT_ID"
```

#### 6.2 Add Action Group

```bash
# Add action group with Lambda
aws bedrock-agent create-agent-action-group \
  --agent-id $AGENT_ID \
  --agent-version DRAFT \
  --action-group-name report-generation-tools \
  --action-group-executor lambda=arn:aws:lambda:ap-southeast-1:YOUR_ACCOUNT_ID:function:esg-agent-tools \
  --api-schema file://../agent/openapi_schema.json \
  --region ap-southeast-1
```

#### 6.3 Grant Lambda Permission

```bash
aws lambda add-permission \
  --function-name esg-agent-tools \
  --statement-id bedrock-agent-invoke \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:ap-southeast-1:YOUR_ACCOUNT_ID:agent/$AGENT_ID" \
  --region ap-southeast-1
```

#### 6.4 Prepare Agent

```bash
# Prepare agent (validates configuration)
aws bedrock-agent prepare-agent \
  --agent-id $AGENT_ID \
  --region ap-southeast-1
```

#### 6.5 Create Alias

```bash
# Create production alias
AGENT_ALIAS_ID=$(aws bedrock-agent create-agent-alias \
  --agent-id $AGENT_ID \
  --agent-alias-name production \
  --region ap-southeast-1 \
  --query 'agentAlias.agentAliasId' \
  --output text)

echo "Agent Alias ID: $AGENT_ALIAS_ID"
```

---

### 📚 Step 7: Deploy Knowledge Base

#### 7.1 Upload Documents to S3

```bash
# Upload ESG framework documents
aws s3 cp ../data/kb_docs/ s3://esg-knowledge-base/documents/ --recursive
```

#### 7.2 Create Knowledge Base (via Console)

**AWS Console Steps:**
1. Go to **Amazon Bedrock** → **Knowledge Bases**
2. Click **Create knowledge base**
3. Name: `ESG-Framework-KB`
4. Data source: **S3**
5. S3 URI: `s3://esg-knowledge-base/documents/`
6. Embeddings model: **Amazon Titan Embeddings v2**
7. Vector store: **Amazon OpenSearch Serverless** (auto-created)
8. Click **Create**
9. **Sync data source** (takes 5-10 min)

#### 7.3 Associate with Agent

```bash
# Get KB ID from console
KB_ID="YOUR_KB_ID"

aws bedrock-agent associate-agent-knowledge-base \
  --agent-id $AGENT_ID \
  --agent-version DRAFT \
  --knowledge-base-id $KB_ID \
  --description "ESG Framework Documentation" \
  --region ap-southeast-1
```

---

### 🎨 Step 8: Deploy Frontend (Amplify)

#### 8.1 Update API URL in Frontend

Edit `esg-chat-app-react/src/api.js`:

```javascript
export const API_BASE_URL = 'https://YOUR_API_ID.execute-api.ap-southeast-1.amazonaws.com/prod'
```

#### 8.2 Commit & Push to GitHub

```bash
cd esg-chat-app-react

git add src/api.js
git commit -m "config: update API endpoint"
git push origin main
```

#### 8.3 Setup Amplify Hosting (via Console)

**AWS Console Steps:**
1. Go to **AWS Amplify** → **All apps** → **New app** → **Host web app**
2. Select **GitHub**
3. Authorize GitHub
4. Select repository: `radityar21/esg-chat-app`
5. Branch: `main`
6. App name: `esg-chat-app`
7. Amplify will auto-detect `amplify.yml` in repo root
8. Click **Save and deploy**
9. Wait 5-10 minutes for build
10. **Copy Amplify URL** (e.g., `https://main.d337jqli3ubqmk.amplifyapp.com`)

---

## Post-Deployment Configuration

### 1. Test Lambda Functions

```bash
# Test validate_input
aws lambda invoke \
  --function-name esg-validate-input \
  --payload '{"reporting_year":2024,"framework":"GRI_305","revenue_idr_billion":92000}' \
  --region ap-southeast-1 \
  output.json

cat output.json
```

### 2. Test Step Functions

```bash
# Start execution
EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:ap-southeast-1:YOUR_ACCOUNT_ID:stateMachine:esg-orchestrator \
  --input '{"reporting_year":2024,"framework":"GRI_305","revenue_idr_billion":92000}' \
  --region ap-southeast-1 \
  --query 'executionArn' \
  --output text)

# Check status
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --region ap-southeast-1
```

### 3. Test API Gateway

```bash
# Test /status
curl "https://YOUR_API_ID.execute-api.ap-southeast-1.amazonaws.com/prod/status?execution_id=test"

# Test /history
curl "https://YOUR_API_ID.execute-api.ap-southeast-1.amazonaws.com/prod/history"

# Test /dashboard-data
curl "https://YOUR_API_ID.execute-api.ap-southeast-1.amazonaws.com/prod/dashboard-data"
```

### 4. Test Bedrock Agent

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id $AGENT_ID \
  --agent-alias-id $AGENT_ALIAS_ID \
  --session-id test-session-1 \
  --input-text "Generate a GRI 305 report for 2024" \
  --region ap-southeast-1
```

### 5. Test Frontend

Open browser: `https://YOUR_AMPLIFY_URL`

- ✅ Overview page loads
- ✅ Chat page connects to Bedrock Agent
- ✅ Analytics page shows charts
- ✅ Reports page lists executions

---

## Verification & Testing

### End-to-End Test

1. **Open Frontend:** Navigate to Amplify URL
2. **Go to Chat page**
3. **Send message:** "Generate a GRI 305 report for 2024"
4. **Agent responds** with execution ID
5. **Check status:** "What's the status of execution_abc123?"
6. **Download report** when complete (3-5 minutes)
7. **Verify DOCX:** Open report in Microsoft Word

### Health Checks

```bash
# Check all Lambda functions are deployed
aws lambda list-functions --region ap-southeast-1 --query "Functions[?starts_with(FunctionName, 'esg-')].{Name:FunctionName,Runtime:Runtime,Status:State}"

# Check Step Functions
aws stepfunctions list-state-machines --region ap-southeast-1

# Check API Gateway
aws apigateway get-rest-apis --region ap-southeast-1 --query "items[?name=='ESG Reporting API']"

# Check S3 buckets
aws s3 ls | grep esg
```

---

## Troubleshooting

### Lambda Errors

**Issue:** `Runtime.ImportModuleError: Unable to import module 'handler'`

**Solution:**
```bash
# Rebuild zip with correct structure
cd lambda/function_name
zip -r ../../deploy/function_name.zip handler.py
aws lambda update-function-code --function-name esg-function-name --zip-file fileb://../../deploy/function_name.zip --region ap-southeast-1
```

### Bedrock Throttling

**Issue:** `ThrottlingException: Rate exceeded`

**Solution:**
```bash
# Request quota increase
aws service-quotas request-service-quota-increase \
  --service-code bedrock \
  --quota-code L-xxx \
  --desired-value 100 \
  --region ap-southeast-1
```

### API Gateway CORS

**Issue:** `No 'Access-Control-Allow-Origin' header`

**Solution:** Re-run CORS setup commands in Step 5.4

### Frontend Not Loading

**Issue:** Amplify build fails

**Solution:**
```bash
# Check Amplify build logs in console
# Verify amplify.yml is correct:
cat amplify.yml
# Should have baseDirectory: esg-chat-app-react/dist
```

---

## Rollback Procedures

### Delete All Infrastructure

```bash
# Delete Lambda functions
for fn in esg-validate-input esg-section-gen esg-filter-sections esg-assembly-doc esg-validation esg-review-handler esg-status-check esg-history esg-athena-query esg-dashboard-data esg-agent-tools; do
  aws lambda delete-function --function-name $fn --region ap-southeast-1
done

# Delete Step Functions
aws stepfunctions delete-state-machine --state-machine-arn arn:aws:states:ap-southeast-1:YOUR_ACCOUNT_ID:stateMachine:esg-orchestrator --region ap-southeast-1

# Delete API Gateway
aws apigateway delete-rest-api --rest-api-id $API_ID --region ap-southeast-1

# Delete S3 buckets (WARNING: deletes all data)
aws s3 rb s3://esg-reporting-output-bucket --force
aws s3 rb s3://esg-athena-results --force
aws s3 rb s3://esg-knowledge-base --force

# Delete IAM roles
aws iam delete-role --role-name ESGLambdaExecutionRole
aws iam delete-role --role-name ESGStepFunctionsRole
aws iam delete-role --role-name ESGBedrockAgentRole
```

---

## 📚 Additional Resources

- **Architecture Diagrams:** `architecture/README.md`
- **Lambda Functions Reference:** `esg-reporting-poc/lambda/README.md`
- **Agent Setup:** `esg-reporting-poc/agent/README.md`
- **Frontend Guide:** `esg-chat-app-react/README.md`
- **Infrastructure Spec:** `INFRASTRUCTURE_SPEC.md`

---

**Deployment complete!** 🎉

For issues, check CloudWatch Logs:
```bash
aws logs tail /aws/lambda/esg-section-gen --follow --region ap-southeast-1
```
