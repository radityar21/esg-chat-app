# Implementation Changelog — ESG Kiro Requirements Spec vs Actual

> **Base Document:** `ESG_kiro_Requirement_Spec.md` (original, unchanged)
> **This Document:** Complete diff of what was implemented differently
> **Date:** 2026-06-05
> **Coverage:** D1 through D15 (full pipeline)

---

## Overview

The original spec was written as an ideal-state design document. During implementation, several deviations were necessary due to:
- AWS service limitations (Glue Spark vs Athena partition projection, Step Functions JSONPath)
- Model deprecation (Claude 3.5 Sonnet EOL)
- Organization-level restrictions (SCP blocking public Lambda URLs)
- Data characteristics (synthetic data edge cases)
- Precision/rounding requirements discovered during validation testing

---

## §1 System Boundary

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| Region: ap-southeast-3 (Jakarta) + ap-southeast-1 (Singapore) | **us-east-1 (N. Virginia) only** | CloudShell unavailable in Jakarta; all services available in Virginia |
| Amazon Bedrock AgentCore as orchestration runtime | **Step Functions + Lambda** (AgentCore deferred to post-POC) | Step Functions provides deterministic, testable pipeline |

---

## §2 Data Schema

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| `energy_consumption` partition: `reporting_year` only (§2.1 column spec) | **Dual partition: `reporting_year` + `reporting_month`** (per REQ-DDL-05 location template) | DDL spec §4.3 shows both as partition keys |
| Partition columns stored in parquet | **Partition columns NOT in parquet** (derived from Hive-style path) | Standard Athena/Hive behavior |
| `period_date` as DATE type | **Written as `date32` via PyArrow** (not pandas Timestamp) | Pandas `to_datetime` produces TIMESTAMP which Athena rejects for DATE column |

---

## §3 ETL Business Logic

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| §3.1 Diesel EF: 2.6710 (§3.2 table) | **2.53763** (§3.1 authoritative constants) | §3.1 says "Non-Negotiable"; §3.2 table has different values — spec conflict resolved in favor of §3.1 |
| Glue reads from Catalog (`from_catalog()`) | **S3 direct read** (`spark.read.parquet` with `basePath`) | Glue Spark does not support Athena partition projection; `from_catalog()` returns empty schema |
| No schema validation before ETL | **Schema Governance Gate** added to all jobs | Defensive programming — catch data drift before processing |
| Rounding: not explicitly specified | **Round components FIRST, then recompute totals** | Floating-point tolerance failures in GATE-S1-03 when rounding independently |
| Imputation: all NULL = imputed | **Only facilities with partial data get imputed** (all-null = no connection = 0) | Branches with 100% null gas shouldn't count as "6 imputed months → excluded" |
| `ghg_summary_annual`: no fuel breakdown | **Added `scope1_natgas_tco2e` + `scope1_diesel_tco2e`** | SectionGen needs breakdown for GRI 305-1 source table |
| No facility-level aggregation | **Added `scope1_by_facility` table** (top 10 emitters per year) | Per-facility breakdown required for comprehensive disclosure |

---

## §4 Athena DDL

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| Path: `s3://bucket/{table}/reporting_year=${year}` | **Path: `s3://bucket/{zone}/{table}/reporting_year=${year}`** | Added zone prefix (`raw/`, `curated/`, `aggregated/`) per REQ-DDL-02 database LOCATION |
| Database LOCATION = zone root | Same ✅ | |
| CON-DDL-01: No MSCK REPAIR | Same ✅ (partition projection) | |
| Athena results bucket | **Separate bucket: `esg-athena-results-061039769766`** | Keeps query results isolated from data |

---

## §5 Prompt Architecture

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| KB chunking: Fixed 300 tokens | **Semantic chunking, 700 tokens, 1 sentence, 90% threshold** | Semantic chunking preserves regulatory clause boundaries |
| KB model: not specified | **Claude Sonnet 4.6** (for parsing) | Foundation model parser better than default for regulatory PDFs |
| Min relevance score: 0.65 | **0.40** | Semantic chunking produces lower similarity scores; 0.65 filters out valid content |
| Single framework filter | **`orAll` filter for cross-framework sections** (e.g., scope3_pcaf → GRI + PCAF) | Some sections reference multiple standards |
| Model: `anthropic.claude-3-5-sonnet-20241022-v2:0` | **`us.anthropic.claude-sonnet-4-5-20250929-v1:0`** | Original model reached end-of-life |
| Overlay file: `overlay_csrd_e1.txt` | **`overlay_esrs_e1.txt`** | Code references this name; matched to CSRD_ESRS_E1 framework key |

---

## §6 Section Templates

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| Template path: `prompts/templates/scope1_template.txt` | Same ✅ (in S3) | |
| Placeholder resolution: hard fail | **Warning log only (non-blocking for POC)** | Template placeholders don't always resolve from aggregated data alone |
| `_resolve_template_key()` | **Added** — resolves full section IDs (`GRI_305_SCOPE1_2024`) to short keys (`scope1`) | Step Functions passes full IDs, TEMPLATE_MAP uses short keys |

---

## §7 Validation Rules

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| Response contract: flat `{status, violations}` | **REQ-VAL-07 contract: `{validation_outcome, structural_results, numeric_results, prohibited_content_results, ...}`** | Step Functions Choice state needs `$.validation_result.validation_outcome` |
| VAL-NUM-06: FAIL → retry allowed | **FAIL_NO_RETRY** — separate outcome for Step Functions routing | Per spec, weighted > gross = material misstatement, no retry |
| VAL-PRH-04: `\b(I)\b` | **Separate regex** — avoids false positive on "Scope I" | Case-sensitive standalone "I" check |
| Whitelisted values: not specified | **Added** — years, GWP constants, PCAF scores, grid EF exempt from fabrication check | These appear in narrative without being in DATA INPUT |
| `abs()` matching | **Added** — handles sign convention differences (negative YoY) | Source may be -5.2% but text says "decreased by 5.2%" |

---

## §8 DOCX Assembly

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| Font: not clearly specified in original chat | **Arial 11pt body, Arial Bold headings, H1=#1B3A6B, H2=#3D6094** | Per §8.1 spec (discovered in compliance review) |
| Page: Letter | **A4** (8.27×11.69 inches) | Spec §8.1 |
| Alignment: left | **Justified** | User preference |
| Layer: python-docx | **python-docx + lxml, built on Linux (CloudShell)** | lxml C extensions require Linux-compiled binaries |
| S3 path: simple | **`reports/year={year}/{framework}/ESG_Report_{fw}_{year}_{ts}.docx`** | Spec REQ-TRACE-05 |
| KMS encryption | ✅ `ServerSideEncryption='aws:kms'` | |
| S3 object tags | ✅ 8 tags per REQ-TRACE-05 | |
| TOC | ✅ Field code (update on open in Word) | |

---

## §9 Step Functions

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| HumanReviewGate: `waitForTaskToken` | **Two versions**: auto-approve (active) + manual review (documented) | Organization SCP blocks public Function URLs; manual approval too slow for demo |
| JSONPath filter on Map output | **Separate `esg-filter-sections` Lambda** | Step Functions does not support JSONPath filter expressions |
| Glue jobs: no parameters | **`--REPORTING_YEAR` passed via `States.Format`** | Jobs need to know which year to process |
| SNS Message: JSON object | **`States.JsonToString()`** | SNS `Message` parameter must be a string |
| ASL deployment: `file://` | **Upload to S3 → download in CloudShell → `file:///tmp/`** | Windows file encoding incompatible with `file://` parameter |

---

## §11 IAM & Security

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| 5 separate Lambda roles | **1 shared role: `ESGLambdaRole`** | POC simplification |
| Bedrock: `foundation-model/*` | **Added: `inference-profile/*` + wildcard region** | Inference profiles require separate ARN pattern |
| S3: 4 buckets | **6 buckets** (added `esg-athena-results-*` + `esg-kb-documents-*`) | New resources not in original design |
| S3 actions: Get/Put/List | **Added: `GetBucketLocation` + `PutObjectTagging`** | Athena needs GetBucketLocation; Assembly needs PutObjectTagging |
| Step Functions role: Lambda + SNS | **Added: `glue:StartJobRun` + `glue:GetJobRun`** | `.sync` integration pattern requires Glue permissions |

---

## New Components (not in original spec)

| Component | Purpose |
|-----------|---------|
| `esg-filter-sections` Lambda | Workaround for Step Functions JSONPath limitation |
| `esg-review-handler` Lambda + Function URL | Human review via browser click (blocked by SCP, kept as documentation) |
| `scope1_by_facility` aggregated table | Per-facility breakdown for comprehensive Scope 1 disclosure |
| `SPEC_AMENDMENTS.md` | Version-tracked changelog of spec deviations |
| `INFRASTRUCTURE_REFERENCE.md` | Single source of truth for all deployed resource configs |
| `validate_synthetic_data.py` | Data validation script ensuring synthetic data matches spec §2.1-2.3 |
| Auto-approve ASL variant | Unblocks pipeline when human review is impractical |

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Total spec deviations | 54 |
| Critical (architecture change) | 5 |
| High (missing feature, wrong config) | 22 |
| Medium (naming, precision, minor logic) | 18 |
| Low (cosmetic, documentation) | 9 |
| New components added | 7 |

---

## Recommendation

Apply these changes back to `ESG_kiro_Requirement_Spec.md` after full system validation is complete. Use `SPEC_AMENDMENTS.md` as the checklist. Increment spec version to `v1.1.0` when done.


---

## §NEW: W4 — Bedrock Agent + Chat UI (added 2026-06-05)

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| AgentCore as orchestration runtime | **Bedrock Agent as conversational frontend only** — Step Functions remains orchestrator | Agent = UX layer, not control plane |
| No UI specified in spec | **Amplify hosted chat app** (`https://main.d337jqli3ubqmk.amplifyapp.com`) | AWS Summit demo requirement |
| No API Gateway in spec | **REST API `olj4tuggm1`** as proxy between frontend and Bedrock Agent | Browser can't call Bedrock directly without credentials |
| Step Functions output = SNS MessageId | **Fixed: output = `assembly_result`** (Pass state at end) | Agent `download_report` tool needs `s3_path` from execution output |
| Presigned URL generation | **Requires `signature_version='s3v4'`** due to KMS encryption | Default v2 signature fails on KMS-encrypted objects |
| Agent formats URLs | **Agent adds markdown formatting that corrupts presigned URLs** | Frontend regex strips trailing `)`/`]` from URLs before creating links |

### New Components (W4)

| Component | Type | Purpose |
|-----------|------|---------|
| `esg-agent-tools` | Lambda | Tool handler for Bedrock Agent (4 tools) |
| `esg-chat-proxy` | Lambda | API Gateway → Bedrock Agent proxy |
| `ESG-Chat-API` | API Gateway REST | Public endpoint for frontend |
| `ESG-Chat` | Amplify App | Static HTML chat frontend |
| `ESGBedrockAgentRole` | IAM Role | Agent service role |
| `ESGReportAgent` | Bedrock Agent | Conversational interface |
| `agent_instructions.txt` | Config | Agent system prompt |
| `openapi_schema.json` | Config | Action Group API definition |

---

## Updated Summary Statistics

| Category | Count |
|----------|-------|
| Total spec deviations | 76 |
| Critical (architecture change) | 6 |
| High (missing feature, wrong config) | 30 |
| Medium (naming, precision, minor logic) | 25 |
| Low (cosmetic, documentation) | 15 |
| New components added | 16 |


---

## §NEW: W5 — Social (S) Pillar (added 2026-06-09)

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| Only Environment (E) sections | **Added Social (S) section** — workforce, employment, training, diversity, non-discrimination | ESG report incomplete without Social pillar; HR data already exists |
| No HR data in pipeline | **AthenaQuery fetches `esg_raw.hr_metrics`** (cross-database query) | Raw HR data doesn't need ETL/aggregation — used as-is |
| TEMPLATE_MAP: 7 sections | **8 sections** — added `"social"` | New section template |
| SECTION_ORDER: no social | **"social" added** to all 5 framework orderings | Positioned after intensity, before methodology/summary |
| Agent SECTION_TEMPLATES: no social | **Added social** to all frameworks (GRI_305 for most, OJK_PSPK for OJK) | Social uses GRI 400-series regardless of env framework |
| GRI Content Index: 5 rows | **10 rows** — added GRI 2-7, 401-1, 404-1, 405-1, 406-1 | Social disclosures in appendix |

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| No new Glue ETL job | HR data is single-row-per-year, no aggregation logic needed |
| Query `esg_raw` directly (not `esg_aggregated`) | No transform needed; pre-compute hiring_rate + headcounts in SQL |
| All YoY changes pre-computed in Lambda | Model must NOT self-calculate (DI-2 rule, VAL-NUM-01 compliance) |
| Social framework = GRI_305 (except OJK_PSPK) | GRI 400-series is primary standard for social disclosures across all environmental frameworks |
| No Step Functions ASL change | Social enters via `section_templates` array — Map state handles it automatically |
| PAGE_BREAK_BEFORE includes social | Visual separation from Environment sections in DOCX |

### New/Modified Files

| File | Change Type | Description |
|------|-------------|-------------|
| `lambda/athena_query/handler.py` | Modified | Added `QUERY_HR_METRICS`, `_build_hr_metrics()`, `_compute_yoy()` |
| `lambda/section_gen/handler.py` | Modified | Added social to TEMPLATE_MAP, RAG_QUERIES, RAG_TOKEN_CAP, `_resolve_template_key()` |
| `lambda/assembly_doc/handler.py` | Modified | Added social to SECTION_ORDER, PAGE_BREAK_BEFORE, `_extract_section_type()`, GRI index |
| `agent/lambda_agent_tools/handler.py` | Modified | Added social to SECTION_TEMPLATES for all 5 frameworks |
| `lambda/validate_input/handler.py` | Modified | Added social to MULTI_FRAMEWORK_SECTIONS |
| `templates/section_social.txt` | **New** | Section template: 5 sub-sections, GRI 2-7/401-1/404-1/405-1/406-1 |

### Expected Test Values (2024 data)

| Metric | Expected Value |
|--------|---------------|
| hiring_rate_pct | 10.38 |
| female_headcount | 10,579 |
| male_headcount | 14,418 |
| yoy_turnover_change_pct | -40.66 |
| yoy_training_change_pct | -23.13 |
| yoy_headcount_change_pct | +2.03 |
| female_pct_change_pp | -3.88 |
| mgmt_female_pct_change_pp | -1.78 |


---

## §NEW: W5b — Silent Polling + Auto-Notification (added 2026-06-09)

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| User must manually ask "check status" | **Frontend auto-polls every 30s, injects completion message** | UX improvement — user doesn't need to babysit |
| No progress indication | **Persistent animated indicator** with elapsed time and check count | User knows something is happening |
| Download link as markdown text | **Styled button** with `target="_blank"` and expiry notice | Prevents URL corruption from markdown formatting |
| No timeout handling | **15-minute timeout** (30 attempts × 30s) with helpful fallback message | Prevents infinite polling |

### Implementation Details

| Feature | How |
|---------|-----|
| Execution ID detection | Regex match on agent response: `/Execution ID:\s*([a-f0-9\-]+)/i` |
| Silent polling | `callAgentSilent()` — same API, not rendered in chat |
| Status detection | String match: `SUCCEEDED`/`complete` → done, `FAILED` → error |
| Download retrieval | Silent agent call: "Download report for execution {id}" → extract URL via regex |
| Indicator | CSS pulse animation, shows elapsed time + check count |
| Session continuity | Same `sessionId` for polling calls — agent retains context |
| Edge cases | Transient errors → retry next interval (no crash), page refresh → polling lost (acceptable) |

### Files Modified

| File | Change |
|------|--------|
| `esg-chat-app/frontend/index.html` | Added polling logic, indicator UI, download button styling, system notification messages |



---

## §NEW: W6 — Analytics Dashboard (added 2026-06-15)

| Spec Says | Actual | Reason |
|-----------|--------|--------|
| No analytics/visualization in spec | **Full analytics dashboard with 14 charts + 6 KPI cards** | Management/investor presentation requirement |
| No dashboard data endpoint | **`GET /dashboard-data` Lambda + API Gateway route** | Frontend needs aggregated metrics API |
| Data always fresh from Athena | **Hybrid S3 cache + on-demand refresh** | Balance between cost and data freshness |
| Single-page chat UI | **Multi-page React app**: Overview, Analytics, Chat, Reports, Reference | Enhanced UX with navigation |
| Basic HTML/CSS | **React + Vite + Tailwind CSS + Recharts** | Modern component-based architecture |
| No deployment automation | **GitHub + Amplify CI/CD** (repo: `radityar21/esg-chat-app`) | Auto-deploy on git push |

### Dashboard Analytics Coverage

**Environmental (E) — 10 charts:**
1. Emissions by Scope (Pie) — Scope 1/2/3 breakdown
2. Scope 1 Sources (Pie) — Natural gas vs diesel
3. Scope 2 Comparison (Bar) — Location vs market-based
4. Year-over-Year Comparison (Bar) — Current vs prior year
5. Emission Intensity (Bar) — Per IDR Bn and per FTE
6. Scope 1 by Facility (Horizontal Bar) — Top 10 emitters
7. PCAF Financed Emissions (Horizontal Bar) — Top sectors
8. PCAF Data Quality (Bar) — Score by sector (color-coded)
9. Portfolio Concentration (Pie) — % by sector
10. PCAF Score Distribution (Pie) — Good/Medium/Poor tiers

**Social (S) — 4 charts:**
11. Gender Diversity (Pie) — Female vs male workforce
12. Female in Management (Ring progress) — % female in mgmt
13. Training Hours/FTE (Bar) — YoY comparison
14. Turnover & Hiring (Bar) — Voluntary turnover vs hiring rate

**6 KPI Cards:**
- Total Emissions (tCO₂e)
- YoY Change (%)
- Intensity per IDR Bn (tCO₂e)
- PCAF Quality Score (1-5)
- Total FTE
- Female %

### Lambda: esg-dashboard-data

| Feature | Implementation |
|---------|----------------|
| **Endpoint** | `GET /dashboard-data` (optional `?refresh=true`) |
| **Default behavior** | Read from S3 cache (`esg-data-aggregated-*/dashboard-cache/latest.json`) |
| **Refresh mode** | Query Athena → update S3 → return fresh data |
| **Queries** | 5 Athena queries: GHG summary, prior year, PCAF sectors, Scope 1 facilities, HR metrics |
| **Cache location** | `s3://esg-data-aggregated-{account}/dashboard-cache/latest.json` |
| **Response structure** | `{reporting_year, last_updated, ghg_summary, prior_year_summary, pcaf_sectors, scope1_facilities, hr_metrics}` |
| **Cost optimization** | S3 read = $0, Athena refresh = ~$0.01 per request (user-triggered only) |
| **IAM permissions** | Athena: `StartQueryExecution`, `GetQueryExecution`, `GetQueryResults` |

### Frontend: React App

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | React 18 + Vite 5 | Fast build, HMR, modern dev experience |
| **Styling** | Tailwind CSS 3 | Utility-first, dark theme, glassmorphism |
| **Charts** | Recharts 2.15 | React-native charts library |
| **Icons** | Lucide React | Modern icon set |
| **Routing** | Client-side (single-page) | No React Router (simple state-based nav) |
| **API layer** | `src/api.js` | Centralized fetch functions |
| **Deployment** | GitHub + Amplify Hosting | Auto-deploy on push to `main` |

### File Structure

```
esg-chat-app-react/
├── src/
│   ├── App.jsx                    # Main app + routing
│   ├── api.js                     # API client (getDashboardData, sendChat, etc.)
│   ├── components/
│   │   └── Sidebar.jsx            # Navigation sidebar
│   └── pages/
│       ├── Overview.jsx           # Landing page (stats + recent reports)
│       ├── Analytics.jsx          # 14 charts + 6 KPIs ⭐ NEW
│       ├── Chat.jsx               # Bedrock Agent chat
│       ├── Reports.jsx            # Report history
│       └── Reference.jsx          # Framework docs
├── public/
│   └── _redirects                 # Amplify SPA routing
├── amplify.yml                    # Build configuration
├── vite.config.js                 # Vite bundler config
├── tailwind.config.js             # Tailwind theme (dark navy)
└── package.json
```

### Design System

| Element | Specification |
|---------|--------------|
| **Theme** | Dark mode (navy #0f172a background) |
| **Glassmorphism** | `backdrop-blur-xl` with `bg-white/[0.02]` |
| **Accent colors** | Blue (#4f8cf7), Teal (#06d6a0), Purple (#7c5cfc) |
| **Typography** | Inter font, 10-12px body, responsive sizing |
| **Charts** | Custom tooltips (dark theme), rounded bars, gradient fills |
| **Navigation** | Sidebar with icons (Lucide), active state indicator |
| **Logo** | "Tokaicom Mitra Indonesia (Tokai Group)" with leaf icon |

### API Gateway Configuration

| Resource | Method | Integration | CORS |
|----------|--------|-------------|------|
| `/dashboard-data` | GET | Lambda `esg-dashboard-data` (proxy) | ✅ Enabled |
| `/dashboard-data` | OPTIONS | MOCK (preflight) | Headers configured |

**CORS Headers:**
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET,OPTIONS
Access-Control-Allow-Headers: Content-Type,X-Amz-Date,Authorization,X-Api-Key
```

### GitHub Repository

| Info | Value |
|------|-------|
| **Repo** | `https://github.com/radityar21/esg-chat-app` |
| **Branch** | `main` |
| **Structure** | Monorepo (contains backend folders + `esg-chat-app-react/`) |
| **.gitignore** | Excludes: `deploy/`, `*.zip`, `node_modules/`, `dist/`, `__pycache__/` |
| **Build trigger** | Auto-deploy on push to `main` |

### Amplify Deployment

| Setting | Value |
|---------|-------|
| **App name** | `esg-reporting-dashboard` |
| **Branch** | `main` |
| **Build command** | `cd esg-chat-app-react && npm ci && npm run build` |
| **Output directory** | `esg-chat-app-react/dist` |
| **Node version** | 18.x (default) |
| **Environment** | Production |
| **URL** | `https://main.{app-id}.amplifyapp.com` |

### Deployment Issues Encountered & Resolved

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| 404 on assets after deploy | Amplify not finding `index.html` in root | Added `amplify.yml` at repo root with correct `baseDirectory` |
| Browser shows white page | Missing `_redirects` file for SPA routing | Added `public/_redirects` with `/* /index.html 200` |
| Zip upload too large | Pushed `deploy/layer/python/` (150MB) to Git | Added `.gitignore` to exclude deployment artifacts |
| Build says "No index.html" | Wrong root directory in Amplify config | Updated `amplify.yml`: `baseDirectory: esg-chat-app-react/dist` |

### Data Flow

```
User clicks "Analytics" 
  → Frontend: useEffect() → getDashboardData(refresh=false)
  → API Gateway: GET /dashboard-data
  → Lambda: esg-dashboard-data
  → Check S3 cache exists?
      Yes → Return cached JSON
      No  → Query Athena (5 queries)
          → Save to S3
          → Return fresh JSON
  → Frontend: Parse JSON → Render 14 charts + 6 KPIs
  
User clicks "Refresh from Athena"
  → Frontend: getDashboardData(refresh=true)
  → Lambda: Force Athena query (skip cache)
  → Update S3 cache
  → Return fresh data
```

### Performance Metrics

| Metric | Value |
|--------|-------|
| **Cold start (cached)** | ~200-500ms (S3 read only) |
| **Cold start (Athena refresh)** | ~8-15s (5 queries in sequence) |
| **Bundle size** | 593 KB JS (gzipped: 174 KB) |
| **First Contentful Paint** | <1s |
| **Charts render time** | ~100-300ms (after data loaded) |

### Testing Commands

```bash
# Test API endpoint (cached)
curl "https://olj4tuggm1.execute-api.us-east-1.amazonaws.com/prod/dashboard-data"

# Test API endpoint (refresh)
curl "https://olj4tuggm1.execute-api.us-east-1.amazonaws.com/prod/dashboard-data?refresh=true"

# Local development
cd esg-chat-app-react
npm install
npm run dev  # Vite dev server on http://localhost:5173

# Production build
npm run build  # Output to dist/

# Deploy
git add .
git commit -m "feat: update analytics"
git push origin main  # Amplify auto-deploys
```

### New Files Added

| File | Purpose |
|------|---------|
| `esg-reporting-poc/lambda/dashboard_data/handler.py` | Lambda function for dashboard data API |
| `esg-chat-app-react/src/pages/Analytics.jsx` | Analytics dashboard page with 14 charts |
| `esg-chat-app-react/src/api.js` | Added `getDashboardData()` function |
| `esg-chat-app-react/public/_redirects` | Amplify SPA routing config |
| `esg-chat-app-react/amplify.yml` | Amplify build configuration |
| `esg-chat-app-react/.gitignore` | Exclude node_modules, dist |
| `.gitignore` (root) | Exclude deploy/, *.zip, backup files |

### IAM Permissions Added

**ESGLambdaRole** (for `esg-dashboard-data`):
```json
{
  "Effect": "Allow",
  "Action": [
    "athena:StartQueryExecution",
    "athena:GetQueryExecution",
    "athena:GetQueryResults"
  ],
  "Resource": "arn:aws:athena:us-east-1:*:workgroup/esg-reporting-workgroup"
}
```

### Cost Analysis

| Component | Cost Structure | Estimated Monthly Cost |
|-----------|---------------|----------------------|
| **Amplify Hosting** | Build minutes + storage + bandwidth | ~$1-5 (low traffic) |
| **S3 cache reads** | GET requests + data transfer | ~$0.01 |
| **Athena queries (cached mode)** | No queries | $0 |
| **Athena queries (refresh mode)** | $5/TB scanned, ~10MB per refresh | ~$0.0001 per refresh |
| **API Gateway** | $3.50/million requests | ~$0.01 (low traffic) |
| **Lambda (dashboard_data)** | $0.20/1M requests + $0.0000166667/GB-sec | ~$0.01 |
| **Total (typical usage)** | 10 users, 5 refreshes/day | **~$2-6/month** |

---

## Updated Summary Statistics (W6)

| Category | Count |
|----------|-------|
| Total spec deviations | 91 |
| Critical (architecture change) | 7 |
| High (missing feature, wrong config) | 38 |
| Medium (naming, precision, minor logic) | 30 |
| Low (cosmetic, documentation) | 16 |
| New components added | 24 |
| Total Lambda functions | 9 |
| Total S3 buckets | 6 |
| Total Athena tables | 12 |
| Total API endpoints | 5 |
| Frontend pages | 5 |
