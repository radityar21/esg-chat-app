# ESG Reporting Solution — AI-Powered Sustainability Reporting for Financial Institutions

> **Automated GHG emissions reporting system powered by Amazon Bedrock, Step Functions, and Athena**

[![AWS](https://img.shields.io/badge/AWS-Cloud-orange)](https://aws.amazon.com)
[![Bedrock](https://img.shields.io/badge/Amazon-Bedrock-blue)](https://aws.amazon.com/bedrock)
[![License](https://img.shields.io/badge/License-Proprietary-red)]()

---

## 🌿 Overview

This solution automates **ESG (Environmental, Social, Governance) sustainability reporting** for **financial institutions**, generating compliance-ready reports for multiple international frameworks:

- **GRI 305** — Global Reporting Initiative (GHG Emissions)
- **IFRS S2** — Climate-related Financial Disclosures
- **CSRD/ESRS E1** — EU Corporate Sustainability Reporting Directive
- **OJK PSPK** — Indonesian Financial Regulator (Pedoman Standar Penyelenggaraan Keberlanjutan)
- **MULTI_FRAMEWORK** — Comprehensive report covering all frameworks

### Key Features

✅ **End-to-end automation** — Data ingestion → ETL → AI generation → DOCX assembly  
✅ **Practitioner-ready reports** — Scope 1/2/3 emissions, PCAF financed emissions, social metrics  
✅ **Conversational AI assistant** — Bedrock Agent for report requests via natural language  
✅ **Analytics dashboard** — 14 charts + 6 KPIs for management/investor presentations  
✅ **Multi-framework support** — Generate 1 report or all 5 frameworks in one run  
✅ **Compliance validation** — Automated checks for accuracy, fabrication, prohibited content  

---

## 📁 Repository Structure

```
bedrock-agentcore-solution/
├── architecture/              # System architecture diagrams (Draw.io)
├── esg-reporting-poc/         # ⭐ Main backend system (Lambda, Glue, Step Functions)
│   ├── agent/                 # Bedrock Agent configuration
│   ├── lambda/                # 9 Lambda functions
│   ├── glue/                  # 3 Glue ETL jobs
│   ├── step_functions/        # Step Functions ASL definition
│   ├── templates/             # Section generation prompts
│   ├── docs/                  # Technical documentation
│   └── tests/                 # Test payloads and validation
├── esg-chat-app-react/        # ⭐ Frontend dashboard (React + Vite)
│   ├── src/
│   │   ├── pages/             # Overview, Analytics, Chat, Reports, Reference
│   │   └── components/        # Sidebar, shared UI components
│   └── public/                # Static assets
├── ESG Document/              # Knowledge base documents (PDFs → markdown)
└── deploy/                    # Deployment artifacts (Lambda layers, zip files)
```

See individual `README.md` files in each folder for detailed documentation.

---

## 🚀 Quick Start

### Prerequisites

- **AWS Account** with permissions for: Lambda, S3, Glue, Athena, Step Functions, Bedrock, API Gateway, Amplify
- **AWS CLI** configured (`aws configure`)
- **Node.js 18+** (for frontend)
- **Python 3.11** (for Lambda functions)

### Deployment

#### 1. Backend (Lambda + Step Functions + Glue)

```bash
cd esg-reporting-poc

# Deploy Lambda functions (see esg-reporting-poc/README.md for details)
./scripts/deploy_lambdas.sh

# Deploy Step Functions state machine
aws stepfunctions create-state-machine \
  --name ESGReportGenerationStateMachine \
  --definition file://step_functions/esg_orchestrator.asl.json \
  --role-arn arn:aws:iam::YOUR_ACCOUNT:role/StepFunctionsESGRole
```

#### 2. Frontend (React Dashboard)

```bash
cd esg-chat-app-react

# Install dependencies
npm install

# Local development
npm run dev  # http://localhost:5173

# Deploy to Amplify (via GitHub)
git add .
git commit -m "deploy: update frontend"
git push origin main  # Amplify auto-deploys
```

See [esg-chat-app-react/README.md](esg-chat-app-react/README.md) for detailed instructions.

---

## 🏗️ Architecture

### High-Level Data Flow

```
┌─────────────────┐
│  S3 Raw Data    │  Synthetic HR, emissions, PCAF data (Parquet)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Glue ETL Jobs  │  Transform → esg_aggregated database
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│           Step Functions Orchestrator                    │
│  ┌─────────────┬─────────────┬─────────────┬─────────┐  │
│  │ Athena      │ Section Gen │ Validation  │Assembly │  │
│  │ Query       │ (Bedrock)   │ (Numeric)   │ (DOCX)  │  │
│  └─────────────┴─────────────┴─────────────┴─────────┘  │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  S3 Reports     │  Final DOCX + PPTX with presigned URLs
└─────────────────┘
```

### Frontend Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Amplify    │ ───► │ API Gateway  │ ───► │   Lambda     │
│  (React UI)  │      │  REST API    │      │  Proxies     │
└──────────────┘      └──────────────┘      └───────┬──────┘
                                                     │
                           ┌─────────────────────────┼────────────┐
                           ▼                         ▼            ▼
                    ┌──────────────┐        ┌──────────────┐  ┌─────────┐
                    │   Bedrock    │        │ Step Functions│  │ Athena  │
                    │    Agent     │        │   Execution  │  │Dashboard│
                    └──────────────┘        └──────────────┘  └─────────┘
```

---

## 📊 Features

### 1. Report Generation
- **9 sections** per report: Executive Summary, Scope 1/2/3, Intensity, PCAF, Social, Methodology
- **AI-powered content** using Claude Sonnet 4.5 with RAG from knowledge base
- **DOCX output** (Arial 11pt, A4, justified, auto-generated TOC)
- **PPTX summary** (4 slides for MULTI_FRAMEWORK)

### 2. Analytics Dashboard
- **14 charts**: Emissions breakdown, YoY trends, PCAF portfolio, HR metrics
- **6 KPI cards**: Total emissions, YoY change, intensity, PCAF quality, FTE, diversity
- **Hybrid caching**: S3 cache (fast) + Athena refresh (on-demand)

### 3. Chat Assistant
- **Natural language** report requests via Bedrock Agent
- **Tool-based actions**: Generate, check status, download reports
- **Auto-polling**: Frontend detects Execution ID and polls silently until completion

### 4. Validation Rules
- **Structural validation**: Required fields, section order, references
- **Numeric validation**: Cross-check AI-generated numbers against source data
- **Prohibited content**: Detect first-person language, unsupported statements
- **Retry logic**: Up to 2 retries for fixable validation failures

---

## 🗂️ Key Components

| Component | Description | Location |
|-----------|-------------|----------|
| **Lambda Functions** | 9 serverless functions (section gen, validation, assembly, etc.) | `esg-reporting-poc/lambda/` |
| **Glue ETL** | 3 PySpark jobs (emissions, HR, PCAF aggregation) | `esg-reporting-poc/glue/` |
| **Step Functions** | Orchestrator state machine (ASL JSON) | `esg-reporting-poc/step_functions/` |
| **Bedrock Agent** | Conversational AI assistant + 4 action tools | `esg-reporting-poc/agent/` |
| **React Dashboard** | 5-page frontend (Overview, Analytics, Chat, Reports, Reference) | `esg-chat-app-react/` |
| **Knowledge Base** | Regulatory docs (GRI, IFRS, CSRD, OJK, PCAF) | `ESG Document/` |

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [IMPLEMENTATION_CHANGELOG.md](esg-reporting-poc/docs/IMPLEMENTATION_CHANGELOG.md) | Complete list of deviations from original spec |
| [INFRASTRUCTURE_REFERENCE.md](esg-reporting-poc/docs/INFRASTRUCTURE_REFERENCE.md) | All deployed AWS resources + configs |
| [ESG_kiro_Requirement_Spec.md](esg-reporting-poc/ESG_kiro_Requirement_Spec.md) | Original requirements specification |
| [agent/README.md](esg-reporting-poc/agent/README.md) | Bedrock Agent setup guide |
| [lambda/README.md](esg-reporting-poc/lambda/README.md) | Lambda function documentation |
| [esg-chat-app-react/README.md](esg-chat-app-react/README.md) | Frontend development guide |

---

## 🧪 Testing

```bash
# Test Lambda function locally
cd esg-reporting-poc/lambda/section_gen
python handler.py < ../../tests/test_section_gen.json

# Test Step Functions execution
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:ESGReportGenerationStateMachine \
  --input file://tests/test_step_function.txt

# Test API endpoints
curl "https://API_ID.execute-api.us-east-1.amazonaws.com/prod/chat" \
  -X POST -H "Content-Type: application/json" \
  -d '{"message":"Generate GRI 305 report for 2024","session_id":"test-123"}'
```

---

## 💰 Cost Estimate

| Component | Monthly Cost (low traffic) |
|-----------|---------------------------|
| Lambda (1M requests) | ~$5 |
| Athena (10GB scanned) | ~$0.05 |
| S3 (100GB storage) | ~$2.30 |
| Bedrock (Claude invocations) | ~$10-50 (usage-based) |
| Amplify Hosting | ~$1-5 |
| API Gateway | ~$3.50 |
| **Total** | **~$22-66/month** |

---

## 🛠️ Tech Stack

**Backend:**
- AWS Lambda (Python 3.11)
- AWS Glue (PySpark 3.3)
- AWS Step Functions (ASL)
- Amazon Athena (Presto SQL)
- Amazon Bedrock (Claude Sonnet 4.5)
- Amazon S3 (data lake)
- API Gateway (REST)

**Frontend:**
- React 18
- Vite 5
- Tailwind CSS 3
- Recharts 2.15
- Lucide Icons
- AWS Amplify Hosting

---

## 📝 License

**Proprietary** — Tokaicom Mitra Indonesia (Tokai Group)

---

## 👥 Contributors

- **Raditya** — Full-stack development, AI engineering, DevOps
- Built for **AWS Summit 2026** showcase

---

## 🔗 Links

- **Live Dashboard**: https://main.d337jqli3ubqmk.amplifyapp.com/
- **GitHub Repo**: https://github.com/radityar21/esg-chat-app
- **AWS Region**: us-east-1 (N. Virginia)

---

## 📞 Support

For questions or issues, please contact the development team or refer to the detailed documentation in each component folder.
