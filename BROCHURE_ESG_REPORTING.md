# 🌿 ESG Intelligent Reporting

### Automated ESG Sustainability Report Generation for Financial Institutions

**By Tokaicom Mitra Indonesia (Tokai Group)**  
**Powered by Amazon Bedrock & AWS Serverless**

---

## 1. The Problem — Why ESG Reporting Hurts

### Sustainability Compliance Is No Longer Optional

Regulators worldwide — from OJK in Indonesia to the EU's CSRD directive — now **mandate** ESG disclosures. Financial institutions face a perfect storm:

| Pain Point | Impact |
|-----------|--------|
| 📄 **Manual report writing** | Sustainability teams spend **6-8 weeks** per annual report, manually compiling data from 10+ systems |
| ⚠️ **Multi-framework chaos** | Must produce reports for GRI, IFRS S2, CSRD/ESRS, AND local regulations (OJK POJK 51) — each with different structures, metrics, and terminology |
| 🔢 **Data accuracy risk** | Manual copy-paste from spreadsheets introduces **human errors** in emission calculations — a single wrong emission factor can misstate thousands of tCO₂e |
| 💰 **Consultant dependency** | Engaging external consultants for ESG reports costs **IDR 500M-2B+** per year |
| ⏱️ **Deadline pressure** | OJK filing deadlines are fixed — late submissions trigger regulatory sanctions |
| 🔄 **No version control** | Multiple stakeholders editing Word docs = version conflicts, lost changes, and audit trail gaps |
| 📊 **No real-time visibility** | Management cannot see ESG metrics until the annual report is published — too late for corrective action |

### Who Feels This Pain?

- **Head of Sustainability / ESG** — owns the report, drowning in manual work
- **CFO / Risk** — needs emission intensity KPIs for investor relations
- **Compliance** — must ensure disclosures meet regulatory standards
- **Board of Directors** — needs dashboard visibility, not 200-page PDFs

> *"Kami menghabiskan 2 bulan setiap tahun hanya untuk menyusun laporan ESG secara manual. Data dari 220 cabang harus dikompilasi satu per satu."*  
> — Typical Sustainability Manager, Indonesian Bank

---

## 2. The Solution — AI That Writes Your ESG Report

### ESG Intelligent Reporting: From Raw Data to Board-Ready Report in Minutes

We replace the **6-8 week manual process** with an AI-powered pipeline that generates compliant ESG reports in **under 5 minutes** — directly from your operational data.

---

### Before vs After

| | ❌ Before (Manual) | ✅ After (ESG Intelligent Reporting) |
|---|---|---|
| **Data Collection** | Export from 5+ systems, manual consolidation in Excel | Automated ingestion from data lake (S3 + Athena) |
| **Calculation** | Sustainability team applies emission factors manually | Glue ETL auto-computes Scope 1/2/3 with verified IPCC/DEFRA factors |
| **Report Writing** | Consultants draft narratives over 4-6 weeks | AI generates compliant narratives in 2-3 minutes per section |
| **Quality Check** | Manual peer review (1-2 weeks) | 21-rule automated validation catches errors instantly |
| **Multi-Framework** | Rewrite entire report per framework | One click: same data → GRI, IFRS S2, CSRD, OJK output |
| **Formatting** | Manual Word/PPT formatting (2-3 days) | Auto-assembled DOCX with corporate branding, TOC, and GRI index |
| **Visibility** | Annual snapshot only | Real-time dashboard with 14 charts + 6 KPIs |
| **Time to Deliver** | 6-8 weeks | **< 5 minutes** (single framework) |
| **Cost** | IDR 500M-2B/year (consultants) | **~IDR 3M/month** (AWS pay-per-use) |

---

### How It Works

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Your Data   │ ──► │  AI Processing  │ ──► │   Validation     │ ──► │  Output      │
│              │     │                 │     │                  │     │              │
│ • Energy     │     │ • ETL Pipeline  │     │ • 21 QA Rules    │     │ • DOCX Report│
│ • Loans      │     │ • Claude 4.5    │     │ • Auto-retry     │     │ • Dashboard  │
│ • HR Metrics │     │ • RAG (KB)      │     │ • Audit trail    │     │ • KPI Cards  │
│ • Financials │     │ • Templates     │     │                  │     │ • Download   │
└──────────────┘     └─────────────────┘     └──────────────────┘     └──────────────┘
```

**User Experience:** Simply chat with the AI assistant — *"Generate my GRI 305 ESG report for 2024"* — and receive a board-ready document.

---

### Key Capabilities

| Capability | Description |
|-----------|-------------|
| 🤖 **Conversational AI** | Chat interface — ask in natural language, get reports |
| 📋 **4 Frameworks** | GRI 305, IFRS S2, CSRD/ESRS E1, OJK POJK 51 |
| 🌍 **Environment + Social** | Scope 1/2/3 emissions AND workforce metrics (GRI 400-series) |
| 📊 **14 Interactive Charts** | Emissions breakdown, PCAF quality, gender diversity, training trends |
| ✅ **Auto-Validation** | 21 rules verify numeric accuracy, prohibit fabricated data |
| 📚 **Knowledge Base** | RAG retrieval from 15+ regulatory documents for accurate citations |
| 🔄 **Multi-Framework** | One dataset → reports for ALL 4 frameworks simultaneously |
| ⚡ **Real-Time Dashboard** | Live KPIs — no more waiting for annual publication |
| 🔒 **Audit Trail** | Every number traceable to source data (S3 object tags + versioning) |

---

## 3. Results — What Our POC Demonstrates

### Business Outcomes (Based on POC with 220 Facilities, 2,200 Loans, 25,000 FTE)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Report generation time** | 6-8 weeks | **3-5 minutes** | **99.9% faster** |
| **Cost per annual report** | IDR 500M-2B | **IDR ~3M/month** | **Up to 99% cost reduction** |
| **Data accuracy** | ~95% (manual errors) | **99.9%** (validated against source) | Eliminates human error |
| **Framework coverage** | 1 framework per engagement | **4 frameworks** simultaneously | 4× more coverage |
| **Time to insight (dashboard)** | Annual (once per year) | **Real-time** (cached <500ms) | Always-on visibility |
| **Headcount dependency** | 3-5 FTE for 2 months | **0 FTE** (fully automated) | Frees sustainability team |
| **Revision cycles** | 3-5 revision rounds | **1 automated retry** + download | Eliminates back-and-forth |

### MVP Scope (Delivered)

| Component | Status | Description |
|-----------|--------|-------------|
| ✅ AI Report Generator | Done | End-to-end pipeline: data → AI narrative → validated DOCX |
| ✅ Chat Interface | Done | Natural language interaction with Bedrock Agent |
| ✅ Analytics Dashboard | Done | 14 charts, 6 KPI cards, real-time data |
| ✅ Multi-Framework | Done | GRI 305, IFRS S2, CSRD ESRS E1, OJK PSPK |
| ✅ Social (S) Pillar | Done | Workforce, diversity, training, non-discrimination |
| ✅ Automated Validation | Done | 21-rule QA engine with retry logic |
| ✅ Download Portal | Done | Presigned URLs for DOCX (1-hour expiry) |
| 🔄 Governance (G) Pillar | Roadmap | Board composition, ethics, anti-corruption |
| 🔄 PDF Export | Roadmap | Alternative to DOCX for public disclosure |
| 🔄 Bahasa Indonesia | Roadmap | Multi-language report generation |

---

## 4. Metrics — AWS Service Performance

### Infrastructure Performance (Measured from POC)

| AWS Service | Metric | Result | Benchmark |
|-------------|--------|--------|-----------|
| **Amazon Bedrock** (Claude Sonnet 4.5) | Section generation latency | 15-25s per section | Target <30s ✅ |
| **Amazon Bedrock** | Token throughput | ~12K tokens input / ~4K output per section | Standard tier |
| **AWS Step Functions** | End-to-end orchestration | 3-5 min (7 sections) | Target <5 min ✅ |
| **AWS Lambda** | Cold start | <200ms | Target <500ms ✅ |
| **AWS Lambda** | Assembly (DOCX gen) | 8-12s | Target <30s ✅ |
| **Amazon Athena** | Dashboard query | <3s (50MB scan) | Target <5s ✅ |
| **Amazon S3** | Cached dashboard read | <200ms | Target <500ms ✅ |
| **API Gateway** | Request latency (P95) | 45ms | Target <100ms ✅ |
| **AWS Amplify** | Frontend First Contentful Paint | <1s | Target <2s ✅ |
| **OpenSearch Serverless** (KB) | RAG retrieval | <2s for 5 relevant chunks | Target <3s ✅ |

### Cost Efficiency

| Scenario | Monthly Cost | Cost per Report |
|----------|-------------|----------------|
| Development (10 reports) | ~$30* | $3.00 |
| Production (100 reports) | ~$190 | $1.90 |
| Optimized (no OpenSearch) | ~$30 | $0.30 |

*\*Without OpenSearch Serverless ($173/month minimum). Can switch to Aurora Serverless vector store for production optimization.*

### Scalability

| Dimension | Current | Scalable To |
|-----------|---------|-------------|
| Concurrent reports | 10 | 100+ (Lambda concurrency) |
| API requests/sec | 1,000 | 10,000 (API Gateway) |
| Data volume | 220 facilities | 10,000+ (Athena partition projection) |
| Frameworks | 4 | Unlimited (template-driven) |
| Languages | English | Multi-language (model capability) |

---

## 5. Industry Context

### Regulatory Landscape (2024-2026)

| Regulation | Jurisdiction | Deadline | Impact |
|-----------|-------------|----------|--------|
| **OJK POJK 51/2017** | Indonesia | Annual filing | All financial institutions MUST report sustainability |
| **CSRD/ESRS** | EU | FY 2024 (large) | 50,000+ companies, mandatory assurance |
| **IFRS S2** (ISSB) | Global | FY 2025 | Climate disclosures for listed companies |
| **GRI 305** | Global | Voluntary → Mandatory trend | De facto standard for emissions reporting |
| **OJK Taxonomy** (Green Finance) | Indonesia | 2024 | Green loan classification + reporting |

### Market Opportunity

- **600+ financial institutions** in Indonesia subject to OJK sustainability reporting
- **Global ESG reporting market** projected to reach $5.6B by 2028 (CAGR 13.7%)
- **73% of Indonesian banks** still use manual Excel-based ESG compilation (2024 survey)
- Average bank spends **3,200 person-hours/year** on sustainability reporting

### Why Financial Institutions First?

1. **Highest regulatory pressure** — OJK mandates, investor demands, green bond requirements
2. **Data already exists** — energy, loans, HR data in core systems
3. **PCAF complexity** — financed emissions (Scope 3 Cat 15) requires sector-level calculations most teams can't do manually
4. **Multi-framework burden** — same institution must report to OJK, GRI, IFRS, and potentially CSRD

---

## 6. Screenshots — What to Capture

> **Instruksi:** Screenshot halaman-halaman berikut dari live app (`https://main.d337jqli3ubqmk.amplifyapp.com`):

### Screenshot 1: Analytics Dashboard (Light Theme)
**Page:** Analytics  
**What to capture:** Full page showing 6 KPI cards at top + first row of 3 charts (Emissions by Scope pie, Scope 1 Sources pie, Scope 2 bar)  
**Theme:** Switch to Light mode first (click Sun icon in sidebar)  
**Why:** Shows the modern, clean UI that executives will interact with daily  

### Screenshot 2: Analytics Dashboard — Social Section (Light Theme)
**Page:** Analytics (scroll down to Social section)  
**What to capture:** The "Social (S)" section header + 4 charts (Gender Diversity, Female in Management ring, Training Hours, Turnover & Hiring)  
**Theme:** Light mode  
**Why:** Demonstrates the breadth of ESG coverage beyond just Environment  

### Screenshot 3: Chat Interface — Report Generation
**Page:** Chat  
**What to capture:** A conversation showing:
1. User asks "Generate a GRI 305 report for 2024"
2. Agent responds with execution ID
3. Progress indicator showing "Generating report..."
4. Success message with Download DOCX button  
**Theme:** Either dark or light (whichever looks better)  
**Why:** Shows the natural language interaction — no training needed  

### Screenshot 4: Overview Dashboard
**Page:** Overview  
**What to capture:** Full page with stat cards (Total Reports, Succeeded, Failed, In Progress), trend chart, and Quick Actions  
**Theme:** Dark mode (shows the premium glassmorphism design)  
**Why:** First impression — demonstrates the executive-level polish  

### Screenshot 5: Architecture Diagram
**File:** `architecture/ESG Bedrock Reporting-ESG Reporting Architecture.png`  
**What to capture:** The full architecture diagram showing AWS services  
**Why:** Technical credibility for IT decision makers  

### Screenshot 6: Generated DOCX Report
**What to capture:** Open a generated ESG report in Microsoft Word, showing:
- Table of Contents
- A section heading (e.g., "GRI 305-1: Direct Scope 1 GHG Emissions")
- Data tables with emission figures
- Professional formatting (Arial, justified text, blue headings)  
**Why:** Shows the final deliverable quality  

### Screenshot 7: Reports History Page
**Page:** Reports  
**What to capture:** Table showing past executions with Status badges (green Succeeded), Framework labels, and Download buttons  
**Theme:** Light mode  
**Why:** Shows traceability and audit trail  

---

## 7. Technology Stack

### AWS Services Used

| Service | Role in Solution | Why This Service |
|---------|-----------------|-----------------|
| **Amazon Bedrock** (Claude Sonnet 4.5) | AI narrative generation + conversational agent | Best-in-class reasoning for regulatory language |
| **Amazon Bedrock Knowledge Base** | RAG retrieval from ESG frameworks | Semantic search over regulatory documents |
| **AWS Step Functions** | Pipeline orchestration (validate → generate → validate → assemble) | Deterministic, observable, retryable workflows |
| **AWS Lambda** (11 functions) | Serverless compute for each pipeline stage | Zero idle cost, auto-scaling |
| **Amazon Athena** | SQL queries over Parquet data lake | Serverless analytics, $5/TB scanned |
| **AWS Glue** | ETL — emission factor calculations | Spark-based processing for raw → curated transformation |
| **Amazon S3** (6 buckets) | Data lake (raw/curated/aggregated) + report storage | Durability, versioning, encryption |
| **Amazon API Gateway** | REST API for frontend | Managed, scalable, CORS-ready |
| **AWS Amplify** | Frontend hosting (React + Vite) | CI/CD from GitHub, CDN distribution |
| **Amazon OpenSearch Serverless** | Vector store for Knowledge Base | Semantic similarity search |

---

## 8. Conclusion

### ESG Intelligent Reporting transforms sustainability compliance from a costly burden into a competitive advantage.

**For the Sustainability Team:**
> Dari 6-8 minggu kerja manual → laporan siap dalam hitungan menit. Tim bisa fokus ke strategi, bukan kompilasi data.

**For the CFO:**
> Dari IDR 500M+ biaya konsultan per tahun → IDR 3M/bulan. ROI tercapai di bulan pertama.

**For the Board:**
> Real-time dashboard dengan 14 chart dan 6 KPI — visibility ESG bukan lagi laporan tahunan yang terlambat.

**For Compliance:**
> 4 framework (GRI, IFRS, CSRD, OJK) dari satu data source, dengan 21 aturan validasi otomatis. Audit trail lengkap.

---

### Next Steps

| Step | Timeline | Action |
|------|----------|--------|
| 1. Discovery | Week 1 | Map your existing data sources + regulatory requirements |
| 2. Data Integration | Week 2-3 | Connect energy/loan/HR data to data lake |
| 3. Configuration | Week 3-4 | Configure frameworks, templates, branding |
| 4. UAT | Week 4-5 | Generate reports, validate against historical publications |
| 5. Go-Live | Week 6 | Production deployment + team training |

**Total Implementation: 6 weeks** (vs. 6 months for traditional ESG software)

---

### Contact

**Tokaicom Mitra Indonesia (Tokai Group)**  
ESG Intelligent Reporting Solution

*Made with ☁️ on Amazon Web Services*

---

## References

| # | Source | Used For |
|---|--------|----------|
| 1 | `esg-reporting-poc/docs/IMPLEMENTATION_CHANGELOG.md` | Technical specs, 91 deviations, execution times, Lambda architecture |
| 2 | `esg-reporting-poc/docs/INFRASTRUCTURE_REFERENCE.md` | Deployed resource configurations, performance data, cost structure |
| 3 | `esg-reporting-poc/docs/SPEC_AMENDMENTS.md` | 76 tracked amendments, design decisions |
| 4 | `esg-reporting-poc/docs/VALIDATION_FALSE_POSITIVES.md` | Validation accuracy metrics |
| 5 | `INFRASTRUCTURE_SPEC.md` | Complete infrastructure specification (32+ resources) |
| 6 | `DEPLOYMENT_GUIDE.md` | Deployment architecture and procedures |
| 7 | `esg-chat-app-react/src/pages/Analytics.jsx` | Dashboard capabilities (14 charts, 6 KPIs) |
| 8 | OJK POJK 51/POJK.03/2017 | Indonesian sustainable finance regulation |
| 9 | GRI 305: Emissions 2016 | GHG emissions reporting standard |
| 10 | IFRS S2 Climate-related Disclosures 2023 | Global climate disclosure standard |
| 11 | CSRD/ESRS E1 2023 | EU climate change reporting standard |
| 12 | PCAF Global GHG Accounting Standard 2022 | Financed emissions methodology |
| 13 | AWS Well-Architected Framework — Serverless Lens | Architecture best practices |
| 14 | Amazon Bedrock Documentation (2025) | AI/ML service capabilities |

---

*Document Version: 1.0 | June 2026 | Tokaicom Mitra Indonesia*
