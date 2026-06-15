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

