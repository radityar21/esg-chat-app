# ESG Reporting POC — Backend System

> **Serverless backend for automated ESG report generation using AWS Lambda, Glue, Step Functions, and Bedrock**

This folder contains all backend components for the ESG reporting system:
- **9 Lambda functions** for orchestration, generation, validation, and assembly
- **3 Glue ETL jobs** for data transformation
- **1 Step Functions state machine** for workflow orchestration
- **Bedrock Agent** for conversational interface
- **Section templates** for AI-powered content generation

---

## 📁 Folder Structure

```
esg-reporting-poc/
├── agent/                      # Bedrock Agent configuration
│   ├── agent_instructions.txt  # Agent system prompt
│   ├── openapi_schema.json     # Action Group API spec
│   └── lambda_agent_tools/     # Agent tool handler Lambda
├── lambda/                     # Lambda functions (9 total)
│   ├── validate_input/         # Input validation
│   ├── athena_query/           # Data aggregation queries
│   ├── section_gen/            # AI section generation (Bedrock)
│   ├── filter_sections/        # Map output filtering
│   ├── validate_sections/      # Content validation
│   ├── assembly_doc/           # DOCX assembly
│   ├── chat_proxy/             # API Gateway → Bedrock Agent
│   ├── history/                # Execution history API
│   └── dashboard_data/         # Analytics data API
├── glue/                       # Glue ETL PySpark jobs
│   ├── etl_ghg_emissions.py    # Scope 1/2/3 aggregation
│   ├── etl_pcaf_financed.py    # PCAF Category 15 (Scope 3)
│   └── etl_hr_metrics.py       # Social pillar (workforce)
├── step_functions/             # Orchestration
│   └── esg_orchestrator.asl.json  # State machine definition
├── templates/                  # Section generation prompts
│   ├── section_scope1.txt      # Scope 1 template
│   ├── section_scope2.txt      # Scope 2 template
│   ├── section_scope3.txt      # Scope 3 template
│   ├── section_pcaf.txt        # PCAF financed emissions
│   ├── section_social.txt      # Social (S) pillar
│   └── ...                     # 9 templates total
├── docs/                       # Documentation
│   ├── IMPLEMENTATION_CHANGELOG.md  # Spec deviations
│   └── INFRASTRUCTURE_REFERENCE.md  # Deployed resources
├── tests/                      # Test payloads
│   ├── test_section_gen.json   # Section generation test
│   └── test_step_function.txt  # End-to-end test
├── scripts/                    # Deployment & utility scripts
│   ├── deploy_lambdas.sh       # Lambda deployment script
│   └── build_matplotlib_layer.sh  # Lambda layer builder
└── result/                     # Sample outputs
    └── GRI_305_SCOPE1_2024.json  # Generated section example
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# AWS CLI configured
aws configure

# Python 3.11
python --version

# IAM role for Lambda with permissions:
# - S3, Athena, Bedrock, Step Functions, SNS
```

### Deployment Steps

#### 1. Deploy Lambda Functions

```bash
# Navigate to each Lambda folder and zip
cd lambda/section_gen
zip -r ../../deploy/section_gen.zip handler.py
cd ../..

# Upload to S3 (or use AWS CLI directly)
aws lambda create-function \
  --function-name esg-section-gen \
  --runtime python3.11 \
  --handler handler.lambda_handler \
  --role arn:aws:iam::ACCOUNT:role/ESGLambdaRole \
  --code S3Bucket=YOUR_BUCKET,S3Key=section_gen.zip \
  --timeout 900 \
  --memory-size 1024

# Repeat for all 9 Lambda functions
```

See [lambda/README.md](lambda/README.md) for detailed per-function instructions.

#### 2. Deploy Glue Jobs

```bash
# Upload Glue scripts to S3
aws s3 cp glue/etl_ghg_emissions.py s3://YOUR_BUCKET/glue-scripts/

# Create Glue job
aws glue create-job \
  --name etl-ghg-emissions \
  --role arn:aws:iam::ACCOUNT:role/GlueServiceRole \
  --command Name=glueetl,ScriptLocation=s3://YOUR_BUCKET/glue-scripts/etl_ghg_emissions.py \
  --default-arguments '{
    "--job-language":"python",
    "--TempDir":"s3://YOUR_BUCKET/glue-temp/"
  }' \
  --glue-version 4.0 \
  --worker-type G.1X \
  --number-of-workers 2
```

#### 3. Deploy Step Functions

```bash
# Upload ASL definition
aws stepfunctions create-state-machine \
  --name ESGReportGenerationStateMachine \
  --definition file://step_functions/esg_orchestrator.asl.json \
  --role-arn arn:aws:iam::ACCOUNT:role/StepFunctionsESGRole \
  --type STANDARD
```

#### 4. Create Bedrock Agent

```bash
# Via AWS Console:
# 1. Bedrock → Agents → Create agent
# 2. Name: ESGReportAgent
# 3. Model: Claude Sonnet 4.5
# 4. Instructions: Paste from agent/agent_instructions.txt
# 5. Action Group: Upload agent/openapi_schema.json
# 6. Lambda: Select esg-agent-tools
# 7. Create & Test
```

---

## 🏗️ Architecture

### Data Pipeline Flow

```
┌─────────────┐
│ S3 Raw Data │  Parquet files (energy, emissions, PCAF, HR)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Glue ETL    │  3 PySpark jobs → esg_aggregated database
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│               Step Functions State Machine                    │
│  ┌────────────┬────────────┬────────────┬────────────────┐   │
│  │ 1. Input   │ 2. Athena  │ 3. Section │ 4. Validation │   │
│  │ Validation │ Aggregation│ Generation │ (Numeric,     │   │
│  │            │            │ (Bedrock)  │  Structural)  │   │
│  └────────────┴────────────┴────────────┴────────────────┘   │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ 5. Assembly (DOCX) → 6. S3 Upload → 7. SNS Notify     │   │
│  └────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

### Lambda Function Dependencies

```
validate_input
    └─> athena_query
           └─> section_gen (Map state, parallel)
                  └─> filter_sections
                         └─> validate_sections
                                └─> assembly_doc

chat_proxy ─────> agent_tools ─────> Step Functions (start execution)
history ────────> Step Functions (list executions)
dashboard_data ─> Athena (direct query)
```

---

## 📝 Lambda Functions

| Function | Purpose | Timeout | Memory |
|----------|---------|---------|--------|
| **validate_input** | Validate request parameters (year, framework, revenue) | 30s | 128MB |
| **athena_query** | Query aggregated tables, build DATA_INPUT for AI | 300s | 512MB |
| **section_gen** | Generate 1 section using Bedrock + RAG | 900s | 1024MB |
| **filter_sections** | Filter Map output (Step Functions limitation workaround) | 30s | 128MB |
| **validate_sections** | Validate generated content (numeric, structural, prohibited) | 300s | 512MB |
| **assembly_doc** | Assemble DOCX/PPTX from validated sections | 300s | 1024MB |
| **agent_tools** | Bedrock Agent action handler (4 tools) | 60s | 256MB |
| **chat_proxy** | API Gateway → Bedrock Agent proxy | 60s | 256MB |
| **history** | List Step Functions executions (report history) | 30s | 128MB |
| **dashboard_data** | Analytics dashboard data (Athena query or S3 cache) | 300s | 512MB |

---

## 🗄️ Data Schema

### Raw Data (S3 Parquet)

**Location:** `s3://esg-data-raw-{account}/{table}/reporting_year={year}/`

| Table | Columns | Purpose |
|-------|---------|---------|
| `energy_consumption` | facility_id, period_date, natgas_kwh, diesel_liters | Scope 1 source data |
| `electricity_consumption` | facility_id, period_date, electricity_kwh | Scope 2 source data |
| `pcaf_portfolio` | sector, outstanding_idr, borrower_emissions_tco2e | Scope 3 (financed) |
| `hr_metrics` | reporting_year, fte_total, fte_female_pct, training_hours, etc. | Social pillar |

### Aggregated Data (Athena Tables)

**Database:** `esg_aggregated`

| Table | Key Metrics | Used By |
|-------|-------------|---------|
| `ghg_summary_annual` | scope1_tco2e, scope2_tco2e, scope3_tco2e, intensity, yoy_change | All sections |
| `scope1_by_facility` | facility-level breakdown | Scope 1 detail |
| `pcaf_by_sector` | sector-level financed emissions, PCAF scores | PCAF section |

---

## 🤖 Bedrock Agent

### Tools Available

| Tool | Description | Lambda Handler |
|------|-------------|----------------|
| `generate_report` | Start Step Functions execution | `start_execution()` |
| `check_status` | Get execution status | `describe_execution()` |
| `download_report` | Generate presigned S3 URL | `get_download_url()` |
| `list_available_years` | Return [2023, 2024] | Hardcoded list |

### Conversation Flow

```
User: "Generate GRI 305 report for 2024"
  ↓
Agent: Calls generate_report(year=2024, framework=GRI_305, revenue=92000)
  ↓
Step Functions: Starts execution → returns Execution ID
  ↓
Agent: "Report generation started. Execution ID: abc-123. ETA: 10-20 minutes."
  ↓
User: "Check status"
  ↓
Agent: Calls check_status(execution_id="abc-123")
  ↓
Returns: {status: "SUCCEEDED", output: {s3_path: "..."}}
  ↓
Agent: Calls download_report(s3_path="...")
  ↓
Returns: Presigned URL (expires in 1 hour)
  ↓
Agent: "Report complete! Download: https://s3.amazonaws.com/..."
```

---

## 🧪 Testing

### Test Individual Lambda

```bash
cd lambda/section_gen
python handler.py < ../../tests/test_section_gen.json
```

### Test Step Functions

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:ESGReportGenerationStateMachine \
  --input '{
    "reporting_year": 2024,
    "framework": "GRI_305",
    "revenue_idr_billion": 92000
  }'

# Get execution ARN from output, then check status:
aws stepfunctions describe-execution \
  --execution-arn arn:aws:states:...
```

### Test Bedrock Agent (via Chat Proxy)

```bash
curl -X POST https://API_ID.execute-api.us-east-1.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Generate GRI 305 report for 2024",
    "session_id": "test-session-123"
  }'
```

---

## 📚 Templates

Section generation templates are stored in `templates/` and uploaded to S3:

```
s3://esg-prompts-{account}/section_templates/
```

Each template follows this structure:

```
CONTEXT:
You are generating the [Section Name] section for a sustainability report...

DATA INPUT:
{DATA_INPUT}

REQUIREMENTS:
- Framework-specific guidance
- Required disclosures
- Formatting rules

OUTPUT FORMAT:
[Structured output specification]
```

See individual template files for full specifications.

---

## 🔒 IAM Permissions

### ESGLambdaRole (for Lambda functions)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": "arn:aws:s3:::esg-*/*"
    },
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:Retrieve"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["athena:StartQueryExecution", "athena:GetQueryResults"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["states:StartExecution", "states:DescribeExecution"],
      "Resource": "arn:aws:states:*:*:stateMachine:ESG*"
    }
  ]
}
```

---

## 📊 Monitoring

### CloudWatch Metrics

- **Lambda invocations** — Per function success/error rate
- **Step Functions executions** — Success/failure count, duration
- **Athena query scanned data** — Cost monitoring

### CloudWatch Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/esg-section-gen --follow

# View Step Functions execution history
aws stepfunctions get-execution-history \
  --execution-arn arn:aws:states:...
```

---

## 🐛 Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| "No data returned from Athena" | Partition not loaded | Run `MSCK REPAIR TABLE` or check partition projection |
| "Bedrock throttling" | Too many concurrent requests | Add exponential backoff in section_gen |
| "Validation failed (VAL-NUM-01)" | AI generated wrong number | Check DATA_INPUT format, retry with clearer prompt |
| "DOCX assembly timeout" | Too many sections | Increase Lambda timeout to 300s |
| "Step Functions failed at Map state" | One section failed | Check CloudWatch logs for specific section error |

---

## 🔄 Version History

- **v1.0.0** (2026-06-05) — Initial POC with GRI 305, IFRS S2, CSRD, OJK
- **v1.1.0** (2026-06-09) — Added Social (S) pillar + silent polling
- **v1.2.0** (2026-06-15) — Added Analytics Dashboard + Amplify deployment

---

## 📞 Support

For detailed documentation, see:
- [IMPLEMENTATION_CHANGELOG.md](docs/IMPLEMENTATION_CHANGELOG.md) — Spec deviations
- [INFRASTRUCTURE_REFERENCE.md](docs/INFRASTRUCTURE_REFERENCE.md) — Resource configs
- [lambda/README.md](lambda/README.md) — Per-function docs
- [agent/README.md](agent/README.md) — Bedrock Agent setup

---

**Next:** Check [../esg-chat-app-react/README.md](../esg-chat-app-react/README.md) for frontend deployment.
