# ESG Reporting System - Deployment Summary

**Quick Reference Guide**  
**Tokaicom Mitra Indonesia (Tokai Group)**  
**Version:** 1.1 — Crosschecked against IMPLEMENTATION_CHANGELOG, INFRASTRUCTURE_REFERENCE, SPEC_AMENDMENTS, VALIDATION_FALSE_POSITIVES

---

## 🚀 Quick Start

### Prerequisites Checklist

```
✅ AWS CLI 2.x installed
✅ AWS Account (061039769766 for POC)
✅ Region: us-east-1 (current) or ap-southeast-1 (future prod)
✅ Node.js 18+ and npm
✅ Python 3.11 (Lambda runtime)
✅ Git configured
✅ Bedrock model access: us.anthropic.claude-sonnet-4-5-20250929-v1:0
✅ CloudShell access (for Lambda Layer build — MUST be Linux)
```

### Environment Variables

```bash
export ACCOUNT_ID="061039769766"
export REGION="us-east-1"
export KB_ID="WVREXI1LEI"
export AGENT_ID="MBERNIQMBG"
export AGENT_ALIAS_ID="QIXEJW2TN6"
export SFN_ARN="arn:aws:states:us-east-1:061039769766:stateMachine:ESGReportGenerationStateMachine"
export API_ID="olj4tuggm1"
```

### Deployment Options

| Method | Time | Complexity | Use Case |
|--------|------|------------|----------|
| **Automated (CDK)** | 15-20 min | Low | Fresh deployment, reproducible |
| **Manual (CLI)** | 30-45 min | Medium | Learning, custom setup, POC |

---

## Option 1: Automated Deployment (CDK)

```bash
# 1. Setup
cd esg-reporting-poc/infra
pip install -r requirements.txt
cdk bootstrap aws://$ACCOUNT_ID/$REGION

# 2. Deploy
cdk deploy ESGInfraStack --require-approval never

# 3. Deploy Frontend
cd ../../esg-chat-app-react
git push origin main  # Amplify auto-deploys
```

---

## Option 2: Manual Deployment

### Step-by-Step Summary

| Step | Action | Tool | Time |
|------|--------|------|------|
| 1 | IAM Roles (3) + S3 Buckets (6) + Glue DBs (3) | `setup_account.sh` in CloudShell | 5 min |
| 2 | Upload synthetic data + Create Athena tables (12) | AWS CLI + SQL | 5 min |
| 3 | Run Glue ETL (Scope 1 → 2 → 3 → Aggregation) | AWS CLI | 10 min |
| 4 | Build Lambda Layer (python-docx + lxml) | CloudShell only | 3 min |
| 5 | Deploy 11 Lambda Functions | Windows zip + AWS CLI | 5 min |
| 6 | Create 2 SNS Topics | AWS CLI | 1 min |
| 7 | Deploy Step Functions | S3 upload + CloudShell | 2 min |
| 8 | Deploy API Gateway (4 endpoints + CORS) | AWS CLI | 5 min |
| 9 | Setup Knowledge Base + Bedrock Agent | Console + CLI | 10 min |
| 10 | Deploy Frontend (GitHub → Amplify) | git push | 5 min |

**See DEPLOYMENT_GUIDE.md for detailed commands.**

---

## 📊 Infrastructure Overview

### Resources Deployed

| Type | Count | Names |
|------|-------|-------|
| IAM Roles | 3 | ESGGlueRole, ESGLambdaRole, ESGStepFunctionsRole |
| S3 Buckets | 6 | esg-data-raw-*, esg-data-curated-*, esg-data-aggregated-*, esg-output-reports-*, esg-kb-documents-*, esg-athena-results-* |
| Lambda Functions | 11 | validate-input, section-gen, filter-sections, assembly-doc, validation, review-handler, status-check, history, athena-query, dashboard-data, agent-tools |
| Lambda Layer | 1 | esg-python-docx:2 (python-docx + lxml) |
| Step Functions | 1 | ESGReportGenerationStateMachine |
| API Gateway | 1 | ESG-Chat-API (4 endpoints: /chat, /status, /history, /dashboard-data) |
| Bedrock Agent | 1 | ESGReportAgent (ID: MBERNIQMBG, Alias: QIXEJW2TN6) |
| Bedrock KB | 1 | ESG-Framework-KB (ID: WVREXI1LEI) |
| Glue Databases | 3 | esg_raw, esg_curated, esg_aggregated |
| Glue ETL Jobs | 4 | scope1-direct, scope2-indirect, scope3-pcaf, aggregation |
| Athena Tables | 12 | energy_consumption, loan_portfolio, hr_metrics, ghg_scope1/2/3, ghg_summary_annual, pcaf_by_sector, scope1_by_facility |
| SNS Topics | 2 | ESG-HumanReview, ESG-ReportComplete |
| Amplify App | 1 | esg-reporting-dashboard (React + Vite + Tailwind + Recharts) |

### Lambda Function Specifications (Actual Deployed)

| Function | Runtime | Memory | Timeout | Key Feature |
|----------|---------|--------|---------|-------------|
| esg-validate-input | Python 3.11 | 256 MB | 30s | Input validation + MULTI_FRAMEWORK expansion |
| esg-section-gen | Python 3.11 | 1024 MB | 120s | Bedrock + KB RAG (8 section types incl. Social) |
| esg-filter-sections | Python 3.11 | 256 MB | 30s | Step Functions JSONPath workaround |
| esg-assembly-doc | Python 3.11 | 1024 MB | 120s | DOCX generation (needs Layer) |
| esg-validation | Python 3.11 | 512 MB | 60s | 21-rule output validation |
| esg-review-handler | Python 3.11 | 256 MB | 30s | Human review (blocked by SCP) |
| esg-status-check | Python 3.11 | 256 MB | 30s | API: check execution status |
| esg-history | Python 3.11 | 256 MB | 30s | API: list executions |
| esg-athena-query | Python 3.11 | 512 MB | 60s | Data fetch (GHG + PCAF + HR metrics) |
| esg-dashboard-data | Python 3.11 | 512 MB | 60s | Analytics (S3 cache + Athena refresh) |
| esg-agent-tools | Python 3.11 | 256 MB | 30s | Bedrock Agent 4 tools |

---

## 💰 Cost Estimate

| Scenario | Monthly Cost | Dominant Cost |
|----------|-------------|---------------|
| **Development** (10 reports) | ~$175 | OpenSearch Serverless ($173) |
| **Production** (100 reports) | ~$190 | OpenSearch + Bedrock |
| **Optimized** (without OpenSearch KB) | ~$30 | Bedrock API ($13) |

**Cost Optimization:**
- OpenSearch Serverless = $172.80/month (minimum 1 OCU-hour × 720 hrs)
- Switch to Aurora Serverless vector store → saves ~$150/month
- Or disable KB entirely (use templates only) → ~$18/month total

---

## 🔍 Monitoring Quick Commands

```bash
# Lambda logs (most common to check)
aws logs tail /aws/lambda/esg-section-gen --follow --region $REGION

# Step Functions recent executions
aws stepfunctions list-executions --state-machine-arn $SFN_ARN --max-results 5 --region $REGION

# Dashboard API (cached)
curl "https://$API_ID.execute-api.$REGION.amazonaws.com/prod/dashboard-data"

# Dashboard API (force refresh from Athena)
curl "https://$API_ID.execute-api.$REGION.amazonaws.com/prod/dashboard-data?refresh=true"

# Test agent via CLI
aws bedrock-agent-runtime invoke-agent \
  --agent-id $AGENT_ID --agent-alias-id $AGENT_ALIAS_ID \
  --session-id test-$(date +%s) \
  --input-text "List available data for ESG reports" \
  --region $REGION
```

---

## 🛠️ Common Operations

### Update Lambda Function

```cmd
REM From Windows CMD:
powershell Compress-Archive -Path esg-reporting-poc\lambda\{function}\handler.py -DestinationPath deploy\{function}.zip -Force
aws s3 cp deploy\{function}.zip s3://esg-data-raw-%ACCOUNT_ID%/lambda-code/{function}.zip
aws lambda update-function-code --function-name esg-{name} --s3-bucket esg-data-raw-%ACCOUNT_ID% --s3-key lambda-code/{function}.zip --region %REGION%
```

### Update Step Functions

```bash
# Upload to S3 (from Windows — avoids encoding issues)
aws s3 cp esg-reporting-poc\step_functions\esg_orchestrator.asl.json s3://esg-data-raw-$ACCOUNT_ID/scripts/

# Deploy from CloudShell
aws s3 cp s3://esg-data-raw-$ACCOUNT_ID/scripts/esg_orchestrator.asl.json /tmp/
aws stepfunctions update-state-machine --state-machine-arn $SFN_ARN --definition file:///tmp/esg_orchestrator.asl.json --region $REGION
```

### Update Bedrock Agent

```bash
aws bedrock-agent update-agent --agent-id $AGENT_ID \
  --instruction "$(cat esg-reporting-poc/agent/agent_instructions.txt)" \
  --agent-name ESGReportAgent \
  --foundation-model "us.anthropic.claude-sonnet-4-5-20250929-v1:0" \
  --agent-resource-role-arn arn:aws:iam::$ACCOUNT_ID:role/ESGBedrockAgentRole \
  --region $REGION

aws bedrock-agent prepare-agent --agent-id $AGENT_ID --region $REGION
```

### Deploy Frontend Changes

```bash
cd esg-chat-app-react
git add .
git commit -m "feat: update feature"
git push origin main  # Amplify auto-deploys in ~3 min
```

### Sync Knowledge Base

```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DATA_SOURCE_ID \
  --region $REGION
```

---

## ⚠️ Known Validation False Positives

These are **NOT bugs** — they are calibration issues in the validation layer. Auto-approve mode handles them correctly.

| Issue | Type | Impact | Status |
|-------|------|--------|--------|
| Scientific notation mismatch | VAL-NUM-01 | LOW | False positive — numbers correct |
| LLM-derived percentages | VAL-NUM-01/03 | LOW | False positive — math correct |
| Table values not in paragraphs | VAL-NUM-07 | LOW | Expected behavior — tables summarize |
| Sector values not in allowed set | VAL-NUM-01 | MEDIUM | `pcaf_sectors` not passed to validator |

**For demo/POC:** Auto-approve is correct. For production: implement fixes per `VALIDATION_FALSE_POSITIVES.md`.

---

## 🚨 Troubleshooting Quick Fixes

| Problem | Likely Cause | Quick Fix |
|---------|-------------|-----------|
| Lambda can't import `lxml` | Layer built on Windows | Rebuild in CloudShell (Linux) |
| Bedrock `AccessDenied` | Missing inference-profile ARN | Add `arn:aws:bedrock:*::inference-profile/*` to IAM |
| Step Functions deploy fails | Windows `file://` encoding | Upload ASL to S3, deploy from CloudShell |
| Presigned URL `SignatureDoesNotMatch` | KMS encryption | Use `signature_version='s3v4'` in boto3 Config |
| Agent corrupts download URLs | Markdown formatting | Frontend regex strips trailing `)` / `]` |
| Frontend 404 after deploy | Missing `_redirects` | Add `/* /index.html 200` to `public/_redirects` |
| Validation flags correct numbers | Validator too strict | Expected — use auto-approve mode |
| Human Review blocked | Organization SCP | Use auto-approve ASL (default) |
| Social section missing | Old templates | Ensure `section_templates` includes `{"template_id": "social"}` |

---

## 📚 Documentation Index

| Document | Purpose |
|----------|---------|
| **DEPLOYMENT_GUIDE.md** | Full step-by-step deployment (this doc's detailed version) |
| **INFRASTRUCTURE_SPEC.md** | Complete infrastructure specification (32 resources) |
| **esg-reporting-poc/docs/IMPLEMENTATION_CHANGELOG.md** | 91 spec deviations across W1-W6 |
| **esg-reporting-poc/docs/INFRASTRUCTURE_REFERENCE.md** | Current deployed resource configs |
| **esg-reporting-poc/docs/SPEC_AMENDMENTS.md** | 76 tracked amendments (AMD-001 to AMD-004) |
| **esg-reporting-poc/docs/VALIDATION_FALSE_POSITIVES.md** | Validator calibration issues |
| **esg-chat-app-react/README.md** | Frontend development guide |
| **esg-reporting-poc/lambda/README.md** | Lambda functions reference |
| **esg-reporting-poc/agent/README.md** | Bedrock Agent setup |
| **architecture/README.md** | Architecture diagrams |

---

## 🔄 Rollback

```bash
# Delete all Lambda functions
for fn in esg-validate-input esg-section-gen esg-filter-sections esg-assembly-doc esg-validation esg-review-handler esg-status-check esg-history esg-athena-query esg-dashboard-data esg-agent-tools esg-chat-proxy; do
  aws lambda delete-function --function-name $fn --region $REGION 2>/dev/null
done

# Delete State Machine
aws stepfunctions delete-state-machine --state-machine-arn $SFN_ARN --region $REGION

# Delete API Gateway
aws apigateway delete-rest-api --rest-api-id $API_ID --region $REGION

# Delete SNS
aws sns delete-topic --topic-arn arn:aws:sns:$REGION:$ACCOUNT_ID:ESG-HumanReview
aws sns delete-topic --topic-arn arn:aws:sns:$REGION:$ACCOUNT_ID:ESG-ReportComplete

# Delete S3 (⚠️ IRREVERSIBLE — deletes all data)
for bucket in esg-data-raw esg-data-curated esg-data-aggregated esg-output-reports esg-kb-documents esg-athena-results; do
  aws s3 rb s3://${bucket}-$ACCOUNT_ID --force
done
```

---

## 🎯 Report Generation Capabilities

### Supported Frameworks

| Framework | Key | Sections |
|-----------|-----|----------|
| GRI 305 | `GRI_305` | scope1, scope2, scope3_pcaf, intensity, social, methodology, summary |
| IFRS S2 | `IFRS_S2` | governance, strategy_risks, metrics, pcaf, intensity, social, summary |
| CSRD ESRS E1 | `CSRD_ESRS_E1` | climate_strategy, metrics, pcaf, intensity, social, methodology, summary |
| OJK PSPK | `OJK_PSPK` | ghg_inventory, pcaf, intensity, social, methodology, summary |
| All Frameworks | `MULTI_FRAMEWORK` | All 15 sections across 4 frameworks |

### Execution Time Benchmarks

| Framework | Sections | Avg Time |
|-----------|----------|----------|
| GRI_305 (single) | 7 | 3-5 min |
| MULTI_FRAMEWORK | 15 | 8-12 min |

---

**Happy deploying!** 🚀
