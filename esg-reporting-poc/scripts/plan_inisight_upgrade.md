
# Kiro Task: Visual Upgrade (Opsi 2) + Insight Layer Implementation
# ⚠️ APPLIES TO ALL FRAMEWORK MODES (Not Just MULTI_FRAMEWORK), you may changes the code with consideration existing workload such as variables and incluided method.

## Context

Current report output is **content-complete** but visually plain — no charts, no styling, no insight annotations. Reader experience is "wall of text with tables." 

We need to add:
1. **Charts** (matplotlib → embedded PNG in DOCX)
2. **Styled elements** (colored headers, KPI boxes, section dividers)
3. **Insight Layer** (KEY INSIGHT box, DIAGNOSTIC paragraph, PRIORITY ACTION callout per section)
4. **Executive Summary 2-Tier Structure** (C-Level Brief → Detailed Performance)

This transforms the report from "data dump" → "executive-ready advisory document."

### ⚠️ CRITICAL: Applies to ALL Framework Modes

This spec is **NOT limited to MULTI_FRAMEWORK/UNIFIED mode**. Insight Layer + Charts + Styling + Executive Summary 2-Tier must apply to ALL report modes:

```
┌─────────────────────────────────────────────────────────────────┐
│ Mode              │ Structure              │ Insight + Charts    │
├───────────────────┼────────────────────────┼─────────────────────┤
│ MULTI_FRAMEWORK   │ Unified (H1/H2)        │ ✅ YES              │
│ GRI_305           │ Legacy (GRI-specific)  │ ✅ YES              │
│ IFRS_S2           │ Legacy (IFRS-specific) │ ✅ YES              │
│ CSRD_ESRS_E1      │ Legacy (ESRS-specific) │ ✅ YES              │
│ OJK_PSPK          │ Legacy (OJK-specific)  │ ✅ YES              │
└─────────────────────────────────────────────────────────────────┘
```

**What is framework-specific (varies by mode):**
- Report structure (unified H1/H2 vs legacy flat)
- Section titles (per framework naming convention)
- Framework cross-reference table (only MULTI_FRAMEWORK)

**What is UNIVERSAL (applies to ALL modes):**
- ✅ Executive Summary 2-Tier (C-Level Brief + Detailed)
- ✅ Insight box (KEY INSIGHT per section)
- ✅ Diagnostic analysis (root causes + risk implications)
- ✅ Priority actions (quantified, peer-referenced)
- ✅ Charts (embedded matplotlib PNGs)
- ✅ KPI highlights (top of each section)
- ✅ Styled tables (colored headers, alternating rows)
- ✅ Cover page (professional with color block)
- ✅ Section ordering (Executive Summary first)
- ✅ Benchmark RAG cap increase (all templates)

---

## Objectives

1. **Executive Summary 2-Tier** — C-Level Brief (1 page, business language) + Detailed Performance (2-3 pages, technical)
2. **Charts embedded in DOCX** — pie, bar, horizontal bar with insight annotations
3. **Executive Summary Charts** — HIGH-LEVEL overview charts, DIFFERENT from detailed section charts
4. **Styled tables** — colored headers, alternating rows
5. **KPI highlight boxes** — large numbers at top of each section
6. **Insight Layer per section** — 3 components: Insight Box, Diagnostic, Priority Actions
7. **Cover page styling** — professional layout with color block
8. **Chart insight annotations** — captions that explain "so what?" not just "what"
9. **ALL modes supported** — single-framework AND multi-framework get same visual treatment
10. **Data validation crosscheck** — ensure chart data matches narrative data matches source data

---

## NEW: Deliverable 0 — Executive Summary 2-Tier Structure

### Purpose

The Executive Summary is the FIRST thing a C-Level/Board Director reads. Current implementation dumps all data equally — no hierarchy of importance. We need:

- **Tier 1 (C-Level Brief):** 1 page MAX. Business language. "So what?" + "What do I need to approve?"
- **Tier 2 (Detailed Performance):** 2-3 pages. Full data, methodology, peer analysis.

### ⚠️ CRITICAL: This applies to ALL framework modes

Whether the report is GRI_305, IFRS_S2, CSRD, OJK, or MULTI_FRAMEWORK — the Executive Summary ALWAYS has 2-tier structure. Only the **emphasis/framing** varies:

```
┌───────────────────────────────────────────────────────────────────┐
│ Framework       │ Tier 1 Emphasis                                  │
├─────────────────┼──────────────────────────────────────────────────┤
│ GRI_305         │ Disclosure completeness, materiality assessment  │
│ IFRS_S2         │ Climate financial risk, TCFD alignment           │
│ CSRD_ESRS_E1    │ Double materiality, transition planning          │
│ OJK_PSPK        │ Kepatuhan regulasi, POJK compliance              │
│ MULTI_FRAMEWORK │ Holistic ESG performance, multi-standard view    │
└───────────────────────────────────────────────────────────────────┘
```

### Tier 1: C-Level Brief — Specification

#### Language Rules (MANDATORY)

The C-Level Brief MUST use **business language** — simple, direct, jargon-free. Written as if explaining to a CEO who has 2 minutes.

```
LANGUAGE DO's:
- "Emisi turun 4%" instead of "Total GHG footprint reduced by 4.07% YoY on location-based methodology"
- "Ini artinya kita perlu invest Rp15M untuk kurangi diesel 40%" instead of "Capital expenditure allocation for diesel displacement via solar+battery hybrid systems"
- "Bank lain sudah lebih maju" instead of "Peer institutions demonstrate superior decarbonization trajectories"
- "Regulator mau kita punya target tahun depan" instead of "OJK POJK 51/2017 compliance timeline mandates target-setting"

LANGUAGE DON'Ts:
- No acronyms without explanation on first use (except common: ESG, GHG, CO2)
- No methodology details (save for Tier 2)
- No footnotes or caveats (save for Tier 2)
- No "it is recommended that..." — use "Kita perlu..." or "Board perlu approve..."
- No passive voice — use active, direct sentences
```

#### Tier 1 Components (JSON Schema)

```json
{
  "section_id": "summary",
  "tier1_brief": {
    "strategic_narrative": "string — max 80 words, business language, must answer: what happened, why it matters, what we need to do",
    
    "scorecard": [
      {
        "pillar": "Environmental | Social | Governance",
        "status": "green | yellow | red",
        "headline": "string — max 5 words, plain language",
        "detail": "string — 1 sentence explaining the status"
      }
    ],
    
    "kpi_boxes": [
      {
        "label": "string — plain language label",
        "value": "string — the big number",
        "unit": "string",
        "context": "string — 1 sentence: what this means in business terms"
      }
    ],
    
    "risks_opportunities": {
      "risks": [
        {
          "risk": "string — 1 sentence, plain language",
          "business_impact": "string — what happens if we don't act",
          "urgency": "high | medium"
        }
      ],
      "opportunities": [
        {
          "opportunity": "string — 1 sentence, plain language",
          "business_benefit": "string — what we gain if we act",
          "readiness": "ready_now | needs_planning | long_term"
        }
      ]
    },
    
    "board_action": {
      "headline": "string — 1 sentence, specific ask to the board",
      "detail": "string — 2-3 sentences explaining why, by when, what's at stake",
      "deadline": "string — specific quarter/year"
    },
    
    "exec_charts": [
      {
        "chart_id": "string",
        "chart_type": "string",
        "title": "string — plain language title",
        "insight_caption": "string — business language 'so what'",
        "data": {}
      }
    ]
  },
  
  "tier2_detailed": {
    "paragraphs": [],
    "tables": [],
    "methodology_notes": [],
    "framework_compliance_status": {},
    "peer_analysis": {}
  }
}
```

#### Tier 1 — Executive Summary Charts (DIFFERENT from Detail Sections)

The Executive Summary has its OWN charts that show the **big picture**. These are NOT the same as detailed section charts. They are simpler, higher-level, and focused on "what does the board need to see?"

```python
EXEC_SUMMARY_CHARTS = {
    # Chart 1: Overall ESG Scorecard Visual
    "exec_esg_scorecard": {
        "chart_type": "bar",  # or custom "gauge" if implementable
        "title": "Kinerja ESG: Posisi Kita vs Target",
        "purpose": "Show at-a-glance where we stand on E, S, G",
        "data_source": "Aggregated from all section KPIs",
        "insight_caption_rule": "Must say where we are GOOD and where we NEED WORK"
    },
    
    # Chart 2: Emission Trend (simple, 2-3 years max)
    "exec_emission_trend": {
        "chart_type": "bar",
        "title": "Total Emisi: Tren 2 Tahun Terakhir",
        "purpose": "Show direction — are we going up or down?",
        "data_source": "total_tco2e from ghg_summary_annual (current + prior year)",
        "insight_caption_rule": "Must state whether trend is good/bad and what's driving it, in 1 sentence"
    },
    
    # Chart 3: Where Emissions Come From (simplified pie — 3 slices max)
    "exec_emission_source": {
        "chart_type": "pie",
        "title": "Dari Mana Emisi Kita Berasal?",
        "purpose": "Show that financed emissions dominate — this is THE story",
        "data_source": "scope1_tco2e, scope2_tco2e, scope3_financed_gross_tco2e",
        "insight_caption_rule": "Must explain in plain language what 'financed emissions' means and why it matters"
    },
    
    # Chart 4: Peer Comparison (if benchmark data available)
    "exec_peer_position": {
        "chart_type": "horizontal_bar",
        "title": "Posisi Kita di Antara Bank Lain",
        "purpose": "Show where we rank among peers — motivate action",
        "data_source": "benchmark KB data (peer emissions intensity or total)",
        "insight_caption_rule": "Must state which peers are ahead, by how much, and 1 thing they did differently",
        "fallback": "If benchmark data unavailable, skip this chart (don't fabricate)"
    }
}
```

**KEY DIFFERENCE: Exec Charts vs Detail Charts**

| Aspect | Exec Summary Charts | Detail Section Charts |
|--------|--------------------|--------------------|
| Audience | Board/C-Level (2 min read) | Technical/Middle Management |
| Complexity | Simple (3 slices max, 2 bars max) | Full detail (8+ categories, multi-series) |
| Labels | Plain language ("Emisi dari Pinjaman") | Technical ("Scope 3 Category 15 PCAF Financed") |
| Captions | "So what for the business" | "So what for the specialist" |
| Data depth | Top-line only | Full breakdown |
| Chart count | 2-4 per summary | 1-3 per section |

#### Tier 1 — Template Instruction for SectionGen

Add this to the **summary section template** (all modes):

```markdown
## EXECUTIVE SUMMARY — TIER 1: C-LEVEL BRIEF (MANDATORY)

You MUST generate a `tier1_brief` object as the FIRST part of the Executive Summary.
This is what the CEO/Board reads. Maximum 1 page when rendered.

### LANGUAGE RULES (CRITICAL — READ CAREFULLY)

Write as if you're briefing a CEO who has 2 minutes between meetings.
- Use SIMPLE, DIRECT language. No jargon. No hedging.
- Write in SHORT sentences. Max 15 words per sentence.
- Use ACTIVE voice: "Kita perlu..." not "It is recommended that..."
- Use CONCRETE numbers: "Turun 4%" not "experienced a decline"
- Explain technical terms in parentheses on first use ONLY in Tier 2, not here.
- Frame everything as BUSINESS IMPACT: revenue risk, regulatory fine, reputation, competitive position.

### WHAT TO INCLUDE

1. `strategic_narrative`: 
   - Open with: What happened? (1 sentence with the big number)
   - Then: Why does this matter for the business? (1 sentence)
   - Then: What's the biggest risk if we don't act? (1 sentence)
   - Close with: What does the board need to do? (1 sentence)
   
2. `scorecard`: Traffic light for E, S, G
   - 🟢 Green = improving AND at/above peer level
   - 🟡 Yellow = stable OR slight concern but manageable
   - 🔴 Red = declining OR major compliance gap OR significantly behind peers
   
3. `kpi_boxes`: 4-5 headline numbers
   - Each must have `context` field explaining what it means in plain language
   - Example: value="99.78%", context="Hampir semua emisi kita datang dari perusahaan yang kita biayai, bukan dari operasional kantor"
   
4. `risks_opportunities`: Top 3 each
   - Risks: state what HAPPENS TO THE BUSINESS (not just "emissions increase")
   - Opportunities: state what WE GAIN (competitive advantage, cost saving, compliance)
   
5. `board_action`: 1 specific ask
   - Must include: WHAT to approve, BY WHEN, WHY it's urgent
   - Example: "Board perlu approve framework tata kelola iklim dan surat komitmen SBTi sebelum Q3 2025, karena OJK akan mewajibkan pengungkapan iklim mulai 2025."

6. `exec_charts`: 2-4 high-level charts (see EXEC_SUMMARY_CHARTS spec)
   - These are DIFFERENT from detailed section charts
   - Simpler, fewer data points, business-language titles and captions
   - MUST include at minimum: emission trend + emission source breakdown

### WHAT NOT TO INCLUDE IN TIER 1
- No methodology details
- No emission factors or calculation notes
- No framework paragraph references (IFRS S2 Para 29, GRI 305-1, etc.)
- No footnotes or source attributions
- No tables with >4 rows
- No technical terms without plain-language alternative
```

#### Tier 2 — Detailed Performance (Existing Content, Enhanced)

Tier 2 is essentially what the Executive Summary currently generates — full data tables, methodology notes, framework compliance, peer analysis. Keep generating this as `tier2_detailed` object.

The ONLY change: add a visual **page break / section separator** between Tier 1 and Tier 2 in AssemblyDoc rendering.

### Assembly Logic (Conceptual — Kiro to implement)

```
When rendering section_id == "summary":
  1. Render Tier 1 (C-Level Brief):
     - Strategic narrative paragraph (large font, business language)
     - ESG Scorecard (traffic light table: 1 row, 3 cols)
     - KPI boxes (4-5 large numbers with context)
     - Exec charts (2-4 high-level charts with business captions)
     - Risks & Opportunities (2-column layout or bullet list)
     - Board Action box (styled callout, prominent)
     - PAGE BREAK
  
  2. Render Tier 2 (Detailed Performance):
     - Full paragraphs with data
     - Detailed tables
     - Methodology notes
     - Framework compliance status
     - Peer analysis with specific references
     - Same insight layer as other sections (insight_box, diagnostic, priority_actions)
```

---

## Architecture Decision: Where to Generate Charts

### Option A: Charts in AssemblyDoc Lambda (Recommended ✅)

```
Lambda #3 (SectionGen) → outputs JSON with chart_config (including exec_charts for summary)
Lambda #5 (AssemblyDoc) → reads chart_config → matplotlib → PNG → embed in DOCX
```

**Why:** 
- SectionGen focuses on content (text + data)
- AssemblyDoc handles ALL visual rendering
- Single Lambda needs matplotlib layer
- Chart data comes from same metrics JSON (no extra queries)

### Lambda Layer Required:
```bash
# Create Lambda layer with matplotlib + dependencies
pip install matplotlib numpy pillow -t python/
zip -r matplotlib-layer.zip python/
aws lambda publish-layer-version \
  --layer-name matplotlib-layer \
  --zip-file fileb://matplotlib-layer.zip \
  --compatible-runtimes python3.11 python3.12
```

**Estimated layer size:** ~50MB (within 250MB Lambda limit)

---

## Deliverable 1: Updated Output JSON Schema (Lambda #3)

Add new fields to section output JSON. **This schema applies to ALL section outputs regardless of framework mode:**

```json
{
  "section_id": "scope1_unified",
  "title": "Direct (Scope 1) GHG Emissions",
  "paragraphs": [...],
  "tables": [...],
  
  // NEW: Insight Layer (MANDATORY for ALL modes)
  "insight_box": {
    "headline": "Scope 1 naik 2.36% sementara peers turun 8-12%",
    "body": "Gap driver: diesel backup (64.7%) — addressable dengan solar+battery investment ~IDR 15B untuk ROI 3 tahun + 40% diesel displacement.",
    "severity": "warning"
  },
  
  "diagnostic": {
    "text": "The 2.36% increase in Scope 1 contrasts sharply with peer performance...",
    "root_causes": [
      "Grid instability in Q2-Q3 forced extended backup generator runtime (+3.66% diesel)",
      "Addition of 3 new branch locations with diesel-powered emergency systems",
      "No renewable energy procurement strategy in place"
    ],
    "risk_implications": [
      "MSCI ESG rating downgrade risk if trend continues",
      "OJK POJK 51/2017 compliance gap widening",
      "Peer gap increasing — reputational risk in investor communications"
    ]
  },
  
  "priority_actions": [
    {
      "action": "Solar+battery at top 5 diesel sites",
      "timeline": "Q3 2025",
      "expected_impact": "-881 tCO₂e/year (-40% diesel at target sites)",
      "estimated_investment": "IDR 15B",
      "peer_reference": "BRI BRILiaN Tower: 19.49% electricity savings",
      "priority": "high"
    }
  ],
  
  // NEW: Chart Configurations (MANDATORY for ALL modes)
  "charts": [...],
  
  // NEW: KPI Highlights (MANDATORY for ALL modes)
  "kpi_highlights": [...],
  
  // Existing fields (keep)
  "advisory_recommendations": [...],
  "framework_cross_reference": {...},
  "key_metrics": [...],
  "footnotes": [...],
  "metadata": {...}
}
```

---

## Deliverable 2: Updated Section Templates (Insight Layer Instructions)

**IMPORTANT:** Add these instructions to ALL section templates — both unified (`section_unified_*.txt`) AND legacy framework-specific (`section_scope1.txt`, `section_scope2.txt`, `section_gri_305_scope1.txt`, etc.).

Every template, regardless of framework mode, must generate insight layer fields:

```markdown
## INSIGHT LAYER (MANDATORY — Generate ALL 3 components)
## ⚠️ This applies to ALL framework modes (GRI, IFRS, ESRS, OJK, UNIFIED)

### 1. INSIGHT BOX
Generate a concise insight box with:
- `headline`: 1 sentence — the "so what?" of this section's data (max 15 words)
- `body`: 2-3 sentences — why this matters + what's the implication (max 50 words)
- `severity`: one of "info" (neutral/positive trend), "warning" (concerning trend), "critical" (immediate action needed), "positive" (outperforming)

Rules:
- MUST reference peer comparison (how does this compare to BRI/DBS/BCA/Mandiri?)
- MUST be actionable (not just "emissions increased" but "emissions increased AND here's why it matters")
- NEVER generic — always specific to the data

GOOD: "Scope 1 naik 2.36% sementara peers turun 8-12% — diesel over-reliance is the gap driver"
BAD: "Emissions have increased year over year" (too generic, no peer context, no "so what")

### 2. DIAGNOSTIC
Generate root cause analysis:
- `text`: 3-4 sentences explaining WHY the numbers are what they are
- `root_causes`: 2-4 bullet points — specific, data-backed causes
- `risk_implications`: 2-3 bullet points — what happens if no action taken

Rules:
- MUST connect data to business risk (regulatory, reputational, financial)
- MUST reference specific regulations (OJK POJK 51, SEOJK 16, EU CSRD timeline)
- MUST quantify where possible ("gap will widen to Xpp by 2026")

### 3. PRIORITY ACTIONS
Generate 2-4 specific actions:
- `action`: What to do (specific, not vague)
- `timeline`: When (quarter + year)
- `expected_impact`: Quantified reduction (tCO₂e or %)
- `estimated_investment`: IDR amount (order of magnitude OK)
- `peer_reference`: Which bank did this + what result they got
- `priority`: "high" | "medium" | "low"

Rules:
- MUST be specific enough to be actionable (not "reduce emissions" but "install solar+battery at top 5 diesel sites")
- MUST include quantified expected impact
- MUST reference a peer bank that already did this successfully
- Order by priority (high first)
- Total projected reduction should be stated

### 4. CHART CONFIGURATIONS
Generate 1-3 chart configs per section:
- Each chart MUST have an `insight_caption` that explains the "so what?" of the visualization
- Caption should tell the reader what to CONCLUDE from the chart, not just describe it

GOOD caption: "99.78% of emissions from financed portfolio — operational reduction alone cannot achieve material impact. Portfolio decarbonization is the ONLY meaningful lever."
BAD caption: "This chart shows the breakdown of emissions by scope." (just describes, no insight)

Chart types to use:
- PIE: for composition/breakdown (scope split, source split, sector split)
- BAR: for comparison/trend (YoY, peer comparison, target vs actual)
- HORIZONTAL BAR: for ranked lists (top sectors, top facilities)
- STACKED BAR: for showing composition over time
```

---

## Deliverable 3: Chart Generation Module (Lambda #5 — AssemblyDoc)

Create new module `chart_generator.py`. Support chart types: pie, bar, horizontal_bar, stacked_bar, line.

**Key requirements:**
- Use matplotlib with 'Agg' backend (non-interactive for Lambda)
- Brand colors: primary="#1B5E20", secondary="#2196F3", accent="#FF9800", danger="#F44336", success="#4CAF50"
- All charts must include `insight_caption` rendered below the chart (italic, smaller font)
- Output: PNG bytes at 150 DPI for embedding in DOCX
- Handle errors gracefully — if chart generation fails, insert placeholder text "[Chart: {title} — generation failed]"

**Logic for each chart type:**
- **pie**: labels + values + colors, autopct percentage, white bold text on slices
- **bar**: categories + series (multi-series support), value labels on bars, annotation support
- **horizontal_bar**: sorted by value (largest at top), color-coded (above mean = danger, below = primary)
- **stacked_bar**: categories + multi-series stacked, legend
- **line**: categories + multi-series with markers

---

## Deliverable 4: DOCX Styling Module (Lambda #5 — AssemblyDoc)

Create new module `docx_styler.py`. Functions needed:

- `add_cover_page(doc, title, institution, year)` — styled cover with dark green color block
- `add_kpi_highlights(doc, kpis)` — table-based KPI boxes (large numbers, trend indicators)
- `add_insight_box(doc, insight)` — colored box with severity-based styling (left border accent)
- `add_priority_actions_box(doc, actions)` — green-accented box with numbered actions
- `style_table_headers(table)` — dark green header with white text
- `style_table_alternating_rows(table)` — light grey alternating
- `add_section_divider(doc, text, level)` — H1 = full color bar, H2 = colored heading text
- `add_esg_scorecard(doc, scorecard)` — traffic light table (green/yellow/red cells)
- `add_board_action_box(doc, board_action)` — prominent styled callout for board ask
- `add_risks_opportunities_layout(doc, risks_opps)` — side-by-side or sequential layout

**Brand colors:**
- primary_dark: #1B5E20 (dark green)
- primary: #2E7D32 (green)
- primary_light: #E8F5E9 (light green bg)
- secondary: #1A237E (dark blue)
- accent/warning: #FF9800 (orange)
- danger: #F44336 (red)
- positive: #4CAF50 (green)
- text_dark: #212121
- text_light: #FFFFFF
- bg_light: #F5F5F5

---

## Deliverable 5: Updated AssemblyDoc Lambda — Integration

Update `handler.py` in Lambda #5 to use new modules.

**IMPORTANT:** The styling + chart + insight rendering logic must run for ALL framework modes. The only difference is `DOCUMENT_STRUCTURE` — which varies by mode.

### Key Integration Logic:

```
For EVERY framework mode:
  1. Render cover page
  2. Render ToC
  3. For section_id == "summary":
     a. If tier1_brief exists: render C-Level Brief (scorecard, KPIs, exec_charts, risks/opps, board_action)
     b. Add PAGE BREAK between Tier 1 and Tier 2
     c. Render Tier 2 as normal section (paragraphs, tables, insight layer)
  4. For all other sections:
     a. Render H2 title
     b. Render KPI highlights
     c. Render insight box
     d. Render paragraphs
     e. Render charts (generate PNG from chart_config, embed)
     f. Render styled tables
     g. Render diagnostic analysis
     h. Render priority actions box
     i. Render framework cross-reference (MULTI_FRAMEWORK only)
     j. Page break
  5. Render appendices
```

### Document Structures (per framework):

**NOTE:** Section ordering updated per framework best practice:

```python
SECTION_ORDER = {
    "GRI_305": ["summary", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social"],
    "IFRS_S2": ["summary", "governance", "scope1", "scope2", "scope3_pcaf", "intensity", "targets", "social"],
    "CSRD_ESRS_E1": ["summary", "governance", "targets", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social"],
    "OJK_PSPK": ["summary", "governance", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social"],
    "MULTI_FRAMEWORK": ["summary", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "governance", "targets", "social"],
}
```

---

## Deliverable 6: Chart Configurations per Section

Define which charts each section should generate. **Same charts for ALL modes.** Use alias pattern: `"scope1_unified": "scope1"` to avoid duplication.

**Default charts per section:**
- `summary`: exec-level overview charts (see EXEC_SUMMARY_CHARTS above) — DIFFERENT from detail
- `scope1`: pie (source breakdown) + bar (YoY trend)
- `scope2`: bar (location vs market-based)
- `scope3_pcaf`: pie (scope split) + horizontal_bar (top sectors) + bar (gross vs weighted)
- `intensity`: bar (revenue intensity vs FTE intensity, YoY)
- `social`: pie (gender composition) + bar (key social metrics YoY)
- `reduction`: bar (targets vs actual)
- `governance`: no chart (text/gap-analysis based)
- `targets`: bar (proposed targets timeline) — optional, only if data available

---

## Deliverable 7: Lambda Layer Setup

Deploy matplotlib + numpy + pillow as Lambda layer:
- Target: manylinux2014_x86_64, python3.11
- Remove test files, sample_data, unused fonts to reduce size
- Estimated size: ~50MB (within 250MB limit)
- Attach to AssemblyDoc Lambda
- Increase Lambda memory to 2048MB
- Increase Lambda timeout to 300s

---

## Deliverable 8: Updated Section Template Example (with Insight Layer)

Full template example for `section_scope1.txt` — includes all insight layer instructions, chart rules, KPI rules, and mandatory constants.

Same insight layer instructions apply to ALL templates regardless of framework mode.

---

## NEW: Deliverable 9 — Data Validation & Crosscheck Logic

### Purpose

Ensure data integrity across the entire report — that numbers in charts match numbers in narrative match numbers from source Athena query. No silent data corruption.

### Validation Points (Logic — Kiro to implement)

#### Validation Point 1: Chart Data ↔ Narrative Data Consistency

```
RULE: Every number displayed in a chart MUST also appear somewhere in the section's 
narrative paragraphs or tables. Charts cannot show data that contradicts the text.

Logic:
- After SectionGen outputs JSON, extract all numeric values from charts[].data
- Compare against numeric values in paragraphs[] and tables[]
- If a chart value doesn't appear in narrative/tables → WARNING (log, don't block)
- If a chart value CONTRADICTS a narrative value (same metric, different number) → ERROR (block)
```

#### Validation Point 2: Section Data ↔ Source Metrics Consistency

```
RULE: All numbers in section output MUST trace back to the Athena metrics payload 
that was input to SectionGen.

Logic:
- Extract all numeric values from section JSON output (paragraphs, tables, charts, KPIs)
- Compare against the metrics_payload that was input to Lambda #3
- Allowed transformations: rounding (±0.01), unit conversion (tCO2e ↔ MtCO2e), percentage calculation
- If a number cannot be traced to source → FLAG as potential model fabrication
```

#### Validation Point 3: Executive Summary ↔ Detail Sections Consistency

```
RULE: KPIs and numbers shown in Executive Summary Tier 1 MUST match the same 
numbers in their respective detail sections.

Logic:
- Extract KPI values from tier1_brief.kpi_boxes
- For each KPI, find the corresponding detail section (e.g., "Total Scope 1" → scope1 section)
- Verify the value matches what's in the detail section
- If mismatch → ERROR (this means Exec Summary tells a different story than the detail)
```

#### Validation Point 4: Chart Insight Captions ↔ Actual Data Direction

```
RULE: Chart insight captions must not contradict the data they describe.

Logic:
- If caption says "increasing" → verify actual data shows increase
- If caption says "X% of total" → verify percentage calculation is correct
- If caption references "peers" → verify peer data came from benchmark RAG (not fabricated)
- Simple directional check — not full NLU, just keyword matching against data trend
```

#### Validation Point 5: Exec Summary Scorecard ↔ Section Performance

```
RULE: Traffic light scorecard must reflect actual section performance.

Logic:
- If Environmental scorecard = "green" → verify YoY change is negative (emissions decreasing)
- If Social scorecard = "red" → verify at least one social metric is declining
- If Governance scorecard = "red" → verify governance section shows gaps/missing frameworks
- Prevent: model saying "everything is fine" when data shows problems (or vice versa)
```

### Where to Run Validation

```
Lambda #4 (Validation) — add these checks to existing validation rules:
- VAL-CHART-01: Chart data matches narrative data
- VAL-CHART-02: Chart insight caption direction matches data direction
- VAL-EXEC-01: Exec summary KPIs match detail section KPIs
- VAL-EXEC-02: Scorecard traffic light consistent with section data
- VAL-SRC-01: All numbers traceable to source metrics payload

Severity levels:
- ERROR (block assembly): contradicting numbers, scorecard misrepresenting data
- WARNING (log, proceed): chart value not in narrative, caption slightly off
```

### Crosscheck Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                   │
│  Athena Metrics Payload (SOURCE OF TRUTH)                        │
│       │                                                           │
│       ▼                                                           │
│  Lambda #3 (SectionGen) → Section JSON output                    │
│       │                                                           │
│       ▼                                                           │
│  Lambda #4 (Validation) ← CROSSCHECK HAPPENS HERE                │
│       │    Check: JSON numbers ↔ Source metrics                   │
│       │    Check: Chart data ↔ Narrative data                     │
│       │    Check: Exec KPIs ↔ Detail section KPIs                 │
│       │    Check: Scorecard ↔ Actual performance                  │
│       │                                                           │
│       ▼                                                           │
│  Lambda #5 (AssemblyDoc) → Final DOCX                            │
│       │    Charts rendered from VALIDATED JSON only                │
│       │                                                           │
│       ▼                                                           │
│  Output: Report with guaranteed data consistency                  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Notes for Kiro

### Priority Order
1. **Deliverable 0** (Exec Summary 2-Tier) — highest impact for demo
2. **Deliverable 9** (Validation crosscheck) — ensures correctness
3. **Deliverable 3-4** (Charts + Styling) — visual impact
4. **Deliverable 2** (Insight Layer templates) — content depth
5. **Deliverable 5** (Assembly integration) — ties everything together
6. **Deliverable 7** (Lambda layer) — infrastructure prerequisite for charts

### Dependencies
```
Deliverable 7 (Lambda layer) MUST be deployed BEFORE testing Deliverable 3 (charts)
Deliverable 0 (Exec Summary) requires Deliverable 4 (styling) for scorecard/board_action rendering
Deliverable 9 (Validation) can be developed in parallel — only needs integration at end
```

### Constraints
- Lambda #5 memory: increase to 2048MB (matplotlib needs ~500MB)
- Lambda #5 timeout: increase to 300s (chart generation adds time)
- Chart generation: handle failures gracefully (fallback to placeholder text)
- Tier 1 language: MUST be validated — if model outputs jargon-heavy text, log warning
- All exec_charts data MUST come from the same metrics payload (no separate query)

### Testing Checklist
After implementation, test ALL 5 framework modes:
- [ ] Executive Summary has 2-tier structure (Tier 1 + page break + Tier 2)
- [ ] Tier 1 language is business-friendly (no framework references, no jargon)
- [ ] Exec charts are DIFFERENT from detail section charts (simpler, higher-level)
- [ ] Each detail section has: insight_box, diagnostic, priority_actions, charts
- [ ] Charts render correctly as embedded PNGs in DOCX
- [ ] Validation catches number mismatches (test with intentionally wrong data)
- [ ] Scorecard accurately reflects section performance
- [ ] Board action box is prominent and specific
- [ ] No chart data contradicts narrative data
- [ ] All numbers traceable to source Athena metrics
