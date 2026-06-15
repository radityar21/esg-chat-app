```markdown

# SPEC-PRACTITIONER-UPGRADE: ESG Report Practitioner Compliance Enhancement
# ESG Reporting System — Kiro IDE Specification
# VERSION: 1.0.0 | DATE: 12/06/2026

---

## 1. Overview

This spec addresses 7 critical gaps identified from ESG practitioner/assurance provider expectations.
All items are additions to existing section generation and assembly — NOT replacements.

**Impact Level**: These gaps are what separate a "checklist report" from an "assurance-ready" report.
**Integration**: SectionGen templates + AssemblyDoc + New Appendix sections.

---

## 2. Changes Summary

| # | Enhancement | Where Applied | Type |
|---|-------------|---------------|------|
| 1 | OJK PSPK Mandatory Table Format | New appendix section | Assembly (programmatic) |
| 2 | IFRS S2 FI-Specific Disclosures | scope3_pcaf section template | SectionGen (LLM) |
| 3 | PCAF Data Quality Improvement Roadmap | scope3_pcaf section template + new sub-section | SectionGen (LLM) |
| 4 | Double Materiality Statement | New section OR executive summary addition | SectionGen (LLM) |
| 5 | NDC Alignment Reference | targets section template | SectionGen (LLM) |
| 6 | Data Provenance Footnotes | All section templates (universal injection) | SectionGen (LLM) |
| 7 | Management Review & Sign-off | New back-matter section | Assembly (programmatic) |

---

## 3. Enhancement 1: OJK PSPK Mandatory Table Format

### 3.1 Requirement

OJK PSPK requires ALL reported indicators in a specific tabular format.
This is NOT optional — non-compliant format = regulatory rejection.

### 3.2 OJK Table Schema

```python
OJK_PSPK_TABLE_CONFIG = {
    "title": "Lampiran: Ringkasan Kinerja Keberlanjutan (OJK PSPK Format)",
    "placement": "appendix_after_framework_crossref",
    "language": "bilingual",  # Indonesian headers, English content acceptable
    "headers": [
        "No.",
        "Indikator / Indicator",
        "Satuan / Unit",
        "Tahun Berjalan / Current Year (FY2024)",
        "Tahun Sebelumnya / Prior Year (FY2023)",
        "Perubahan / Change (%)",
        "Target",
        "Pencapaian / Achievement",
    ],
    "rows": [
        # === ENVIRONMENTAL ===
        {
            "no": "1",
            "indicator": "Total Emisi GRK (Scope 1 + 2 + 3) / Total GHG Emissions",
            "unit": "tCO₂e",
            "current_key": "total_tco2e",
            "prior_key": "total_tco2e_prior",
            "change_key": "yoy_change_pct",
            "target": "Annual reduction",
            "achievement_logic": "yoy_change_pct < 0 → 'Tercapai' else 'Belum Tercapai'",
        },
        {
            "no": "2",
            "indicator": "Emisi GRK Langsung (Scope 1) / Direct GHG Emissions",
            "unit": "tCO₂e",
            "current_key": "scope1_tco2e",
            "prior_key": "scope1_prior",
            "change_key": "scope1_yoy_pct",
            "target": "Reduce diesel dependency",
            "achievement_logic": "scope1_yoy_pct < 0 → 'Tercapai' else 'Belum Tercapai'",
        },
        {
            "no": "3",
            "indicator": "Emisi GRK Tidak Langsung dari Energi (Scope 2) / Energy Indirect Emissions",
            "unit": "tCO₂e",
            "current_key": "scope2_location_tco2e",
            "prior_key": "scope2_loc_prior",
            "change_key": "scope2_yoy_pct",
            "target": "Procure renewable energy",
            "achievement_logic": "renewable_pct > 0 → 'Dalam Proses' else 'Belum Tercapai'",
        },
        {
            "no": "4",
            "indicator": "Emisi GRK Tidak Langsung Lainnya (Scope 3 — Financed) / Other Indirect Emissions",
            "unit": "tCO₂e",
            "current_key": "scope3_financed_gross_tco2e",
            "prior_key": "scope3_gross_prior",
            "change_key": "scope3_yoy_pct",
            "target": "Improve PCAF score <3.0",
            "achievement_logic": "portfolio_weighted_pcaf_score < 3.0 → 'Tercapai' else 'Belum Tercapai'",
        },
        {
            "no": "5",
            "indicator": "Intensitas Emisi / Emission Intensity",
            "unit": "tCO₂e/IDR miliar",
            "current_key": "intensity_tco2e_per_billion_idr",
            "prior_key": "intensity_prior",
            "change_key": "intensity_yoy_pct",
            "target": "Annual intensity reduction",
            "achievement_logic": "intensity_yoy_pct < 0 → 'Tercapai' else 'Belum Tercapai'",
        },
        {
            "no": "6",
            "indicator": "Konsumsi Energi / Energy Consumption",
            "unit": "MWh",
            "current_key": "total_energy_mwh",
            "prior_key": "total_energy_mwh_prior",
            "change_key": "energy_yoy_pct",
            "target": "Reduce 5% annually",
            "achievement_logic": "energy_yoy_pct < -5 → 'Tercapai' else 'Belum Tercapai'",
        },
        {
            "no": "7",
            "indicator": "Proporsi Energi Terbarukan / Renewable Energy Share",
            "unit": "%",
            "current_key": "renewable_pct",
            "prior_key": "renewable_pct_prior",
            "change_key": None,
            "target": "≥10% by 2026",
            "achievement_logic": "renewable_pct >= 10 → 'Tercapai' else 'Belum Tercapai'",
        },
        # === SOCIAL ===
        {
            "no": "8",
            "indicator": "Jumlah Karyawan / Total Employees",
            "unit": "FTE",
            "current_key": "fte_total",
            "prior_key": "fte_total_prior",
            "change_key": "fte_yoy_pct",
            "target": "N/A",
            "achievement_logic": "N/A",
        },
        {
            "no": "9",
            "indicator": "Proporsi Karyawan Perempuan / Female Workforce Share",
            "unit": "%",
            "current_key": "fte_female_pct",
            "prior_key": "fte_female_pct_prior",
            "change_key": None,
            "target": "≥40%",
            "achievement_logic": "fte_female_pct >= 40 → 'Tercapai' else 'Belum Tercapai'",
        },
        {
            "no": "10",
            "indicator": "Perempuan di Manajemen / Women in Management",
            "unit": "%",
            "current_key": "fte_management_female_pct",
            "prior_key": "fte_mgmt_female_prior",
            "change_key": None,
            "target": "≥30%",
            "achievement_logic": "fte_management_female_pct >= 30 → 'Tercapai' else 'Belum Tercapai'",
        },
        {
            "no": "11",
            "indicator": "Rata-rata Jam Pelatihan / Average Training Hours",
            "unit": "jam/karyawan",
            "current_key": "training_hours_avg",
            "prior_key": "training_hours_prior",
            "change_key": "training_yoy_pct",
            "target": "≥40 hours",
            "achievement_logic": "training_hours_avg >= 40 → 'Tercapai' else 'Belum Tercapai'",
        },
        {
            "no": "12",
            "indicator": "Tingkat Pergantian Sukarela / Voluntary Turnover Rate",
            "unit": "%",
            "current_key": "voluntary_turnover_pct",
            "prior_key": "turnover_prior",
            "change_key": None,
            "target": "<10%",
            "achievement_logic": "voluntary_turnover_pct < 10 → 'Tercapai' else 'Belum Tercapai'",
        },
        # === GOVERNANCE ===
        {
            "no": "13",
            "indicator": "Komite ESG di Tingkat Dewan / ESG Board Committee",
            "unit": "Ya/Tidak",
            "current_key": "has_esg_committee",
            "prior_key": None,
            "change_key": None,
            "target": "Established by Q2 2025",
            "achievement_logic": "has_esg_committee → 'Tercapai' else 'Belum Tercapai'",
        },
        {
            "no": "14",
            "indicator": "Kebijakan Iklim / Climate Policy",
            "unit": "Ya/Tidak",
            "current_key": "has_climate_policy",
            "prior_key": None,
            "change_key": None,
            "target": "Approved by Q3 2025",
            "achievement_logic": "has_climate_policy → 'Tercapai' else 'Belum Tercapai'",
        },
        {
            "no": "15",
            "indicator": "Komitmen SBTi / SBTi Commitment",
            "unit": "Status",
            "current_key": "sbti_status",
            "prior_key": None,
            "change_key": None,
            "target": "Committed by Q3 2025",
            "achievement_logic": "sbti_status == 'Committed' → 'Tercapai' else 'Belum Tercapai'",
        },
    ],
}

3.3 Rendering Logic
python

def _render_ojk_pspk_table(doc, metrics: dict):
    """
    Generate OJK PSPK mandatory format table.
    Programmatic — no LLM involvement.
    """
    add_styled_heading(doc, "Lampiran: Ringkasan Kinerja Keberlanjutan", level=2)
    add_styled_heading(doc, "(Format Pelaporan OJK PSPK)", level=3)
    
    # Add regulatory reference
    add_styled_paragraph(doc, 
        "Disusun sesuai dengan POJK No. 51/POJK.03/2017 tentang Penerapan Keuangan "
        "Berkelanjutan bagi Lembaga Jasa Keuangan, Emiten, dan Perusahaan Publik.",
        style="methodology"
    )
    
    headers = OJK_PSPK_TABLE_CONFIG["headers"]
    tbl = doc.add_table(rows=1 + len(OJK_PSPK_TABLE_CONFIG["rows"]), cols=len(headers))
    
    # Populate headers
    for i, header in enumerate(headers):
        tbl.rows[0].cells[i].text = header
    
    # Populate rows from metrics
    for row_idx, row_config in enumerate(OJK_PSPK_TABLE_CONFIG["rows"]):
        cells = tbl.rows[row_idx + 1].cells
        cells[0].text = row_config["no"]
        cells[1].text = row_config["indicator"]
        cells[2].text = row_config["unit"]
        
        # Current year value
        current_val = metrics.get(row_config["current_key"], "N/A")
        cells[3].text = _format_metric_value(current_val, row_config["unit"])
        
        # Prior year value
        prior_val = metrics.get(row_config["prior_key"], "N/A") if row_config["prior_key"] else "N/A"
        cells[4].text = _format_metric_value(prior_val, row_config["unit"])
        
        # Change %
        change_val = metrics.get(row_config["change_key"], "N/A") if row_config["change_key"] else "N/A"
        cells[5].text = f"{change_val:+.2f}%" if isinstance(change_val, (int, float)) else str(change_val)
        
        # Target
        cells[6].text = row_config["target"]
        
        # Achievement
        cells[7].text = _evaluate_achievement(metrics, row_config["achievement_logic"])
    
    style_table(tbl)
    
    # Add NDC alignment note at bottom

3.4 Placement in Assembly
python

# In _assemble_appendices():
# Add AFTER Framework Cross-Reference, BEFORE Glossary

if framework in ["OJK_PSPK", "MULTI_FRAMEWORK"]:
    doc.add_page_break()
    _render_ojk_pspk_table(doc, aggregated_metrics)

4. Enhancement 2: IFRS S2 Financial Institution-Specific Disclosures
4.1 Requirement
IFRS S2 Para 29 + Industry-based guidance requires FIs to disclose specific portfolio boundary details for financed emissions that go BEYOND standard PCAF methodology statement.

4.2 Template Addition (inject into scope3_pcaf section template)
python

IFRS_S2_FI_SPECIFIC_BLOCK = """

== ADDITIONAL REQUIREMENT: IFRS S2 FINANCIAL INSTITUTION DISCLOSURES ==

After the standard financed emissions narrative, you MUST include a sub-section titled:
"### Portfolio Boundary & Coverage Statement (IFRS S2 Para 29)"

This sub-section MUST contain ALL of the following elements:

1. COVERAGE DECLARATION:
   "This disclosure covers {coverage_pct}% of the institution's gross lending portfolio
   by outstanding amount as of {reporting_date}."

2. INCLUDED ASSET CLASSES (table format):
   | Asset Class | Outstanding (IDR) | % of Total | Included in Calculation |
   | Business Loans (Corporate) | {value} | {pct}% | Yes |
   | Business Loans (SME) | {value} | {pct}% | Yes |
   | Project Finance | {value} | {pct}% | Yes/No + reason |
   | Sovereign Debt | {value} | {pct}% | No — sovereign excluded per PCAF |
   | Retail Mortgages | {value} | {pct}% | No — methodology under development |

3. EXCLUSIONS WITH JUSTIFICATION:
   For each excluded asset class, state:
   - What is excluded
   - Why (methodology gap, data unavailability, immateriality)
   - Timeline for inclusion (if planned)

4. UNDRAWN COMMITMENTS:
   "Undrawn loan commitments of IDR {value} ({pct}% of total facilities) are
   [included/excluded] from financed emissions calculations.
   Rationale: [PCAF Standard treats undrawn as separate — include if drawn-down
   probability is assessed]."

5. OFF-BALANCE SHEET:
   "Off-balance sheet exposures including guarantees and letters of credit
   (IDR {value}) are [included/excluded]. Treatment follows [PCAF/institutional methodology]."

6. ATTRIBUTION METHODOLOGY:
   "Attribution factor calculated as: Outstanding Amount ÷ (Total Equity + Total Debt)
   of the borrower. Where borrower financials are unavailable, [alternative approach stated]."

DATA KEYS:
- coverage_pct: data_quality_coverage_pct (from metrics)
- reporting_date: "31 December {reporting_year}"
- Asset class breakdown: from sector_breakdown[] or portfolio_composition[]
- Undrawn: from undrawn_commitments_idr (if available) or state "Data not available — planned for FY2025"
- Off-balance: from obs_exposure_idr (if available) or state "Not yet assessed"

RULES:
- If data key not available in metrics, state explicitly: "Information not available for this reporting period. Planned inclusion: FY{reporting_year + 1}."

4.3 Integration Point
python

# In SectionGen Lambda, when section_id == "scope3_pcaf":
# Append IFRS_S2_FI_SPECIFIC_BLOCK to the section template BEFORE insight layer

if "IFRS" in framework or framework == "MULTI_FRAMEWORK":
    section_template += "\n" + IFRS_S2_FI_SPECIFIC_BLOCK

5. Enhancement 3: PCAF Data Quality Improvement Roadmap
5.1 Requirement
Rating agencies (MSCI, Sustainalytics, CDP) evaluate YoY DATA QUALITY improvement trajectory, not just current score. A roadmap signals intentionality.

5.2 Template Addition (inject into scope3_pcaf section template)
python

PCAF_ROADMAP_BLOCK = """

== ADDITIONAL REQUIREMENT: DATA QUALITY IMPROVEMENT ROADMAP ==

After the data quality narrative, include a sub-section titled:
"### PCAF Data Quality Improvement Roadmap"

Generate a TABLE with the following structure:

| Year | Target PCAF Score | Key Actions | Score Bucket Focus | Expected Impact |
|------|-------------------|-------------|-------------------|-----------------|
| FY2024 (Actual) | {actual_score} | Baseline established | — | — |
| FY2025 | {target_25} | [Action 1], [Action 2] | Move Score 5 → 4 | -X.XX on weighted avg |
| FY2026 | {target_26} | [Action 1], [Action 2] | Move Score 4 → 3 | -X.XX on weighted avg |
| FY2027 | <3.0 | [Action 1], [Action 2] | Move Score 3 → 2 | -X.XX on weighted avg |

SCORING LOGIC for targets:
- Current score: {portfolio_weighted_pcaf_score}
- Annual improvement target: 0.15-0.20 per year (aggressive but achievable)
- Target FY2025: current - 0.15
- Target FY2026: current - 0.35
- Target FY2027: <3.0

ACTIONS PER SCORE BUCKET:
- Score 5 → 4: Request borrower revenue data (enables EEIO + revenue model vs pure sector average)
- Score 4 → 3: Engage top 20 borrowers for physical activity data (production volumes, energy consumption)
- Score 3 → 2: Integrate CDP responses + annual report disclosures from listed borrowers
- Score 2 → 1: Request verified GHG inventories from major borrowers (SBTi-committed clients)

STRATEGY NARRATIVE (2-3 sentences):
- State which score bucket has highest concentration
- Explain the cost-benefit: "Improving top 50 borrowers (representing X% of portfolio) from Score 4 to Score 3 would reduce weighted average by X.XX"
- Reference peer trajectory if available from KB context

CONSTRAINT:
- Target score values MUST be calculated from current score (not made up)
- Actions must be specific to financial institution context (not generic)
- Include "Confidence gap narrowing" metric: current gap% → projected gap% at target score
"""

5.3 Confidence Gap Projection Table
python

CONFIDENCE_GAP_PROJECTION = """

Also include a "Confidence Gap Projection" mini-table:

| Metric | Current (FY2024) | Target (FY2027) |
|--------|------------------|-----------------|
| Portfolio PCAF Score | {current_score} | <3.0 |
| Confidence Factor (weighted avg) | {current_cf} | ≥0.75 |
| Gross-Weighted Gap | {current_gap_pct}% | <15% |
| Confidence Interval (implied) | ±{current_uncertainty}% | ±<15% |

Where:
- current_cf = weighted average confidence factor (from PCAF score mapping)
- current_gap_pct = (gross - weighted) / gross × 100
- current_uncertainty ≈ gap_pct (as a proxy for uncertainty band)
"""

6. Enhancement 4: Double Materiality Statement
6.1 Requirement
ESRS E1 requires assessment of BOTH impact materiality (how org affects climate) AND financial materiality (how climate affects org's financial position).

6.2 New Section: Climate-Related Financial Materiality
python

DOUBLE_MATERIALITY_CONFIG = {
    "section_id": "double_materiality",
    "placement": "AFTER targets section, BEFORE appendices",
    "condition": "framework in ['CSRD_ESRS_E1', 'MULTI_FRAMEWORK']",
    "generation_mode": "LLM",  # SectionGen with template below
}

DOUBLE_MATERIALITY_TEMPLATE = """
You are generating a Climate-Related Financial Materiality Assessment section.

This addresses ESRS E1 (Double Materiality) and IFRS S2 (Financial impact of climate).

== STRUCTURE ==

### Climate-Related Financial Materiality Assessment

#### Impact Materiality (Inside-Out)
Summary statement referencing the environmental sections already produced:
"As disclosed in Sections 1.1–1.5, the institution's operations and financed activities
contribute {total_tco2e} tCO₂e to global GHG emissions, with {scope3_pct}% attributable
to financed emissions in {top_sectors}."
[1-2 sentences only — this is already covered in detail in other sections]

#### Financial Materiality (Outside-In)

Generate content addressing:

1. PHYSICAL RISK EXPOSURE:
   - What % of lending portfolio is in climate-vulnerable geographies?
   - Sectors with high physical risk: agriculture, coastal infrastructure, mining
   - If data available: state portfolio-at-risk value
   - If data NOT available: state explicitly "Physical risk assessment not yet conducted.
     Planned for FY{reporting_year + 1} in alignment with [ESRS E1 DR E1-9 / IFRS S2 Para 22]."

2. TRANSITION RISK EXPOSURE:
   - Portfolio in carbon-intensive sectors (use concentration data from scope3_pcaf: {top_3_sectors_exposure_idr})
   - Stranded asset risk: Oil & Gas exposure (IDR {oil_gas_exposure}) + Coal (if any)
   - Regulatory risk: OJK PSPK compliance deadline, potential taxonomy-based capital requirements
   - Client readiness: "Of the top 10 financed emitters, {sbti_clients} have SBTi commitments."

3. FINANCIAL IMPACT QUANTIFICATION:
   - If available: Expected Credit Loss impact under climate scenarios
   - If NOT available (likely): "Climate stress testing not yet integrated into ICAAP/ICLAAP.
     The institution plans to conduct climate scenario analysis per [Bank Indonesia / OJK guidance]
     by FY{reporting_year + 1}."

4. MATURITY STATEMENT (mandatory honesty):
   Generate a maturity self-assessment:
   | Element | Status | Timeline |
   | Physical risk assessment | Not conducted | FY2025 |

6.3 Section Order Update
python

# Updated SECTION_ORDER to include double_materiality
SECTION_ORDER = {
    "MULTI_FRAMEWORK": [
        "summary", "scope1", "scope2", "scope3_pcaf", "intensity", 
        "reduction", "social", "governance", "targets", "double_materiality"
    ],
    "CSRD_ESRS_E1": [
        "summary", "targets", "scope1", "scope2", "scope3_pcaf", 
        "intensity", "reduction", "double_materiality", "social", "governance"
    ],
    # GRI_305 and OJK_PSPK: double_materiality NOT included (not required)
}

7. Enhancement 5: NDC Alignment Reference
7.1 Requirement
Indonesian ESG reports MUST contextualize targets against national climate commitments. Without this = floating targets with no policy anchor.

7.2 Template Addition (inject into targets section template)
python

NDC_ALIGNMENT_BLOCK = """

== ADDITIONAL REQUIREMENT: NDC ALIGNMENT STATEMENT ==

Within the targets section, include a sub-section titled:
"### Alignment with Indonesia's National Climate Commitments"

Content MUST include:

1. NDC REFERENCE (factual, hardcoded):
   "Indonesia's Enhanced Nationally Determined Contribution (NDC), updated 2022, commits to:
   - Unconditional target: 31.89% emission reduction below BAU by 2030
   - Conditional target: 43.2% emission reduction below BAU by 2030 (with international support)
   - Long-term strategy: Net Zero Emission (NZE) by 2060 or sooner"

2. INSTITUTIONAL ALIGNMENT ASSESSMENT:
   Compare the institution's recommended/actual targets against NDC:
   - "Our recommended Scope 1+2 reduction target of {recommended_scope12_target}% by 2030
     [aligns with / falls short of / exceeds] Indonesia's unconditional NDC commitment."
   - "Current trajectory of {yoy_change_pct}% annual reduction [is / is not] sufficient to
     achieve the {recommended_scope12_target}% target by 2030, requiring acceleration to
     approximately {required_annual_rate}% per year."

3. SECTORAL ALIGNMENT (for financed emissions):
   "For financed emissions, sector-specific decarbonization pathways aligned with Indonesia's
   NDC and sector roadmaps include:
   - Energy sector: Aligned with RUPTL (PLN's electricity supply plan) coal phase-down trajectory
   - Cement: Aligned with Indonesia Cement Association low-carbon roadmap
   - Steel: Referenced against GCCA/worldsteel 2050 pathway"

4. GAP STATEMENT (if targets not yet set):
   "As of the reporting date, the institution has not formally adopted science-based targets.
   The absence of validated targets creates a gap against Indonesia's NDC implementation
   requirements under Presidential Regulation No. 98/2021 on Carbon Economic Value."

RULES:
- NDC figures (31.89%, 43.2%) are HARDCODED — do not pull from metrics
- Net Zero 2060 is Indonesia's official target — state explicitly
- Reference Presidential Regulation No. 98/2021 (Nilai Ekonomi Karbon / Carbon Economic Value)
- If institution has NO formal targets, state the gap explicitly — do not hedge
- Calculate required annual rate: if target = -30% by 2030 from 2024 base, required = ~5.8% per year
"""

7.3 Required Annual Rate Calculation
python

NDC_CALCULATION_INSTRUCTION = """
CALCULATION (include in narrative):
- Years remaining: 2030 - {reporting_year} = {years_remaining}
- Required total reduction: {target_pct}%
- Required annual compound rate: 1 - (1 - target_pct/100)^(1/years_remaining)
- Example: 30% by 2030 from 2024 = 1 - (0.70)^(1/6) ≈ 5.8% per year
- Current rate: {yoy_change_pct}% per year
- Gap: {required_rate - current_rate}% acceleration needed

State this explicitly: "Closing this gap requires {gap}x acceleration from current trajectory."
"""

8. Enhancement 6: Data Provenance Footnotes
8.1 Requirement
Assurance providers need to trace EVERY reported metric back to its source. Without provenance = cannot verify = limited assurance CANNOT be issued.

8.2 Universal Injection (added to INSIGHT_LAYER_INSTRUCTIONS.txt)
python

DATA_PROVENANCE_INSTRUCTIONS = """

== ADDITIONAL REQUIREMENT: DATA PROVENANCE ==

At the END of each section (after Priority Actions, before Framework References),
include a "Data Provenance" footnote block:

Format:
---
📋 DATA PROVENANCE:
- Primary data source: {source_system} (extracted: {extraction_date})
- Emission factors: {ef_source} ({ef_year})
- Calculation methodology: {methodology_reference}
- Data quality tier: {quality_tier}
- Last validated: {validation_date}
- Responsible function: {responsible_team}
---

RULES FOR GENERATION:
- source_system: Use "Internal ERP / Facility Management System" for Scope 1+2,
  "Core Banking System + PCAF Database" for Scope 3, "HR Information System" for Social
- extraction_date: Use "{reporting_year}-12-31" (year-end)
- ef_source: Use actual EF source per section (IPCC 2006, DEFRA 2025, PLN/ESDM 2023, PCAF DB)
- methodology_reference: "GHG Protocol Corporate Standard (2004, revised)" for Scope 1+2,
  "PCAF Global Standard Part A (2022)" for Scope 3
- quality_tier: "Measured" for Scope 1+2, "Estimated (PCAF Score {avg_score})" for Scope 3,
  "Reported" for Social
- validation_date: Use current report generation date
- responsible_team: "Sustainability & ESG Division" (default)

PROVENANCE VALUES BY SECTION:
- scope1: source="Facility Management System", ef="IPCC 2006 GL Vol 2 + DEFRA 2025", methodology="GHG Protocol Corporate Standard"
- scope2: source="PLN Billing Records / Facility Management System", ef="ESDM Ministerial Decree 2023 (0.7886 kg CO₂/kWh)", methodology="GHG Protocol Scope 2 Guidance (2015)"
- scope3_pcaf: source="Core Banking System (outstanding amounts) + PCAF Emission Factor Database", ef="PCAF DB 2023 + National Statistics", methodology="PCAF Global Standard Part A (2022)"
- intensity: source="Financial statements (audited revenue) + GHG inventory", ef="N/A (derived metric)", methodology="GHG Protocol / IFRS S2 Para 29(b)"
- reduction: source="Derived from Scope 1+2+3 YoY comparison", ef="N/A", methodology="GHG Protocol"
- social: source="HR Information System (SAP HCM / equivalent)", ef="N/A", methodology="GRI 401/403/404/405"
- governance: source="Corporate Secretary records + Board minutes", ef="N/A", methodology="IFRS S2 Para 5-9 + ESRS 2 GOV"
- targets: source="Strategic planning documents + Board resolutions", ef="N/A", methodology="SBTi Target Validation Protocol v5"

CONSTRAINT:
- This is NOT optional — every section MUST have provenance footnotes
- If actual source system name unknown, use generic categories above
- Dates must use DD/MM/YYYY format
"""

8.3 Validation Rule Addition
python

# Add to Validation Lambda rules:
PROVENANCE_VALIDATION = {
    "VAL-PROV-01": {
        "check": "Section contains '📋 DATA PROVENANCE:' block",
        "severity": "WARNING",
        "retry": True,
    },
    "VAL-PROV-02": {
        "check": "Provenance block contains all 6 required fields",
        "severity": "WARNING",
        "retry": True,
    },
}

9. Enhancement 7: Management Review & Sign-off Section
9.1 Requirement
Assurance engagement REQUIRES evidence of management ownership. "DRAFT" watermark is not enough — need explicit sign-off structure.

9.2 Implementation (Programmatic — AssemblyDoc)
python

MANAGEMENT_SIGNOFF_CONFIG = {
    "placement": "AFTER all content sections, BEFORE appendices",
    "title": "Management Statement & Sign-off",
    "components": [
        "responsibility_statement",
        "review_declaration",
        "signoff_block",
        "assurance_status",
    ],
}

def _render_management_signoff(doc, config: dict):
    """
    Generate Management Sign-off section.
    Programmatic — content is templated with config values.
    """
    doc.add_page_break()
    add_styled_heading(doc, "Management Statement & Sign-off", level=1)
    
    # === Responsibility Statement ===
    add_styled_heading(doc, "Statement of Responsibility", level=2)
    add_styled_paragraph(doc, 
        f"The Board of Directors and Management of {config['institution_name']} are responsible "
        f"for the preparation of this Sustainability Report for the financial year ended "
        f"31 December {config['reporting_year']}. This report has been prepared in accordance "
        f"with the reporting frameworks stated herein and presents a balanced and reasonable "
        f"representation of the institution's environmental, social, and governance performance.",
        style="narrative"
    )
    
    # === Internal Review Declaration ===
    add_styled_heading(doc, "Internal Review Process", level=2)
    add_styled_paragraph(doc,
        "This report has undergone the following internal review process:",
        style="narrative"
    )
    
    # Review process table
    review_table_data = {
        "headers": ["Review Stage", "Responsible Party", "Date Completed", "Status"],
        "rows": [
            ["Data Collection & Compilation", "Sustainability Division", f"[DD/MM/{config['reporting_year'] + 1}]", "☐ Completed"],
            ["Methodology Verification", "Risk Management Division", f"[DD/MM/{config['reporting_year'] + 1}]", "☐ Completed"],
            ["Management Review", "Chief Sustainability Officer", f"[DD/MM/{config['reporting_year'] + 1}]", "☐ Completed"],
            ["Board Approval", "Board of Directors", f"[DD/MM/{config['reporting_year'] + 1}]", "☐ Completed"],
        ],
    }
    tbl = doc.add_table(rows=5, cols=4)
    for i, header in enumerate(review_table_data["headers"]):
        tbl.rows[0].cells[i].text = header

10. Updated Assembly Flow
python

# UPDATED SECTION_PLACEMENT_ORDER (with new sections)
SECTION_PLACEMENT_ORDER_V2 = [
    "cover_page",
    "table_of_contents",
    "summary",                # Executive Summary (Tier 1 + Tier 2)
    "scope1",
    "scope2",
    "scope3_pcaf",            # Now includes IFRS S2 FI-specific + PCAF roadmap
    "intensity",
    "reduction",
    "social",
    "governance",
    "targets",                # Now includes NDC alignment
    "double_materiality",     # NEW: Only for CSRD/MULTI_FRAMEWORK
    "management_signoff",     # NEW: Management Statement & Sign-off
    # === APPENDICES ===
    "appendix_methodology",
    "appendix_emission_factors",
    "appendix_data_quality",
    "appendix_sector_classification",
    "appendix_gri_index",
    "appendix_framework_crossref",
    "appendix_ojk_table",     # NEW: OJK PSPK mandatory format
    "appendix_glossary",
]

11. Template Injection Summary
python

# Which enhancements go WHERE in the prompt architecture:

ENHANCEMENT_INJECTION_MAP = {
    # Enhancement 2: IFRS S2 FI-specific → appended to scope3_pcaf template
    "ifrs_s2_fi_specific": {
        "target": "section_template",
        "section_id": "scope3_pcaf",
        "condition": "framework in ['IFRS_S2', 'MULTI_FRAMEWORK']",
        "content": IFRS_S2_FI_SPECIFIC_BLOCK,
    },
    
    # Enhancement 3: PCAF roadmap → appended to scope3_pcaf template
    "pcaf_roadmap": {
        "target": "section_template",
        "section_id": "scope3_pcaf",
        "condition": "ALWAYS",  # All frameworks benefit from data quality transparency
        "content": PCAF_ROADMAP_BLOCK + CONFIDENCE_GAP_PROJECTION,
    },
    
    # Enhancement 5: NDC alignment → appended to targets template
    "ndc_alignment": {
        "target": "section_template",
        "section_id": "targets",
        "condition": "ALWAYS",
        "content": NDC_ALIGNMENT_BLOCK + NDC_CALCULATION_INSTRUCTION,
    },
    
    # Enhancement 6: Data provenance → appended to INSIGHT_LAYER (universal)
    "data_provenance": {
        "target": "insight_layer",
        "section_id": "ALL",
        "condition": "ALWAYS",
        "content": DATA_PROVENANCE_INSTRUCTIONS,
    },
    
    # Enhancement 4: Double materiality → NEW section (own template)
    "double_materiality": {
        "target": "new_section_template",
        "section_id": "double_materiality",
        "condition": "framework in ['CSRD_ESRS_E1', 'MULTI_FRAMEWORK']",
        "content": DOUBLE_MATERIALITY_TEMPLATE,
    },
    
    # Enhancement 1: OJK table → programmatic assembly (no LLM)
    "ojk_table": {
        "target": "assembly_programmatic",
        "section_id": None,
        "condition": "framework in ['OJK_PSPK', 'MULTI_FRAMEWORK']",
        "content": None,  # Uses OJK_PSPK_TABLE_CONFIG directly
    },

12. Validation Rules Addition
python

PRACTITIONER_VALIDATION_RULES = {
    # OJK Table
    "VAL-OJK-01": {
        "check": "OJK PSPK table present in appendix (if framework includes OJK)",
        "severity": "ERROR",
        "retry": False,
    },
    "VAL-OJK-02": {
        "check": "OJK table has all 8 column headers",
        "severity": "ERROR",
        "retry": False,
    },
    
    # IFRS S2 FI-specific
    "VAL-IFRS-01": {
        "check": "Scope 3 section contains 'Portfolio Boundary & Coverage Statement'",
        "severity": "WARNING",
        "retry": True,
    },
    "VAL-IFRS-02": {
        "check": "Exclusions table present with justification for each excluded asset class",
        "severity": "WARNING",
        "retry": True,
    },
    
    # PCAF Roadmap
    "VAL-PCAF-01": {
        "check": "PCAF Improvement Roadmap table present in Scope 3 section",
        "severity": "WARNING",
        "retry": True,
    },
    "VAL-PCAF-02": {
        "check": "Roadmap target scores decrease monotonically (each year lower than prior)",
        "severity": "ERROR",
        "retry": True,
    },
    
    # Double Materiality
    "VAL-DM-01": {
        "check": "Double materiality section present (if CSRD/MULTI framework)",
        "severity": "WARNING",
        "retry": True,
    },
    "VAL-DM-02": {
        "check": "Maturity self-assessment table present with timeline",
        "severity": "WARNING",
        "retry": True,
    },
    
    # NDC Alignment

13. Data Schema Additions
python

# New fields needed in Athena aggregated tables:

SCHEMA_ADDITIONS = {
    "ghg_summary_annual": {
        # EXISTING columns unchanged
        # ADD:
        "undrawn_commitments_idr": "DOUBLE — Total undrawn loan commitments (IDR)",
        "obs_exposure_idr": "DOUBLE — Off-balance sheet exposure (IDR)",
        "renewable_pct": "DOUBLE — Renewable energy procurement %",
        "total_energy_mwh": "DOUBLE — Total energy consumption in MWh",
        "sbti_clients_count": "INT — Number of financed clients with SBTi commitments",
    },
    "portfolio_composition": {
        # NEW TABLE
        "asset_class": "STRING — e.g., 'Business Loans (Corporate)', 'Retail Mortgages'",
        "outstanding_idr": "DOUBLE — Outstanding amount in IDR",
        "pct_of_total": "DOUBLE — % of total portfolio",
        "included_in_financed_emissions": "BOOLEAN — Whether included in PCAF calculation",
        "exclusion_reason": "STRING — Reason for exclusion (if applicable)",
        "inclusion_timeline": "STRING — Planned inclusion date (if currently excluded)",
    },
}

14. Constraints
CON-PRAC-01: OJK table is MANDATORY for OJK/MULTI framework — ERROR severity if missing
CON-PRAC-02: Double materiality section only for CSRD/MULTI (not GRI-only or OJK-only)
CON-PRAC-03: NDC figures (31.89%, 43.2%, NZE 2060) are HARDCODED — never pull from metrics
CON-PRAC-04: Management sign-off uses PLACEHOLDER names ([Name]) — human fills in
CON-PRAC-05: Data provenance is WARNING level (report still valid without, but flagged)
CON-PRAC-06: IFRS S2 FI-specific: if data unavailable, MUST state "not available + timeline"
CON-PRAC-07: PCAF roadmap targets must be CALCULATED from current score (not fabricated)
CON-PRAC-08: All date placeholders use DD/MM/YYYY format
CON-PRAC-09: Achievement logic in OJK table evaluated PROGRAMMATICALLY (not by LLM)
CON-PRAC-10: Segregation of duties table is TEMPLATE — actual org structure filled by human
15. Deployment Checklist
python

DEPLOYMENT_STEPS = [
    # Template updates (S3)
    "1. Append IFRS_S2_FI_SPECIFIC_BLOCK to scope3_pcaf template in s3://esg-templates/",
    "2. Append PCAF_ROADMAP_BLOCK to scope3_pcaf template in s3://esg-templates/",
    "3. Append NDC_ALIGNMENT_BLOCK to targets template in s3://esg-templates/",
    "4. Append DATA_PROVENANCE_INSTRUCTIONS to INSIGHT_LAYER_INSTRUCTIONS.txt",
    "5. Create new template: DOUBLE_MATERIALITY_TEMPLATE → s3://esg-templates/double_materiality.txt",
    
    # Lambda updates
    "6. Update SectionGen Lambda: add double_materiality to section routing",
    "7. Update SectionGen Lambda: conditional IFRS S2 block injection for scope3_pcaf",
    "8. Update AssemblyDoc Lambda: add _render_ojk_pspk_table() function",
    "9. Update AssemblyDoc Lambda: add _render_management_signoff() function",
    "10. Update AssemblyDoc Lambda: updated SECTION_PLACEMENT_ORDER_V2",
    "11. Update Validation Lambda: add PRACTITIONER_VALIDATION_RULES",
    
    # Step Functions
    "12. Update state machine: add double_materiality section to ParallelSectionGeneration",
    "13. Update state machine: section ordering includes new sections",
    
    # Schema (if data available)
    "14. (Optional) Add portfolio_composition table to Athena schema",
    "15. (Optional) Add renewable_pct, total_energy_mwh to ghg_summary_annual",
    
    # Test
    "16. Run full pipeline with MULTI_FRAMEWORK",
    "17. Verify: OJK table renders with all 15 rows + 8 columns",
    "18. Verify: Scope 3 section now has IFRS S2 coverage + PCAF roadmap",
    "19. Verify: Targets section references NDC 31.89% / 43.2%",
    "20. Verify: All sections have 📋 DATA PROVENANCE block",
    "21. Verify: Management sign-off section present with placeholder names",
    "22. Verify: Double materiality section present with maturity table",
]

Done! Satu spec yang covers semua 7 practitioner gaps. Summary:
| Enhancement | Type | Effort |
|-------------|------|--------|
| **OJK PSPK table** | Programmatic (AssemblyDoc) | Medium — new function, 15 rows hardcoded |
| **IFRS S2 FI-specific** | Template append (scope3_pcaf) | Low — inject block ke existing template |
| **PCAF roadmap** | Template append (scope3_pcaf) | Low — inject block ke existing template |
| **Double materiality** | New section (LLM-generated) | Medium — new template + section routing |
| **NDC alignment** | Template append (targets) | Low — inject block ke existing template |
| **Data provenance** | Universal injection (insight layer) | Low — append ke INSIGHT_LAYER_INSTRUCTIONS.txt |
| **Management sign-off** | Programmatic (AssemblyDoc) | Medium — new function, templated content |