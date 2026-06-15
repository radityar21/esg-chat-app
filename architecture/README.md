# Architecture Documentation

Visual documentation of the ESG Reporting System architecture, data flows, and service topology.

---

## 📐 Architecture Diagrams

### 1. ESG Reporting Architecture (Full System)

**File:** `ESG Bedrock Reporting-ESG Reporting Architecture.png`  
**Source:** `ESG Bedrock Reporting-ESG Reporting Architecture.drawio.xml`

**Components:**
- **Frontend:** React SPA (Amplify Hosting)
- **API Gateway:** RESTful endpoints for chat, status, history, analytics
- **Bedrock Agent:** AI-powered ESG assistant (Claude 3.5 Sonnet)
- **Step Functions:** Report generation orchestrator (9 Lambda parallel execution)
- **Lambda Functions:** 10 functions (validation, section generation, assembly, etc.)
- **S3 Storage:** Reports, Athena results, knowledge base documents
- **Athena:** Analytics queries on ESG data
- **Glue Data Catalog:** ESG data schema (emissions, portfolio, social)

**Key Flows:**
1. User → Frontend → API Gateway → Bedrock Agent → Step Functions
2. Step Functions → Lambda (section_gen × 9) → Bedrock API → S3
3. Frontend (Analytics) → API Gateway → Lambda (dashboard_data) → Athena/S3

---

### 2. Service Overview & Topology

**File:** `ESG Bedrock Reporting-Service overview.drawio.png`  
**Source:** `ESG Bedrock Reporting-Service overview.drawio.xml`  
**Updated:** `ESG Bedrock Reporting-service-overview-v2.drawio.png`

**Service Layers:**
1. **Presentation Layer:**
   - React Frontend (Vite + Tailwind)
   - Amplify Hosting (GitHub CI/CD)

2. **API Layer:**
   - API Gateway REST API
   - `/chat`, `/status`, `/history`, `/dashboard-data` endpoints

3. **Orchestration Layer:**
   - Amazon Bedrock Agents
   - AWS Step Functions

4. **Compute Layer:**
   - 10 Lambda functions (Python 3.12)
   - Lambda Layer (python-docx, python-pptx, matplotlib)

5. **Data Layer:**
   - S3 (reports, cache)
   - Athena (analytics queries)
   - Glue Data Catalog

6. **AI/ML Layer:**
   - Amazon Bedrock (Claude 3.5 Sonnet)
   - Bedrock Knowledge Base (RAG)

---

### 3. Data Flow Process (Business View)

**File:** `ESG Bedrock Reporting-Data Flow Process Business.drawio.png`  
**Source:** `ESG Bedrock Reporting-Data Flow Process Business.drawio.xml`  
**Updated:** `ESG Bedrock Reporting-Data-flow-v2.png`

**Process Steps:**
1. **User Request** → "Generate GRI 305 report for 2024"
2. **Agent Processing** → Validates request, starts Step Functions
3. **ETL Pipeline** → Glue job extracts emissions data from RDS
4. **AI Generation** → 9 sections generated in parallel (Bedrock API)
5. **Assembly** → DOCX + PPTX reports created
6. **Validation** → Report quality checks
7. **Delivery** → Presigned S3 URLs returned to user

**Data Sources:**
- **RDS (MySQL):** Raw emissions, portfolio, social data
- **Glue ETL:** Transforms to Parquet format
- **Athena Tables:** `esg_emissions`, `pcaf_portfolio`, `social_metrics`, etc.

---

### 4. Step Functions Workflow

**File:** `stepfunctions_graph.png`  
**Updated:** `stepfunctions_graph_v2.png`

**States:**
1. **ValidateInput** (Task) → Lambda: `validate_input`
2. **GenerateSections** (Map) → Parallel execution of `section_gen` × 9
   - GRI_305_SCOPE1, SCOPE2, SCOPE3, INTENSITY, METHODOLOGY
   - IFRS_S2_STRATEGY_RISKS, GOVERNANCE, METRICS, PCAF_FINANCED_EMISSIONS
   - (Optional) DOUBLE_MATERIALITY
3. **FilterSections** (Task) → Lambda: `filter_sections`
4. **AssembleDocument** (Task) → Lambda: `assembly_doc`
5. **ValidateReport** (Task) → Lambda: `validation`
6. **HumanReview** (Choice) → Skip or wait for approval
7. **Success** (Succeed) → Return download URLs

**Execution Time:**
- **GRI_305:** ~3 minutes (5 sections)
- **IFRS_S2:** ~4 minutes (4 sections)
- **MULTI_FRAMEWORK:** ~8-12 minutes (9 sections + PPTX)

---

## 🎨 Diagram Details

### Color Coding

**Service Categories:**
- 🟦 **Blue** — Frontend & User Interface
- 🟩 **Green** — API & Integration
- 🟨 **Yellow** — Orchestration & Workflow
- 🟧 **Orange** — Compute & Processing
- 🟪 **Purple** — AI/ML Services
- 🟥 **Red** — Data Storage & Analytics

---

### Key Design Decisions

#### 1. Why Step Functions for Orchestration?
- **Parallel Execution:** Generate 9 sections simultaneously (9× faster)
- **Built-in Retry:** Auto-retry on transient Bedrock API errors
- **Visual Monitoring:** Execution timeline visible in console
- **Cost-Effective:** Pay only for state transitions (~$0.025 per execution)

#### 2. Why Lambda Layer for Document Generation?
- **Shared Dependencies:** python-docx, python-pptx used by multiple functions
- **Smaller Deployment Packages:** Functions stay under 10MB
- **Version Control:** Update layer once, all functions get new version
- **Cold Start Optimization:** Layer cached by Lambda runtime

#### 3. Why Athena for Analytics?
- **Serverless:** No database to manage
- **Cost-Optimized:** Pay only for data scanned (~$5/TB)
- **S3-Native:** Direct queries on Parquet files
- **Standard SQL:** Easy to add new metrics

#### 4. Why S3 Cache for Dashboard Data?
- **Cost Reduction:** Athena queries cost $0.01 each; cache is free
- **Faster Load Times:** S3 read = 100ms; Athena query = 3-5s
- **Refresh Control:** User triggers refresh only when needed
- **Hybrid Approach:** Best of both worlds (speed + freshness)

---

## 📊 Data Architecture

### Glue Tables

| Table | Columns | Partition | Format |
|-------|---------|-----------|--------|
| **esg_emissions** | year, scope, source, tco2e, location | year | Parquet |
| **pcaf_portfolio** | year, sector, borrower_id, loan_amount_idr, financed_emissions_tco2e, data_quality_score | year | Parquet |
| **social_metrics** | year, metric_type, department, value, unit | year | Parquet |
| **emission_factors** | source, region, factor_tco2e_per_unit, unit | - | Parquet |
| **sector_mapping** | borrower_id, sector_name, industry_code | - | Parquet |

### Data Flow

```
RDS (MySQL)
    ↓
Glue ETL Job (Python/PySpark)
    ↓
S3 Raw Data (Parquet)
    ↓
Glue Data Catalog
    ↓
Athena SQL Queries
    ↓
S3 Cache / Lambda Response
    ↓
Frontend Analytics Dashboard
```

---

## 🔄 Report Generation Flow

### Detailed Sequence

```
1. User: "Generate MULTI_FRAMEWORK report for 2024"
   └─> Frontend Chat.jsx → POST /chat

2. API Gateway → Bedrock Agent
   └─> Agent parses intent → Calls generate_report tool

3. Lambda (agent_tools) → Step Functions
   └─> StartExecution(esg-orchestrator)

4. Step Functions: ValidateInput
   └─> Lambda (validate_input)
   └─> ✅ Year=2024, Framework=MULTI_FRAMEWORK

5. Step Functions: GenerateSections (Map State)
   ├─> Lambda (section_gen) → "GRI_305_SCOPE1"
   ├─> Lambda (section_gen) → "GRI_305_SCOPE2"
   ├─> Lambda (section_gen) → "GRI_305_SCOPE3"
   ├─> Lambda (section_gen) → "IFRS_S2_STRATEGY_RISKS"
   ├─> Lambda (section_gen) → "IFRS_S2_GOVERNANCE"
   ├─> Lambda (section_gen) → "IFRS_S2_METRICS"
   ├─> Lambda (section_gen) → "IFRS_S2_PCAF_FINANCED_EMISSIONS"
   ├─> Lambda (section_gen) → "CSRD_ESRS_E1_CLIMATE_STRATEGY"
   └─> Lambda (section_gen) → "OJK_PSPK_GHG_INVENTORY"
       └─> Each Lambda → Bedrock API (Claude 3.5 Sonnet)
       └─> Each Lambda → S3 (section JSON)

6. Step Functions: FilterSections
   └─> Lambda (filter_sections)
   └─> Returns all 9 sections (no filtering)

7. Step Functions: AssembleDocument
   └─> Lambda (assembly_doc)
   └─> Reads 9 section JSONs from S3
   └─> Creates DOCX (42 pages) using python-docx
   └─> Creates PPTX (4 slides) using python-pptx
   └─> Uploads to S3: reports/MULTI_FRAMEWORK_2024_exec_abc123.docx
   └─> Uploads to S3: reports/MULTI_FRAMEWORK_2024_exec_abc123.pptx

8. Step Functions: ValidateReport
   └─> Lambda (validation)
   └─> ✅ DOCX readable, 9 sections present, 42 pages

9. Step Functions: Success
   └─> Return output with download URLs

10. User: "What's the status?"
    └─> Frontend → GET /status?execution_id=exec_abc123
    └─> Lambda (status_check) → Step Functions API
    └─> Response: "SUCCEEDED" + download_url + download_url_pptx
```

---

## 🔐 Security Architecture

### Network Security
- **Frontend:** HTTPS only (Amplify auto-SSL)
- **API Gateway:** TLS 1.2+ enforced
- **VPC (Optional):** Lambda can run in private subnet with NAT Gateway

### IAM Roles

```
┌─────────────────────────────────────────────┐
│ Bedrock Agent Role                          │
│ - bedrock:InvokeModel (Claude 3.5 Sonnet)  │
│ - bedrock:Retrieve (Knowledge Base)         │
│ - lambda:InvokeFunction (agent_tools)       │
└─────────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ Lambda (agent_tools) Role                   │
│ - states:StartExecution                     │
│ - states:DescribeExecution                  │
│ - s3:GetObject, s3:PutObject                │
└─────────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ Step Functions Role                         │
│ - lambda:InvokeFunction (all 10 Lambdas)    │
│ - states:StartExecution (self)              │
└─────────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ Lambda (section_gen, assembly, etc.) Role   │
│ - bedrock:InvokeModel (Claude 3.5 Sonnet)  │
│ - s3:GetObject, s3:PutObject                │
│ - athena:StartQueryExecution                │
│ - glue:GetTable                             │
│ - logs:CreateLogStream, logs:PutLogEvents   │
└─────────────────────────────────────────────┘
```

### Data Security
- **S3 Encryption:** AES-256 (server-side)
- **Presigned URLs:** Expire after 1 hour
- **Athena Results:** Encrypted at rest
- **RDS:** TLS for data in transit

---

## 💰 Cost Breakdown (per Report)

| Service | Usage | Cost |
|---------|-------|------|
| **Bedrock API (Claude 3.5 Sonnet)** | 9 sections × 12K tokens | $0.10 |
| **Step Functions** | 1 execution × 12 state transitions | $0.025 |
| **Lambda (section_gen)** | 9 invocations × 45s × 512 MB | $0.013 |
| **Lambda (assembly_doc)** | 1 invocation × 30s × 1024 MB | $0.005 |
| **Lambda (other)** | 5 invocations × 2s × 256 MB | $0.002 |
| **S3 Storage** | 1 report × 2 MB | $0.00005 |
| **Total per Report** | | **~$0.15** |

**Analytics Dashboard (per month):**
- S3 cache reads (default): **Free** (1000 reads = $0.0004)
- Athena refresh (manual): **$0.01 per query** (assume 10/month = $0.10)
- **Total Analytics:** **~$0.10/month**

---

## 📈 Scalability

### Current Limits
- **Bedrock API:** 10 requests/second (can increase via quota request)
- **Lambda Concurrency:** 1000 concurrent executions per region
- **Step Functions:** 100 concurrent executions (configurable)

### Scaling Strategy
1. **Horizontal Scaling:** Add more Lambda concurrency
2. **Rate Limiting:** API Gateway throttling (1000 req/sec)
3. **Batch Processing:** Queue reports in SQS for high volume
4. **Multi-Region:** Deploy to multiple regions for global users

### Performance Benchmarks
- **Report Generation:** 3-12 minutes (depends on framework)
- **Status Check API:** <500ms
- **Analytics Dashboard:** 100-300ms (S3 cache), 3-5s (Athena refresh)
- **Chat Response:** 2-4s (with knowledge base retrieval)

---

## 🛠️ Monitoring & Observability

### CloudWatch Dashboards

**1. Report Generation Metrics**
- Executions per hour (Step Functions)
- Success/Failure rate
- Average execution duration
- Bedrock API latency

**2. API Gateway Metrics**
- Request count per endpoint
- 4xx/5xx error rate
- Integration latency
- Cache hit rate

**3. Lambda Metrics**
- Invocation count per function
- Error rate
- Duration (P50, P90, P99)
- Concurrent executions

### Alarms
- **Critical:** Step Functions execution failures > 5%
- **Warning:** Lambda duration > 500s (section_gen)
- **Info:** API Gateway 5xx errors > 1%

---

## 🔄 CI/CD Pipeline

### Frontend (React)
```
GitHub (main branch)
    ↓
Amplify Build (auto-triggered)
    ↓
npm ci && npm run build
    ↓
Deploy to CDN (CloudFront)
    ↓
Live at: main.d337jqli3ubqmk.amplifyapp.com
```

### Backend (Lambda)
```
Local Development
    ↓
zip -r deploy/function.zip handler.py
    ↓
aws lambda update-function-code (manual)
    ↓
Test in AWS Console
    ↓
Tag version: aws lambda publish-version
```

**Future:** GitHub Actions for automated Lambda deployment

---

## 🔗 Diagram Files

All diagrams created with **draw.io** (free, open-source):
- Edit online: https://app.diagrams.net/
- Import `.drawio.xml` files to modify
- Export as PNG for documentation

**Version Control:**
- Keep both `.drawio.xml` (source) and `.png` (rendered) in repo
- Update both when making architecture changes

---

## 📚 Related Documentation

- **Backend README:** `../esg-reporting-poc/README.md`
- **Frontend README:** `../esg-chat-app-react/README.md`
- **Lambda Functions:** `../esg-reporting-poc/lambda/README.md`
- **Agent Setup:** `../esg-reporting-poc/agent/README.md`
- **Root README:** `../README.md`

---

**Maintained by:** Tokaicom Mitra Indonesia (Tokai Group)  
**Last Updated:** June 15, 2026
