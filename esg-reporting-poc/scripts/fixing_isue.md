
# Kiro Task: Restructure ESG Report — Unified 2-Level Hierarchy (Opsi A)

## Context

Current report output is FLAT (all sections at same heading level, framework-specific sections
repeat the same data 4x with different framing). This creates a confusing reader experience.

We want to restructure to:
1. **2-level hierarchy** — H1 per pillar/theme, H2 per topic
2. **Unified narrative** — one section per topic that covers ALL frameworks simultaneously
3. **Framework cross-reference table** at end of each section (maps to GRI, IFRS, ESRS, OJK)
4. **Fix OJK title handling** — Indonesian titles for OJK-specific sections

## Target Report Structure

```
Cover Page
Table of Contents

═══ EXECUTIVE SUMMARY (H1) ═══
  Overview of total emissions, key trends, strategic highlights

═══ 1. ENVIRONMENTAL PERFORMANCE (H1) ═══
  ├── 1.1 Direct GHG Emissions — Scope 1 (H2)
  │     Unified narrative covering GRI 305-1, IFRS S2 Para 29(a)(i),
  │     ESRS E1-6 DR E1-6.44, OJK PSPK Emisi Lingkup 1
  │     + Framework Cross-Reference Table at end
  │
  ├── 1.2 Energy Indirect GHG Emissions — Scope 2 (H2)
  │     Unified narrative covering GRI 305-2, IFRS S2 Para 29(a)(ii),
  │     ESRS E1-6 DR E1-6.46, OJK PSPK Emisi Lingkup 2
  │     + Framework Cross-Reference Table
  │
  ├── 1.3 Financed Emissions — Scope 3 Category 15 (H2)
  │     Unified narrative covering GRI 305-3, IFRS S2 Para 29(a)(iv),
  │     ESRS E1-6 DR E1-6.51, OJK PSPK Emisi Lingkup 3
  │     + PCAF methodology detail
  │     + Sector breakdown table
  │     + Framework Cross-Reference Table
  │
  ├── 1.4 GHG Emissions Intensity (H2)
  │     Unified narrative covering GRI 305-4, IFRS S2 Para 29(b),
  │     ESRS E1-6 DR E1-6.53, OJK PSPK Intensitas Emisi
  │     + Framework Cross-Reference Table
  │
  └── 1.5 Emission Reduction Initiatives & Targets (H2)
        Unified narrative covering GRI 305-5, IFRS S2 Para 33-36,
        ESRS E1-4 DR E1-4, OJK PSPK Target Pengurangan
        + Gap analysis (where data not available)
        + Framework Cross-Reference Table

═══ 2. SOCIAL PERFORMANCE (H1) ═══
  └── 2.1 Workforce & Human Capital (H2)
        Covers GRI 401-1, 404-1, 405-1, 406-1
        + Diversity, training, turnover, discrimination
        + Framework Cross-Reference Table

═══ 3. GOVERNANCE & STRATEGY (H1) ═══
  ├── 3.1 Climate Governance & ESG Oversight (H2)
  │     Covers IFRS S2 Para 5-7, ESRS E1 GOV,
  │     OJK Tata Kelola Keberlanjutan
  │     + Gap analysis (where data not captured)
  │     + Framework Cross-Reference Table
  │
  └── 3.2 Climate Targets & Transition Plan (H2)
        Covers IFRS S2 Para 33-37, ESRS E1-4,
        OJK Target Iklim
        + Gap analysis
        + Framework Cross-Reference Table

═══ 4. ADVISORY RECOMMENDATIONS (H1) ═══
  └── 4.1 Strategic Recommendations & Peer Benchmarks (H2)
        Consolidated recommendations from all sections
        + Priority matrix (High/Medium/Low)
        + Peer bank references (BRI, DBS, BCA, Mandiri, OCBC)
        + Suggested targets with timeline

═══ APPENDICES (H1) ═══
  ├── A. Methodology Notes
  ├── B. Data Quality Summary
  ├── C. GRI Content Index
  ├── D. IFRS S2 Disclosure Mapping
  ├── E. ESRS E1 Disclosure Mapping
  └── F. OJK PSPK Compliance Mapping
```

## Key Design Decisions

### 1. Unified Narrative (NOT separate per framework)

BEFORE (current — repetitive):
```
Section: GRI 305-1 Scope 1 → "Scope 1 = 3,402.997 tCO₂e..."
Section: IFRS S2 Scope 1  → "Scope 1 = 3,402.997 tCO₂e..." (same data, different framing)
Section: ESRS E1-6 Scope 1 → "Scope 1 = 3,402.997 tCO₂e..." (same data again)
Section: OJK Scope 1      → "Lingkup 1 = 3.402,997 tCO₂e..." (same data, Indonesian)
```

AFTER (unified):
```
Section 1.1: Direct GHG Emissions — Scope 1
  Paragraph 1: Core data narrative (numbers, trends, methodology)
  Paragraph 2: Framework-specific requirements addressed
  Table: Framework Cross-Reference
    | Framework | Disclosure Ref | Requirement | Status |
    | GRI 305   | 305-1a-g      | Gross Scope 1 | ✅ Disclosed |
    | IFRS S2   | Para 29(a)(i) | Absolute gross | ✅ Disclosed |
    | ESRS E1   | DR E1-6.44    | Gross Scope 1 | ✅ Disclosed |
    | OJK PSPK  | Emisi Lingkup 1| Emisi langsung | ✅ Disclosed |
```

### 2. Framework Cross-Reference Table (End of Each Section)

Every section ends with a table showing:
```markdown
#### Framework Compliance Cross-Reference

| Framework | Disclosure Reference | Requirement Description | Compliance Status |
|-----------|---------------------|------------------------|-------------------|
| GRI 305-1 | 305-1a | Gross direct Scope 1 in tCO₂e | ✅ Fully Disclosed |
| GRI 305-1 | 305-1b | Gases included | ✅ Fully Disclosed |
| GRI 305-1 | 305-1e | Emission factors & GWP source | ✅ Fully Disclosed |
| IFRS S2 | Para 29(a)(i) | Absolute gross Scope 1 | ✅ Fully Disclosed |
| ESRS E1 | DR E1-6.44 | Gross Scope 1 GHG emissions | ✅ Fully Disclosed |
| OJK PSPK | Lampiran Emisi | Emisi GRK langsung (Lingkup 1) | ✅ Fully Disclosed |
```

### 3. Section Title Convention

| Section | English Title (H2) | Framework Subtitle (if needed) |
|---------|-------------------|-------------------------------|
| 1.1 | Direct GHG Emissions — Scope 1 | — |
| 1.2 | Energy Indirect GHG Emissions — Scope 2 | — |
| 1.3 | Financed Emissions — Scope 3 Category 15 | — |
| 1.4 | GHG Emissions Intensity | — |
| 1.5 | Emission Reduction Initiatives & Targets | — |
| 2.1 | Workforce & Human Capital | — |
| 3.1 | Climate Governance & ESG Oversight | — |
| 3.2 | Climate Targets & Transition Plan | — |
| 4.1 | Strategic Recommendations & Peer Benchmarks | — |

**NO MORE framework-specific titles.** Titles are topic-based, framework mapping is in the cross-reference table.

## Implementation Changes Required

### Change 1: Update `MULTI_FRAMEWORK_SECTIONS` Config

BEFORE (16 entries, many duplicates per framework):
```python
MULTI_FRAMEWORK_SECTIONS = [
    {"template_id": "scope1", "framework": "GRI_305"},
    {"template_id": "scope1", "framework": "IFRS_S2"},
    {"template_id": "scope1", "framework": "CSRD_ESRS_E1"},
    {"template_id": "scope1", "framework": "OJK_PSPK"},
    ...
]
```

AFTER (9 entries, unified — each section generated ONCE):
```python
MULTI_FRAMEWORK_SECTIONS = [
    {"template_id": "summary", "framework": "MULTI_FRAMEWORK", "heading1": "Executive Summary"},
    {"template_id": "scope1", "framework": "MULTI_FRAMEWORK", "heading1": "Environmental Performance", "heading2": "1.1 Direct GHG Emissions — Scope 1"},
    {"template_id": "scope2", "framework": "MULTI_FRAMEWORK", "heading2": "1.2 Energy Indirect GHG Emissions — Scope 2"},
    {"template_id": "scope3_pcaf", "framework": "MULTI_FRAMEWORK", "heading2": "1.3 Financed Emissions — Scope 3 Category 15"},
    {"template_id": "intensity", "framework": "MULTI_FRAMEWORK", "heading2": "1.4 GHG Emissions Intensity"},
    {"template_id": "reduction", "framework": "MULTI_FRAMEWORK", "heading2": "1.5 Emission Reduction Initiatives & Targets"},
    {"template_id": "social", "framework": "MULTI_FRAMEWORK", "heading1": "Social Performance", "heading2": "2.1 Workforce & Human Capital"},
    {"template_id": "governance", "framework": "MULTI_FRAMEWORK", "heading1": "Governance & Strategy", "heading2": "3.1 Climate Governance & ESG Oversight"},
    {"template_id": "targets", "framework": "MULTI_FRAMEWORK", "heading2": "3.2 Climate Targets & Transition Plan"},
]
```

**Benefits:**
- 16 sections → 9 sections (faster execution, lower cost)
- No duplicate content
- Each section generated once with ALL framework requirements embedded

### Change 2: Update Section Templates (Unified Multi-Framework)

Each template must now instruct the model to:
1. Write ONE unified narrative (not framework-specific)
2. Address ALL framework requirements within that narrative
3. End with Framework Cross-Reference Table
4. Include Advisory Recommendations block

Example template structure for `section_scope1.txt`:

```
You are generating a UNIFIED multi-framework section for an ESG Sustainability Report.

### SECTION TITLE
1.1 Direct GHG Emissions — Scope 1

### FRAMEWORKS ADDRESSED IN THIS SECTION
This single section must satisfy ALL of the following framework requirements simultaneously:
- GRI 305-1 (Disclosures a through g)
- IFRS S2 Paragraph 29(a)(i) — absolute gross Scope 1
- ESRS E1-6 DR E1-6.44 — gross Scope 1 GHG emissions
- OJK PSPK — Emisi Gas Rumah Kaca Langsung (Lingkup 1)

### NARRATIVE APPROACH
Write a SINGLE coherent narrative that naturally addresses all framework requirements.
Do NOT create separate sub-sections per framework.
Do NOT repeat the same data multiple times.
The narrative should flow as: Overview → Detail → Methodology → Trend Analysis → Advisory.

### REQUIRED ELEMENTS
1. **Opening paragraph**: Total Scope 1 figure, what it represents, operational boundary
2. **Source breakdown**: Natural gas vs diesel, percentages, primary uses
3. **Methodology paragraph**: GHG Protocol standard, emission factors (source), GWP values (IPCC AR6), consolidation approach, gases included
4. **Year-over-year comparison**: Prior year figure, absolute change, percentage change, explanation of drivers
5. **Data tables**:
   - Table 1: Scope 1 by source (natural gas, diesel, total)
   - Table 2: YoY comparison
6. **Framework Cross-Reference Table** (MANDATORY — end of section):
   | Framework | Disclosure Ref | Requirement | Status |
   Must include rows for GRI, IFRS S2, ESRS E1, OJK PSPK
7. **Advisory Recommendations** (MANDATORY):
   - 2-3 specific recommendations with peer bank references
   - Format: Finding → Benchmark → Recommendation → Reference → Priority

### TITLE RULES
- Section title MUST be: "1.1 Direct GHG Emissions — Scope 1"
- Do NOT use framework-specific titles (no "GRI 305-1:", no "IFRS S2:", no "ESRS E1-6:")
- The framework mapping is handled by the cross-reference table

### LANGUAGE
- Main narrative: English
- OJK compliance note (if needed): Can include brief Indonesian translation of key figures
  in a callout box or footnote, e.g., "Catatan OJK: Total emisi langsung Lingkup 1 = 3.402,997 tCO₂e"
```

### Change 3: Update AssemblyDoc Lambda (Heading Hierarchy)

```python
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH

REPORT_STRUCTURE = [
    # (type, text, style_level)
    ("heading1", "Executive Summary", 1),
    ("section", "summary"),
    ("heading1", "1. Environmental Performance", 1),
    ("section", "scope1"),
    ("section", "scope2"),
    ("section", "scope3_pcaf"),
    ("section", "intensity"),
    ("section", "reduction"),
    ("heading1", "2. Social Performance", 1),
    ("section", "social"),
    ("heading1", "3. Governance & Strategy", 1),
    ("section", "governance"),
    ("section", "targets"),
    ("heading1", "Appendices", 1),
    ("appendix", "methodology"),
    ("appendix", "data_quality"),
    ("appendix", "gri_index"),
]

def assemble_document(sections_data: list[dict], output_path: str):
    doc = docx.Document("template.docx")  # Base template with styles

    for item in REPORT_STRUCTURE:
        if item[0] == "heading1":
            # Add Heading 1 (page break before, except first)
            if item[1] != "Executive Summary":
                doc.add_page_break()
            doc.add_heading(item[1], level=1)

        elif item[0] == "section":
            section_id = item[1]
            section_data = find_section(sections_data, section_id)
            if section_data:
                # Section title as Heading 2
                doc.add_heading(section_data["title"], level=2)
                # Add paragraphs
                for para in section_data["paragraphs"]:
                    doc.add_paragraph(para["text"])
                # Add tables
                for table in section_data.get("tables", []):
                    add_table(doc, table)
                # Advisory recommendations
                if section_data.get("advisory_recommendations"):
                    add_recommendations(doc, section_data["advisory_recommendations"])
```

### Change 4: Fix Title Generation in SectionGen Lambda

Remove hardcoded titles. Instead, use `heading2` from config:

```python
def _get_section_title(template_id: str, framework: str, config: dict) -> str:
    """Get section title from config (not from model generation)."""
    # Title comes from MULTI_FRAMEWORK_SECTIONS config, not model
    if "heading2" in config:
        return config["heading2"]

    # Fallback mapping (for backward compatibility)
    TITLE_MAP = {
        "scope1": "1.1 Direct GHG Emissions — Scope 1",
        "scope2": "1.2 Energy Indirect GHG Emissions — Scope 2",
        "scope3_pcaf": "1.3 Financed Emissions<artifact id="kiro-spec-unified-structure-v2" title="Kiro Spec & Prompt — Unified 2-Level Hierarchy Report Structure (Opsi A)" type="text/markdown">
# Kiro Task: Implement Unified 2-Level Hierarchy Report Structure (Opsi A)

## Context

Current report structure is **flat** — each framework (GRI, IFRS, ESRS, OJK) generates separate sections for the same metric (e.g., Scope 1 appears 4 times). This creates:
- Repetitive content (reader confusion)
- Poor narrative flow
- Unprofessional appearance

**Target:** Implement **2-level hierarchy** with unified narrative per metric + framework cross-reference appendix.

```
BEFORE (Flat — 17 sections):
├── GRI 305-1: Scope 1
├── IFRS S2: Scope 1
├── ESRS E1-6: Scope 1
├── OJK: Scope 1
├── GRI 305-2: Scope 2
├── ... (13 more flat sections)

AFTER (Hierarchical — 8 unified sections):
H1: Environmental Performance
  ├── H2: Direct Emissions (Scope 1)          ← Unified narrative
  ├── H2: Energy Indirect Emissions (Scope 2)
  ├── H2: Financed Emissions (Scope 3 — PCAF)
  ├── H2: Emissions Intensity
  └── H2: Reduction Initiatives & Targets
H1: Social Performance
  └── H2: Workforce & Human Capital
H1: Governance
  └── H2: Climate Governance & ESG Oversight
H1: Framework Alignment (Appendix)
  └── Cross-reference table: Section → GRI/IFRS/ESRS/OJK mappings
```

---

## Objectives

1. **Unified narrative per metric** — one Scope 1 section (not 4)
2. **2-level heading hierarchy** — H1 per pillar (E/S/G), H2 per section
3. **Framework cross-reference** — table mapping unified sections to framework disclosure IDs
4. **Fix OJK title handling** — Indonesian titles for OJK framework
5. **Executive Summary at top** — page 2 (after ToC)
6. **Professional structure** — aligned with OCBC Indonesia 2024 & BRI 2023 best practice

---

## Deliverables

### Deliverable 1: New Section Template — `section_unified_scope1.txt`

Create a **unified Scope 1 template** that generates ONE narrative covering all framework requirements (GRI 305-1, IFRS S2 Para 29, ESRS E1-6, OJK PSPK).

**Key differences from current `section_scope1.txt`:**

| Aspect | Current (Framework-Specific) | New (Unified) |
|--------|------------------------------|---------------|
| Title | "GRI 305-1: Direct (Scope 1) GHG Emissions" | "Direct (Scope 1) GHG Emissions" (framework-agnostic) |
| Narrative | GRI-focused language | Covers all framework requirements in one narrative |
| Framework references | Implicit (GRI only) | Explicit table at end mapping to all frameworks |
| Output structure | Single framework perspective | Multi-framework comprehensive |

**Template structure:**

```markdown
# Unified Section Template: Direct (Scope 1) GHG Emissions
# Covers: GRI 305-1, IFRS S2 Para 29, ESRS E1-6, OJK PSPK

## SECTION TITLE (MANDATORY)
EXACT_TITLE: "Direct (Scope 1) GHG Emissions"

## REQUIRED ELEMENTS

### 1. Quantitative Disclosure (ALL frameworks require this)
- Total gross Scope 1 emissions (tCO₂e) — GRI 305-1a, IFRS S2 Para 29(a)(i), ESRS E1-6
- Breakdown by source (natural gas, diesel, etc.) — GRI 305-1
- Year-over-year comparison — IFRS S2 Para 29(b), ESRS E1-6

### 2. Methodology Disclosure (ALL frameworks require this)
- Consolidation approach (operational control / equity share) — GRI 305-1f, IFRS S2 Para 29(c)
- Emission factors source — GRI 305-1e, ESRS E1-6
- GWP values (IPCC AR6) — GRI 305-1e
- Standards used (GHG Protocol) — GRI 305-1g, IFRS S2 Para 29(c)

### 3. Gases Included (GRI 305-1b, ESRS E1-6)
- CO₂, CH₄, N₂O disclosure
- Statement on HFCs, PFCs, SF₆, NF₃ if not material

### 4. Contextual Analysis (IFRS S2 Para 29(b), ESRS E1-6)
- Explanation of significant changes YoY
- Identification of emission hotspots (e.g., diesel 64.7% of Scope 1)

### 5. Advisory Recommendations (MANDATORY)
- 2-3 specific, data-backed recommendations
- Peer benchmarks (BRI, DBS, BCA, Mandiri)
- Priority flagging (High/Medium/Low)

### 6. Framework Cross-Reference Table (NEW — MANDATORY)
Generate a table at the END of the section:

| Framework | Disclosure ID | Requirement Met | Location in Section |
|-----------|---------------|-----------------|---------------------|
| GRI 305 | 305-1a | Gross Scope 1 emissions | Table 1 |
| GRI 305 | 305-1b | Gases included | Paragraph 4 |
| GRI 305 | 305-1e | Emission factors & GWP | Paragraph 3 |
| GRI 305 | 305-1f | Consolidation approach | Paragraph 3 |
| GRI 305 | 305-1g | Standards used | Paragraph 3 |
| IFRS S2 | Para 29(a)(i) | Absolute gross GHG emissions | Table 1 |
| IFRS S2 | Para 29(b) | Trends over time | Table 2 |
| IFRS S2 | Para 29(c) | Measurement approach | Paragraph 3 |
| ESRS E1 | E1-6 | Gross Scope 1 GHG emissions | Table 1 |
| OJK PSPK | Emisi GRK Langsung | Emisi Lingkup 1 | Table 1 |

## OUTPUT FORMAT
{
  "section_id": "scope1_unified",
  "title": "Direct (Scope 1) GHG Emissions",
  "heading_level": 2,
  "paragraphs": [...],
  "tables": [...],
  "framework_cross_reference": {
    "GRI_305": ["305-1a", "305-1b", "305-1e", "305-1f", "305-1g"],
    "IFRS_S2": ["Para 29(a)(i)", "Para 29(b)", "Para 29(c)"],
    "CSRD_ESRS_E1": ["E1-6"],
    "OJK_PSPK": ["Emisi GRK Langsung (Lingkup 1)"]
  },
  "advisory_recommendations": [...]
}
```

**Create similar unified templates for:**
- `section_unified_scope2.txt`
- `section_unified_scope3_pcaf.txt`
- `section_unified_intensity.txt`
- `section_unified_reduction.txt`
- `section_unified_social.txt`
- `section_unified_governance.txt`
- `section_unified_targets.txt`

---

### Deliverable 2: Update Lambda #1 (ValidateInput) — New Section Config

Replace `MULTI_FRAMEWORK_SECTIONS` with unified section list:

```python
# BEFORE (17 sections — framework-specific):
MULTI_FRAMEWORK_SECTIONS = [
    {"template_id": "scope1", "framework": "GRI_305"},
    {"template_id": "scope1", "framework": "IFRS_S2"},
    {"template_id": "scope1", "framework": "CSRD_ESRS_E1"},
    {"template_id": "scope1", "framework": "OJK_PSPK"},
    # ... 13 more
]

# AFTER (8 unified sections):
UNIFIED_SECTIONS = [
    {"template_id": "scope1_unified", "heading_level": 2, "parent_heading": "Environmental Performance"},
    {"template_id": "scope2_unified", "heading_level": 2, "parent_heading": "Environmental Performance"},
    {"template_id": "scope3_pcaf_unified", "heading_level": 2, "parent_heading": "Environmental Performance"},
    {"template_id": "intensity_unified", "heading_level": 2, "parent_heading": "Environmental Performance"},
    {"template_id": "reduction_unified", "heading_level": 2, "parent_heading": "Environmental Performance"},
    {"template_id": "social_unified", "heading_level": 2, "parent_heading": "Social Performance"},
    {"template_id": "governance_unified", "heading_level": 2, "parent_heading": "Governance"},
    {"template_id": "targets_unified", "heading_level": 2, "parent_heading": "Governance"},
]
```

---

### Deliverable 3: Update Lambda #3 (SectionGen) — Unified Template Logic

**Changes needed:**

1. **Template mapping** — add unified templates to `TEMPLATE_MAP`:

```python
TEMPLATE_MAP = {
    # Legacy (keep for backward compat):
    "scope1": "section_scope1.txt",
    "scope2": "section_scope2.txt",
    # ... existing ...
    
    # NEW unified templates:
    "scope1_unified": "section_unified_scope1.txt",
    "scope2_unified": "section_unified_scope2.txt",
    "scope3_pcaf_unified": "section_unified_scope3_pcaf.txt",
    "intensity_unified": "section_unified_intensity.txt",
    "reduction_unified": "section_unified_reduction.txt",
    "social_unified": "section_unified_social.txt",
    "governance_unified": "section_unified_governance.txt",
    "targets_unified": "section_unified_targets.txt",
}
```

2. **RAG query logic** — unified sections need to query ALL frameworks:

```python
# BEFORE (framework-specific):
rag_query = f"GRI 305-1 disclosure requirements direct emissions consolidation approach"
kb_filter = {"equals": {"key": "framework", "value": "GRI_305"}}

# AFTER (unified — query multiple frameworks):
if template_id.endswith("_unified"):
    # Query all framework docs (no filter)
    rag_query = f"{metric_area} disclosure requirements GRI IFRS ESRS OJK"
    kb_filter = None  # or use orAll filter for GRI|IFRS|ESRS|OJK
```

3. **Output structure** — add `framework_cross_reference` field to JSON output.

---

### Deliverable 4: Update Lambda #5 (AssemblyDoc) — 2-Level Hierarchy

**Major changes:**

1. **New section order** with H1 headings:

```python
DOCUMENT_STRUCTURE = [
    {"type": "cover"},
    {"type": "toc"},
    
    {"type": "heading1", "text": "Executive Summary"},
    {"type": "section", "id": "summary"},
    
    {"type": "heading1", "text": "Environmental Performance"},
    {"type": "section", "id": "scope1_unified"},
    {"type": "section", "id": "scope2_unified"},
    {"type": "section", "id": "scope3_pcaf_unified"},
    {"type": "section", "id": "intensity_unified"},
    {"type": "section", "id": "reduction_unified"},
    
    {"type": "heading1", "text": "Social Performance"},
    {"type": "section", "id": "social_unified"},
    
    {"type": "heading1", "text": "Governance"},
    {"type": "section", "id": "governance_unified"},
    {"type": "section", "id": "targets_unified"},
    
    {"type": "heading1", "text": "Framework Alignment"},
    {"type": "appendix", "id": "framework_mapping"},
    
    {"type": "heading1", "text": "Appendices"},
    {"type": "appendix", "id": "methodology"},
    {"type": "appendix", "id": "data_quality"},
    {"type": "appendix", "id": "gri_index"},
]
```

2. **Heading rendering logic** — add H1 support:

```python
def _add_heading(doc, text, level):
    """Add heading with proper styling."""
    if level == 1:
        heading = doc.add_heading(text, level=1)
        heading.style = "Heading 1"
        # Optional: add page break before H1 (except first)
    elif level == 2:
        heading = doc.add_heading(text, level=2)
        heading.style = "Heading 2"
```

3. **Framework mapping appendix** — generate from `framework_cross_reference` data:

```python
def _generate_framework_mapping_appendix(doc, all_sections):
    """Generate Framework Alignment appendix from section metadata."""
    doc.add_heading("Framework Alignment", level=1)
    doc.add_paragraph(
        "This appendix maps unified report sections to specific framework disclosure requirements."
    )
    
    table = doc.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 1"
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Report Section"
    hdr_cells[1].text = "Framework"
    hdr_cells[2].text = "Disclosure ID"
    hdr_cells[3].text = "Page"
    
    for section in all_sections:
        if "framework_cross_reference" in section:
            for framework, disclosure_ids in section["framework_cross_reference"].items():
                for disclosure_id in disclosure_ids:
                    row = table.add_row().cells
                    row[0].text = section["title"]
                    row[1].text = framework
                    row[2].text = disclosure_id
                    row[3].text = str(section.get("page_number", "—"))
```

---

### Deliverable 5: Fix OJK Title Handling (All Templates)

For **ALL templates** (unified or legacy), add conditional title logic:

```markdown
## SECTION TITLE (MANDATORY — framework-aware)

IF framework contains "OJK" OR section is for Indonesian regulatory compliance:
  Use Indonesian title format:
  - Scope 1: "Emisi GRK Langsung (Lingkup 1)"
  - Scope 2: "Emisi GRK Tidak Langsung dari Energi (Lingkup 2)"
  - Scope 3: "Emisi GRK Tidak Langsung Lainnya (Lingkup 3) — Emisi Pembiayaan PCAF"
  - Intensity: "Intensitas Emisi GRK"
  - Reduction: "Pengurangan Emisi GRK"
  - Social: "Kinerja Sosial: Tenaga Kerja dan Modal Manusia"
  - Governance: "Tata Kelola Iklim dan Pengawasan ESG"

ELSE (GRI/IFRS/ESRS):
  Use English title format per framework standard
```

**Implementation in prompt template:**

```
You are generating a section for framework: {framework}

TITLE RULES:
- If {framework} = "OJK_PSPK": Use Indonesian title "Emisi GRK Langsung (Lingkup 1)"
- If {framework} = "GRI_305": Use "GRI 305-1: Direct (Scope 1) GHG Emissions"
- If {framework} = "IFRS_S2": Use "IFRS S2 Cross-Industry Metric: Direct (Scope 1) GHG Emissions"
- If {framework} = "CSRD_ESRS_E1": Use "ESRS E1-6: Direct (Scope 1) GHG Emissions"
- If unified (no specific framework): Use "Direct (Scope 1) GHG Emissions"

CRITICAL: Output the title in the "title" field of JSON exactly as specified above.
```

---

### Deliverable 6: Update Agent Tools Lambda — Unified Section Config

Update `SECTION_TEMPLATES` dict to include unified option:

```python
SECTION_TEMPLATES = {
    # ... existing framework-specific configs ...
    
    "UNIFIED": [
        {"template_id": "scope1_unified", "heading_level": 2},
        {"template_id": "scope2_unified", "heading_level": 2},
        {"template_id": "scope3_pcaf_unified", "heading_level": 2},
        {"template_id": "intensity_unified", "heading_level": 2},
        {"template_id": "reduction_unified", "heading_level": 2},
        {"template_id": "social_unified", "heading_level": 2},
        {"template_id": "governance_unified", "heading_level": 2},
        {"template_id": "targets_unified", "heading_level": 2},
        {"template_id": "summary", "framework": "NONE"},
    ],
}
```

---

## Testing Plan

### Phase 1: Template Testing (Isolated)
1. Test `section_unified_scope1.txt` standalone (Lambda #3 manual invoke)
2. Verify output includes `framework_cross_reference` field
3. Verify narrative covers GRI + IFRS + ESRS + OJK requirements
4. Verify advisory recommendations present

### Phase 2: Pipeline Testing (End-to-End)
1. Update Lambda #1 config to use `UNIFIED_SECTIONS`
2. Deploy all 5 Lambdas
3. Trigger Step Functions with `framework: "UNIFIED"`
4. Verify output DOCX:
   - H1 headings present (Environmental Performance, Social Performance, Governance)
   - H2 sections under correct H1
   - Executive Summary at page 2
   - Framework Alignment appendix present
   - No duplicate sections
   - OJK titles in Indonesian (if OJK-specific sections remain)

### Phase 3: Validation
1. Check ToC structure (2-level hierarchy visible)
2. Verify page count reduced (8 unified sections vs 17 framework-specific)
3. Verify framework cross-reference table accuracy
4. Verify all GRI/IFRS/ESRS/OJK requirements covered in unified narrative

---

## Acceptance Criteria

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | Report has 2-level heading hierarchy | H1 per pillar (E/S/G), H2 per section |
| 2 | No duplicate sections | Each metric (Scope 1, 2, 3, etc.) appears ONCE |
| 3 | Executive Summary at top | Page 2 (after ToC) |
| 4 | Framework cross-reference present | Appendix table mapping sections → GRI/IFRS/ESRS/OJK |
| 5 | OJK titles in Indonesian | If OJK-specific sections exist, titles must be Indonesian |
| 6 | Unified narrative quality | Single Scope 1 section covers ALL framework requirements |
| 7 | Advisory recommendations | Present in all unified sections with peer benchmarks |
| 8 | Page count reduction | ~30-40 pages (vs current 58 pages with duplicates) |

---

## File Locations

| Deliverable | Files to Create/Modify | Location |
|-------------|------------------------|----------|
| Unified templates (8 files) | `section_unified_scope1.txt`, `section_unified_scope2.txt`, etc. | `s3://esg-kb-documents-061039769766/prompts/templates/` |
| Lambda #1 config | `handler.py` — replace `MULTI_FRAMEWORK_SECTIONS` with `UNIFIED_SECTIONS` | Lambda esg-validate-input |
| Lambda #3 logic | `handler.py` — add unified template mapping + multi-framework RAG query | Lambda esg-section-gen |
| Lambda #5 structure | `handler.py` — implement `DOCUMENT_STRUCTURE` with H1/H2 + framework mapping appendix | Lambda esg-assembly-doc |
| Agent tools config | `handler.py` — add `UNIFIED` to `SECTION_TEMPLATES` | Lambda esg-agent-tools |

---

## Deploy Order

1. Create 8 unified template files → upload to S3
2. Update Lambda #1 (ValidateInput) → deploy
3. Update Lambda #3 (SectionGen) → deploy
4. Update Lambda #5 (AssemblyDoc) → deploy
5. Update Agent tools Lambda → deploy
6. Test end-to-end with `framework: "UNIFIED"`

---

## Constraints

- Maintain backward compatibility: keep legacy framework-specific templates for single-framework reports
- Temperature = 0.0 (deterministic output)
- S3 pass-by-reference pattern (no inline content in Step Functions payload)
- All numeric data must be traceable to source columns (VAL-NUM-01 compliance)
- Benchmark RAG must retrieve content (fix `chars_retrieved: 0` issue if still present)

---

## Notes

- This is a **significant refactor** — unified templates require careful design to cover all framework requirements in one narrative
- Recommend **phased rollout**: test unified Scope 1 first, then expand to other sections
- Consider keeping framework-specific mode as option for clients who want separate GRI/IFRS/ESRS reports
- OJK title handling applies to both unified AND legacy templates (fix in both)