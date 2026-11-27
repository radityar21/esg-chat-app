"""
Generate a visually rich DOCX brochure for the Intelligent Report Generation Platform.
Run: python generate_brochure_docx.py
Output: BROCHURE_INTELLIGENT_REPORTING.docx
"""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
import os

# ─── Color Palette ────────────────────────────────────────────────────────────
DARK_BLUE = RGBColor(0x1B, 0x3A, 0x6B)
ACCENT_BLUE = RGBColor(0x4F, 0x8C, 0xF7)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF8, 0xFA, 0xFC)
GRAY_500 = RGBColor(0x64, 0x74, 0x8B)
GRAY_700 = RGBColor(0x33, 0x41, 0x55)

doc = Document()

# ─── Page Setup ───────────────────────────────────────────────────────────────
section = doc.sections[0]
section.page_width = Cm(21)
section.page_height = Cm(29.7)
section.top_margin = Cm(2)
section.bottom_margin = Cm(2)
section.left_margin = Cm(2.5)
section.right_margin = Cm(2.5)

# ─── Helper Functions ─────────────────────────────────────────────────────────

def set_cell_shading(cell, color_hex):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading)

def add_styled_table(headers, rows, header_color="0F172A"):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(9)
                run.font.color.rgb = WHITE
        set_cell_shading(cell, header_color)
    for r_idx, row_data in enumerate(rows):
        for c_idx, val in enumerate(row_data):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = str(val)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
                    run.font.color.rgb = GRAY_700
            if r_idx % 2 == 0:
                set_cell_shading(cell, "F1F5F9")

def heading(text, level=1, color=DARK_BLUE):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = color

def body(text, bold=False, color=GRAY_700, size=Pt(10.5)):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.size = size
    run.font.color.rgb = color
    p.paragraph_format.space_after = Pt(6)

def callout(text, bg="EBF5FF"):
    table = doc.add_table(rows=1, cols=1)
    cell = table.rows[0].cells[0]
    cell.text = text
    for p in cell.paragraphs:
        for run in p.runs:
            run.font.size = Pt(10)
            run.font.italic = True
            run.font.color.rgb = DARK_BLUE
    set_cell_shading(cell, bg)
    doc.add_paragraph()

def kpi_row(kpis):
    table = doc.add_table(rows=2, cols=len(kpis))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (value, label) in enumerate(kpis):
        cv = table.rows[0].cells[i]
        cv.text = value
        for p in cv.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(22)
                run.font.color.rgb = ACCENT_BLUE
        set_cell_shading(cv, "F0F7FF")
        cl = table.rows[1].cells[i]
        cl.text = label
        for p in cl.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.font.size = Pt(8.5)
                run.font.color.rgb = GRAY_500
        set_cell_shading(cl, "F0F7FF")
    doc.add_paragraph()

# ═══════════════════════════════════════════════════════════════════════════════
# COVER PAGE
# ═══════════════════════════════════════════════════════════════════════════════
doc.add_paragraph()
doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("🧠").font.size = Pt(48)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Intelligent Report\nGeneration Platform")
run.bold = True
run.font.size = Pt(28)
run.font.color.rgb = DARK_BLUE

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("AI-Powered Automated Document Generation\nAny Industry  •  Any Standard  •  Any Format")
run.font.size = Pt(13)
run.font.color.rgb = GRAY_500

doc.add_paragraph()
doc.add_paragraph()

kpi_row([
    ("99%", "Faster Than Manual"),
    ("421%", "3-Year ROI*"),
    ("<5 min", "Per Report"),
    ("$0.35", "Per Document"),
])

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("By Tokaicom Mitra Indonesia (Tokai Group)")
run.font.size = Pt(11)
run.font.color.rgb = GRAY_700
run.bold = True

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Built on Amazon Web Services")
run.font.size = Pt(9)
run.font.color.rgb = GRAY_500

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("*IDC/TechTarget, 'The Business Value of Amazon Bedrock' (2025)")
run.font.size = Pt(7.5)
run.font.color.rgb = GRAY_500
run.italic = True

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# THE PROBLEM (Generic — not ESG specific)
# ═══════════════════════════════════════════════════════════════════════════════
heading("The Problem", level=1)
heading("Everyone Has Reports. Nobody Enjoys Making Them.", level=2, color=GRAY_700)

body("Across every industry, skilled professionals spend a disproportionate amount of time producing structured documents — reports, filings, memos, analyses — that follow the same predictable pattern cycle after cycle.")

doc.add_paragraph()
add_styled_table(
    ["Challenge", "What It Costs You"],
    [
        ["⏱️ It takes too long", "6-8 weeks per report cycle, 3-5 people involved full-time"],
        ["🔄 Same structure, every time", "Report rewritten from scratch despite an identical format each period"],
        ["⚠️ Errors creep in", "Manual number copying between systems introduces credibility-damaging mistakes"],
        ["📋 Multiple formats required", "Same data must be presented differently for different audiences or regulators"],
        ["💸 Expensive to outsource", "$30K-$120K per cycle for external consultants or specialized staff"],
        ["🔍 No traceability", "No clear link between the final document and its source data"],
        ["📊 Insight arrives too late", "Reports produced quarterly/annually — leadership sees issues months late"],
    ],
    header_color="1B3A6B"
)

doc.add_paragraph()
callout(
    "Imagine a compliance team that spends 8 weeks every cycle manually compiling data from multiple systems, "
    "writing narratives, and reformatting for three different regulatory bodies — knowing that any error could trigger an audit finding.",
    bg="FFF7ED"
)

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# THE SOLUTION (Generic)
# ═══════════════════════════════════════════════════════════════════════════════
heading("The Solution", level=1)
heading("Simple for Users. Sophisticated Under the Hood.", level=2, color=GRAY_700)

body("From the user's perspective, the experience is straightforward:")
body("1. ASK — Type what you need in plain language (e.g., \"Generate our quarterly compliance report\")")
body("2. WAIT — The system gathers data, generates content, validates accuracy, and assembles the document (3-5 minutes)")
body("3. DOWNLOAD — Receive a professionally formatted Word document, ready for review or submission")

doc.add_paragraph()
add_styled_table(
    ["Step", "What Happens", "Why It Matters"],
    [
        ["Validate", "Checks request parameters", "Prevents wasted processing on bad input"],
        ["Gather Data", "Queries your data sources automatically", "Single source of truth — no manual export"],
        ["Generate", "AI writes each section using data + reference docs", "Consistent, grounded in facts, not hallucinated"],
        ["Quality Check", "21+ automated rules verify every number", "Catches errors before they reach anyone"],
        ["Auto-Retry", "Failed sections regenerated automatically", "No human intervention needed for fixes"],
        ["Assemble", "Branded Word doc with TOC, headers, tables", "Professional output, zero manual formatting"],
        ["Deliver", "Secure, time-limited download link", "Encrypted access, audit trail preserved"],
    ],
    header_color="064E3B"
)

doc.add_paragraph()
heading("What Makes This Different from Generic AI Chat", level=2, color=GRAY_700)

add_styled_table(
    ["Aspect", "Generic AI (ChatGPT)", "This Platform"],
    [
        ["Data access", "None — you paste manually", "Directly queries your systems"],
        ["Accuracy", "Can hallucinate numbers", "Every figure validated against source"],
        ["Format", "Unformatted text", "Branded DOCX with TOC, tables, headers"],
        ["Compliance", "No standard awareness", "Built-in regulatory framework templates"],
        ["Audit trail", "None", "Full traceability: source → text → document"],
        ["Security", "Data leaves your org", "Runs entirely in your cloud environment"],
        ["Multi-section", "One prompt, one output", "7-15 sections with individual QA gates"],
    ],
    header_color="4F8CF7"
)

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# BEFORE VS AFTER (Generic)
# ═══════════════════════════════════════════════════════════════════════════════
heading("Before vs. After", level=1)

add_styled_table(
    ["", "❌ Before (Manual)", "✅ After (Platform)"],
    [
        ["Data Collection", "Export from 5+ systems, consolidate in Excel", "Automated from your data lake or databases"],
        ["Calculations", "Staff applies formulas manually", "Pre-computed with verified business logic"],
        ["Writing", "SME drafts narratives over 4-6 weeks", "AI generates in 2-3 minutes per section"],
        ["Quality Check", "Peer review (1-2 weeks, 3-5 rounds)", "21-rule automated validation, instant"],
        ["Multi-Format", "Rewrite for each audience/standard", "One click — all formats simultaneously"],
        ["Formatting", "Manual Word/PPT work (2-3 days)", "Auto-assembled with your corporate branding"],
        ["Visibility", "Periodic snapshot only", "Real-time dashboard with live KPIs"],
        ["Time to Deliver", "6-8 weeks", "Under 5 minutes"],
        ["Cost", "$30K-$120K per cycle", "~$200/month infrastructure"],
    ],
    header_color="1B3A6B"
)

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS — ESG as ONE case study among many
# ═══════════════════════════════════════════════════════════════════════════════
heading("Proven Results", level=1)
heading("Demonstrated with ESG Sustainability Reporting (One of Many Possible Use Cases)", level=2, color=GRAY_700)
body("To prove the architecture, we deployed the platform for a financial institution needing multi-framework sustainability reports. The same pattern applies to any structured document generation.")

doc.add_paragraph()
kpi_row([
    ("99.9%", "Faster"),
    ("99%", "Cost Savings"),
    ("99.9%", "Data Accuracy"),
    ("4×", "Framework Coverage"),
])

add_styled_table(
    ["Measure", "Before (Manual)", "After (Platform)", "Improvement"],
    [
        ["Time to produce", "6-8 weeks", "3-5 minutes", "Over 99% reduction"],
        ["Cost per cycle", "$30K-$120K", "~$200/month", "Up to 99% savings"],
        ["Data accuracy", "~95%", "99.9% (validated)", "Near-zero errors"],
        ["Output formats", "1 per engagement", "4 simultaneously", "4× coverage"],
        ["Revision rounds", "3-5 cycles", "1 automated retry", "Eliminated"],
        ["Real-time visibility", "Annual only", "Live dashboard", "Always-on"],
        ["Staff dependency", "3-5 people, 2 months", "Zero (automated)", "Team freed for strategy"],
    ],
    header_color="064E3B"
)

doc.add_paragraph()
callout(
    "If the platform can produce a 15-section multi-framework regulatory report — pulling from 12 data tables, "
    "writing in compliance language, validating every number, and assembling a branded document — "
    "it can handle any structured report your organization needs.",
    bg="ECFDF5"
)

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# INDUSTRY METRICS
# ═══════════════════════════════════════════════════════════════════════════════
heading("Industry Benchmarks", level=1)
body("Published results from organizations using the same cloud services that power this platform:")

doc.add_paragraph()
add_styled_table(
    ["Organization", "Use Case", "Result", "Source"],
    [
        ["BlueOceanAI", "AI agents for operations", "97% efficiency gain", "AWS Case Study"],
        ["Genpact", "Document verification", "90% less manual work", "AWS Case Study"],
        ["Affinda", "Document processing", "90% cost + time reduction", "AWS Case Study"],
        ["Sonrai", "Research report generation", "Timelines halved, 5× fewer errors", "AWS Case Study"],
        ["CyberGRX", "Automated modeling", "8 days → 1 hour", "AWS Case Study"],
        ["OneMain Financial", "Process automation", "97.5% faster", "AWS Case Study"],
        ["Katalon", "Serverless analytics", "70%+ cost savings", "AWS Case Study"],
    ],
    header_color="4F8CF7"
)

doc.add_paragraph()
heading("Independent Research", level=2, color=GRAY_700)

add_styled_table(
    ["Metric", "Finding", "Source"],
    [
        ["ROI of Amazon Bedrock", "421% three-year ROI, payback in 9 months", "IDC / TechTarget (2025)"],
        ["Revenue impact", "Over $10M annual gains per organization", "IDC / TechTarget (2025)"],
        ["GenAI productivity potential", "$4.4 trillion in added value globally", "McKinsey (2023)"],
        ["Agentic AI automation", "60% of work hours theoretically automatable", "McKinsey (2025)"],
        ["Enterprise adoption by 2026", "80%+ will deploy GenAI in production", "Gartner (2023)"],
        ["AI document gen market", "$13.6B (2025) → $92.2B (2036)", "Future Market Insights"],
        ["GenAI software spending", "$299B (2025) → $895B (2028)", "Gartner (2025)"],
    ],
    header_color="7C5CFC"
)

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# USE CASES (Generic — multi-industry)
# ═══════════════════════════════════════════════════════════════════════════════
heading("Multi-Industry Application", level=1)
body("This platform is not a single-purpose tool. The same architecture applies to any domain where documents follow a predictable structure. Changing to a new report type takes 1-2 weeks of configuration — not months of development.")

doc.add_paragraph()
add_styled_table(
    ["Industry", "Example Use Case", "What Gets Automated"],
    [
        ["Banking & Finance", "Sustainability (ESG) Report", "Data + narrative + multi-framework formatting"],
        ["Banking & Finance", "Regulatory Filing (Central Bank)", "Compliance report from core systems"],
        ["Banking & Finance", "Credit Analysis Memo", "Financial analysis + risk assessment doc"],
        ["Legal & Compliance", "Audit Findings Report", "Evidence → findings → recommendations"],
        ["Healthcare", "Clinical Discharge Summary", "Patient data → referral letter"],
        ["Construction", "Project Progress Report", "Schedule + costs → stakeholder update"],
        ["Consulting", "Market Analysis Report", "Research data → board-ready presentation"],
        ["Manufacturing", "Quality Inspection Report", "Sensor data → ISO compliance document"],
        ["Government", "Annual Performance Report", "KPI data → public accountability document"],
    ],
    header_color="1B3A6B"
)

doc.add_paragraph()
heading("Adapting to New Use Cases", level=2, color=GRAY_700)

add_styled_table(
    ["What Changes", "Effort", "Example"],
    [
        ["Input parameters", "Half a day", "Year, region, business unit, report type"],
        ["Data queries", "2-3 days", "Connect to different database tables or APIs"],
        ["Section templates", "1-2 days", "New prompt instructions per section"],
        ["Reference documents", "1 day", "Upload standards, policies, or guidelines"],
        ["Validation rules", "1-2 days", "Define what 'correct' looks like"],
        ["Document styling", "1 day", "Headers, fonts, logos, layout"],
        ["Total for new use case", "1-2 weeks", "Full production-ready report type"],
    ],
    header_color="064E3B"
)

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# SCREENSHOTS PLACEHOLDER
# ═══════════════════════════════════════════════════════════════════════════════
heading("Platform Screenshots", level=1)
body("The platform includes a modern web application with real-time dashboards, a chat interface, and a report management portal:")

doc.add_paragraph()

screenshots = [
    "Analytics Dashboard — Real-time KPIs and interactive charts",
    "Chat Interface — Natural language conversation to generate documents",
    "Report History — Full audit trail with status tracking and download links",
    "Generated Document — Professional DOCX output opened in Microsoft Word",
]

for title in screenshots:
    table = doc.add_table(rows=1, cols=1)
    cell = table.rows[0].cells[0]
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"\n\n[ INSERT SCREENSHOT: {title} ]\n\n")
    run.font.size = Pt(10)
    run.font.color.rgb = GRAY_500
    run.font.italic = True
    set_cell_shading(cell, "F1F5F9")
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cap.add_run(title)
    run.font.size = Pt(9)
    run.font.color.rgb = GRAY_700
    run.italic = True
    doc.add_paragraph()

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# CONCLUSION
# ═══════════════════════════════════════════════════════════════════════════════
heading("Conclusion", level=1)
heading("One Platform. Unlimited Report Types. Minutes Instead of Weeks.", level=2, color=GRAY_700)

doc.add_paragraph()

stakeholders = [
    ("For Leadership:", "Your team spends weeks producing reports that follow the same structure. This platform reduces that to minutes — freeing people to focus on analysis and strategy."),
    ("For Finance:", "External consultants cost $30K-$120K per report cycle. This platform costs under $200/month. Return on investment is measured in days, not years."),
    ("For Compliance:", "Multiple regulatory frameworks, one data source, automated validation. Every number is traceable to its origin. Audit trail is built in."),
    ("For Operations:", "No training required. No complex software to learn. Users type what they need and receive a finished document."),
]

for title, desc in stakeholders:
    p = doc.add_paragraph()
    run = p.add_run(title + " ")
    run.bold = True
    run.font.size = Pt(10.5)
    run.font.color.rgb = ACCENT_BLUE
    run = p.add_run(desc)
    run.font.size = Pt(10.5)
    run.font.color.rgb = GRAY_700

doc.add_paragraph()
heading("Getting Started", level=2, color=GRAY_700)

add_styled_table(
    ["Phase", "Timeline", "What Happens"],
    [
        ["Discovery", "Week 1", "Identify highest-value report type and map data sources"],
        ["Configuration", "Week 2-3", "Setup templates, connect data, define quality rules"],
        ["Testing", "Week 4", "Generate reports and compare against historical output"],
        ["Go-Live", "Week 5-6", "Production deployment and team walkthrough"],
    ],
    header_color="064E3B"
)

doc.add_paragraph()
body("First use case live in 6 weeks. Additional report types in 1-2 weeks each.", bold=True, color=ACCENT_BLUE)
body("Each subsequent use case reuses 80% of the infrastructure — your first deployment proves the platform, every one after costs a fraction of the first.")

doc.add_paragraph()
doc.add_paragraph()

# Footer
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("─" * 50)
run.font.color.rgb = LIGHT_GRAY

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Tokaicom Mitra Indonesia (Tokai Group)")
run.bold = True
run.font.size = Pt(12)
run.font.color.rgb = DARK_BLUE

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Intelligent Report Generation Platform\nBuilt on Amazon Web Services")
run.font.size = Pt(9)
run.font.color.rgb = GRAY_500

# ═══════════════════════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════════════════════
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BROCHURE_INTELLIGENT_REPORTING.docx")
doc.save(output_path)
print(f"Done! Brochure saved: {output_path}")
