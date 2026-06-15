# ESG Reporting System - Deployment Summary

**Quick Reference Guide**  
**Tokaicom Mitra Indonesia (Tokai Group)**

---

## 🚀 Quick Start

### Prerequisites Checklist

```bash
✅ AWS CLI 2.x installed
✅ AWS Account with appropriate permissions
✅ Node.js 18+ and npm
✅ Python 3.12
✅ Git configured
✅ Bedrock Claude 3.5 Sonnet access enabled
```

### Deployment Options

| Method | Time | Complexity | Use Case |
|--------|------|------------|----------|
| **Automated (CDK)** | 15-20 min | Low | Fresh deployment, reproducible |
| **Manual (CLI)** | 30-45 min | Medium | Learning, custom setup |

---

## Option 1: Automated Deployment (Recommended)

```bash
# 1. Setup
cd esg-reporting-poc/infra
pip install -r requirements.txt
cdk bootstrap aws://YOUR_ACCOUNT_ID/ap-southeast-1

# 2. Deploy
cdk deploy ESGInfraStack --require-approval never

# 3. Deploy Frontend
cd ../../esg-chat-app-react
git push origin main  # Amplify auto-deploys
```

**Done!** Infrastructure + Frontend deployed in ~20 minutes.

---

## Option 2: Manual Deployment

### Step-by-Step Commands

```bash
# 1. IAM Roles & S3 Buckets
cd esg-reporting-poc/scripts
chmod +x setup_account.sh
./setup_account.sh

# 2. Lambda Layer
cd ../deploy/layer
# Build layer with Docker or use pre-built layer.zip
aws lambda publish-layer-version \
  --layer-name esg-reporting-layer \
  --zip-file fileb://../layer.zip \
  --compatible-runtimes python3.12 \
  --region ap-southeast-1

# 3. Deploy 11 Lambda Functions
# See DEPLOYMENT_GUIDE.md Section "Step 3" for all 11 commands

# 4. Deploy Step Functions
cd ../step_functions
aws stepfunctions create-state-machine \
  --name esg-orchestrator \
  --definition file://esg_orchestrator.asl.json \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/ESGStepFunctionsRole \
  --region ap-southeast-1

# 5. Deploy API Gateway
# See DEPLOYMENT_GUIDE.md Section "Step 5" for detailed commands

# 6. Deploy Bedrock Agent & Knowledge Base
# See DEPLOYMENT_GUIDE.md Section "Step 6-7"

# 7. Deploy Frontend
cd ../../esg-chat-app-react
# Update src/api.js with API Gateway URL
git push origin main
```

---

## Post-Deployment Verification

### 1. Test Lambda Functions

```bash
aws lambda invoke \
  --function-name esg-validate-input \
  --payload '{"reporting_year":2024,"framework":"GRI_305"}' \
  --region ap-southeast-1 \
  output.json && cat output.json
```

### 2. Test Step Functions

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:ap-southeast-1:ACCOUNT_ID:stateMachine:esg-orchestrator \
  --input '{"reporting_year":2024,"framework":"GRI_305"}' \
  --region ap-southeast-1
```

### 3. Test API Gateway

```bash
curl "https://API_ID.execute-api.ap-southeast-1.amazonaws.com/prod/status?execution_id=test"
```

### 4. Test Frontend

Open: `https://main.d337jqli3ubqmk.amplifyapp.com`

---

## 📊 Infrastructure Overview

### 32 Resources Deployed

| Type | Count | Examples |
|------|-------|----------|
| IAM Roles | 5 | ESGLambdaExecutionRole, ESGStepFunctionsRole |
| Lambda Functions | 11 | esg-section-gen, esg-assembly-doc, esg-agent-tools |
| Lambda Layer | 1 | esg-reporting-layer (python-docx, pptx) |
| Step Functions | 1 | esg-orchestrator |
| API Gateway | 1 | ESG Reporting API (4 endpoints) |
| Bedrock Agent | 1 | ESG-Report-Assistant |
| Bedrock KB | 1 | ESG-Framework-KB |
| S3 Buckets | 3 | reports, athena-results, knowledge-base |
| Glue Database | 1 | esg_reporting_db |
| Amplify App | 1 | esg-chat-app (React frontend) |

---

## 💰 Cost Estimate

| Scenario | Monthly Cost | Notes |
|----------|-------------|-------|
| **Development** (10 reports) | ~$20 | OpenSearch dominant |
| **Production** (100 reports) | ~$190 | OpenSearch $173, Bedrock $13 |
| **Optimized** (100 reports) | ~$30 | Without OpenSearch KB |

**Cost Breakdown:**
- OpenSearch Serverless: $172.80/month (can be optimized)
- Bedrock API: $12.96/month
- Lambda: $2/month
- Other services: <$5/month

**Optimization:** Switch Knowledge Base to Aurora Serverless to reduce cost from $190 → $30/month

---

## 🔍 Monitoring

### CloudWatch Dashboards

Access via: AWS Console → CloudWatch → Dashboards

**Key Metrics:**
- Lambda invocations & errors
- Step Functions execution status
- API Gateway request count & latency
- Bedrock token usage

### Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/esg-section-gen --follow --region ap-southeast-1

# View Step Functions logs
aws logs tail /aws/vendedlogs/states/esg-orchestrator --follow --region ap-southeast-1

# View API Gateway logs
aws logs tail /aws/apigateway/esg-reporting-api --follow --region ap-southeast-1
```

---

## 🛠️ Common Operations

### Update Lambda Function

```bash
cd esg-reporting-poc/lambda/function_name
zip -r ../../deploy/function_name.zip handler.py
aws lambda update-function-code \
  --function-name esg-function-name \
  --zip-file fileb://../../deploy/function_name.zip \
  --region ap-southeast-1
```

### Update Step Functions

```bash
cd esg-reporting-poc/step_functions
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:ap-southeast-1:ACCOUNT_ID:stateMachine:esg-orchestrator \
  --definition file://esg_orchestrator.asl.json \
  --region ap-southeast-1
```

### Update Bedrock Agent Instructions

```bash
aws bedrock-agent update-agent \
  --agent-id AGENT_ID \
  --instruction file://agent_instructions.txt \
  --region ap-southeast-1

aws bedrock-agent prepare-agent --agent-id AGENT_ID --region ap-southeast-1
```

### Deploy Frontend Changes

```bash
cd esg-chat-app-react
git add .
git commit -m "feat: update feature"
git push origin main  # Amplify auto-deploys
```

---

## 🚨 Troubleshooting

### Lambda Errors

**Issue:** Function timeout

**Solution:**
```bash
aws lambda update-function-configuration \
  --function-name esg-section-gen \
  --timeout 600 \
  --region ap-southeast-1
```

### Bedrock Throttling

**Issue:** `ThrottlingException: Rate exceeded`

**Solution:** Request quota increase via AWS Service Quotas console

### API Gateway CORS

**Issue:** `No 'Access-Control-Allow-Origin' header`

**Solution:** Re-run CORS setup commands in DEPLOYMENT_GUIDE.md Step 5.4

### Frontend Build Fails

**Issue:** Amplify build error

**Solution:** Check `amplify.yml` baseDirectory points to `esg-chat-app-react/dist`

---

## 📚 Documentation

| Document | Purpose | Location |
|----------|---------|----------|
| **DEPLOYMENT_GUIDE.md** | Full deployment instructions | Root folder |
| **INFRASTRUCTURE_SPEC.md** | Complete infrastructure spec | Root folder |
| **README.md** (root) | Project overview | Root folder |
| **esg-reporting-poc/README.md** | Backend architecture | Backend folder |
| **esg-chat-app-react/README.md** | Frontend development | Frontend folder |
| **esg-reporting-poc/lambda/README.md** | Lambda functions reference | Lambda folder |
| **esg-reporting-poc/agent/README.md** | Bedrock Agent setup | Agent folder |
| **architecture/README.md** | Architecture diagrams | Architecture folder |

---

## 🔄 Rollback Procedure

### Complete Rollback

```bash
# Delete Lambda functions
for fn in esg-validate-input esg-section-gen esg-filter-sections esg-assembly-doc esg-validation esg-review-handler esg-status-check esg-history esg-athena-query esg-dashboard-data esg-agent-tools; do
  aws lambda delete-function --function-name $fn --region ap-southeast-1
done

# Delete Step Functions
aws stepfunctions delete-state-machine \
  --state-machine-arn arn:aws:states:ap-southeast-1:ACCOUNT_ID:stateMachine:esg-orchestrator \
  --region ap-southeast-1

# Delete S3 buckets (WARNING: deletes all data)
aws s3 rb s3://esg-reporting-output-bucket --force
aws s3 rb s3://esg-athena-results --force
aws s3 rb s3://esg-knowledge-base --force
```

---

## 🎯 Next Steps

After successful deployment:

1. **Configure Bedrock Agent** with Knowledge Base
2. **Upload ESG framework documents** to S3 knowledge base bucket
3. **Sync Knowledge Base** in Bedrock console
4. **Test end-to-end** report generation via Chat UI
5. **Setup CloudWatch Alarms** for production monitoring
6. **Enable S3 Cross-Region Replication** for disaster recovery (optional)
7. **Configure custom domain** for Amplify app (optional)

---

## 📞 Support

- **Technical Issues:** Check CloudWatch Logs
- **Documentation:** See README files in each folder
- **Architecture Questions:** See `architecture/README.md`

---

**Happy deploying!** 🚀

For detailed step-by-step instructions, see **DEPLOYMENT_GUIDE.md**
