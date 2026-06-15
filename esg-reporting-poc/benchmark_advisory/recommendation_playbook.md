---
framework: BENCHMARK
document_type: recommendation_playbook
category: advisory
region: indonesia
sector: banking
source_year: 2023-2025
---

# ESG Recommendation Playbook — Decision Tree
## Untuk Lembaga Jasa Keuangan Indonesia (Financial Institutions)

---

## Cara Pakai
```
IF [metric_status] = declining/below_peer
  → DIAGNOSE root cause
  → SELECT action from playbook
  → REFERENCE peer bank implementation
  → SET target (time-bound)
```

---

## 1. ENVIRONMENT — Emissions Increasing

### Decision Node: Scope 1+2 YoY ↑ >2%

```
├── IF Scope 1 ↑ (diesel/fuel)
│   ├── DIAGNOSIS: Expanded operations OR grid instability (genset usage)
│   ├── ACTION:
│   │   ├── [Short] Switch to biodiesel B35+ for gensets
│   │   ├── [Medium] Install solar panel at branches (ref: BRI Green Network)
│   │   └── [Long] EV fleet conversion (ref: BRI 118 EV cars + 150 bikes)
│   ├── PEER REF: BRI — 19.49% electricity savings via green building
│   └── TARGET: ↓5% Scope 1 within 12 months
│
├── IF Scope 2 ↑ (electricity)
│   ├── DIAGNOSIS: Data center expansion OR new branches
│   ├── ACTION:
│   │   ├── [Short] Auto-shutdown systems (ref: BRI Kaseya program)
│   │   ├── [Short] LED retrofit + elevator scheduling
│   │   ├── [Medium] Green building certification (ref: BRI Gold GBCI)
│   │   └── [Long] PPA with renewable provider OR RE100 commitment (ref: DBS)
│   ├── PEER REF: DBS — 62% renewable, ↓12% emissions YoY
│   └── TARGET: ↓3% Scope 2 intensity/employee within 12 months
│
└── IF Financed Emissions ↑ (Scope 3 Cat 15)
    ├── DIAGNOSIS: Portfolio growth in carbon-intensive sectors
    ├── ACTION:
    │   ├── [Short] Enhance ESRM screening for new loans
    │   ├── [Medium] Sectoral credit policy (ref: BCA — coal, palm oil, cement, O&G)
    │   ├── [Medium] Client engagement program for top 20 emitters
    │   └── [Long] Science-Based Target submission (ref: BRI — first ID FI)
    ├── PEER REF: BRI — SBTi committed, portfolio temp target 1.75°C by 2040
    └── TARGET: ↓4% financed emissions intensity within 24 months
```

---

## 2. SOCIAL — Training Hours Below Peer

### Decision Node: Training Hours/employee < 40 hours

```
├── IF low across all levels
│   ├── DIAGNOSIS: Budget constraint OR low L&D prioritization
│   ├── ACTION:
│   │   ├── [Short] Deploy e-learning platform (low cost, scalable)
│   │   ├── [Medium] Mandatory ESG module all levels (ref: BCA Sustainability Awareness Month)
│   │   └── [Long] Structured learning path per position level
│   ├── PEER REF: BRI — 62.4 hrs avg, training includes BoC to Non-staff
│   └── TARGET: ≥50 hours/employee within 12 months
│
├── IF low for leadership specifically
│   ├── DIAGNOSIS: BoD/BoC not engaged in sustainability
│   ├── ACTION:
│   │   ├── [Short] Annual ESG refresher for Board (ref: BCA practice)
│   │   ├── [Medium] External ESG expert sessions at Board meetings
│   │   └── [Long] ESG KPI in Board remuneration (ref: DBS 20% weight)
│   ├── PEER REF: BCA — BoD/BoC annual ESG refresher with GRI, CDP, OJK collaboration
│   └── TARGET: 100% Board completion of ESG program annually
```

---

## 3. SOCIAL — Gender Diversity Below Threshold

### Decision Node: Female in Management < 30%

```
├── IF pipeline issue (low female in middle management)
│   ├── DIAGNOSIS: Promotion bottleneck OR bias in selection
│   ├── ACTION:
│   │   ├── [Short] Set 30% female target for leadership pipeline
│   │   ├── [Medium] Mentorship/sponsorship program for women
│   │   └── [Long] Board Diversity Policy (ref: DBS — 33% female on Board)
│   ├── PEER REF: DBS — 38% female in management, equal pay 1:0.99
│   └── TARGET: ≥30% female management within 24 months
│
├── IF disclosure gap (no gender pay data)
│   ├── DIAGNOSIS: Data system not capturing OR strategic avoidance
│   ├── ACTION:
│   │   ├── [Short] Gender pay audit (internal)
│   │   ├── [Medium] Publish gender pay ratio in sustainability report
│   │   └── [Long] Full equal pay disclosure (ref: DBS practice)
│   └── TARGET: Disclose by next reporting cycle
```

---

## 4. GOVERNANCE — ESG Rating Below Peer

### Decision Node: MSCI < A OR Sustainalytics > 25

```
├── IF low E-score (environment)
│   ├── DIAGNOSIS: Insufficient climate disclosure OR no target
│   ├── ACTION:
│   │   ├── [Short] Publish TCFD-aligned climate report
│   │   ├── [Medium] Set science-based target (SBTi letter)
│   │   ├── [Medium] Expand Scope 3 measurement (beyond Cat 15)
│   │   └── [Long] Achieve reasonable assurance on GHG data
│   ├── PEER REF: DBS — MSCI AA, CDP A-, full TCFD, SBTi committed
│   └── TARGET: MSCI upgrade to A within 18 months
│
├── IF low G-score (governance)
│   ├── DIAGNOSIS: Weak ESG governance linkage to strategy
│   ├── ACTION:
│   │   ├── [Short] Establish Board-level ESG committee (ref: BRI model)
│   │   ├── [Medium] Link ESG KPI to executive remuneration
│   │   └── [Long] Independent CSO/Chief Sustainability Officer role (ref: DBS)
│   ├── PEER REF: BRI — BoD-level ESG Committee since 2021, KPI integrated
│   └── TARGET: Full governance structure within 6 months
│
└── IF low S-score (social)
    ├── DIAGNOSIS: Disclosure gap on labor practices or supply chain
    ├── ACTION:
    │   ├── [Short] Publish workforce data (diversity, turnover, training)
    │   ├── [Medium] Supply chain due diligence (human rights)
    │   └── [Long] Living wage commitment + supply chain ESG audit
    ├── PEER REF: BCA — zero tolerance policy, 100% whistleblowing investigated
    └── TARGET: Improve social disclosure score within 12 months
```

---

## 5. COMPLIANCE — Framework Gap

### Decision Node: Framework Adoption Incomplete

```
├── IF no PCAF calculation
│   ├── ACTION: Start with top 3 sectors by exposure → expand
│   ├── PEER REF: BRI (6 asset classes), BCA (Scope 3 Cat 15)
│   └── TARGET: First PCAF disclosure within 12 months
│
├── IF no TCFD/ISSB alignment
│   ├── ACTION: Map existing disclosures → gap analysis → phased adoption
│   ├── PEER REF: BCA — initial IFRS S1/S2 analysis started
│   └── TARGET: Full TCFD alignment by next report, ISSB by 2027
│
├── IF SFAP target missed
│   ├── DIAGNOSIS: Green portfolio growth slower than total portfolio
│   ├── ACTION:
│   │   ├── [Short] Redefine eligible activities per THI/TKBI
│   │   ├── [Medium] Launch SLL product for existing clients
│   │   └── [Long] Green bond issuance to attract dedicated capital
│   ├── PEER REF: BCA — exceeded SFAP target via SLL + Green Loan schemes
│   └── TARGET: Exceed SFAP target by 10% next fiscal year
│
└── IF no external assurance
    ├── ACTION: Start with limited assurance on Scope 1+2 → expand
    ├── PEER REF: DBS — progressing to reasonable assurance on key metrics
    └── TARGET: Limited assurance Year 1, Reasonable on GHG by Year 3
```

---

## Quick Reference: Bank Strengths to Benchmark

| Bank | Strongest Pillar | Learn From Them For |
|------|-----------------|---------------------|
| **BRI** | Climate commitment (SBTi, NZE, PCAF full) | Financed emissions methodology, SBTi process, EV fleet |
| **BCA** | Governance + SFAP execution | Sectoral credit policies, Board ESG integration, green office |
| **DBS** | ESG ratings + Renewable energy | RE100 journey, MSCI AA achievement, reasonable assurance |
| **Mandiri** | Scale + MSME reach | Financial inclusion metrics, SDG impact measurement |
