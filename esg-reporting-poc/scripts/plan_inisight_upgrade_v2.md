# phase 1

# SPEC-CHARTS: Chart Rendering System
# ESG Reporting System — Kiro IDE Specification
# VERSION: 1.0.0 | DATE: 11/06/2026

---

## 1. Overview

This spec defines the chart rendering system for the ESG Report AssemblyDoc Lambda.
Charts are rendered as matplotlib images embedded into python-docx documents as inline pictures.

**Runtime**: Lambda `esg-assembly-doc` (Python 3.11, 2048MB, 300s timeout)
**Layer**: `esg-matplotlib-layer:1` (matplotlib + numpy)
**Output**: PNG images → `doc.add_picture()` inline

---

## 2. Chart Registry (Section → Chart Mapping)

```python
CHART_REGISTRY = {
    "scope1": {
        "chart_type": "pie",
        "title": "Scope 1 Emissions by Source",
        "data_keys": ["scope1_natgas_tco2e", "scope1_diesel_tco2e"],
        "labels": ["Natural Gas", "Diesel"],
        "unit": "tCO₂e",
        "size": (5.5, 3.5),  # inches (width, height)
    },
    "scope2": {
        "chart_type": "grouped_bar",
        "title": "Scope 2: Location-Based vs Market-Based",
        "data_keys": ["scope2_location_tco2e", "scope2_market_tco2e"],
        "labels": ["Location-Based", "Market-Based"],
        "unit": "tCO₂e",
        "size": (5.5, 3.5),
    },
    "scope3_pcaf": {
        "chart_type": "horizontal_bar",
        "title": "Top 5 Sectors by Financed Emissions",
        "data_keys": ["sector_breakdown"],  # JSON array from Athena
        "value_key": "financed_emissions_gross_tco2e",
        "label_key": "sector_display_name",
        "unit": "tCO₂e",
        "size": (6.0, 4.0),
    },
    "intensity": {
        "chart_type": "bar_with_line",
        "title": "Emission Intensity Trend",
        "data_keys": ["intensity_trend"],  # multi-year array
        "bar_key": "total_tco2e",
        "line_key": "intensity_tco2e_per_idr_bn",
        "x_key": "reporting_year",
        "bar_unit": "tCO₂e",
        "line_unit": "tCO₂e/IDR Bn",
        "size": (6.0, 4.0),
    },
    "reduction": {
        "chart_type": "waterfall",
        "title": "YoY Emission Changes by Scope",
        "data_keys": ["prior_total", "scope1_delta", "scope2_delta", "scope3_delta", "current_total"],
        "labels": ["FY2023", "Scope 1 Δ", "Scope 2 Δ", "Scope 3 Δ", "FY2024"],
        "unit": "tCO₂e",
        "size": (6.0, 3.5),
    },
    "social": {
        "chart_type": "grouped_bar",
        "title": "Workforce Composition & Diversity",
        "data_keys": ["fte_female_pct", "fte_management_female_pct"],
        "labels": ["Female %", "Female in Management %"],
        "compare_years": True,
        "unit": "%",
        "size": (5.5, 3.5),
    },
    "summary": {
        "chart_type": "stacked_bar",
        "title": "Total GHG Emissions by Scope",
        "data_keys": ["scope1_tco2e", "scope2_market_tco2e", "scope3_cat15_gross_tco2e"],
        "labels": ["Scope 1", "Scope 2 (Market)", "Scope 3 (Financed)"],
        "compare_years": True,
        "unit": "tCO₂e",
        "size": (6.0, 4.0),
    },
}
3. Color Palette

CHART_COLORS = {
    "primary": "#1B3A6B",       # Dark navy (headers, primary bars)
    "secondary": "#3D6094",     # Medium blue (secondary bars)
    "tertiary": "#4A7AB5",      # Light blue (tertiary elements)
    "accent": "#F2F6FA",        # Light blue-grey (backgrounds)
    "positive": "#2E7D32",      # Green (positive change)
    "negative": "#C62828",      # Red (negative change / increase)
    "neutral": "#757575",       # Grey (neutral elements)
    "scope1": "#1B3A6B",        # Scope 1 color
    "scope2": "#3D6094",        # Scope 2 color
    "scope3": "#4A7AB5",        # Scope 3 color
    "highlight": "#FF8F00",     # Amber (annotations, callouts)
}

# Pie chart palette (max 6 segments)
PIE_COLORS = ["#1B3A6B", "#3D6094", "#4A7AB5", "#7BA7CC", "#A8CCE0", "#D4E6F1"]

# Bar chart year comparison
YEAR_COLORS = {
    "prior": "#A8CCE0",         # Light (prior year)
    "current": "#1B3A6B",       # Dark (current year)
}

4. Chart Type Implementations
4.1 Pie Chart (pie)
Used for: Scope 1 source breakdown, PCAF sector distribution Requirements:

Maximum 6 slices; if more, group smallest into "Others"
Show percentage labels outside with connecting lines (autopct)
Show absolute values in legend
No 3D effects; flat style
Start angle: 90° (top)
Counter-clockwise direction
Legend positioned below chart, horizontal layout
Data Contract (input from section JSON):

json

{
  "chart_data": {
    "labels": ["Natural Gas", "Diesel"],
    "values": [2580.4521, 822.9112],
    "unit": "tCO₂e"
  }
}

4.2 Vertical Bar Chart (bar / grouped_bar)
Used for: YoY comparison, workforce metrics Requirements:

Bar width: 0.35 (grouped), 0.6 (single)
Y-axis starts at 0 (NEVER truncate)
Value labels on top of each bar (formatted with comma separator)
X-axis: category labels or years
Grid lines: horizontal only, style='--', alpha=0.3
If compare_years=True: show prior year (light) + current year (dark) side by side
Data Contract:

json

{
  "chart_data": {
    "categories": ["2023", "2024"],
    "series": [
      {"name": "Location-Based", "values": [44600.123, 44614.456]},
      {"name": "Market-Based", "values": [44590.789, 44614.456]}
    ],
    "unit": "tCO₂e"
  }
}

4.3 Horizontal Bar Chart (horizontal_bar)
Used for: PCAF top sectors, peer benchmark comparison Requirements:

Sorted descending (highest at top)
Maximum 5-7 bars
Value labels at end of each bar
Category labels on Y-axis (truncate at 25 chars + "...")
Single color (primary) unless benchmark comparison
If benchmark: current entity = primary color, peers = neutral
Data Contract:

json

{
  "chart_data": {
    "categories": ["Energy Oil & Gas", "Cement", "Steel", "Mining", "Agriculture"],
    "values": [6900000, 4200000, 2800000, 1500000, 900000],
    "unit": "tCO₂e"
  }
}

4.4 Bar + Line Combo (bar_with_line)
Used for: Intensity trend (absolute on bar axis, intensity on line axis) Requirements:

Primary Y-axis (left): bar values
Secondary Y-axis (right): line values
Line style: solid, marker='o', linewidth=2
Line color: highlight (amber)
Bar color: primary (navy)
Both axes labeled with units
Data labels on both bars and line points
Data Contract:

json

{
  "chart_data": {
    "x_labels": ["2023", "2024"],
    "bar_values": [22980000, 22030000],
    "bar_unit": "tCO₂e",
    "line_values": [270.12, 239.40],
    "line_unit": "tCO₂e/IDR Bn"
  }
}

4.5 Stacked Bar Chart (stacked_bar)
Used for: Total emissions by scope (multi-year) Requirements:

Each stack segment colored per scope (scope1, scope2, scope3 from palette)
Legend positioned below chart
Total value annotation on top of each stacked bar
Y-axis starts at 0
Data Contract:

json

{
  "chart_data": {
    "x_labels": ["2023", "2024"],
    "stacks": [
      {"name": "Scope 1", "values": [3324, 3403], "color": "#1B3A6B"},
      {"name": "Scope 2", "values": [44601, 44614], "color": "#3D6094"},
      {"name": "Scope 3", "values": [22930000, 21980000], "color": "#4A7AB5"}
    ],
    "unit": "tCO₂e"
  }
}

4.6 Waterfall Chart (waterfall)
Used for: YoY emission changes decomposition Requirements:

First bar (baseline) and last bar (final) = solid color (primary)
Intermediate bars = positive (green, going up) or negative (red, going down)
Connector lines between bars (thin, dashed)
Value labels on each bar showing delta ("+X" or "−X")
Total annotation on final bar
Data Contract:

json

{
  "chart_data": {
    "labels": ["FY2023 Total", "Scope 1 Δ", "Scope 2 Δ", "Scope 3 Δ", "FY2024 Total"],
    "values": [22980000, 79, 13, -950000, 22030000],
    "types": ["total", "delta", "delta", "delta", "total"],
    "unit": "tCO₂e"
  }
}

5. Global Chart Styling

CHART_STYLE = {
    "font_family": "Arial",
    "title_size": 11,
    "title_weight": "bold",
    "title_color": "#1B3A6B",
    "label_size": 9,
    "tick_size": 8,
    "legend_size": 8,
    "dpi": 150,
    "figure_facecolor": "white",
    "axes_facecolor": "white",
    "grid_alpha": 0.3,
    "grid_style": "--",
    "grid_color": "#CCCCCC",
    "spine_visible": {"top": False, "right": False, "bottom": True, "left": True},
    "spine_color": "#CCCCCC",
}

6. YoY Annotation System
When yoy_change_pct is available for a metric, add annotation:
ANNOTATION_CONFIG = {
    "format": "{direction} {abs_value:.1f}% YoY",  # e.g., "▼ 4.07% YoY"
    "positive_symbol": "▲",
    "negative_symbol": "▼",
    "positive_color": "#C62828",   # Red = emissions INCREASED (bad)
    "negative_color": "#2E7D32",   # Green = emissions DECREASED (good)
    "font_size": 9,
    "font_weight": "bold",
    "position": "top_right",       # Relative to chart area
    "bbox": {"boxstyle": "round,pad=0.3", "facecolor": "#F2F6FA", "edgecolor": "#CCCCCC"},
}

7. Data Flow & Integration Point
7.1 Where chart data comes from
AthenaQueryFn (Lambda #2) → section_metrics JSON → stored in S3
                                                         ↓
AssemblyDoc (Lambda #5) reads section JSON → extracts chart_data → renders chart
7.2 Chart data injection in SectionGen output
The SectionGen Lambda MUST include a chart_data field in its JSON output:

{
  "section_id": "GRI_305_S1_2024",
  "title": "...",
  "paragraphs": [...],
  "tables": [...],
  "chart_data": {
    "chart_type": "pie",
    "labels": ["Natural Gas", "Diesel"],
    "values": [2580.4521, 822.9112],
    "unit": "tCO₂e"
  }
}

If chart_data is null or missing → skip chart for that section (no placeholder text).

7.3 AssemblyDoc integration

def _add_chart(doc, section_json, chart_registry):
    """
    Render and embed chart for a section.
    Called AFTER section narrative paragraphs, BEFORE tables.
    """
    chart_data = section_json.get("chart_data")
    if not chart_data:
        return  # No chart for this section — silently skip
    
    section_type = section_json["section_id"].split("_")[-2]  # e.g., "S1" → map to "scope1"
    config = chart_registry.get(section_type, {})
    
    # Render chart to BytesIO PNG buffer
    # Embed using doc.add_picture(buffer, width=Inches(config["size"][0]))
    # Add caption paragraph below: "Figure X: {title}" (italic, 9pt, centered)


8. Figure Numbering
Auto-increment figure counter per report
Format: "Figure {n}: {chart_title}"
Style: Italic, 9pt, centered, color #666666
Spacing: 6pt before, 12pt after


9. Error handling

def _add_chart(doc, section_json, chart_registry):
    chart_data = section_json.get("chart_data")
    if not chart_data:
        return
    
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend (REQUIRED for Lambda)
        import matplotlib.pyplot as plt
    except ImportError as e:
        logger.error(f"matplotlib import failed: {e}")
        return  # Silent skip — do NOT add placeholder text
    
    try:
        fig = _render_chart(chart_data, config)
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=CHART_STYLE["dpi"], 
                    bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        plt.close(fig)  # CRITICAL: prevent memory leak in Lambda
        
        doc.add_picture(buffer, width=Inches(config["size"][0]))
        _add_figure_caption(doc, config["title"])
        
    except Exception as e:
        logger.error(f"Chart rendering failed for {section_json['section_id']}: {e}")
        # Do NOT add placeholder — report assembles without chart
        return


10. Number Formatting in Charts
python

def format_chart_number(value, unit):
    """Format numbers for chart display."""
    if abs(value) >= 1_000_000:
        return f"{value/1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"{value/1_000:.1f}K"
    elif unit == "%":
        return f"{value:.1f}%"
    else:
        return f"{value:,.1f}"

11. Placement Rules

| Section | Chart Position | Rationale |
|---------|---------------|-----------|
| scope1 | After methodology paragraph, before table | Visual then data |
| scope2 | After dual-reporting paragraph | Compare location vs market |
| scope3_pcaf | After sector breakdown narrative | Visualize top emitters |
| intensity | After trend paragraph | Show trajectory |
| reduction | After YoY analysis | Decompose changes |
| social | After workforce paragraph | Diversity visual |
| summary | After executive narrative | Big picture overview |

12. Constraints
CON-CHART-01: matplotlib Agg backend ONLY (no display server in Lambda)
CON-CHART-02: plt.close(fig) after EVERY render (memory management)
CON-CHART-03: Max chart width = 6.27 inches (page width - margins)
CON-CHART-04: All text in charts MUST use Arial font
CON-CHART-05: No chart renders if data is None/empty — NEVER show placeholder text
CON-CHART-06: DPI fixed at 150 (balance quality vs file size)
CON-CHART-07: Chart images NOT stored separately — rendered in-memory only
---

```markdown

# SPEC-STYLING: DOCX Styling System (docx_styler)
# ESG Reporting System — Kiro IDE Specification
# VERSION: 1.0.0 | DATE: 11/06/2026

---

## 1. Overview

This spec defines the `docx_styler` module — a pure Python module that applies visual styling
to the ESG report DOCX output. It handles KPI boxes, insight boxes, priority action lists,
table formatting, cover page, and page setup.

**Module path**: `layers/python/docx_styler.py` (bundled in esg-python-docx layer)
**Dependencies**: python-docx, docx.oxml (lxml)
**No LLM involvement**: All styling is deterministic Python.

---

## 2. Page Setup

```python
PAGE_CONFIG = {
    "page_size": "A4",          # 210mm × 297mm
    "width_inches": 8.27,
    "height_inches": 11.69,
    "margin_top": 1.0,          # inches
    "margin_bottom": 1.0,
    "margin_left": 1.0,
    "margin_right": 1.0,
    "default_font": "Arial",
    "default_font_size": 11,    # pt
    "fallback_font": "Calibri",
}
3. Heading Styles

HEADING_STYLES = {
    1: {
        "font": "Arial",
        "size_pt": 18,
        "bold": True,
        "color": "#1B3A6B",
        "space_before_pt": 24,
        "space_after_pt": 12,
        "keep_with_next": True,
    },
    2: {
        "font": "Arial",
        "size_pt": 14,
        "bold": True,
        "color": "#3D6094",
        "space_before_pt": 18,
        "space_after_pt": 8,
        "keep_with_next": True,
    },
    3: {
        "font": "Arial",
        "size_pt": 12,
        "bold": True,
        "color": "#4A7AB5",
        "space_before_pt": 12,
        "space_after_pt": 6,
        "keep_with_next": True,
    },
}


4. Body Text Styles
python

BODY_STYLES = {
    "normal": {
        "font": "Arial",
        "size_pt": 11,
        "color": "#000000",
        "line_spacing": 1.15,
        "space_after_pt": 8,
        "space_before_pt": 0,
    },
    "methodology": {
        "font": "Arial",
        "size_pt": 11,
        "italic": True,
        "color": "#333333",
        "line_spacing": 1.15,
        "space_after_pt": 8,
    },
    "footnote": {
        "font": "Arial",
        "size_pt": 9,
        "italic": True,
        "color": "#666666",
        "line_spacing": 1.0,
        "space_after_pt": 4,
    },
    "forward_looking": {
        "font": "Arial",
        "size_pt": 11,
        "italic": True,  # qualifier prefix italic
        "color": "#000000",
        "line_spacing": 1.15,
        "space_after_pt": 8,
    },
    "framework_reference": {
        "font": "Arial",
        "size_pt": 9,
        "color": "#666666",
        "format": "(Ref: {reference})",
    },
}

KPI_BOX_CONFIG = {
    "max_metrics": 4,
    "layout": "single_row_table",  # 1 row × N columns
    "cell_background": "#F2F6FA",
    "cell_border": "0.5pt solid #D0D0D0",
    "cell_padding_top_pt": 8,
    "cell_padding_bottom_pt": 8,
    "cell_padding_left_pt": 12,
    "cell_padding_right_pt": 12,
    "label_font_size_pt": 8,
    "label_color": "#666666",
    "label_bold": False,
    "value_font_size_pt": 14,
    "value_color": "#1B3A6B",
    "value_bold": True,
    "unit_font_size_pt": 9,
    "unit_color": "#666666",
    "space_before_pt": 12,
    "space_after_pt": 12,
}

5.3 Data Contract (from section JSON key_metrics)
json

{
  "key_metrics": [
    {"label": "Total Scope 1", "value": "3,403.21", "unit": "tCO₂e"},
    {"label": "YoY Change", "value": "+2.36%", "unit": ""},
    {"label": "Data Quality", "value": "2.1", "unit": "/4"},
    {"label": "Facilities", "value": "47", "unit": ""}
  ]
}

5.4 Rendering Function Signature

def add_kpi_highlights(doc: Document, metrics: list[dict]) -> None:
    """
    Add a KPI highlight box (1-row table) after the section heading.
    
    Args:
        doc: python-docx Document object
        metrics: list of {"label": str, "value": str, "unit": str}
    
    Renders as:
    ┌──────────────┬──────────────┬──────────────┬──────────────┐
    │ Total Scope 1│ YoY Change   │ Data Quality │ Facilities   │
    │ 3,403.21     │ +2.36%       │ 2.1/4        │ 47           │
    │ tCO₂e        │              │              │              │
    └──────────────┴──────────────┴──────────────┴──────────────┘
    """


6. Insight Boxes (⚠️ KEY INSIGHT)
6.1 Design
Insight boxes are left-bordered colored boxes containing advisory content. They appear inline within the narrative at specific points.

6.2 Specification

INSIGHT_BOX_CONFIG = {
    "border_left_color": "#FF8F00",   # Amber left border
    "border_left_width_pt": 3,
    "background_color": "#FFF8E1",    # Light amber background
    "padding_top_pt": 8,
    "padding_bottom_pt": 8,
    "padding_left_pt": 12,
    "padding_right_pt": 12,
    "title_prefix": "⚠️ KEY INSIGHT",
    "title_font_size_pt": 10,
    "title_bold": True,
    "title_color": "#E65100",
    "body_font_size_pt": 10,
    "body_color": "#333333",
    "space_before_pt": 12,
    "space_after_pt": 12,
}

6.3 Detection Pattern
SectionGen output contains insight markers in paragraphs:

⚠️ KEY INSIGHT: {insight text here}
The AssemblyDoc parser detects this pattern and routes to add_insight_box().

6.4 Rendering Function

def add_insight_box(doc: Document, insight_text: str) -> None:
    """
    Add a styled insight box with amber left border.
    
    Implementation:
    - Create 1×1 table (for border control)
    - Apply left border (amber, 3pt)
    - Set cell background to light amber
    - Add title run ("⚠️ KEY INSIGHT") bold
    - Add body text below title
    """


7. Priority Action Lists (⚡ PRIORITY ACTIONS)
7.1 Design
Priority actions are numbered action items with urgency indicators. Rendered as a styled list with icons and timeline context.

7.2 Specification

PRIORITY_ACTION_CONFIG = {
    "container_border": "1pt solid #E0E0E0",
    "container_background": "#FAFAFA",
    "container_padding_pt": 10,
    "header_text": "⚡ PRIORITY ACTIONS",
    "header_font_size_pt": 10,
    "header_bold": True,
    "header_color": "#1B3A6B",
    "item_font_size_pt": 10,
    "item_color": "#333333",
    "item_bullet_style": "numbered",  # 1. 2. 3.
    "item_spacing_pt": 4,
    "urgency_colors": {
        "immediate": "#C62828",   # Red
        "short_term": "#E65100",  # Orange  
        "medium_term": "#1B3A6B", # Navy
    },
    "space_before_pt": 12,
    "space_after_pt": 12,
}


7.3 Detection Pattern
⚡ PRIORITY ACTIONS:
1. [Immediate] Action text here (timeline)
2. [Short-term] Action text here (timeline)
3. [Medium-term] Action text here (timeline)

7.4 Rendering Function
python

def add_priority_actions(doc: Document, actions: list[dict]) -> None:
    """
    Add a styled priority actions box.
    
    Args:
        actions: list of {"urgency": str, "text": str, "timeline": str}
    """


8. Diagnostic Analysis Box
8.1 Specification

DIAGNOSTIC_BOX_CONFIG = {
    "border_left_color": "#1B3A6B",   # Navy left border
    "border_left_width_pt": 3,
    "background_color": "#F2F6FA",    # Light blue-grey
    "title_prefix": "📊 DIAGNOSTIC ANALYSIS",
    "title_font_size_pt": 10,
    "title_bold": True,
    "title_color": "#1B3A6B",
    "body_font_size_pt": 10,
    "body_color": "#333333",
}

8.2 Detection Pattern
📊 DIAGNOSTIC ANALYSIS: {analysis text}
9. Table Styling
9.1 ESG_Table Custom Style

TABLE_STYLE_CONFIG = {
    "style_name": "ESG_Table",
    "header_background": "#1B3A6B",
    "header_font": "Arial",
    "header_font_size_pt": 10,
    "header_font_color": "#FFFFFF",
    "header_bold": True,
    "body_font": "Arial",
    "body_font_size_pt": 10,
    "body_font_color": "#000000",
    "alternating_row_color": "#F2F6FA",  # Even rows
    "odd_row_color": None,               # White (no shading)
    "cell_padding_top_pt": 4,
    "cell_padding_bottom_pt": 4,
    "cell_padding_left_pt": 6,
    "cell_padding_right_pt": 6,
    "border_color": "#D0D0D0",
    "border_width_pt": 0.5,
    "numeric_alignment": "right",
    "text_alignment": "left",
    "table_width": "100%",
    "autofit": True,
    "caption_font_size_pt": 9,
    "caption_italic": True,
    "caption_alignment": "center",
    "caption_format": "Table {n}: {caption_text}",
}


9.2 Rendering Function

def style_table(table, caption: str = None) -> None:
    """
    Apply ESG_Table style to a python-docx table object.
    
    Steps:
    1. Set header row background (#1B3A6B navy)
    2. Set header row font (white, bold, 10pt)
    3. Apply alternating row shading (even rows: #F2F6FA)
    4. Set borders (0.5pt #D0D0D0 all cells)
    5. Set cell padding
    6. Detect numeric columns → right-align
    7. Set table width to 100%
    """

9.3 Cell Shading Implementation

def set_cell_shading(cell, color_hex: str) -> None:
    """Apply background color to table cell using OxmlElement."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), color_hex)
    shading_elm.set(qn('w:val'), 'clear')
    shading_elm.set(qn('w:color'), 'auto')
    cell._tc.get_or_add_tcPr().append(shading_elm)


9.4 Numeric Detection

def is_numeric_column(table, col_index: int) -> bool:
    """Check if majority of cells in column contain numeric data."""
    numeric_count = 0
    for row in table.rows[1:]:  # Skip header
        cell_text = row.cells[col_index].text.strip()
        # Remove formatting chars: commas, %, -, +, spaces
        cleaned = cell_text.replace(',', '').replace('%', '').replace('+', '').replace('-', '', 1)
        try:
            float(cleaned)
            numeric_count += 1
        except ValueError:
            pass
    return numeric_count > len(table.rows[1:]) * 0.5


10. Cover Page
10.1 Design
Full-page cover with dark navy color block (top 40%), white section (bottom 60%).

10.2 Specification

COVER_PAGE_CONFIG = {
    "color_block_height_pct": 40,
    "color_block_color": "#1B3A6B",
    "institution_name_size_pt": 28,
    "institution_name_color": "#FFFFFF",
    "institution_name_bold": True,
    "report_title": "ESG Sustainability Report",
    "report_title_size_pt": 22,
    "report_title_color": "#FFFFFF",
    "report_title_bold": False,
    "subtitle": "Multi-Framework Disclosure",
    "subtitle_size_pt": 14,
    "subtitle_color": "#A8CCE0",
    "year_size_pt": 36,
    "year_color": "#1B3A6B",
    "year_bold": True,
    "metadata_items": [
        "Reporting Period: January – December {year}",
        "Frameworks: GRI 305, IFRS S2, CSRD/ESRS E1, OJK PSPK",
        "Prepared: {generation_date}",
        "Status: DRAFT — Subject to Review",
    ],
    "metadata_size_pt": 10,
    "metadata_color": "#666666",
    "disclaimer": "CONFIDENTIAL — This report has not been subject to external assurance.",
    "disclaimer_size_pt": 9,
    "disclaimer_color": "#999999",
    "disclaimer_italic": True,
}

10.3 Implementation Approach
Cover page is implemented as a full-page table (1 column, 2 rows) with:

Row 1: Navy background, white text (institution name, report title, subtitle)
Row 2: White background (year, metadata, disclaimer)
Page break after cover

def add_cover_page(doc: Document, config: dict) -> None:
    """
    Generate styled cover page.
    Uses 1-column table for color block control.
    Adds page break after cover.
    """

11. Header & Footer

HEADER_FOOTER_CONFIG = {
    "header_right": "{institution_name} | Reporting Year {year}",
    "header_font": "Arial",
    "header_size_pt": 9,
    "header_color": "#888888",
    "footer_left": "ESG Sustainability Report — {framework}",
    "footer_right": "Page {page} of {total}",
    "footer_font": "Arial",
    "footer_size_pt": 9,
    "footer_color": "#888888",
}

12. Page Break Logic

PAGE_BREAK_SECTIONS = {
    0,   # After cover page
    1,   # Before Scope 1
    2,   # Before Scope 2
    3,   # Before Scope 3 PCAF
    5,   # Before Reduction
    8,   # Before Governance
    11,  # Before Targets
    12,  # Before Executive Summary
}

def should_insert_page_break(section_index: int) -> bool:
    return section_index in PAGE_BREAK_SECTIONS


13. Assembly Loop Integration
The docx_styler functions are called in this order per section:

def assemble_section(doc, section_json, section_index):
    # 1. Page break (if needed)
    if should_insert_page_break(section_index):
        doc.add_page_break()
    
    # 2. Section heading (H1)
    add_styled_heading(doc, section_json["title"], level=1)
    
    # 3. KPI highlights (if key_metrics present)
    if section_json.get("key_metrics"):
        add_kpi_highlights(doc, section_json["key_metrics"])
    
    # 4. Paragraphs (with inline detection for insight/action boxes)
    for para in section_json["paragraphs"]:
        text = para["text"]
        para_type = para.get("paragraph_type", "narrative")
        
        if text.startswith("⚠️ KEY INSIGHT:"):
            add_insight_box(doc, text.replace("⚠️ KEY INSIGHT:", "").strip())
        elif text.startswith("⚡ PRIORITY ACTIONS:"):
            actions = parse_priority_actions(text)
            add_priority_actions(doc, actions)
        elif text.startswith("📊 DIAGNOSTIC ANALYSIS:"):
            add_diagnostic_box(doc, text.replace("📊 DIAGNOSTIC ANALYSIS:", "").strip())
        else:
            add_styled_paragraph(doc, text, style=para_type)
    
    # 5. Chart (if chart_data present) — handled by SPEC-CHARTS
    
    # 6. Tables
    for table_data in section_json.get("tables", []):
        tbl = create_table(doc, table_data["headers"], table_data["rows"])
        style_table(tbl)
        add_table_caption(doc, table_data.get("caption", ""))
    
    # 7. Footnotes
    if section_json.get("footnotes"):
        add_footnote_block(doc, section_json["footnotes"])
    
    # 8. Framework references
    if section_json.get("framework_references"):
        add_framework_refs(doc, section_json["framework_references"])

14. Constraints
CON-STYLE-01: No LLM involvement in styling — purely deterministic
CON-STYLE-02: All colors MUST use hex codes (not named colors)
CON-STYLE-03: Font fallback chain: Arial → Calibri → system default
CON-STYLE-04: NEVER use Times New Roman
CON-STYLE-05: Table borders via OxmlElement (python-docx has no native border API)
CON-STYLE-06: KPI box = 1-row table (for consistent cell background rendering)
CON-STYLE-07: Insight/Diagnostic boxes = 1×1 table with left border
CON-STYLE-08: Cover page color block = table with shaded row (not shape/image)

---

```markdown

# SPEC-MARKDOWN-PARSER: Markdown → DOCX Converter
# ESG Reporting System — Kiro IDE Specification
# VERSION: 1.0.0 | DATE: 11/06/2026

---

## 1. Overview

This spec defines the markdown-to-DOCX parser for the AssemblyDoc Lambda.
The SectionGen Lambda returns narrative text with markdown formatting.
The parser converts markdown syntax into proper python-docx elements.

**Problem**: Currently `## Heading Text` renders as literal plain text in the DOCX.
**Solution**: Parse markdown patterns and convert to DOCX heading/formatting objects.

---

## 2. Supported Markdown Elements

| Markdown Syntax | DOCX Output | Style Applied |
|----------------|-------------|---------------|
| `# Heading` | `doc.add_heading(text, level=1)` | Heading 1 (18pt, #1B3A6B) |
| `## Heading` | `doc.add_heading(text, level=2)` | Heading 2 (14pt, #3D6094) |
| `### Heading` | `doc.add_heading(text, level=3)` | Heading 3 (12pt, #4A7AB5) |
| `**bold text**` | `run.bold = True` | Bold run within paragraph |
| `*italic text*` | `run.italic = True` | Italic run within paragraph |
| `***bold italic***` | `run.bold = True; run.italic = True` | Bold+Italic run |
| `- list item` | Bulleted list paragraph | List Bullet style |
| `1. list item` | Numbered list paragraph | List Number style |
| `> blockquote` | Indented paragraph | Left indent 0.5", italic |
| `---` | Horizontal rule | Thin line (0.5pt, #CCCCCC) |
| `` `inline code` `` | Monospace run | Consolas 10pt, #F5F5F5 bg |
| `\n\n` (double newline) | New paragraph | Normal style |
| `\n` (single newline within para) | Same paragraph, soft return | Line break |

---

## 3. Parsing Priority (Order of Operations)

```python
PARSE_ORDER = [
    "headings",          # Must be first (line-level detection)
    "horizontal_rules",  # Line-level: ---
    "blockquotes",       # Line-level: > text
    "list_items",        # Line-level: - or 1.
    "inline_formatting", # Inline: **bold**, *italic*, `code`
]
Rule: Line-level patterns are detected FIRST (before inline parsing). A line starting with ## is a heading — do NOT parse inline formatting within it.

4. Heading Parser
4.1 Pattern
python

import re

HEADING_PATTERN = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)

4.2 Level Mapping
python

HEADING_LEVEL_MAP = {
    1: 1,  # # → Heading 1 (Section title — rare, usually from section_json["title"])
    2: 2,  # ## → Heading 2 (Subsection)
    3: 3,  # ### → Heading 3 (Sub-subsection)
}

4.3 Implementation
python

def parse_heading(line: str) -> tuple[int, str] | None:
    """
    Parse a markdown heading line.
    
    Returns:
        (level, text) if heading detected, None otherwise
    
    Example:
        "## Workforce Overview" → (2, "Workforce Overview")
    """
    match = HEADING_PATTERN.match(line.strip())
    if match:
        level = len(match.group(1))  # Count # characters
        text = match.group(2).strip()
        return (level, text)
    return None

5. Inline Formatting Parser
5.1 Patterns
python

# Order matters: bold-italic before bold before italic
INLINE_PATTERNS = [
    ("bold_italic", re.compile(r'\*\*\*(.+?)\*\*\*')),
    ("bold", re.compile(r'\*\*(.+?)\*\*')),
    ("italic", re.compile(r'\*(.+?)\*')),
    ("code", re.compile(r'`(.+?)`')),
]

5.2 Implementation
python
def add_formatted_paragraph(doc, text: str, base_style: str = "normal") -> None:
    """
    Add a paragraph with inline markdown formatting converted to runs.
    
    Strategy:
    1. Split text by inline patterns
    2. For each segment, create a run with appropriate formatting
    3. Unformatted text → normal run
    4. **text** → bold run
    5. *text* → italic run
    6. `text` → monospace run
    """
    paragraph = doc.add_paragraph()
    apply_paragraph_style(paragraph, base_style)
    
    # Tokenize: split into (text, format_type) tuples
    tokens = tokenize_inline(text)
    
    for token_text, token_format in tokens:
        run = paragraph.add_run(token_text)
        run.font.name = "Arial"
        run.font.size = Pt(11)
        
        if token_format == "bold_italic":
            run.bold = True
            run.italic = True
        elif token_format == "bold":
            run.bold = True
        elif token_format == "italic":
            run.italic = True
        elif token_format == "code":
            run.font.name = "Consolas"
            run.font.size = Pt(10)
            # Note: background color on run not natively supported
            # Use character shading via OxmlElement if needed

5.3 Tokenizer
python
def tokenize_inline(text: str) -> list[tuple[str, str | None]]:
    """
    Tokenize text into segments with formatting info.
    
    Returns list of (text, format_type) where format_type is:
        None = plain text
        "bold" = **text**
        "italic" = *text*
        "bold_italic" = ***text***
        "code" = `text`
    
    Example:
        "Total is **3,403 tCO₂e** which is *significant*"
        → [("Total is ", None), ("3,403 tCO₂e", "bold"), (" which is ", None), ("significant", "italic")]
    """
    tokens = []
    remaining = text
    
    while remaining:
        earliest_match = None
        earliest_pos = len(remaining)
        earliest_format = None
        
        for fmt_name, pattern in INLINE_PATTERNS:
            match = pattern.search(remaining)
            if match and match.start() < earliest_pos:
                earliest_match = match
                earliest_pos = match.start()
                earliest_format = fmt_name
        
        if earliest_match is None:
            tokens.append((remaining, None))
            break
        
        # Add text before match
        if earliest_pos > 0:
            tokens.append((remaining[:earliest_pos], None))
        
        # Add matched formatted text
        tokens.append((earliest_match.group(1), earliest_format))
        
        # Continue after match
        remaining = remaining[earliest_match.end():]
    
    return tokens

6. List Parser
6.1 Patterns
python

BULLET_PATTERN = re.compile(r'^[\-\*]\s+(.+)$')
NUMBERED_PATTERN = re.compile(r'^\d+[\.\)]\s+(.+)$')

6.2 Implementation
def parse_list_item(line: str) -> tuple[str, str] | None:
    """
    Detect list item type.
    
    Returns:
        ("bullet", text) or ("numbered", text) or None
    """
    bullet_match = BULLET_PATTERN.match(line.strip())
    if bullet_match:
        return ("bullet", bullet_match.group(1))
    
    numbered_match = NUMBERED_PATTERN.match(line.strip())
    if numbered_match:
        return ("numbered", numbered_match.group(1))
    
    return None


def add_list_item(doc, text: str, list_type: str) -> None:
    """Add a list item paragraph with appropriate style."""
    para = doc.add_paragraph(style='List Bullet' if list_type == "bullet" else 'List Number')
    # Apply inline formatting within the list item text
    tokens = tokenize_inline(text)
    for token_text, token_format in tokens:
        run = para.add_run(token_text)
        if token_format == "bold":
            run.bold = True
        elif token_format == "italic":
            run.italic = True

7. Blockquote Parser
7.1 Pattern
python

BLOCKQUOTE_PATTERN = re.compile(r'^>\s*(.+)$')


7.2 Implementation
python

def add_blockquote(doc, text: str) -> None:
    """Add indented italic paragraph for blockquotes."""
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Inches(0.5)
    run = para.add_run(text)
    run.italic = True
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

8. Horizontal Rule
8.1 Pattern
python

HR_PATTERN = re.compile(r'^-{3,}$')

8.2 Implementation

def add_horizontal_rule(doc) -> None:
    """Add thin horizontal line as paragraph border."""
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(6)
    para.paragraph_format.space_after = Pt(6)
    
    # Add bottom border to paragraph
    pPr = para._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '4')  # 0.5pt
    bottom.set(qn('w:color'), 'CCCCCC')
    bottom.set(qn('w:space'), '1')
    pBdr.append(bottom)
    pPr.append(pBdr)

9. Table Parser (Markdown Tables)
9.1 Pattern
python

TABLE_ROW_PATTERN = re.compile(r'^\|(.+)\|$')
TABLE_SEPARATOR_PATTERN = re.compile(r'^\|[\s\-\|:]+\|$')
9.2 Implementation
def parse_markdown_table(lines: list[str]) -> tuple[list[str], list[list[str]]] | None:
    """
    Parse markdown table lines into headers and rows.
    
    Input lines:
        | Header 1 | Header 2 | Header 3 |
        |----------|----------|----------|
        | Cell 1   | Cell 2   | Cell 3   |
        | Cell 4   | Cell 5   | Cell 6   |
    
    Returns:
        (["Header 1", "Header 2", "Header 3"], [["Cell 1", ...], ["Cell 4", ...]])
    """
    if len(lines) < 3:
        return None
    
    # First line = headers
    header_match = TABLE_ROW_PATTERN.match(lines[0].strip())
    if not header_match:
        return None
    
    # Second line = separator (skip)
    if not TABLE_SEPARATOR_PATTERN.match(lines[1].strip()):
        return None
    
    headers = [cell.strip() for cell in header_match.group(1).split('|')]
    
    rows = []
    for line in lines[2:]:
        row_match = TABLE_ROW_PATTERN.match(line.strip())
        if row_match:
            cells = [cell.strip() for cell in row_match.group(1).split('|')]
            rows.append(cells)
        else:
            break  # End of table
    
    return (headers, rows)


def add_markdown_table(doc, headers: list[str], rows: list[list[str]]) -> None:
    """
    Create a python-docx table from parsed markdown table data.
    Apply ESG_Table styling via docx_styler.style_table().
    """
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    
    # Set headers
    for i, header in enumerate(headers):
        table.rows[0].cells[i].text = header
    
    # Set body rows
    for row_idx, row_data in enumerate(rows):
        for col_idx, cell_text in enumerate(row_data):
            if col_idx < len(table.columns):
                table.rows[row_idx + 1].cells[col_idx].text = cell_text
    
    # Apply styling (from SPEC-STYLING)
    style_table(table)

10. Master Parser (Main Entry Point)

def parse_markdown_to_docx(doc, markdown_text: str) -> None:
    """
    Master parser: converts markdown-formatted text to python-docx elements.
    
    This is the MAIN entry point called by AssemblyDoc for each paragraph text.
    
    Strategy:
    1. Split text into lines
    2. Group consecutive lines of same type (e.g., list items, table rows)
    3. Process each group through appropriate sub-parser
    4. Apply inline formatting within each element
    
    Args:
        doc: python-docx Document object
        markdown_text: raw markdown string from SectionGen output
    """
    lines = markdown_text.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            i += 1
            continue
        
        # 1. Check heading
        heading = parse_heading(stripped)
        if heading:
            level, text = heading
            add_styled_heading(doc, text, level=level)
            i += 1
            continue
        
        # 2. Check horizontal rule
        if HR_PATTERN.match(stripped):
            add_horizontal_rule(doc)
            i += 1
            continue
        
        # 3. Check blockquote
        bq_match = BLOCKQUOTE_PATTERN.match(stripped)
        if bq_match:
            add_blockquote(doc, bq_match.group(1))
            i += 1
            continue
        
        # 4. Check table (look ahead for separator on next line)
        if TABLE_ROW_PATTERN.match(stripped) and i + 1 < len(lines):
            if TABLE_SEPARATOR_PATTERN.match(lines[i + 1].strip()):
                # Collect all table lines
                table_lines = []
                j = i
                while j < len(lines) and (TABLE_ROW_PATTERN.match(lines[j].strip()) or TABLE_SEPARATOR_PATTERN.match(lines[j].strip())):
                    table_lines.append(lines[j])
                    j += 1
                result = parse_markdown_table(table_lines)
                if result:
                    headers, rows = result
                    add_markdown_table(doc, headers, rows)
                i = j
                continue
        
        # 5. Check list items (group consecutive)
        list_result = parse_list_item(stripped)
        if list_result:
            list_type, item_text = list_result
            add_list_item(doc, item_text, list_type)
            i += 1
            continue
        
        # 6. Default: regular paragraph with inline formatting
        # Group consecutive non-special lines into one paragraph
        para_lines = []
        while i < len(lines):
            current = lines[i].strip()
            if not current:
                break  # Empty line = paragraph break
            if parse_heading(current) or HR_PATTERN.match(current) or parse_list_item(current) or BLOCKQUOTE_PATTERN.match(current):
                break  # Next line is special
            para_lines.append(current)
            i += 1
        
        if para_lines:
            full_text = ' '.join(para_lines)
            add_formatted_paragraph(doc, full_text)
            continue
        
        i += 1

11. Integration with AssemblyDoc
11.1 Before (current broken behavior)
python

# CURRENT: treats markdown as plain text
for para in section_json["paragraphs"]:
    doc.add_paragraph(para["text"])  # ← ## shows as literal text

11.2 After (with parser)
# FIXED: parse markdown into proper DOCX elements
for para in section_json["paragraphs"]:
    text = para["text"]
    para_type = para.get("paragraph_type", "narrative")
    
    # Check for special styled elements (insight/priority boxes)
    if text.startswith("⚠️ KEY INSIGHT:"):
        add_insight_box(doc, text.replace("⚠️ KEY INSIGHT:", "").strip())
    elif text.startswith("⚡ PRIORITY ACTIONS:"):
        actions = parse_priority_actions(text)
        add_priority_actions(doc, actions)
    elif text.startswith("📊 DIAGNOSTIC ANALYSIS:"):
        add_diagnostic_box(doc, text.replace("📊 DIAGNOSTIC ANALYSIS:", "").strip())
    else:
        # Apply markdown parsing
        parse_markdown_to_docx(doc, text)

12. Table of Contents Fix
12.1 Problem
TOC field code shows "Update this table" until user presses F9 in Word. This is a known python-docx limitation — NOT fixable programmatically.

12.2 Implementation

def add_table_of_contents(doc) -> None:
    """
    Insert TOC field code.
    User must press F9 or right-click → Update Field in Word.
    """
    paragraph = doc.add_paragraph()
    run = paragraph.add_run()
    
    # Begin field
    fldChar_begin = OxmlElement('w:fldChar')
    fldChar_begin.set(qn('w:fldCharType'), 'begin')
    run._r.append(fldChar_begin)
    
    # Field instruction
    run2 = paragraph.add_run()
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = ' TOC \\o "1-3" \\h \\z \\u '
    run2._r.append(instrText)
    
    # Separate
    run3 = paragraph.add_run()
    fldChar_sep = OxmlElement('w:fldChar')
    fldChar_sep.set(qn('w:fldCharType'), 'separate')
    run3._r.append(fldChar_sep)
    
    # Placeholder text
    run4 = paragraph.add_run("Table of Contents — Update this field (F9)")
    run4.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    run4.font.italic = True
    
    # End field
    run5 = paragraph.add_run()
    fldChar_end = OxmlElement('w:fldChar')
    fldChar_end.set(qn('w:fldCharType'), 'end')
    run5._r.append(fldChar_end)

13. Edge Cases & Error Handling
python

# Edge case handlers
EDGE_CASES = {
    "nested_formatting": "NOT SUPPORTED — e.g., **bold *and italic*** won't work. Keep simple.",
    "escaped_chars": "\\* and \\# are treated as literal chars (strip backslash)",
    "empty_heading": "# with no text → skip (don't add empty heading)",
    "single_pipe": "| at start but no closing | → treat as regular text",
    "unicode_bullets": "• (unicode bullet) treated same as - (markdown bullet)",
}

def sanitize_markdown(text: str) -> str:
    """
    Pre-process markdown text before parsing.
    
    Steps:
    1. Replace unicode bullets (•) with markdown bullets (-)
    2. Strip escaped characters: \\# → #, \\* → *
    3. Normalize line endings: \\r\\n → \\n
    4. Remove trailing whitespace per line
    5. Collapse 3+ consecutive newlines to 2
    """
    text = text.replace('\r\n', '\n')
    text = text.replace('•', '-')
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [line.rstrip() for line in text.split('\n')]
    return '\n'.join(lines)

14. Constraints
CON-MD-01: NO nested inline formatting (e.g., **bold *italic***)
CON-MD-02: Heading detection is LINE-START only (# must be first char after whitespace)
CON-MD-03: Tables require separator row (|---|---|) — without it, treated as text
CON-MD-04: Maximum heading level = 3 (#### and beyond are treated as plain text)
CON-MD-05: Code blocks (```) are NOT supported — only inline code
CON-MD-06: Images/links in markdown are NOT parsed — stripped to plain text
CON-MD-07: Parser MUST be idempotent — running twice on same text produces same output
CON-MD-08: Unicode (tCO₂e, °C, etc.) MUST be preserved through parsing

# Phase 2


# SPEC-EXEC-SUMMARY: Executive Summary 2-Tier System
# ESG Reporting System — Kiro IDE Specification
# VERSION: 1.0.0 | DATE: 12/06/2026

---

## 1. Overview

This spec defines the 2-tier Executive Summary section for the ESG report.
The summary section is the LAST section generated but placed FIRST in the final document (after cover page + TOC).

**Problem**: Current summary is single-tier — just data narrative + table. No strategic framing.
**Solution**: Implement Tier 1 (C-Level Brief) → PAGE BREAK → Tier 2 (Detailed Performance).

---

## 2. Architecture

SectionGen Lambda receives section_id = "summary" → Detects summary → uses EXEC_SUMMARY_TIER1_TEMPLATE (not standard template) → Receives ALL other section metrics as context (aggregated from prior sections) → Generates Tier 1 + Tier 2 in single response (separated by marker) → AssemblyDoc places summary FIRST (after cover + TOC), despite being generated last


---

## 3. Tier 1: C-Level Strategic Brief

### 3.1 Purpose

One-page strategic overview for Board/C-Suite consumption.
Must be readable in <2 minutes. No technical jargon.

### 3.2 Components (in order)

```python
TIER1_COMPONENTS = [
    "strategic_headline",      # 1 sentence: overall ESG position
    "esg_scorecard",           # Traffic light matrix (E/S/G)
    "key_numbers_strip",       # 4 headline KPIs
    "board_action_required",   # 2-3 decisions needed from Board
    "risk_opportunity_matrix", # 2×2 matrix: risk vs opportunity
    "outlook_statement",       # Forward-looking qualifier + 1 paragraph
]
3.3 ESG Scorecard
python

ESG_SCORECARD_CONFIG = {
    "format": "table",  # 3-column table rendered in DOCX
    "columns": ["Dimension", "Rating", "Key Driver"],
    "dimensions": [
        {
            "name": "Environmental",
            "rating_logic": {
                "green": "yoy_change_pct < -3.0",       # Emissions decreasing >3%
                "amber": "-3.0 <= yoy_change_pct <= 0",  # Flat or slight decrease
                "red": "yoy_change_pct > 0",             # Emissions increasing
            },
            "driver_source": "scope3_pcaf section insight",
        },
        {
            "name": "Social",
            "rating_logic": {
                "green": "fte_female_pct >= 40 AND training_hours_avg >= 30",
                "amber": "fte_female_pct >= 30 OR training_hours_avg >= 20",
                "red": "fte_female_pct < 30 AND training_hours_avg < 20",
            },
            "driver_source": "social section metrics",
        },
        {
            "name": "Governance",
            "rating_logic": {
                "green": "has_esg_committee AND has_climate_policy AND has_targets",
                "amber": "has_esg_committee OR has_climate_policy",
                "red": "none of the above",
            },
            "driver_source": "governance section gap analysis",
        },
    ],
    "rating_symbols": {
        "green": "🟢",
        "amber": "🟡",
        "red": "🔴",
    },
}

3.4 Key Numbers Strip (KPI Highlights)
python

TIER1_KPI_STRIP = [
    {
        "label": "Total GHG Emissions",
        "source_key": "total_tco2e",
        "format": "{value:,.0f} tCO₂e",
        "yoy_key": "yoy_change_pct",
    },
    {
        "label": "Emission Intensity",
        "source_key": "intensity_tco2e_per_billion_idr",
        "format": "{value:.1f} tCO₂e/IDR Bn",
        "yoy_key": "intensity_yoy_pct",
    },
    {
        "label": "Portfolio Coverage",
        "source_key": "data_quality_coverage_pct",
        "format": "{value:.0f}%",
        "yoy_key": None,
    },
    {
        "label": "PCAF Data Quality",
        "source_key": "portfolio_weighted_pcaf_score",
        "format": "{value:.2f}/5",
        "yoy_key": None,
    },
]

3.5 Board Action Required
python

BOARD_ACTION_CONFIG = {
    "max_items": 3,
    "format": "numbered_list",
    "required_elements_per_item": [
        "action_verb",       # e.g., "Approve", "Mandate", "Allocate"
        "specific_ask",      # What exactly needs to happen
        "rationale",         # Why (1 sentence, data-backed)
        "timeline",          # By when
    ],
    "example": "1. **Approve** SBTi commitment letter submission — current peer gap (BRI committed 2023, BCA 2024) creates reputational risk. Timeline: Q3 2025.",
    "generation_instruction": "Derive from PRIORITY ACTIONS across all sections. Select top 3 by strategic impact.",
}

3.6 Risk & Opportunity Matrix
python

RISK_OPP_MATRIX_CONFIG = {
    "format": "2x2_table",
    "headers": ["", "Short-term (1-2 years)", "Medium-term (3-5 years)"],
    "rows": ["Risks", "Opportunities"],
    "cell_content": "1-2 bullet points per cell",
    "generation_instruction": """
        Risks: Derive from diagnostic analyses + peer gaps + regulatory exposure.
        Opportunities: Derive from positive trends + market positioning + capability gaps that can be closed.
        Short-term: Actionable within current budget cycle.
        Medium-term: Requires strategic investment or structural change.
    """,
    "styling": {
        "risk_color": "#FFF3E0",      # Light orange background
        "opportunity_color": "#E8F5E9", # Light green background
        "header_color": "#1B3A6B",
    },
}

3.7 Outlook Statement
python

OUTLOOK_CONFIG = {
    "qualifier_prefix": "Forward-looking statement: ",
    "qualifier_style": "italic",
    "max_sentences": 4,
    "must_include": [
        "trajectory_direction",    # Improving/declining/stable
        "key_dependency",          # What success depends on
        "peer_context",            # Where institution stands vs peers
    ],
    "prohibited": [
        "specific_future_numbers",  # No "we will reduce by X%"
        "guaranteed_outcomes",      # No "we will achieve"
        "unsubstantiated_claims",   # Must be derivable from data
    ],
}

4. Tier 2: Detailed Performance Summary
4.1 Purpose
Comprehensive data summary for technical stakeholders (Sustainability team, Risk, Compliance). Contains all key metrics from all sections in consolidated view.

4.2 Components (in order)
python

TIER2_COMPONENTS = [
    "environmental_summary_table",   # All E metrics in one table
    "social_summary_table",          # All S metrics in one table
    "governance_maturity_table",     # G assessment summary
    "framework_compliance_matrix",   # Which frameworks covered, gaps
    "data_quality_assessment",       # PCAF scores, coverage, confidence
    "yoy_trend_summary",            # All YoY changes in one view
]

4.3 Environmental Summary Table
python

ENV_SUMMARY_TABLE = {
    "title": "Environmental Performance Summary",
    "columns": ["Metric", "FY2023", "FY2024", "YoY Change", "Peer Benchmark"],
    "rows": [
        {"metric": "Total GHG Emissions (tCO₂e)", "keys": ["total_tco2e_prior", "total_tco2e", "yoy_change_pct", "peer_avg_total"]},
        {"metric": "Scope 1 (tCO₂e)", "keys": ["scope1_prior", "scope1_tco2e", "scope1_yoy_pct", "peer_avg_scope1"]},
        {"metric": "Scope 2 — Location (tCO₂e)", "keys": ["scope2_loc_prior", "scope2_location_tco2e", "scope2_yoy_pct", "peer_avg_scope2"]},
        {"metric": "Scope 3 — Financed Gross (tCO₂e)", "keys": ["scope3_gross_prior", "scope3_financed_gross_tco2e", "scope3_yoy_pct", "peer_avg_scope3"]},
        {"metric": "Scope 3 — Financed Weighted (tCO₂e)", "keys": ["scope3_weighted_prior", "scope3_financed_weighted_tco2e", None, None]},
        {"metric": "Intensity (tCO₂e/IDR Bn)", "keys": ["intensity_prior", "intensity_tco2e_per_billion_idr", "intensity_yoy_pct", "peer_avg_intensity"]},
        {"metric": "PCAF Score (weighted)", "keys": [None, "portfolio_weighted_pcaf_score", None, "peer_avg_pcaf"]},
    ],
}

4.4 Social Summary Table
python

SOCIAL_SUMMARY_TABLE = {
    "title": "Social Performance Summary",
    "columns": ["Metric", "FY2023", "FY2024", "YoY Change", "Peer Benchmark"],
    "rows": [
        {"metric": "Total FTE", "keys": ["fte_total_prior", "fte_total", "fte_yoy_pct", None]},
        {"metric": "Female Workforce (%)", "keys": ["fte_female_pct_prior", "fte_female_pct", None, "peer_avg_female_pct"]},
        {"metric": "Female in Management (%)", "keys": ["fte_mgmt_female_prior", "fte_management_female_pct", None, "peer_avg_mgmt_female"]},
        {"metric": "Training Hours (avg/employee)", "keys": ["training_hours_prior", "training_hours_avg", "training_yoy_pct", "peer_avg_training"]},
        {"metric": "Voluntary Turnover (%)", "keys": ["turnover_prior", "voluntary_turnover_pct", None, "peer_avg_turnover"]},
        {"metric": "Lost Time Injury Rate", "keys": ["ltir_prior", "lost_time_injury_rate", None, "peer_avg_ltir"]},
    ],
}

4.5 Framework Compliance Matrix
python

FRAMEWORK_COMPLIANCE_MATRIX = {
    "title": "Framework Compliance Status",
    "columns": ["Requirement", "GRI 305", "IFRS S2", "CSRD E1", "OJK PSPK"],
    "cell_values": ["✅ Disclosed", "⚠️ Partial", "❌ Gap", "N/A"],
    "rows": [
        "Scope 1 & 2 Emissions",
        "Scope 3 / Financed Emissions",
        "Emission Intensity",
        "Reduction Targets",
        "Transition Plan",
        "Governance Structure",
        "Risk Management Process",
        "Scenario Analysis",
        "Social Metrics",
    ],
    "generation_instruction": "Assess based on data availability and section content. If data exists → ✅. If partial/estimated → ⚠️. If no data/not addressed → ❌.",
}

5. Section Generation Template
5.1 Prompt Template for SectionGen Lambda
python

EXEC_SUMMARY_TEMPLATE = """
You are generating the Executive Summary for an ESG Sustainability Report.
This section has TWO tiers separated by the marker: <<<TIER_BREAK>>>

== TIER 1: C-LEVEL STRATEGIC BRIEF ==
Target audience: Board of Directors, C-Suite executives.
Reading time: <2 minutes.
Tone: Strategic, decisive, action-oriented.

Generate the following components IN ORDER:

1. STRATEGIC HEADLINE (1 sentence)
   - Summarize the institution's overall ESG position in FY{reporting_year}
   - Include the most significant metric change

2. ESG SCORECARD (table format)
   | Dimension | Rating | Key Driver |
   Use 🟢 (strong/improving), 🟡 (adequate/stable), 🔴 (concern/declining)
   Rating criteria:
   - Environmental: Based on total emission YoY trend
   - Social: Based on diversity + training metrics
   - Governance: Based on structure maturity vs framework requirements

3. KEY NUMBERS (format as key_metrics JSON for KPI box rendering)
   Select 4 most impactful metrics from the data provided.

4. ⚡ BOARD ACTIONS REQUIRED:
   1. [Action verb] specific ask — rationale (timeline)
   2. [Action verb] specific ask — rationale (timeline)
   3. [Action verb] specific ask — rationale (timeline)

5. RISK & OPPORTUNITY MATRIX (table format)
   |  | Short-term (1-2 years) | Medium-term (3-5 years) |
   | Risks | ... | ... |
   | Opportunities | ... | ... |

6. OUTLOOK (with forward-looking qualifier prefix in italic)

<<<TIER_BREAK>>>

== TIER 2: DETAILED PERFORMANCE SUMMARY ==
Target audience: Sustainability team, Risk, Compliance, Auditors.
Tone: Technical, comprehensive, data-rich.

Generate the following tables:
1. Environmental Performance Summary (all emission metrics, YoY, peer benchmark)
2. Social Performance Summary (workforce metrics, YoY, peer benchmark)
3. Governance Maturity Assessment (gap analysis summary)
4. Framework Compliance Matrix (GRI/IFRS/CSRD/OJK coverage status)
5. Data Quality Assessment (PCAF scores, coverage, confidence gap)

5.2 Data Injection
The summary section receives ALL metrics from ALL other sections:

python

def _prepare_summary_context(all_section_results: list[dict]) -> dict:
    """
    Aggregate metrics from all completed sections for summary generation.
    Called by AthenaQuery Lambda when section_id == "summary".
    """
    aggregated = {}
    for section in all_section_results:
        metrics = section.get("metrics", {})
        aggregated.update(metrics)
    
    # Add computed fields
    aggregated["total_sections_generated"] = len(all_section_results)
    aggregated["sections_with_insights"] = sum(
        1 for s in all_section_results if "KEY INSIGHT" in str(s.get("paragraphs", []))
    )
    
    return aggregated

6. Assembly Placement Logic
python

SECTION_PLACEMENT_ORDER = [
    "cover_page",       # Index 0 — always first
    "table_of_contents", # Index 1
    "summary",          # Index 2 — Executive Summary (generated LAST, placed FIRST after TOC)
    "scope1",           # Index 3
    "scope2",           # Index 4
    "scope3_pcaf",      # Index 5
    "intensity",        # Index 6
    "reduction",        # Index 7
    "social",           # Index 8
    "governance",       # Index 9
    "targets",          # Index 10
]

6.1 Tier Break Handling in AssemblyDoc
python

def assemble_summary_section(doc, summary_json):
    """
    Special handler for summary section — splits into Tier 1 and Tier 2.
    """
    paragraphs = summary_json["paragraphs"]
    
    # Find tier break marker
    tier_break_idx = None
    for i, para in enumerate(paragraphs):
        if "<<<TIER_BREAK>>>" in para.get("text", ""):
            tier_break_idx = i
            break
    
    if tier_break_idx is None:
        # Fallback: treat entire section as single tier
        _assemble_standard_section(doc, summary_json)
        return
    
    # === TIER 1 ===
    doc.add_page_break()
    add_styled_heading(doc, "Executive Summary", level=1)
    add_styled_heading(doc, "Strategic Brief", level=2)
    
    # KPI highlights for Tier 1
    if summary_json.get("key_metrics"):
        add_kpi_highlights(doc, summary_json["key_metrics"])
    
    # Process Tier 1 paragraphs
    for para in paragraphs[:tier_break_idx]:
        text = para["text"]
        if text.startswith("⚡"):
            actions = parse_priority_actions(text)
            add_priority_actions(doc, actions)
        else:
            parse_markdown_to_docx(doc, text)
    
    # === PAGE BREAK between tiers ===
    doc.add_page_break()
    
    # === TIER 2 ===
    add_styled_heading(doc, "Detailed Performance Summary", level=2)
    
    # Process Tier 2 paragraphs
    for para in paragraphs[tier_break_idx + 1:]:
        text = para["text"]
        parse_markdown_to_docx(doc, text)
    
    # Process Tier 2 tables
    for table_data in summary_json.get("tables", []):
        tbl = create_table(doc, table_data["headers"], table_data["rows"])

7. Constraints
CON-EXEC-01: Summary is generated LAST (needs all other section data) but placed FIRST in document
CON-EXEC-02: Tier 1 MUST fit on 1 page (max ~500 words narrative + tables)
CON-EXEC-03: ESG Scorecard ratings MUST be derivable from actual metrics (no subjective assessment)
CON-EXEC-04: Board Actions MUST trace back to Priority Actions in detail sections
CON-EXEC-05: <<<TIER_BREAK>>> marker MUST be on its own line (paragraph)
CON-EXEC-06: Forward-looking statements MUST have italic qualifier prefix
CON-EXEC-07: Peer benchmarks only from KB retrieval — if not found, show "N/A" (never fabricate)

---

```markdown

# SPEC-INSIGHT-LAYER: Advisory Insight Injection System
# ESG Reporting System — Kiro IDE Specification
# VERSION: 1.0.0 | DATE: 12/06/2026

---

## 1. Overview

This spec defines the Insight Layer — a unified instruction file that is programmatically
injected into ALL section generation prompts to produce advisory content (KEY INSIGHT boxes,
Diagnostic Analysis, Priority Actions) without editing individual templates.

**Architecture Decision**: 1 file (`INSIGHT_LAYER_INSTRUCTIONS.txt`) auto-injected to ALL templates.
**Injection Point**: AFTER template + data (appended as "Output Format Requirements").
**Exception**: Executive Summary gets its own file (`EXEC_SUMMARY_TIER1_INSTRUCTIONS.txt`).

---

## 2. Injection Mechanism

### 2.1 SectionGen Lambda Integration

```python
def _build_final_prompt(section_id: str, template: str, metrics_json: str, kb_context: str) -> str:
    """
    Construct the final prompt for Bedrock InvokeModel.
    
    Prompt Architecture:
        FINAL_PROMPT = BASE_PROMPT + FRAMEWORK_OVERLAY + SECTION_TEMPLATE + DATA + KB_CONTEXT + INSIGHT_LAYER
    """
    # Load insight layer instructions
    if section_id == "summary":
        insight_instructions = _load_s3_text("s3://esg-templates/EXEC_SUMMARY_TIER1_INSTRUCTIONS.txt")
    else:
        insight_instructions = _load_s3_text("s3://esg-templates/INSIGHT_LAYER_INSTRUCTIONS.txt")
    
    final_prompt = f"""{template}

== DATA (Source of Truth — use ONLY these numbers) ==
{metrics_json}

== KNOWLEDGE BASE CONTEXT (Peer Benchmarks & Framework Guidance) ==
{kb_context}

== OUTPUT FORMAT REQUIREMENTS ==
{insight_instructions}
"""
    return final_prompt
2.2 Injection Order Rationale
1. Template (framework-specific structure)     ← Defines WHAT to write
2. Data (Athena metrics JSON)                  ← Defines WITH WHAT numbers
3. KB Context (RAG retrieval)                  ← Provides peer/benchmark context
4. Insight Layer (this spec)                   ← Defines HOW to present insights
Why LAST? Prevents insight instructions from overriding framework-specific structure. The model follows template structure first, then applies insight formatting on top.

3. INSIGHT_LAYER_INSTRUCTIONS.txt Content
text

== ADVISORY INSIGHT REQUIREMENTS ==

You MUST include the following advisory elements in your output.
These are OUTPUT FORMAT requirements — they do NOT change the section structure.

---

### 1. ⚠️ KEY INSIGHT (Required: exactly 1 per section)

Format:
⚠️ KEY INSIGHT: [Insight text — 2-3 sentences maximum]

Rules:
- Place AFTER the main data narrative paragraph, BEFORE tables
- Must be data-driven (reference specific numbers from the metrics provided)
- Must include peer comparison OR framework gap OR trend implication
- Must be actionable (imply what should be done)
- Tone: Direct, analytical, slightly urgent
- Do NOT use vague language ("should consider", "may want to")
- DO use specific language ("requires immediate attention", "creates regulatory exposure")

Examples:
⚠️ KEY INSIGHT: Scope 1 emissions increased +2.36% YoY while peers BRI (-3.2%) and DBS (-12%) achieved reductions. The diesel dependency (64.7% of Scope 1) represents the primary lever — a 20% diesel reduction would eliminate the entire YoY increase.

⚠️ KEY INSIGHT: The 30.5% gap between gross (21.98M tCO₂e) and confidence-weighted (15.27M tCO₂e) financed emissions indicates significant data quality uncertainty. Improving PCAF score from 3.36 to 2.5 would narrow this gap to ~15% and strengthen regulatory credibility.

---

### 2. 📊 DIAGNOSTIC ANALYSIS (Required: exactly 1 per section)

Format:
📊 DIAGNOSTIC ANALYSIS: [Analysis text — 3-5 sentences]

Rules:
- Place AFTER the KEY INSIGHT
- Provide root cause analysis or decomposition of the key finding
- Include quantified breakdown where possible
- Reference specific data points from metrics
- Connect cause → effect → implication chain
- If peer data available from KB context, include comparative positioning

Example:
📊 DIAGNOSTIC ANALYSIS: Scope 2 emissions stability (+0.03% YoY) masks underlying dynamics. Grid electricity consumption increased 2.1% (driven by 3 new branch offices) but was offset by PLN grid factor improvement. Zero renewable energy procurement means the institution has no control over Scope 2 trajectory — it is entirely dependent on PLN's generation mix. Peers DBS (62% renewable) and BCA (solar PPA pilot) have decoupled from grid dependency.

---

### 3. ⚡ PRIORITY ACTIONS (Required: exactly 1 block per section, 2-3 items)

Format:
⚡ PRIORITY ACTIONS:

4. Section-Specific Insight Guidance
While the insight layer is universal, each section has natural focus areas:

python

SECTION_INSIGHT_FOCUS = {
    "scope1": {
        "insight_focus": "Source breakdown dominance, fuel dependency, facility concentration",
        "diagnostic_focus": "Top emitters, fuel mix, YoY driver decomposition",
        "action_focus": "Fuel switching, efficiency, monitoring",
    },
    "scope2": {
        "insight_focus": "Grid dependency, renewable gap, location vs market method gap",
        "diagnostic_focus": "Consumption trend vs grid factor trend, peer renewable comparison",
        "action_focus": "Renewable procurement, PPA, REC strategy",
    },
    "scope3_pcaf": {
        "insight_focus": "Sector concentration risk, data quality gap, gross vs weighted gap",
        "diagnostic_focus": "Top 3 sector contribution, PCAF score distribution, portfolio coverage",
        "action_focus": "Client engagement, data improvement, sector policy",
    },
    "intensity": {
        "insight_focus": "Decoupling trend (emissions vs revenue), peer intensity comparison",
        "diagnostic_focus": "Revenue growth vs emission growth decomposition",
        "action_focus": "Intensity target setting, SBTi alignment",
    },
    "reduction": {
        "insight_focus": "Net change direction, which scope drove the change",
        "diagnostic_focus": "Scope-by-scope waterfall, offsetting effects",
        "action_focus": "Reduction target formalization, pathway planning",
    },
    "social": {
        "insight_focus": "Gender gap at management level, training investment trend",
        "diagnostic_focus": "Pipeline analysis (total vs management female %), turnover drivers",
        "action_focus": "Diversity targets, training program, retention",
    },
    "governance": {
        "insight_focus": "Framework compliance gaps, committee structure maturity",
        "diagnostic_focus": "Gap analysis vs IFRS S2 para 6 requirements, peer governance comparison",
        "action_focus": "Committee formation, policy development, KPI integration",
    },
    "targets": {
        "insight_focus": "Target ambition vs science-based pathway, SBTi status",
        "diagnostic_focus": "Current trajectory vs required trajectory, feasibility assessment",
        "action_focus": "SBTi commitment, interim milestones, monitoring framework",
    },
}

5. Knowledge Base Query Strategy for Insights
5.1 Benchmark Retrieval
python

def _query_knowledge_base_for_insights(section_id: str, metrics: dict) -> str:
    """
    Query Bedrock KB with section-specific benchmark questions.
    Filter: metadata.framework == "BENCHMARK"
    """
    BENCHMARK_QUERIES = {
        "scope1": f"What are peer Indonesian bank Scope 1 emissions and reduction rates? BRI BCA DBS Mandiri diesel natural gas",
        "scope2": f"What renewable energy procurement percentage do peer banks achieve? DBS BCA BRI solar PPA REC",
        "scope3_pcaf": f"What PCAF data quality scores do peer Indonesian banks report? BRI BCA Mandiri sector coverage",
        "intensity": f"What emission intensity per revenue do peer banks report? tCO2e per billion IDR benchmark",
        "reduction": f"What YoY emission reduction rates have peer banks achieved? BRI DBS BCA targets",
        "social": f"What female representation in management do peer Indonesian banks report? BRI Mandiri BCA diversity training hours",
        "governance": f"What ESG governance structures do peer banks have? committee board oversight climate policy SBTi",
        "targets": f"What science-based targets have peer Indonesian banks committed to? SBTi net zero 2050 pathway",
    }
    
    query = BENCHMARK_QUERIES.get(section_id, "ESG benchmark Indonesian banking sector")
    
    # Call Bedrock KB with filter
    response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 5,
                "filter": {
                    "equals": {"key": "framework", "value": "BENCHMARK"}
                }
            }
        }
    )
    
    # Concatenate retrieved passages (cap at RAG_TOKEN_CAP)
    passages = [r["content"]["text"] for r in response["retrievalResults"]]
    return "\n---\n".join(passages)[:RAG_TOKEN_CAP]

5.2 RAG Token Budget
python

RAG_TOKEN_CAP = 1500  # Increased from 500-700 (only using ~7% of 200K context window)

6. Output Validation Rules
The Validation Lambda (Lambda #4) checks insight layer compliance:

python

INSIGHT_VALIDATION_RULES = {
    "VAL-INS-01": {
        "check": "Section contains exactly 1 '⚠️ KEY INSIGHT:' marker",
        "severity": "WARNING",  # Not blocking — section still valid without
        "retry": True,
    },
    "VAL-INS-02": {
        "check": "Section contains exactly 1 '📊 DIAGNOSTIC ANALYSIS:' marker",
        "severity": "WARNING",
        "retry": True,
    },
    "VAL-INS-03": {
        "check": "Section contains exactly 1 '⚡ PRIORITY ACTIONS:' block",
        "severity": "WARNING",
        "retry": True,
    },
    "VAL-INS-04": {
        "check": "All numbers in insight text exist in source metrics",
        "severity": "ERROR",  # Blocking — hallucinated numbers
        "retry": True,
    },
    "VAL-INS-05": {
        "check": "Priority actions have [Urgency] tag and Timeline",
        "severity": "WARNING",
        "retry": True,
    },
    "VAL-INS-06": {
        "check": "Peer names cited exist in KB context (not fabricated)",
        "severity": "ERROR",
        "retry": True,
    },
}

7. Constraints
CON-INS-01: Insight layer is APPENDED (never prepended) to prevent structure override
CON-INS-02: ONE file for all sections (except summary) — no per-section instruction files
CON-INS-03: Insight content must be DERIVABLE from provided data + KB context
CON-INS-04: If KB returns no peer data, insight must still work (omit comparison, focus on internal trend)
CON-INS-05: Maximum 1 of each advisory element per section (no duplicate insight boxes)
CON-INS-06: Advisory elements are WARNING-level validation (section passes even without them)
CON-INS-07: Temperature = 0 for deterministic output (no creative variation between runs)

---

```markdown

# SPEC-ASSEMBLY-INTEGRATION: AssemblyDoc Handler Integration
# ESG Reporting System — Kiro IDE Specification
# VERSION: 1.0.0 | DATE: 12/06/2026

---

## 1. Overview

This spec defines the complete integration of ALL Phase 1 + Phase 2 specs into the
AssemblyDoc Lambda handler (`esg-assembly-doc`). This is the MASTER assembly loop
that ties together: Charts, Styling, Markdown Parser, Executive Summary, and Insight Layer.

**Lambda**: `esg-assembly-doc`
**Runtime**: Python 3.11, 2048MB, 300s timeout
**Layers**: `esg-python-docx:2`, `esg-matplotlib-layer:1`
**Input**: S3 paths to all validated section JSONs
**Output**: Final `.docx` file in `s3://esg-output-reports-061039769766/reports/year={year}/`

---

## 2. Handler Entry Point

```python
import json
import logging
import io
import boto3
from datetime import datetime

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# Local imports from Lambda layer
from docx_styler import (
    add_cover_page,
    add_table_of_contents,
    add_styled_heading,
    add_kpi_highlights,
    add_insight_box,
    add_diagnostic_box,
    add_priority_actions,
    add_styled_paragraph,
    add_footnote_block,
    add_framework_refs,
    style_table,
    add_table_caption,
    add_horizontal_rule,
    set_page_setup,
    add_header_footer,
    should_insert_page_break,
    parse_priority_actions,
    HEADING_STYLES,
    BODY_STYLES,
    PAGE_CONFIG,
)
from markdown_parser import (
    parse_markdown_to_docx,
    sanitize_markdown,
)
from chart_renderer import (
    add_chart,
    CHART_REGISTRY,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')


def handler(event, context):
    """
    AssemblyDoc Lambda handler.
    
    Input event:
    {
        "report_id": "uuid",
        "reporting_year": 2024,
        "institution_name": "GENERIC_FI_001",
        "framework": "MULTI_FRAMEWORK",
        "section_paths": [
            "s3://esg-sections-bucket/sections/scope1_validated.json",
            "s3://esg-sections-bucket/sections/scope2_validated.json",
            ...
        ],
        "output_bucket": "esg-output-reports-061039769766",
        "output_key": "reports/year=2024/ESG_Report_MULTI_FRAMEWORK_2024_{timestamp}.docx"
    }
    """
    try:
        report_id = event["report_id"]
        reporting_year = event["reporting_year"]
        institution_name = event["institution_name"]
        framework = event["framework"]
        section_paths = event["section_paths"]
        output_bucket = event["output_bucket"]
        output_key = event["output_key"]
        
        logger.info(f"Assembly started: {report_id}, {len(section_paths)} sections")
        
        # 1. Load all section JSONs from S3
        sections = _load_sections(section_paths)
        
        # 2. Sort sections into correct placement order
        ordered_sections = _order_sections(sections, framework)
        
        # 3. Create document
        doc = Document()
        
        # 4. Apply page setup
        set_page_setup(doc, PAGE_CONFIG)
        
        # 5. Add cover page
        add_cover_page(doc, {
            "institution_name": institution_name,
            "reporting_year": reporting_year,
            "framework": framework,
            "generation_date": datetime.utcnow().strftime("%d/%m/%Y"),
        })
        
        # 6. Add TOC
        add_table_of_contents(doc)
        doc.add_page_break()
        
        # 7. Add header/footer
        add_header_footer(doc, {
            "institution_name": institution_name,
            "reporting_year": reporting_year,
            "framework": framework,
        })
        
        # 8. Assemble sections
        figure_counter = 0
        table_counter = 0
        
        for idx, section_json in enumerate(ordered_sections):
            section_id = section_json.get("section_id", f"section_{idx}")
            logger.info(f"Assembling section {idx}: {section_id}")
            
            if section_id.startswith("summary"):
                # Special handler for 2-tier executive summary
                figure_counter, table_counter = _assemble_summary(
                    doc, section_json, figure_counter, table_counter
                )
            else:
                # Standard section assembly
                figure_counter, table_counter = _assemble_section(
                    doc, section_json, idx, figure_counter, table_counter
                )
        
        # 9. Save to buffer
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        # 10. Upload to S3
        s3.put_object(
            Bucket=output_bucket,
            Key=output_key,
            Body=buffer.getvalue(),
            ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            Metadata={
                'report_id': report_id,
                'framework': framework,
                'reporting_year': str(reporting_year),
                'sections_count': str(len(ordered_sections)),
                'generated_at': datetime.utcnow().isoformat(),
            }
        )
        
        file_size_kb = len(buffer.getvalue()) / 1024
        logger.info(f"Assembly complete: {output_key} ({file_size_kb:.1f} KB)")
        
        return {
            "statusCode": 200,
            "report_id": report_id,
            "output_path": f"s3://{output_bucket}/{output_key}",
            "file_size_kb": round(file_size_kb, 1),
            "sections_assembled": len(ordered_sections),
        }
        
    except Exception as e:
        logger.error(f"Assembly failed: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "error": str(e),
            "report_id": event.get("report_id", "unknown"),
        }
3. Section Loading & Ordering
python

SECTION_ORDER = {
    "MULTI_FRAMEWORK": ["summary", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social", "governance", "targets"],
    "GRI_305": ["summary", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social", "governance", "targets"],
    "IFRS_S2": ["summary", "governance", "scope1", "scope2", "scope3_pcaf", "intensity", "targets", "reduction", "social"],
    "CSRD_ESRS_E1": ["summary", "targets", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social", "governance"],
    "OJK_PSPK": ["summary", "governance", "scope1", "scope2", "scope3_pcaf", "intensity", "reduction", "social", "targets"],
}


def _load_sections(section_paths: list[str]) -> list[dict]:
    """Load all section JSONs from S3."""
    sections = []
    for path in section_paths:
        bucket, key = _parse_s3_path(path)
        response = s3.get_object(Bucket=bucket, Key=key)
        section_json = json.loads(response['Body'].read().decode('utf-8'))
        sections.append(section_json)
    return sections


def _order_sections(sections: list[dict], framework: str) -> list[dict]:
    """
    Reorder sections according to framework-specific placement.
    Summary always first (after cover/TOC).
    """
    order = SECTION_ORDER.get(framework, SECTION_ORDER["MULTI_FRAMEWORK"])
    
    # Create lookup by section_id
    section_map = {}
    for s in sections:
        # Extract base section type from section_id
        # e.g., "GRI_305_scope1_2024" → "scope1"
        sid = s.get("section_id", "")
        for section_type in order:
            if section_type in sid:
                section_map[section_type] = s
                break
    
    # Return in order (skip missing sections)
    ordered = []
    for section_type in order:
        if section_type in section_map:
            ordered.append(section_map[section_type])
        else:
            logger.warning(f"Section '{section_type}' not found in results — skipping")
    
    return ordered

4. Standard Section Assembly Loop
python

def _assemble_section(doc, section_json: dict, section_index: int, 
                      figure_counter: int, table_counter: int) -> tuple[int, int]:
    """
    Assemble a standard (non-summary) section.
    
    Flow:
    1. Page break (conditional)
    2. Section heading (H1)
    3. KPI highlights (if present)
    4. Paragraphs (with insight/action detection + markdown parsing)
    5. Chart (if chart_data present)
    6. Tables (styled)
    7. Footnotes
    8. Framework references
    
    Returns updated (figure_counter, table_counter).
    """
    # 1. Page break
    if should_insert_page_break(section_index):
        doc.add_page_break()
    
    # 2. Section heading
    title = section_json.get("title", f"Section {section_index}")
    add_styled_heading(doc, title, level=1)
    
    # 3. KPI highlights
    key_metrics = section_json.get("key_metrics")
    if key_metrics:
        add_kpi_highlights(doc, key_metrics)
    
    # 4. Paragraphs
    paragraphs = section_json.get("paragraphs", [])
    for para in paragraphs:
        text = para.get("text", "")
        if not text.strip():
            continue
        
        # Sanitize markdown
        text = sanitize_markdown(text)
        
        # Detect special advisory elements
        if text.startswith("⚠️ KEY INSIGHT:"):
            insight_text = text.replace("⚠️ KEY INSIGHT:", "").strip()
            add_insight_box(doc, insight_text)
        
        elif text.startswith("📊 DIAGNOSTIC ANALYSIS:"):
            diag_text = text.replace("📊 DIAGNOSTIC ANALYSIS:", "").strip()
            add_diagnostic_box(doc, diag_text)
        
        elif text.startswith("⚡ PRIORITY ACTIONS:"):

5. Summary Section Assembly (2-Tier)
python

def _assemble_summary(doc, section_json: dict, 
                      figure_counter: int, table_counter: int) -> tuple[int, int]:
    """
    Special assembly for Executive Summary with 2-tier structure.
    See SPEC-EXEC-SUMMARY for full design.
    """
    paragraphs = section_json.get("paragraphs", [])
    
    # Find tier break marker
    tier_break_idx = None
    for i, para in enumerate(paragraphs):
        if "<<<TIER_BREAK>>>" in para.get("text", ""):
            tier_break_idx = i
            break
    
    # === TIER 1: C-Level Strategic Brief ===
    doc.add_page_break()
    add_styled_heading(doc, "Executive Summary", level=1)
    add_styled_heading(doc, "Strategic Brief", level=2)
    
    # KPI highlights
    key_metrics = section_json.get("key_metrics")
    if key_metrics:
        add_kpi_highlights(doc, key_metrics)
    
    # Tier 1 paragraphs
    tier1_end = tier_break_idx if tier_break_idx else len(paragraphs)
    for para in paragraphs[:tier1_end]:
        text = sanitize_markdown(para.get("text", ""))
        if not text.strip():
            continue
        
        if text.startswith("⚡"):
            actions = parse_priority_actions(text)
            add_priority_actions(doc, actions)
        elif text.startswith("⚠️ KEY INSIGHT:"):
            add_insight_box(doc, text.replace("⚠️ KEY INSIGHT:", "").strip())
        else:
            parse_markdown_to_docx(doc, text)
    
    # Tier 1 tables (scorecard, risk matrix)
    tier1_tables = [t for t in section_json.get("tables", []) if t.get("tier") == 1]
    for table_data in tier1_tables:
        table_counter += 1
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        if headers and rows:
            tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
            for i, header in enumerate(headers):
                tbl.rows[0].cells[i].text = header

6. Section JSON Schema (Expected Input)
python

SECTION_JSON_SCHEMA = {
    "section_id": "str — e.g., 'GRI_305_scope1_2024' or 'MULTI_scope3_pcaf_2024'",
    "title": "str — Section display title",
    "key_metrics": [
        {"label": "str", "value": "str", "unit": "str"}  # For KPI box (max 4)
    ],
    "paragraphs": [
        {
            "text": "str — Markdown-formatted narrative text",
            "paragraph_type": "str — 'narrative'|'methodology'|'forward_looking'|'insight'|'action'",
        }
    ],
    "tables": [
        {
            "headers": ["str"],
            "rows": [["str"]],
            "caption": "str",
            "tier": "int — 1 or 2 (for summary section only)",
        }
    ],
    "chart_data": {
        "chart_type": "str — from CHART_REGISTRY",
        # ... chart-specific fields per SPEC-CHARTS
    },
    "footnotes": ["str"],
    "framework_references": ["str — e.g., 'GRI 305-1', 'IFRS S2 para 29(a)'"],
}

7. Error Handling Strategy
python

ERROR_HANDLING = {
    "section_load_failure": {
        "action": "Skip section, log error, continue assembly",
        "rationale": "Partial report better than no report",
    },
    "chart_render_failure": {
        "action": "Skip chart silently, log error, continue",
        "rationale": "Report readable without charts",
    },
    "styling_failure": {
        "action": "Fall back to unstyled element, log warning",
        "rationale": "Content > presentation",
    },
    "markdown_parse_failure": {
        "action": "Add as plain text paragraph, log warning",
        "rationale": "Raw text still readable",
    },
    "s3_upload_failure": {
        "action": "Retry 3x with exponential backoff, then FAIL",
        "rationale": "No output = pipeline failure",
    },
    "memory_exceeded": {
        "action": "plt.close('all') after each chart, gc.collect() between sections",
        "rationale": "matplotlib accumulates memory in Lambda",
    },
}

7.1 Memory Management
python

import gc

def _assemble_section(doc, section_json, ...):
    # ... assembly logic ...
    
    # Memory cleanup after chart rendering
    try:
        import matplotlib.pyplot as plt
        plt.close('all')
    except ImportError:
        pass
    
    # Force garbage collection every 3 sections
    if section_index % 3 == 0:
        gc.collect()
    
    return (figure_counter, table_counter)

8. Logging & Observability
python

ASSEMBLY_LOG_EVENTS = {
    "ASSEMBLY_START": "report_id, framework, section_count",
    "SECTION_LOADED": "section_id, size_bytes",
    "SECTION_ASSEMBLED": "section_id, duration_ms, has_chart, has_insights",
    "CHART_RENDERED": "section_id, chart_type, duration_ms",
    "CHART_SKIPPED": "section_id, reason",
    "STYLING_APPLIED": "element_type, section_id",
    "STYLING_FALLBACK": "element_type, section_id, error",
    "MARKDOWN_PARSED": "section_id, elements_count",
    "ASSEMBLY_COMPLETE": "report_id, output_path, file_size_kb, duration_total_ms",
    "ASSEMBLY_FAILED": "report_id, error_type, error_message",
}

9. Performance Budget
python

PERFORMANCE_TARGETS = {
    "total_assembly_time": "< 60 seconds (for 9 sections)",
    "per_section_budget": "< 5 seconds (without chart)",
    "per_chart_budget": "< 3 seconds (matplotlib render)",
    "s3_upload": "< 5 seconds",
    "cold_start": "< 5 seconds (matplotlib import)",
    "memory_peak": "< 1500 MB (of 2048 MB allocated)",
    "output_file_size": "< 5 MB (typical: 200-500 KB)",
}

10. Integration Test Checklist
python

INTEGRATION_TESTS = [
    # Cover + TOC
    "T01: Cover page renders with correct institution name and year",
    "T02: TOC field code present (shows 'Update this field' placeholder)",
    
    # Section Assembly
    "T03: All 9 sections present in correct order for MULTI_FRAMEWORK",
    "T04: Summary section placed FIRST (after cover + TOC)",
    "T05: Page breaks at correct section boundaries",
    
    # Markdown Parser
    "T06: ## headings render as DOCX Heading 2 (not plain text)",
    "T07: **bold** renders as bold run",
    "T08: Bullet lists render with List Bullet style",
    "T09: Markdown tables render as styled DOCX tables",
    
    # Styling
    "T10: KPI boxes render with blue-grey background",
    "T11: Insight boxes render with amber left border",
    "T12: Priority actions render with numbered items + urgency colors",
    "T13: Table headers have navy background + white text",
    "T14: Alternating row shading on data tables",
    
    # Charts
    "T15: At least 1 chart renders as embedded PNG (not placeholder text)",
    "T16: Chart has figure caption below",
    "T17: plt.close() called after each render (no memory leak)",
    
    # Executive Summary
    "T18: Summary has Tier 1 (Strategic Brief) heading",
    "T19: Page break between Tier 1 and Tier 2",
    "T20: ESG Scorecard table with 🟢🟡🔴 symbols present",
    "T21: Board Actions block present in Tier 1",
    
    # Insight Layer
    "T22: At least 5 of 8 detail sections have ⚠️ KEY INSIGHT box",
    "T23: At least 5 of 8 detail sections have 📊 DIAGNOSTIC ANALYSIS box",
    "T24: At least 5 of 8 detail sections have ⚡ PRIORITY ACTIONS block",
    "T25: No insight contains numbers not in source metrics",
    
    # Error Resilience
    "T26: Report assembles successfully even if 1 chart fails",
    "T27: Report assembles successfully even if styling partially fails",
    "T28: Missing section (e.g., targets) doesn't crash assembly",
]

11. Deployment Checklist
python

DEPLOYMENT_STEPS = [
    "1. Update Lambda layer esg-python-docx:3 (add docx_styler.py, markdown_parser.py, chart_renderer.py)",
    "2. Deploy updated handler.py to esg-assembly-doc Lambda",
    "3. Upload INSIGHT_LAYER_INSTRUCTIONS.txt to s3://esg-templates/",
    "4. Upload EXEC_SUMMARY_TIER1_INSTRUCTIONS.txt to s3://esg-templates/",
    "5. Update SectionGen Lambda to inject insight layer (per SPEC-INSIGHT-LAYER §2.1)",
    "6. Update Step Functions state machine: summary section runs LAST (after all others complete)",
    "7. Update Step Functions: pass all section metrics to summary AthenaQuery",
    "8. Run integration test: trigger full MULTI_FRAMEWORK pipeline",
    "9. Verify output DOCX against T01-T28 checklist",
    "10. If charts still fail: check CloudWatch logs for actual error (not ImportError)",
]

12. Constraints
CON-ASM-01: NO LLM involvement in assembly — purely deterministic Python
CON-ASM-02: Section order determined by framework (not generation order)
CON-ASM-03: Summary generated LAST but placed FIRST
CON-ASM-04: Graceful degradation — partial report > no report
CON-ASM-05: Memory management: plt.close() + gc.collect() mandatory
CON-ASM-06: All S3 paths use consistent format: s3://{bucket}/{key}
CON-ASM-07: Output metadata includes report_id, framework, timestamp
CON-ASM-08: Maximum 300s execution (Lambda timeout) — must complete within budget

---

Done! Phase 2 complete. Summary:

| Spec | ~Words | Key Deliverable |
|------|--------|-----------------|
| SPEC-EXEC-SUMMARY | ~2,400 | 2-tier structure, ESG scorecard 🟢🟡🔴, board actions, risk/opp matrix, tier break handling |
| SPEC-INSIGHT-LAYER | ~2,600 | Unified injection file, advisory elements (insight/diagnostic/actions), KB query strategy, validation rules |
| SPEC-ASSEMBLY-INTEGRATION | ~3,000 | Master handler, section ordering, assembly loop, error handling, memory management, integration tests |



# PHASE 3
# Kiro Spec: Appendix Sections — Production-Ready Implementation

## Context
- Current state: 3 appendices (A, B, C) — all placeholder (1-2 sentences each)
- Target: 5 appendices, fully populated, framework-compliant
- Section ID: `appendix` (new section type, generated AFTER `summary`)
- Generation approach: Template-driven with data injection (same as other sections)
- NOT LLM-generated narrative — these are structured reference tables + methodology notes

---

# phase 3


# SPEC-APPENDIX: Appendix Generation System
# ESG Reporting System — Kiro IDE Specification
# VERSION: 1.0.0 | DATE: 12/06/2026

---

## 1. Overview

This spec defines the automated appendix generation for the ESG report.
Appendices are generated PROGRAMMATICALLY (no LLM) from section metadata collected during assembly.

**Key Principle**: Appendix content is DERIVED from section JSONs — not generated by Bedrock.
**Placement**: After all content sections, before back cover.
**Page Break**: Each appendix starts on a new page.

---

## 2. Appendix Sections (in order)

```python
APPENDIX_SECTIONS = [
    "methodology_notes",       # A: Methodology & Calculation Approach
    "emission_factors",        # B: Emission Factors & Constants Used
    "data_quality_statement",  # C: Data Quality & Assurance Statement
    "sector_classification",   # D: Sector Classification & PCAF Mapping
    "gri_content_index",       # E: GRI Content Index (if GRI framework)
    "framework_disclosure_map",# F: Framework Disclosure Cross-Reference
    "glossary",                # G: Glossary of Terms & Abbreviations
]


  A: Methodology & Calculation Approach .... 28
  B: Emission Factors & Constants .......... 30
  C: Data Quality & Assurance Statement .... 31
  D: Sector Classification ................. 32
  E: GRI Content Index ..................... 33
  F: Framework Cross-Reference ............. 34
  G: Glossary .............................. 35
4. Header & Footer
4.1 Configuration
python

HEADER_FOOTER_CONFIG = {
    "header": {
        "left": "{institution_name}",
        "right": "ESG Sustainability Report FY{reporting_year}",
        "font_size": Pt(8),
        "font_color": RGBColor(0x66, 0x66, 0x66),
        "border_bottom": True,
        "border_color": RGBColor(0x1B, 0x3A, 0x6B),
    },
    "footer": {
        "left": "{framework_display_short}",
        "center": "Page {PAGE} of {NUMPAGES}",
        "right": "DRAFT — Confidential",
        "font_size": Pt(8),
        "font_color": RGBColor(0x99, 0x99, 0x99),
        "border_top": True,
    },
    "first_page_different": True,  # No header/footer on cover page
}

4.2 Implementation
python

def add_header_footer(doc: Document, config: dict):
    """
    Add header and footer to all sections (except first page = cover).
    """
    for section in doc.sections[1:]:  # Skip cover page section
        section.different_first_page_header_footer = False
        
        # === HEADER ===
        header = section.header
        header_para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        header_para.clear()
        
        # Left-aligned institution name
        left_run = header_para.add_run(config["institution_name"])
        left_run.font.size = HEADER_FOOTER_CONFIG["header"]["font_size"]
        left_run.font.color.rgb = HEADER_FOOTER_CONFIG["header"]["font_color"]
        
        # Tab to right
        header_para.add_run("\t\t")
        
        # Right-aligned report title
        right_run = header_para.add_run(f"ESG Sustainability Report FY{config['reporting_year']}")
        right_run.font.size = HEADER_FOOTER_CONFIG["header"]["font_size"]
        right_run.font.color.rgb = HEADER_FOOTER_CONFIG["header"]["font_color"]
        
        # Bottom border
        pBdr = OxmlElement('w:pBdr')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '4')
        bottom.set(qn('w:color'), '1B3A6B')
        pBdr.append(bottom)
        header_para._p.get_or_add_pPr().append(pBdr)
        
        # === FOOTER ===
        footer = section.footer
        footer_para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        footer_para.clear()
        
        # Left: framework
        left_run = footer_para.add_run(config.get("framework_short", "Multi-Framework"))
        left_run.font.size = HEADER_FOOTER_CONFIG["footer"]["font_size"]
        left_run.font.color.rgb = HEADER_FOOTER_CONFIG["footer"]["font_color"]
        
        # Center: page number (using field codes)
        footer_para.add_run("\t")
        _add_page_number_field(footer_para)
        
        # Right: confidentiality
        footer_para.add_run("\t")

5. Constraints
CON-COV-01: Cover page uses full-page table trick (python-docx limitation — no native background color)
CON-COV-02: First section has zero margins (cover), subsequent sections have 2.54cm margins
CON-COV-03: TOC uses Word field codes — requires user to "Update Field" for page numbers
CON-COV-04: Header/footer NOT on cover page (first_page_different)
CON-COV-05: Page numbers use field codes (auto-increment)
CON-COV-06: Draft watermark only shown when is_draft == True (configurable)
CON-COV-07: All colors from centralized STYLE_CONSTANTS (no hardcoded hex in functions)

---

```markdown

# SPEC-FRAMEWORK-OVERLAY: Framework-Specific Overlay Templates
# ESG Reporting System — Kiro IDE Specification
# VERSION: 1.0.0 | DATE: 12/06/2026

---

## 1. Overview

This spec defines the Framework Overlay system — the second layer of the prompt architecture
that customizes section generation output based on the selected reporting framework.

**Prompt Architecture Recap**:
FINAL_PROMPT = BASE_PROMPT + FRAMEWORK_OVERLAY[framework] + SECTION_TEMPLATE[section_id] + DATA + KB_CONTEXT + INSIGHT_LAYER


**This spec covers**: `FRAMEWORK_OVERLAY[framework]` — the framework-specific instructions
injected AFTER the base prompt but BEFORE the section template.

---

## 2. Overlay Purpose

Each framework has different:
- **Disclosure requirements** (what MUST be stated)
- **Terminology** (e.g., "direct emissions" vs "Scope 1")
- **Structure expectations** (paragraph order, required sub-sections)
- **Cross-references** (which paragraph/article to cite)
- **Compliance language** (mandatory vs recommended disclosures)

The overlay ensures the LLM output meets framework-specific requirements WITHOUT
duplicating the entire template for each framework.

---

## 3. Framework Overlay Registry

```python
FRAMEWORK_OVERLAYS = {
    "GRI_305": GRI_305_OVERLAY,
    "IFRS_S2": IFRS_S2_OVERLAY,
    "CSRD_ESRS_E1": CSRD_ESRS_E1_OVERLAY,
    "OJK_PSPK": OJK_PSPK_OVERLAY,
    "MULTI_FRAMEWORK": MULTI_FRAMEWORK_OVERLAY,
}
4. GRI 305 Overlay
python

GRI_305_OVERLAY = """
== FRAMEWORK: GRI 305: Emissions 2016 ==

You are writing disclosures per GRI 305. Each section maps to a specific GRI Disclosure.
Follow GRI's "shall report" requirements exactly.

SECTION-TO-DISCLOSURE MAPPING:
- scope1 → Disclosure 305-1: Direct (Scope 1) GHG emissions
- scope2 → Disclosure 305-2: Energy indirect (Scope 2) GHG emissions
- scope3_pcaf → Disclosure 305-3: Other indirect (Scope 3) GHG emissions
- intensity → Disclosure 305-4: GHG emissions intensity
- reduction → Disclosure 305-5: Reduction of GHG emissions

MANDATORY ELEMENTS PER DISCLOSURE (305-1 through 305-5):
a. Gross emissions in metric tons of CO₂ equivalent
b. Gases included in calculation (CO₂, CH₄, N₂O)
c. Base year (if applicable) with rationale
d. Source of emission factors and GWP rates
e. Consolidation approach (operational control)
f. Standards/methodologies used

ADDITIONAL REQUIREMENTS:
- State consolidation approach: "Operational control per GHG Protocol Corporate Standard"
- State GWP source: "IPCC Sixth Assessment Report (AR6), 100-year timeframe"
- For Scope 2: Report BOTH location-based AND market-based (if applicable)
- For Scope 3: Identify categories included (Category 15: Investments for PCAF)
- Biogenic CO₂ reported separately (if applicable)
- Exclude GHG trades from gross figures

TERMINOLOGY:
- Use "Direct (Scope 1) GHG emissions" (not just "Scope 1")
- Use "Energy indirect (Scope 2) GHG emissions" (not just "Scope 2")
- Use "Other indirect (Scope 3) GHG emissions" (not just "Scope 3")
- Use "metric tons of CO₂ equivalent" on first mention, then "tCO₂e"

FRAMEWORK REFERENCE FORMAT:
- End each section with: "This disclosure addresses GRI 305-X requirements (a) through (g)."
- Note: "GRI 305-1 through 305-5 superseded by GRI 102: Climate Change 2025 (effective 1 January 2027)."

NOTE ON GRI 102:
- GRI 102: Climate Change 2025 supersedes Disclosures 305-1 to 305-5
- Effective date: 1 January 2027
- Early adoption encouraged
- Include this note in framework references
"""

5. IFRS S2 Overlay
python

IFRS_S2_OVERLAY = """
== FRAMEWORK: IFRS S2 — Climate-related Disclosures ==

You are writing disclosures per IFRS S2 (issued June 2023, effective January 2024).
IFRS S2 follows the TCFD structure: Governance → Strategy → Risk Management → Metrics & Targets.

SECTION-TO-PARAGRAPH MAPPING:
- governance → Paragraphs 5-9 (Governance)
- scope1 → Paragraph 29(a)(i) (Absolute Scope 1 in tCO₂e)
- scope2 → Paragraph 29(a)(ii) (Absolute Scope 2 — location + market-based)
- scope3_pcaf → Paragraph 29(a)(iii-iv) (Absolute Scope 3 + Category 15)
- intensity → Paragraph 29(b) (Emission intensity per unit of physical/economic output)
- targets → Paragraphs 33-36 (Climate-related targets)
- reduction → Paragraph 33-34 (Progress against targets)

MANDATORY ELEMENTS:
- Paragraph 29(a): Absolute GHG emissions (Scope 1, 2, 3) in tCO₂e
- Paragraph 29(a)(ii): Scope 2 MUST include location-based; market-based if applicable
- Paragraph 29(a)(iv): Categories of Scope 3 included + reasons for exclusion
- Paragraph 29(b): Intensity metric with denominator specified
- Paragraph 29(c): GHG Protocol as measurement approach

SPECIFIC REQUIREMENTS:
- Cross-industry metric: Scope 1+2+3 absolute emissions (non-negotiable)
- Financed emissions: Disclose for Category 15 (Investments) per PCAF
- Measurement approach: State "GHG Protocol Corporate Standard" and "PCAF Standard"
- Transition plan: If no formal plan, state absence and explain why
- Scenario analysis: If not performed, state absence and timeline for implementation

TERMINOLOGY:
- Use "climate-related risks and opportunities" (not just "ESG risks")
- Use "transition risks" and "physical risks" where applicable
- Use "financed emissions" (not "portfolio emissions")
- Reference specific paragraphs: "Per IFRS S2 paragraph 29(a)(i)..."

GOVERNANCE SECTION REQUIREMENTS (Para 5-9):
- Governance body responsible for climate oversight
- How climate is integrated into strategy and risk management
- Management's role in assessing and managing climate risks
- Whether climate targets are linked to remuneration

FRAMEWORK REFERENCE FORMAT:
- Cite specific paragraphs: "IFRS S2 Para 29(a)(i)", "IFRS S2 Para 33"
- Note industry-specific guidance applicability
"""

6. CSRD/ESRS E1 Overlay
python

CSRD_ESRS_E1_OVERLAY = """
== FRAMEWORK: CSRD / ESRS E1 — Climate Change ==

You are writing disclosures per ESRS E1 (European Sustainability Reporting Standards).
ESRS E1 has 9 Disclosure Requirements (DR E1-1 through E1-9).

SECTION-TO-DR MAPPING:
- targets → DR E1-4: Targets related to climate change mitigation and adaptation (§34-42)
- scope1 → DR E1-6: Gross Scope 1, 2, 3 and Total GHG emissions (§44-46)
- scope2 → DR E1-6: §47-48 (Location-based + Market-based)
- scope3_pcaf → DR E1-6: §51-54 (Scope 3 categories, financed emissions)
- intensity → DR E1-6: §55-56 (GHG intensity per net revenue)
- reduction → DR E1-4: §34-36 (Reduction targets and progress)
- governance → ESRS 2 GOV-1 through GOV-5

MANDATORY ELEMENTS (DR E1-6):
- §44: Gross Scope 1 in tCO₂e, disaggregated by:
  - (a) Consolidated accounting group
  - (b) Associates/joint ventures (if applicable)
- §47: Scope 2 location-based in tCO₂e
- §48: Scope 2 market-based in tCO₂e (if contractual instruments exist)
- §51: Total Scope 3 in tCO₂e
- §52: Scope 3 by significant category (Category 15 for FIs)
- §55: GHG intensity = Total emissions / Net revenue (tCO₂e per million EUR or local currency)

TARGETS (DR E1-4):
- §34: Whether targets are science-based (SBTi validated or aligned)
- §35: Base year and base year emissions
- §36: Target year and target value (absolute or intensity)
- §37: Interim milestones
- §38: Methodology (SBTi sectoral decarbonisation or contraction)
- Cross-sector reduction pathway: -42% by 2030, -90% by 2050 (vs 2020 base)

TRANSITION PLAN (DR E1-1):
- If no transition plan: State "The undertaking has not yet adopted a transition plan"
- If in development: State timeline for adoption
- Required elements when adopted: decarbonisation levers, CapEx/OpEx alignment, locked-in emissions

SPECIFIC REQUIREMENTS:
- Use "undertaking" (not "organization" or "company")
- Separate operational emissions from financed emissions clearly
- State whether GHG accounting is per GHG Protocol or ISO 14064
- If market-based = location-based (no RECs): State explicitly

FRAMEWORK REFERENCE FORMAT:
- Cite: "ESRS E1, DR E1-6, §44" or "ESRS E1, DR E1-4, §34-36"
- Note CSRD phased implementation timeline
"""

7. OJK PSPK Overlay
python

OJK_PSPK_OVERLAY = """
== FRAMEWORK: OJK PSPK — Penerapan Keuangan Berkelanjutan ==

You are writing disclosures per OJK regulations on sustainable finance for Indonesian financial institutions.
Primary regulation: POJK No. 51/POJK.03/2017 and subsequent amendments.

SECTION-TO-LAMPIRAN MAPPING:
- governance → Lampiran I: Tata Kelola Keuangan Berkelanjutan
- scope1 → Lampiran II.A.1: Emisi GRK Langsung (Scope 1)
- scope2 → Lampiran II.A.2: Emisi GRK Tidak Langsung dari Energi (Scope 2)
- scope3_pcaf → Lampiran II.A.3: Emisi GRK Tidak Langsung Lainnya (Scope 3)
- intensity → Lampiran II.B: Intensitas Emisi
- reduction → Lampiran II.C: Pengurangan Emisi GRK
- social → Lampiran IV: Kinerja Sosial
- targets → Lampiran III: Target dan Rencana Aksi

MANDATORY ELEMENTS:
- Lampiran I: Struktur tata kelola keberlanjutan (komite, kebijakan, prosedur)
- Lampiran II: Data emisi GRK per scope dengan metodologi perhitungan
- Lampiran III: Target pengurangan emisi dan rencana transisi
- Lampiran IV: Data ketenagakerjaan, kesetaraan gender, pelatihan

SPECIFIC REQUIREMENTS:
- Language: Report content in English (this is an English-language report)
- Reference OJK regulation numbers explicitly
- Include KKUB (Kategori Kegiatan Usaha Berkelanjutan) classification if applicable
- State alignment with Indonesia's NDC (Nationally Determined Contribution)
- Reference Indonesia's Net Zero Emission 2060 target
- Include PLN grid emission factor source (ESDM Ministerial Decree)

GOVERNANCE REQUIREMENTS (Lampiran I):
- ESG committee existence and composition
- Board-level oversight of sustainability
- Integration of ESG into risk management framework
- Sustainability-linked KPIs for management

TERMINOLOGY:
- Use "Lembaga Jasa Keuangan" (LJK) when referencing OJK's term for financial institutions
- Use "Keuangan Berkelanjutan" for sustainable finance
- Use "Emisi Gas Rumah Kaca (GRK)" for GHG emissions
- Reference "POJK 51/2017" and "SE OJK" (Surat Edaran) where applicable

FRAMEWORK REFERENCE FORMAT:
- Cite: "OJK PSPK, Lampiran II.A.1" or "POJK 51/2017, Pasal 4"
- Note: OJK taxonomy alignment (Taksonomi Hijau Indonesia)
"""

8. Multi-Framework Overlay
python

MULTI_FRAMEWORK_OVERLAY = """
== FRAMEWORK: MULTI-FRAMEWORK (Unified Report) ==

This report addresses MULTIPLE frameworks simultaneously:
- GRI 305: Emissions 2016
- IFRS S2: Climate-related Disclosures
- CSRD/ESRS E1: Climate Change
- OJK PSPK: Penerapan Keuangan Berkelanjutan

APPROACH:
Write content that satisfies ALL frameworks simultaneously. Where requirements overlap,
use the MOST COMPREHENSIVE requirement. Where they differ, address each explicitly.

STRUCTURE:
- Primary structure follows GRI 305 disclosure order (305-1 through 305-5)
- IFRS S2 paragraph references included as cross-references
- ESRS E1 DR references included as cross-references
- OJK Lampiran references included as cross-references

MANDATORY CROSS-REFERENCE BLOCK:
At the end of each section, include a "Framework References" block:

Framework References:

GRI 305-X (Disclosure requirement a-g)
IFRS S2 Para XX
ESRS E1, DR E1-X, §XX
OJK PSPK, Lampiran XX

CONFLICT RESOLUTION:
- Scope 2: Report BOTH location-based AND market-based (IFRS S2 + ESRS E1 require both)
- Intensity denominator: Use revenue (satisfies all frameworks)
- Targets: If no SBTi commitment, state gap explicitly (ESRS E1 requires this)
- Governance: Address IFRS S2 Para 5-9 AND ESRS 2 GOV-1 requirements together
- Transition plan: If absent, state per ESRS E1 DR E1-1 requirement

TERMINOLOGY:
- Use GHG Protocol terminology as baseline (most universally recognized)
- First mention: Full term + abbreviation. Subsequent: abbreviation only.
- Avoid framework-specific jargon that conflicts across frameworks

COMPLETENESS CHECK:
Each section MUST address requirements from ALL 4 frameworks.
If a framework has no specific requirement for a section, state "N/A for [framework]".
"""
9. Overlay Injection Logic
python

def _get_framework_overlay(framework: str, section_id: str) -> str:
    """
    Get the appropriate framework overlay for prompt construction.
    
    For MULTI_FRAMEWORK: Returns the multi-framework overlay.
    For single frameworks: Returns the specific framework overlay.
    """
    overlay = FRAMEWORK_OVERLAYS.get(framework, MULTI_FRAMEWORK_OVERLAY)
    return overlay


def _build_final_prompt(
    section_id: str,
    framework: str,
    base_prompt: str,
    section_template: str,
    metrics_json: str,
    kb_context: str,
    insight_instructions: str,
) -> str:
    """
    Construct the complete prompt for Bedrock InvokeModel.
    
    Order matters:
    1. BASE_PROMPT (universal rules)
    2. FRAMEWORK_OVERLAY (framework-specific requirements)
    3. SECTION_TEMPLATE (section-specific structure)
    4. DATA (metrics JSON)
    5. KB_CONTEXT (RAG retrieval)
    6. INSIGHT_LAYER (advisory output format)
    """
    framework_overlay = _get_framework_overlay(framework, section_id)
    
    final_prompt = f"""{base_prompt}

{framework_overlay}

{section_template}

== DATA (Source of Truth — use ONLY these numbers) ==
{metrics_json}

== KNOWLEDGE BASE CONTEXT (Peer Benchmarks & Framework Guidance) ==
{kb_context}

== OUTPUT FORMAT REQUIREMENTS ==
{insight_instructions}
"""
    return final_prompt

10. Section Order by Framework
python

SECTION_ORDER = {
    "GRI_305": [
        "summary",       # Executive Summary (generated last, placed first)
        "scope1",        # 305-1
        "scope2",        # 305-2
        "scope3_pcaf",   # 305-3
        "intensity",     # 305-4
        "reduction",     # 305-5
        "social",        # GRI 401/403/404/405
        "governance",



## Appendix A: GHG Calculation Methodology

### Purpose
Satisfy GRI 305-1 clause 2.1.c, PCAF Chapter 6 transparency principle, ESRS 2 BP-2 (sources of estimation uncertainty), GHG Protocol Chapter 7 (inventory quality)

### Required Content Structure

```
A.1 Reporting Boundary & Consolidation Approach
- Consolidation approach: Operational Control (per GHG Protocol)
- Organizational boundary: All facilities under operational control
- Reporting period: 01/01/2024 – 31/12/2024
- Base year: 2023 (first year of comprehensive GHG inventory)
- Recalculation policy: Triggered if structural changes affect >5% of total emissions

A.2 Scope 1 — Direct Emissions Methodology
- Sources covered: Stationary combustion (diesel generators, natural gas), Mobile combustion (company vehicles)
- Calculation method: Fuel-based (activity data × emission factor)
- Emission factors:
  | Fuel Type | CO₂ Factor | CH₄ Factor | N₂O Factor | Source |
  |-----------|-----------|-----------|-----------|--------|
  | Diesel | 2.6710 kg/L | 0.00029 kgCO₂e/L | 0.03308 kgCO₂e/L | DEFRA 2025 |
  | Natural Gas | 56.10 kg/GJ | 0.0298 kgCO₂e/GJ | 0.0273 kgCO₂e/GJ | IPCC AR6 |
- GWP values: CH₄ = 29.8, N₂O = 273.0 (IPCC AR6, 100-year)
- Data sources: Smart meter API (primary), manual entry (secondary), facility-type average (imputation)
- Imputation method: Monthly facility-type average for missing data points
- Exclusions: Refrigerant leakage (HFCs) — not material for banking operations

A.3 Scope 2 — Indirect Emissions Methodology
- Method: Location-based (primary), Market-based (supplementary)
- Grid emission factor: 0.7886 kg CO₂/kWh (PLN National Grid Average 2023, DJK-ESDM)
- REC treatment: Renewable Energy Certificates deducted from market-based only
- Data sources: Utility bills, smart meter readings
- Exclusions: District heating/cooling (not applicable in Indonesia)

A.4 Scope 3 Category 15 — Financed Emissions Methodology
- Standard: PCAF Global GHG Accounting Standard, 2nd Edition (2022)
- Asset classes covered: Business loans, project finance
- Attribution formula: Financed Emissions = Σ (Attribution Factor × Borrower Emissions)
- Attribution factor: Outstanding Amount / (Total Equity + Total Debt)
- Borrower emissions scope: Scope 1 + Scope 2 of borrower
- Sectors covered: 10 NACE sectors (see Appendix D for full list)
- Data quality scoring: PCAF 5-tier scale (Score 1 = verified, Score 5 = sector average)
- Confidence weighting: Applied per PCAF score tier (see Appendix B)
- Portfolio coverage: 100% of productive loan portfolio
- Exclusions: Sovereign debt, retail consumer loans, interbank lending

A.5 Intensity Metrics Methodology
- Revenue intensity: Total Emissions (tCO₂e) / Operating Revenue (IDR billion)
- FTE intensity: Total Scope 1+2 Emissions (tCO₂e) / Total FTE headcount
- Denominator sources: Audited financial statements (revenue), HR system (FTE)
```

### Data Source for Population
- Emission factor constants: Hardcoded from spec (Section 3.1)
- Methodology text: Template-driven (NOT LLM-generated)
- Populate from: `esg_aggregated.ghg_summary_annual` for actual values used

---

## Appendix B: Data Quality Statement & Uncertainty Assessment

### Purpose
Satisfy PCAF reporting requirement (data quality disclosure), ESRS 2 BP-2 para 11 (sources of estimation uncertainty), GHG Protocol Chapter 7

### Required Content Structure

```
B.1 Operational Emissions Data Quality
- Data completeness: {data_completeness_pct}% of facility-months with primary data
- Imputed data points: {imputed_months} facility-months estimated using facility-type averages
- Data quality score: {data_quality_score}/4
  | Score | Criteria | Facility Count |
  |-------|----------|---------------|
  | 1 (High) | 0 imputed months | {count} |
  | 2 (Good) | 1-2 imputed months | {count} |
  | 3 (Moderate) | 3-5 imputed months | {count} |
  | 4 (Low) | 6+ imputed months | {count} |
- Meter calibration: Smart meters calibrated annually per ISO 50001
- Improvement plan: Targeting 100% smart meter coverage by Q4 2025

B.2 Financed Emissions Data Quality (PCAF)
- Portfolio-weighted PCAF score: {portfolio_weighted_pcaf_score}/5.0
- Score distribution:
  | PCAF Score | Description | Loan Count | % Portfolio Value |
  |-----------|-------------|-----------|-----------------|
  | 1.0 | Audited & verified | {n} | {pct}% |
  | 1.5 | Audited & unverified | {n} | {pct}% |
  | 2.0 | Physical activity-based | {n} | {pct}% |
  | 3.0 | EEIO + revenue | {n} | {pct}% |
  | 4.0 | EEIO + assets | {n} | {pct}% |
  | 5.0 | Sector average | {n} | {pct}% |
- Confidence weighting applied:
  | PCAF Score | Confidence Factor | Rationale |
  |-----------|------------------|-----------|
  | 1.0 | 1.00 | Verified data, no uncertainty discount |
  | 1.5 | 0.95 | Minor uncertainty from lack of verification |
  | 2.0 | 0.90 | Physical proxy introduces ~10% uncertainty |
  | 3.0 | 0.75 | Revenue-based EEIO has ~25% uncertainty |
  | 4.0 | 0.60 | Asset-based EEIO has ~40% uncertainty |
  | 5.0 | 0.45 | Sector average has ~55% uncertainty |
- Gross vs. confidence-weighted gap: {gap_pct}%
- Data improvement roadmap:
  - 2025: Engage top 20 borrowers for direct emissions reporting (target: move 15% from Score 4→2)
  - 2026: Integrate CDP data feed for listed borrowers

B.3 Uncertainty Assessment
- Key sources of uncertainty:
  1. Grid emission factor (PLN 2023) — may not reflect actual generation mix at point of consumption
  2. Borrower emissions data lag (typically 12-18 months)
  3. Attribution factor sensitivity to balance sheet timing
- Quantified uncertainty range: ±{uncertainty_pct}% for Scope 1+2, ±{uncertainty_pct_s3}% for Scope 3
- Mitigation: Conservative approach applied (higher EF used when range available)

B.4 Limitations & Exclusions
- Scope 3 categories not assessed: Categories 1-14 (not material for banking, per GHG Protocol screening)
- Financed emissions exclusions: Sovereign debt, retail consumer, interbank (methodology not yet standardized per PCAF)
- Temporal mismatch: Borrower emissions data may be 1-2 years lagged vs. loan outstanding date
- Geographic limitation: Grid EF uses national average (not regional grid factors)
```

### Data Source for Population
- PCAF scores: `esg_curated.ghg_scope3_financed` (avg_pcaf_score, high_quality_data_pct)
- Imputation stats: `esg_curated.ghg_scope1` (imputed_months, data_quality_score)
- Gap calculation: `esg_aggregated.ghg_summary_annual` (gross vs weighted)

---

## Appendix C: Framework Disclosure Index (Cross-Reference Table)

### Purpose
Satisfy GRI Content Index requirement (GRI 1 Foundation 2021, Requirement 7), CSRD/ESRS 2 IRO-2, OJK PSPK disclosure mapping

### Required Content Structure

```
C.1 GRI Content Index
| GRI Standard | Disclosure | Description | Section Reference | Page |
|-------------|-----------|-------------|-------------------|------|
| GRI 305-1 | a-g | Direct (Scope 1) GHG emissions | Section 1.1 | {page} |
| GRI 305-2 | a-g | Energy indirect (Scope 2) GHG emissions | Section 1.2 | {page} |
| GRI 305-3 | a-g | Other indirect (Scope 3) GHG emissions | Section 1.3 | {page} |
| GRI 305-4 | a-d | GHG emissions intensity | Section 1.4 | {page} |
| GRI 305-5 | a-e | Reduction of GHG emissions | Section 1.5 | {page} |
| GRI 2-7 | a-e | Employees | Section 2.1 | {page} |
| GRI 401-1 | a-b | New employee hires and turnover | Section 2.1 | {page} |
| GRI 404-1 | a-c | Average hours of training | Section 2.1 | {page} |
| GRI 405-1 | a-b | Diversity of governance bodies | Section 2.1 | {page} |

C.2 IFRS S2 Mapping
| IFRS S2 Paragraph | Requirement | Section Reference | Status |
|-------------------|-------------|-------------------|--------|
| Para 5-15 | Governance | Section 3.1 | Disclosed |
| Para 16-22 | Strategy | Section 3.1 | Partial |
| Para 23-24 | Risk Management | Section 3.1 | Disclosed |
| Para 25-37 | Metrics & Targets | Sections 1.1-1.5, 1.8 | Disclosed |
| Para 29(a) | Scope 1 emissions | Section 1.1 | Disclosed |
| Para 29(a) | Scope 2 emissions | Section 1.2 | Disclosed |
| Para 29(a) | Scope 3 emissions | Section 1.3 | Disclosed |
| Para 29(b) | Financed emissions | Section 1.3 | Disclosed |

C.3 CSRD/ESRS E1 Mapping
| ESRS E1 DR | Requirement | Section Reference | Status |
|-----------|-------------|-------------------|--------|
| E1-1 | Transition plan | Section 1.8 | Gap identified |
| E1-2 | Policies | Section 3.1 | Partial |
| E1-3 | Actions and resources | Section 1.5 | Disclosed |
| E1-4 | Targets | Section 1.8 | Disclosed |
| E1-5 | Energy consumption | Appendix A | Disclosed |
| E1-6 | Scope 1, 2, 3 emissions | Sections 1.1-1.3 | Disclosed |
| E1-7 | GHG removals/carbon credits | N/A | Not applicable |
| E1-8 | Internal carbon pricing | Section 3.1 | Gap identified |
| E1-9 | Financial effects | Section 3.1 | Gap identified |

C.4 OJK PSPK Mapping
| OJK Requirement | Description | Section Reference | Status |
|----------------|-------------|-------------------|--------|
| Lampiran II.A | Environmental aspects | Sections 1.1-1.5 | Disclosed |
| Lampiran II.B | Social aspects | Section 2.1 | Disclosed |
| Lampiran II.C | Governance aspects | Section 3.1 | Disclosed |
| Lampiran III | GHG emissions data | Sections 1.1-1.3 | Disclosed |
| Lampiran IV | Sustainable finance portfolio | Section 1.3 | Disclosed |
```

### Data Source for Population
- Section references: Derived from assembly order (section_id → chapter.section mapping)
- Page numbers: Populated by AssemblyDoc AFTER full document assembly (post-processing pass)
- Status: Derived from validation results (section present + data populated = "Disclosed", section present + gaps = "Partial", section absent = "Gap identified")

---

## Appendix D: Sector Classification & Emission Factors Reference

### Purpose
Transparency requirement per PCAF (disclose sectors covered, EF sources used), GRI 305-1 clause 2.1.e

### Required Content Structure

```
D.1 NACE Sector Classification
| Sector Code | Sector Name | Loan Count | Portfolio Share (%) | Avg PCAF Score |
|------------|-------------|-----------|-------------------|---------------|
| energy_oil_gas | Energy — Oil & Gas | {n} | {pct}% | {score} |
| manufacturing_cement | Manufacturing — Cement | {n} | {pct}% | {score} |
| manufacturing_steel | Manufacturing — Steel | {n} | {pct}% | {score} |
| manufacturing_food | Manufacturing — Food & Beverage | {n} | {pct}% | {score} |
| real_estate_commercial | Real Estate — Commercial | {n} | {pct}% | {score} |
| real_estate_residential | Real Estate — Residential | {n} | {pct}% | {score} |
| transportation_road | Transportation — Road | {n} | {pct}% | {score} |
| agriculture | Agriculture | {n} | {pct}% | {score} |
| financial_services | Financial Services | {n} | {pct}% | {score} |
| retail_trade | Retail Trade | {n} | {pct}% | {score} |

D.2 Emission Factor Registry
| Factor ID | Description | Value | Unit | Source | Vintage |
|----------|-------------|-------|------|--------|---------|
| EF-S1-D-CO2 | Diesel CO₂ | 2.6710 | kg/L | DEFRA 2025 | 2025 |
| EF-S1-D-CH4 | Diesel CH₄ (pre-multiplied) | 0.00029 | kgCO₂e/L | DEFRA 2025 | 2025 |
| EF-S1-D-N2O | Diesel N₂O (pre-multiplied) | 0.03308 | kgCO₂e/L | DEFRA 2025 | 2025 |
| EF-S1-NG-CO2 | Natural Gas CO₂ | 56.10 | kg/GJ | IPCC AR6 | 2021 |
| EF-S1-NG-CH4 | Natural Gas CH₄ | 0.001 | kg/GJ | IPCC AR6 | 2021 |
| EF-S1-NG-N2O | Natural Gas N₂O | 0.0001 | kg/GJ | IPCC AR6 | 2021 |
| EF-S2-GRID | PLN Grid Average | 0.7886 | kg CO₂/kWh | DJK-ESDM 2023 | 2023 |
| GWP-CH4 | Methane GWP (100yr) | 29.8 | — | IPCC AR6 | 2021 |
| GWP-N2O | Nitrous Oxide GWP (100yr) | 273.0 | — | IPCC AR6 | 2021 |

D.3 PCAF Sector Emission Factors (for Score 5 estimates)
| Sector | Emission Intensity | Unit | Source |
|--------|-------------------|------|--------|
| Energy — Oil & Gas | {value} | tCO₂e/IDR billion revenue | EEIO Indonesia 2022 |
| Manufacturing — Cement | {value} | tCO₂e/IDR billion revenue | EEIO Indonesia 2022 |
| ... | ... | ... | ... |
```

### Data Source for Population
- Sector data: `esg_curated.ghg_scope3_financed` (loan_count, total_outstanding, avg_pcaf_score per sector)
- EF registry: Hardcoded constants from spec Section 3.1
- PCAF sector EFs: From KB benchmark documents (if available) or marked as "Institution-specific"

---

## Appendix E: Glossary & Abbreviations

### Purpose
Reader accessibility, framework compliance (GRI requires defined terms), OJK readability requirement

### Required Content Structure

```
E.1 Abbreviations
| Abbreviation | Full Term |
|-------------|-----------|
| CO₂e | Carbon Dioxide Equivalent |
| CSRD | Corporate Sustainability Reporting Directive |
| DEFRA | UK Department for Environment, Food & Rural Affairs |
| ESRS | European Sustainability Reporting Standards |
| EF | Emission Factor |
| EEIO | Environmentally Extended Input-Output |
| FTE | Full-Time Equivalent |
| GHG | Greenhouse Gas |
| GRI | Global Reporting Initiative |
| GWP | Global Warming Potential |
| IDR | Indonesian Rupiah |
| IFRS | International Financial Reporting Standards |
| IPCC | Intergovernmental Panel on Climate Change |
| ISSB | International Sustainability Standards Board |
| OJK | Otoritas Jasa Keuangan (Financial Services Authority) |
| PCAF | Partnership for Carbon Accounting Financials |
| PLN | Perusahaan Listrik Negara (State Electricity Company) |
| REC | Renewable Energy Certificate |
| SBTi | Science Based Targets initiative |
| tCO₂e | Metric Tonnes of Carbon Dioxide Equivalent |
| YoY | Year-over-Year |

E.2 Key Definitions
| Term | Definition |
|------|-----------|
| Attribution Factor | Ratio of outstanding loan amount to borrower's total equity plus debt, used to allocate borrower emissions to the financial institution |
| Base Year | The historical datum against which emissions are tracked over time (2023 for this report) |
| Confidence-Weighted Emissions | Financed emissions adjusted by PCAF data quality confidence factors to reflect measurement uncertainty |
| Financed Emissions | GHG emissions associated with the institution's lending and investment portfolio (Scope 3 Category 15) |
| Location-Based Method | Scope 2 accounting using average grid emission factors for the location of electricity consumption |
| Market-Based Method | Scope 2 accounting using emission factors from contractual instruments (e.g., RECs, PPAs) |
| Materiality | The threshold at which sustainability topics become sufficiently important to warrant reporting |
| Operational Control | Consolidation approach where the institution accounts for 100% of emissions from operations it controls |
| Scope 1 | Direct GHG emissions from sources owned or controlled by the reporting entity |
| Scope 2 | Indirect GHG emissions from purchased electricity, steam, heating, and cooling |
| Scope 3 | All other indirect GHG emissions in the value chain |
```

### Data Source for Population
- Static content (hardcoded in template)
- No dynamic data injection needed
- Updated annually if new terms introduced

---

## Implementation Approach

### Option 1: Template-Driven (RECOMMENDED for POC)
- Appendices A, D, E = **static templates** with data placeholders `{variable}`
- Appendices B, C = **hybrid** (static structure + dynamic data from Athena)
- AssemblyDoc populates placeholders from `ghg_summary_annual` + `ghg_scope3_financed`
- NO LLM involvement — pure data injection

### Option 2: LLM-Assisted (Future Production)
- SectionGen generates appendix narrative with strict template constraints
- Useful when client-specific methodology notes vary significantly

### Assembly Integration
- Appendices assembled AFTER `summary` section
- Each appendix = separate page (page break before each)
- Appendix headings: Heading Level 1 ("Appendix A: [Title]")
- Tables use same styling as body sections (colored headers, alternating rows)
- Page numbers in Appendix C populated via post-processing pass (after full doc assembled)

### New Athena Query Required
```
Query ID: appendix_data_quality
Purpose: Populate Appendix B tables
Returns: imputed_months distribution, PCAF score distribution, portfolio coverage stats
Source: esg_curated.ghg_scope1 + esg_curated.ghg_scope3_financed
```

### Validation Rules (Appendix-Specific)
- VAL-APP-01: All emission factors in Appendix D MUST match constants used in ETL calculation (cross-check with spec Section 3.1)
- VAL-APP-02: PCAF score distribution in Appendix B MUST sum to 100%
- VAL-APP-03: Sector list in Appendix D MUST match sectors in Section 1.3 (Scope 3 PCAF)
- VAL-APP-04: Framework index section references MUST correspond to actual assembled sections

---

## File Artifacts to Create
1. `appendix_a_template.json` — Methodology notes (static + placeholders)
2. `appendix_b_template.json` — Data quality (dynamic from Athena)
3. `appendix_c_template.json` — Framework index (dynamic from assembly metadata)
4. `appendix_d_template.json` — Sector & EF reference (static + Athena sector data)
5. `appendix_e_template.json` — Glossary (fully static)
6. `query_appendix_data_quality.sql` — New Athena query for Appendix B population

---

## References
- GRI 305:2016 Disclosure requirements (clause 2.1.c-e)
- PCAF Global GHG Standard 2nd Ed. Chapter 6 (Reporting Requirements)
- ESRS 2 General Disclosures BP-1, BP-2 (basis for preparation, uncertainty)
- GHG Protocol Corporate Standard Chapter 7 (Managing Inventory Quality)
- BRI Sustainability Report 2023 (appendix structure reference)
- BCA Sustainability Report 2025 (financed emissions methodology notes)

