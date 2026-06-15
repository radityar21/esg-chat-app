# ESG Kiro Requirements Spec — Amendment Log

> **Document:** `ESG_kiro_Requirement_Spec.md`
> **Purpose:** Track all implementation deviations from original spec. Apply amendments after system is fully operational.
> **Status:** PENDING — will be applied to spec document post-POC completion.

---

## Version History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| AMD-001 | 2026-06-04 | POC Team | Initial amendment log — 36 items from W1-W2 implementation |

---

## Amendment AMD-001 (2026-06-04)

**Scope:** D1–D14 implementation (Data Layer + Lambda deployment)
**Trigger:** Lessons learned during hands-on build
**Items:** 36 changes across 7 spec sections

---

### §5 Knowledge Base Configuration (D8)

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 1 | §5.1 Chunking Strategy | Chunking type | Fixed size 300 tokens | **Semantic chunking** |
| 2 | §5.1 Chunking Config | Max token size | 300 | **700** |
| 3 | §5.1 Chunking Config | Add: Buffer size | N/A | **1 sentence** |
| 4 | §5.1 Chunking Config | Add: Breakpoint threshold | N/A | **90%** |
| 5 | §5.2 Parsing Strategy | Parser | Default | **Foundation Model (Anthropic Claude Haiku)** |
| 6 | §5.3 Embedding | Model | (if different) | **Amazon Titan Embeddings V2, 1024 dimensions, floating** |
| 7 | §5.4 Vector Store | Type | OpenSearch Serverless | **OpenSearch Serverless (Quick Create)** |
| 8 | §5.4 Vector Store | Active replicas | N/A | **Disabled** |
| 9 | §5.4 Vector Store | Standby replicas | N/A | **Disabled** |
| 10 | §5.5 RAG Threshold | Min relevance score | 0.65 (or whatever spec says) | **0.40** |
| 11 | §5.5 RAG Config | Token cap | (if specified) | **700 chars** |
| 12 | §5.6 KB Filter Logic | Filter for cross-framework sections | Single framework filter | **`orAll` filter (e.g., GRI_305 + PCAF for scope3_pcaf)** |

---

### §3 ETL Pipeline (Glue Jobs)

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 13 | §3.2 S3 Path Structure | Curated zone partitioning | Not explicitly detailed | **Flat partition: `reporting_year=YYYY/reporting_month=MM/` (no category subfolders)** |
| 14 | §3.2 S3 Path Structure | Aggregated zone | Not explicitly detailed | **Flat partition: `reporting_year=YYYY/` (no category subfolders)** |
| 15 | §3.3 Data Governance | Schema governance gate | Not in spec | **Add: `validate_schema()` with expected columns + dtype check** |
| 16 | §3.3 Data Governance | Source data fingerprint | Not in spec | **Add: SHA-256 hash of input for traceability** |
| 17 | §3.3 Data Governance | Row count assertion | Not in spec | **Add: Pre/post row count validation** |
| 18 | §3.3 Data Governance | Cross-field validation | Not in spec | **Add: Scope1 = NatGas + Diesel (±0.0001)** |
| 19 | §3.3 Data Governance | Output schema enforcement | Not in spec | **Add: `.select(EXPECTED_COLUMNS)` before write** |
| 20 | §3.3 Data Governance | Partition overwrite | Not in spec | **Add: `mode("overwrite")` with `partitionOverwriteMode=dynamic`** |
| 21 | §3.4 Precision Handling | Rounding strategy | Not explicit | **Add: Round AFTER all arithmetic, use `F.round(expr, N)` on final values only** |

---

### §12.3 ETL Implementation Standards (NEW SECTION)

| # | What to Add |
|---|-------------|
| 22 | Full §12.3 text (Schema Governance Gate, Source Data Fingerprint, Row Count Assertion, Cross-field Validation, Output Schema Enforcement, Partition Overwrite Safety, Decimal Precision Handling) |

---

### §6 Lambda Functions

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 23 | §6.3 SectionGenFn | Model ID | `anthropic.claude-3-5-sonnet...` | **`us.anthropic.claude-sonnet-4-5-20250929-v1:0` (inference profile)** |
| 24 | §6.3 SectionGenFn | KB filter logic | Single framework | **`orAll` for cross-framework sections (scope3_pcaf → GRI_305 + PCAF)** |
| 25 | §6.3 SectionGenFn | RAG graceful degradation | Not specified | **try/except with logger.warning, continues without RAG on failure** |
| 26 | §6.4 ValidationFn | Numeric comparison | Direct match | **Absolute value matching: `abs(text_value) vs abs(source_value)` for sign convention handling** |
| 27 | §6.4 ValidationFn | Outcome values | PASS/WARN/RETRY/FAIL | **Add: `FAIL_NO_RETRY` for VAL-NUM-06 → Step Functions routes to HumanReviewState** |
| 28 | §6.5 AssemblyDocFn | Layer dependency | python-docx | **Lambda Layer: python-docx + lxml (built with `--platform manylinux2014_x86_64`)** |

---

### §4 Athena / Infrastructure

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 29 | §4.1 Athena Workgroup | Region | ap-southeast-3 (Jakarta) | **us-east-1 (N. Virginia)** — for Amazon Quick integration |
| 30 | §4.1 Athena Workgroup | Engine | N/A | **Athena SQL (Engine v3)** |
| 31 | §4.1 Athena Workgroup | Authentication | N/A | **IAM only** |
| 32 | §4.1 Athena Workgroup | Query result location | N/A | **s3://esg-athena-results-061039769766/query-results/** |

---

### §9 Prompt Engineering

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 33 | §9.1 Base Prompt | Add: Length attribute | Not present | **Add `length` field per section type (medium/long/short)** |
| 34 | §9.1 Base Prompt | Model compatibility | Claude 3.5 Sonnet | **Compatible with all Claude models (Haiku, Sonnet, Opus via inference profiles)** |

---

### §11 IAM & Security

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 35 | §11.1 SectionGenFn Role | Bedrock permissions | `foundation-model/*` | **Add: `inference-profile/*` + wildcard region `*` for cross-region inference** |
| 36 | §11.2 KB Service Role | Bedrock permissions | Titan Embeddings only | **Add: Claude Haiku invoke permission (for Foundation Model parser)** |

---

## Summary

| Priority | Category | Items | Status |
|----------|----------|-------|--------|
| **HIGH** | §5 KB Config (chunking, threshold, filter) | 12 | ⏳ Pending |
| **HIGH** | §12.3 ETL Standards (new section) | 1 | ⏳ Pending |
| **MEDIUM** | §6 Lambda updates (model ID, abs matching, FAIL_NO_RETRY) | 6 | ⏳ Pending |
| **MEDIUM** | §3 ETL path structure + precision handling | 9 | ⏳ Pending |
| **LOW** | §4 Athena workgroup details | 4 | ⏳ Pending |
| **LOW** | §9 Prompt engineering | 2 | ⏳ Pending |
| **LOW** | §11 IAM permission details | 2 | ⏳ Pending |

**Total items to update:** 36
**New sections to add:** 1 (§12.3)
**Sections significantly rewritten:** §5 (KB Configuration)

---

## How to Apply

1. Wait until full system is operational (D15+ Step Functions working end-to-end)
2. Update `ESG_kiro_Requirement_Spec.md` section by section using this checklist
3. Increment spec version header to `v1.1.0`
4. Mark each item status as ✅ Applied when done
5. Create new AMD-002 entry for any subsequent changes

---

## Future Amendments (Template)

### Amendment AMD-NNN (YYYY-MM-DD)

**Scope:** [Description]
**Trigger:** [What caused the change]
**Items:**

| # | Section | What to Update | Old | New |
|---|---------|---------------|-----|-----|
| ... | ... | ... | ... | ... |


---

## Amendment AMD-002 (2026-06-05)

**Scope:** D15 Step Functions + Human Review + Assembly + Validation refinements
**Trigger:** End-to-end testing revealed runtime issues, Organization SCP limitations, and UX gaps
**Items:** 18 changes

---

### §9 Step Functions Orchestration

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 37 | §9.1 HumanReviewGate | Review mechanism | `waitForTaskToken` + manual CLI | **Auto-approve mode** (SNS notification + proceed). Manual review available as separate ASL file. |
| 38 | §9.1 HumanReviewGate | Review UI | Not specified | **Lambda Function URL attempted, blocked by Organization SCP**. Fallback: CloudShell `send-task-success`. |
| 39 | §9.1 State Machine | ExcludeSection state | Referenced by ReviewChoice | **Removed in auto-approve ASL** (unreachable). Kept in manual review ASL. |
| 40 | §9.1 FilterSections | JSONPath filter | `$.generated_sections[?(@.status=='INCLUDED')]` | **Separate Lambda** (`esg-filter-sections`) — Step Functions does not support JSONPath filter expressions. |
| 41 | §9.1 Glue Parameters | Job arguments | Not passed | **`--REPORTING_YEAR` passed via `States.Format`** |
| 42 | §9.1 SNS Message | Format | JSON object | **`States.JsonToString()` — SNS Message must be string** |
| 43 | §9.1 ASL deployment | Method | `file://` from CLI | **Upload to S3 → download in CloudShell → `file:///tmp/`** (Windows encoding incompatible with `file://`) |

---

### §6 Lambda Functions (Runtime Fixes)

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 44 | §6.3 SectionGenFn | Template key resolution | Direct `TEMPLATE_MAP[section_id]` | **`_resolve_template_key()` function** — handles both short keys (`scope1`) and full IDs (`GRI_305_SCOPE1_2024`) |
| 45 | §6.3 SectionGenFn | Model ID | `anthropic.claude-3-5-sonnet-20241022-v2:0` | **`us.anthropic.claude-sonnet-4-5-20250929-v1:0`** (inference profile, old model deprecated) |
| 46 | §6.3 SectionGenFn | KB relevance threshold | 0.65 | **0.40** (semantic chunking produces lower scores) |
| 47 | §6.5 AssemblyDocFn | Paragraph alignment | Left-aligned | **Justified** (`WD_ALIGN_PARAGRAPH.JUSTIFY`) |
| 48 | §6.5 AssemblyDocFn | Layer build | Windows pip | **CloudShell only** (`--platform manylinux2014_x86_64`) |
| 49 | §6.2 AthenaQueryFn | Scope 1 breakdown | Total only | **Added `scope1_natgas_tco2e` + `scope1_diesel_tco2e`** |
| 50 | §6.2 AthenaQueryFn | Facility breakdown | Not in spec | **Added `QUERY_SCOPE1_FACILITIES` (top 10 by emissions)** |

---

### §3 ETL Pipeline

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 51 | §3.5 Aggregation | ghg_summary_annual columns | scope1_tco2e only | **Added: `scope1_natgas_tco2e`, `scope1_diesel_tco2e`** |
| 52 | §3.5 Aggregation | Facility breakdown | Not in spec | **New output: `scope1_by_facility` (top 10 per year)** |
| 53 | §4.3 DDL | ghg_summary_annual | 12 columns | **14 columns** (natgas + diesel added) |
| 54 | §4.3 DDL | New table | N/A | **`esg_aggregated.scope1_by_facility`** |

---

### Summary (AMD-002)

| Priority | Category | Items |
|----------|----------|-------|
| **HIGH** | §9 Step Functions (auto-approve, filter Lambda, deploy method) | 7 |
| **HIGH** | §6 Lambda (model ID, template resolution, assembly styling) | 7 |
| **MEDIUM** | §3 ETL (natgas/diesel breakdown, facility table) | 4 |

**Total new items:** 18 (AMD-002)
**Cumulative total:** 54 (AMD-001: 36 + AMD-002: 18)


---

## Amendment AMD-003 (2026-06-05)

**Scope:** W4 — Bedrock Agent + Chat UI + Amplify deployment
**Trigger:** AWS Summit demo requirement — conversational interface for report generation
**Items:** 10 changes

---

### §NEW: Bedrock Agent Layer

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 55 | §1.2 System Boundary | AgentCore usage | "Amazon Bedrock AgentCore as orchestration runtime" | **Bedrock Agent as conversational frontend** (Step Functions remains orchestrator) |
| 56 | §NEW Agent Config | Agent model | N/A | **Claude Sonnet 4.5 (inference profile)** |
| 57 | §NEW Agent Tools | Action Group | N/A | **4 tools: generate_report, check_status, download_report, list_available_data** |
| 58 | §NEW Agent Instructions | Conversation flow | N/A | **Sequential questions (year → framework → revenue), guardrails for invalid input** |
| 59 | §NEW Chat Proxy | API Gateway + Lambda | N/A | **REST API → esg-chat-proxy Lambda → bedrock:InvokeAgent** |
| 60 | §NEW Frontend | UI | N/A | **Amplify hosted static HTML chat (single-page, no framework)** |

---

### §9 Step Functions (Output Fix)

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 61 | §9.1 Success state | Terminal state | `Succeed` type | **`Pass` type that outputs `$.assembly_result`** (needed for agent download_report tool) |
| 62 | §9.1 NotifyCompletion | ResultPath | Not set (overwrites state) | **`ResultPath: "$.sns_result"`** (preserves assembly_result in state) |

---

### §11 IAM

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 63 | §11 Lambda Role | New permissions | N/A | **`bedrock:InvokeAgent`, `states:StartExecution`, `states:DescribeExecution`** |
| 64 | §11 Agent Role | New role | N/A | **`ESGBedrockAgentRole` — bedrock:InvokeModel + lambda:InvokeFunction** |

---

### Summary (AMD-003)

| Priority | Category | Items |
|----------|----------|-------|
| **HIGH** | Bedrock Agent + tools | 5 |
| **HIGH** | Chat App (frontend + proxy) | 2 |
| **MEDIUM** | Step Functions output fix | 2 |
| **LOW** | IAM updates | 2 |

**Cumulative total:** 64 (AMD-001: 36 + AMD-002: 18 + AMD-003: 10)


---

## Amendment AMD-004 (2026-06-09)

**Scope:** Social (S) Pillar — Add workforce & human capital disclosures to ESG report pipeline
**Trigger:** ESG report covers only Environment (E). Social (S) section needed using existing `esg_raw.hr_metrics` data.
**Items:** 11 changes

---

### §6 Lambda Functions (Social Section Support)

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 65 | §6.2 AthenaQueryFn | HR metrics query | Not present | **Added `QUERY_HR_METRICS`** — queries `esg_raw.hr_metrics` for current + prior year, pre-computes `hiring_rate_pct`, `female_headcount`, `male_headcount` in SQL |
| 66 | §6.2 AthenaQueryFn | YoY computation | Not present | **Added `_build_hr_metrics()` + `_compute_yoy()`** — pre-computes `yoy_headcount_change_pct`, `yoy_turnover_change_pct`, `yoy_training_change_pct`, `female_pct_change_pp`, `mgmt_female_pct_change_pp` |
| 67 | §6.2 AthenaQueryFn | Response shape | 4 keys (ghg_summary, pcaf_sectors, prior_year, facilities) | **5 keys** — added `hr_metrics` dict with nested `prior_year` and `yoy_changes` |
| 68 | §6.3 SectionGenFn | TEMPLATE_MAP | 7 entries (scope1→summary) | **8 entries** — added `"social": "templates/social_template.txt"` |
| 69 | §6.3 SectionGenFn | RAG_QUERIES | 7 entries | **8 entries** — added social RAG query: `"GRI 2-7 401-1 404-1 405-1 406-1 workforce employment training diversity non-discrimination disclosure requirements"` |
| 70 | §6.3 SectionGenFn | `_resolve_template_key()` | No social pattern | **Added `"social" in sid` pattern match** (before `"summary"`) |
| 71 | §6.5 AssemblyDocFn | SECTION_ORDER | No social entry | **Added `"social"` to all 5 framework orderings** (after intensity, before methodology/summary) |
| 72 | §6.5 AssemblyDocFn | PAGE_BREAK_BEFORE | 5 section types | **6 section types** — added `"social"` |
| 73 | §6.5 AssemblyDocFn | GRI Content Index | 5 rows (305-1 to 305-5) | **10 rows** — added GRI 2-7, 401-1, 404-1, 405-1, 406-1 |

---

### §NEW: Section Template (Social)

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 74 | §6.6 Templates | Social template | Not present | **`templates/social_template.txt`** — 5 sub-sections: Workforce Overview (GRI 2-7), Employment (GRI 401-1), Training (GRI 404-1), Diversity (GRI 405-1), Non-Discrimination (GRI 406-1) |

---

### §9 Step Functions / Agent

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 75 | §9.2 Agent Tools | SECTION_TEMPLATES per framework | No social entry | **Added `{"template_id": "social", "framework": "GRI_305"}` to GRI_305, IFRS_S2, CSRD_ESRS_E1, MULTI_FRAMEWORK; `"framework": "OJK_PSPK"` for OJK_PSPK** |

---

### §9.1 ValidateInput (MULTI_FRAMEWORK auto-population)

| # | Section | What to Update | Old (Spec) | New (Actual) |
|---|---------|---------------|-------------|--------------|
| 76 | §9.1 ValidateInputFn | MULTI_FRAMEWORK_SECTIONS | 14 entries (no social) | **15 entries** — added `{"template_id": "social", "framework": "GRI_305"}` after intensity |

---

### Design Decisions (AMD-004)

1. **No new Glue ETL job** — HR data is used as-is from `esg_raw.hr_metrics` (no aggregation needed)
2. **Cross-database query** — AthenaQuery Lambda queries `esg_raw` database (not `esg_aggregated`) for HR metrics
3. **Social uses GRI framework** for all except OJK_PSPK — GRI 400-series is the primary standard for social disclosures regardless of environment framework
4. **All YoY pre-computed** — model receives pre-calculated values; validation rule VAL-NUM-01 covers Social metrics
5. **No Step Functions ASL change** — social section enters pipeline via `section_templates` array (Map state iteration)

---

### Summary (AMD-004)

| Priority | Category | Items |
|----------|----------|-------|
| **HIGH** | §6 Lambda functions (AthenaQuery, SectionGen, AssemblyDoc) | 9 |
| **HIGH** | Section template (social) | 1 |
| **MEDIUM** | Agent tools + ValidateInput | 2 |

**Total new items:** 12 (AMD-004)
**Cumulative total:** 76 (AMD-001: 36 + AMD-002: 18 + AMD-003: 10 + AMD-004: 12)
