
# Kiro Task: Implement Benchmark KB Documents + Advisory Recommendations in Report

## Context
The ESG report currently generates data-only disclosures (numbers + basic trend narrative).
We want to ADD:
1. **Benchmark KB documents** — reference data from BCA, DBS, OCBC, BRI, Mandiri reports
2. **Advisory recommendations** per section — specific, data-backed, referencing which bank has done it
3. **Recommendation block** as a required element in section templates

The system already has Bedrock KB (OpenSearch Serverless vector store) with RAG retrieval
injected via `{rag_context_*}` placeholders in section templates.

## Architecture (NO CHANGES needed to infra)
```
Bedrock KB (OpenSearch Serverless)
    ↓ semantic search
{rag_context_social} injected into prompt template
    ↓
SectionGen (Lambda #3) → Claude generates narrative + recommendations
```

KB bucket: `s3://esg-kb-documents-061039769766/`
KB ID: WVREXI1LEI
Chunking: Semantic
RAG threshold: 0.40

## Deliverables

### Deliverable 1: Benchmark KB Documents (Upload to S3 KB bucket)

Create the following markdown documents. Each must be:
- Structured with clear headers and tables
- Include source attribution (bank name, report year, page/section)
- Include specific numeric benchmarks
- Formatted for optimal semantic chunking (one topic per section, 200-400 tokens per chunk)

#### Document 1: `benchmarks_environment_banking_id.md`
Content must cover (sourced from reports in our KB):

**GHG Emissions Benchmarks:**
| Bank | Scope 1 (tCO₂e) | Scope 2 (tCO₂e) | Scope 3 Financed (tCO₂e) | Total | Intensity |
- OCBC Indonesia 2024: Total 20,609 tCO₂e (down from 21,398 in 2023), carbon neutral Scope 1,2,3 (business trips)
- DBS 2023: Full PCAF disclosure, NZBA signatory, RE100 member
- BRI 2023: GRI 305-1 to 305-7 full coverage

**Energy Benchmarks:**
- OCBC Indonesia 2024: 83,889 GJ total, 23,144,925 kWh electricity
- Include energy intensity per employee / per revenue where available

**Water & Waste:**
- OCBC 2024: 116,153 m³ water consumption
- OCBC 2024: 11,000 mangrove seeds (biodiversity)

**Reduction Initiatives:**
- DBS: RE100 membership, renewable energy procurement
- OCBC: Smart & Green Building transformation
- BCA: Climate Change Strategy as internal guideline, exclusion list for high environmental risk

#### Document 2: `benchmarks_social_banking_id.md`
Content must cover:

**Training & Development:**
| Bank | Avg Hours/FTE | Notes | Source |
- OCBC Indonesia 2024: 62.6 hours/employee (target minimum: 40 hours)
- DBS 2023: 32.5 hours (permanent employees), 40.3 hours (SVP-MD level)
- DBS note: declining hours ≠ declining quality (shift to concise impactful modules)
- OCBC 2024: 215 counseling sessions for 124 employees (well-being program)

**Gender Diversity:**
| Bank | Female Workforce % | Female Management % | Female Senior/Board % | Source |
- BCA 2025: 61.1% total, 61.6% managerial (exceeds 35% target), 38.5% top management
- OCBC 2024: 52% total, 40% senior leadership
- DBS 2023: 50% total, 41% SVP to MD level
- Mandiri 2023: 52% total, 35% above AVP, 22% BoD & BoC

**Turnover & Retention:**
- BCA: detailed turnover table with retention strategies (remuneration, career development, safe facilities)
- OCBC 2024: 942 total turnover
- DBS 2023: GRI 401-1 externally assured

**Employee Programs:**
- DBS: 30% internal fill rate (40% excluding entry level)
- DBS: gender-diverse interview panels
- OCBC: KAWA Programme (719 participants, women empowerment)
- DBS: Women in Banking Communities, Reimagine programme

#### Document 3: `benchmarks_governance_banking_id.md`
Content must cover:

**Governance Structure:**
- BCA: ESG Subdivision → Corsec-IVR & ESG Division → Director of Planning & Finance
- BCA: ESG KPIs in BoD performance, BoC supervisory role on SFAP
- OCBC: GCG Rating 1 "Sangat Baik"

**Anti-Corruption:**
- BRI: GRI 205-1 operations assessed
- DBS: GRI 205-2 externally assured
- OCBC: Bank-wide e-learning anti-corruption
- BCA: Whistleblowing mechanism with resolution % as KPI

**Cybersecurity:**
- OCBC 2024: Cyber Level 1: 39%, Level 2: 34%, vulnerability rate 1.13%, reporting rate 18.45%

**Sustainable Finance:**
- OCBC 2024: Rp37.85T sustainable finance (22% of total loans), +17% YoY
- OCBC 2024: Rp16.02T green financing (42.3% of sustainable portfolio)
- OCBC 2024: Green Mortgage Rp25.90B, Sustainable Investment Rp1.90T (+46% YoY)
- DBS: NZBA aligned, GFANZ, TRACTION project for transition finance

#### Document 4: `benchmarks_framework_compliance.md`
Content must cover:

**External Assurance:**
- DBS 2023: Limited assurance by PwC, 17 GRI disclosures assured, ISAE 3000 standard
- Assured disclosures include: 305-1, 305-2, 305-3, 401-1, 404-1, 405-1

**ESG Ratings:**
- DBS: MSCI A, Sustainalytics 18.5 (Low Risk, 20th percentile), RobecoSAM 53/100 (88th percentile)
- DBS: Bloomberg Gender Equality Index (since 2018), FTSE4Good (since 2017)

**Required Indices:**
- GRI Content Index (in accordance 2021): all banks
- POJK 51/POJK.03/2017 Index: OCBC, BCA
- TCFD Content Index: DBS, OCBC
- SASB Index: OCBC

**Regulatory Targets (Indonesia):**
- OJK: 30% female representation target
- OJK: Sustainable Finance Action Plan (SFAP) mandatory for banks
- POJK requirements for ESG risk integration

#### Document 5: `recommendation_playbook.md`
Content structure — for each metric area, provide:

```markdown
## [Metric Area]

### If metric is DECLINING:
- Diagnosis: What typically causes this decline in banking sector
- Recommendations: 2-3 specific actions with expected impact
- Bank reference: Which bank successfully addressed this + how
- Target suggestion: Realistic improvement target based on peer benchmarks

### If metric is IMPROVING:
- Context: Where does the institution stand vs peers
- Recommendations: How to sustain/accelerate improvement
- Bank reference: Best-in-class example
- Next milestone: What the next target should be
```

Areas to cover:
1. Training hours declining → Ref: DBS "concise impactful modules" strategy
2. Female representation declining → Ref: BCA (61.6%), DBS (gender-diverse panels)
3. Turnover improving → Ref: BCA retention strategy
4. Emissions increasing → Ref: OCBC carbon neutral, DBS RE100
5. PCAF data quality low → Ref: DBS improvement roadmap
6. No external assurance → Ref: DBS PwC limited assurance on 17 disclosures

### Deliverable 2: Update Section Templates — Add Recommendation Block

For EACH existing section template (scope1, scope2, scope3_pcaf, intensity, social),
add the following block to REQUIRED ELEMENTS:

```
#### Advisory Recommendation Block (MANDATORY)
Generate 2-3 specific, actionable recommendations based on the data trends:

FORMAT per recommendation:
- **Finding**: [One-sentence observation from data, e.g., "Training hours declined 23% YoY"]
- **Benchmark**: [Peer comparison from RAG context, e.g., "Below OCBC Indonesia's 62.6 hrs/FTE"]
- **Recommendation**: [Specific action, e.g., "Implement blended learning (e-learning + workshops) to target 55 hrs/FTE"]
- **Reference**: [Bank that has done this, e.g., "DBS shifted to concise impactful modules while maintaining development quality"]
- **Priority**: [High/Medium/Low based on gap size]

RULES:
- Recommendations MUST reference specific bank examples from RAG context
- Recommendations MUST include numeric targets based on peer benchmarks
- Do NOT generate generic recommendations like "improve this area"
- If metric is IMPROVING, acknowledge it and suggest next milestone
- If metric is DECLINING, flag as risk and provide corrective action
- Each recommendation must be different (no repetition across scopes)
```

### Deliverable 3: Update Lambda #3 (SectionGen) — RAG Query Enhancement

Currently, SectionGen queries KB with generic terms. Update the KB retrieval query
to specifically pull benchmark data:

```python
# Current (generic):
rag_query = f"{section_id} {framework} methodology disclosure"

# Updated (benchmark-focused):
rag_queries = [
    f"{section_id} {framework} methodology disclosure requirements",
    f"benchmark {metric_area} Indonesian banking sector best practice peer comparison",
]

# Run both queries, merge results (deduplicate), inject as rag_context
```

This ensures the model receives BOTH framework requirements AND benchmark data.

### Deliverable 4: Verify RAG Retrieval

After uploading documents and syncing KB:
1. Test query: "Indonesian banking training hours benchmark per employee"
   Expected: returns OCBC 62.6 hrs, DBS 32.5 hrs data
2. Test query: "gender diversity female management percentage banking Indonesia"
   Expected: returns BCA 61.6%, OCBC 40%, DBS 41%, Mandiri 35%
3. Test query: "GHG emissions reduction best practice financial institution"
   Expected: returns OCBC carbon neutral, DBS RE100, BCA exclusion list

## File Locations

| Deliverable | Files to Create/Modify | Location |
|---|---|---|
| Benchmark docs (5 files) | `benchmarks_environment_banking_id.md`, `benchmarks_social_banking_id.md`, `benchmarks_governance_banking_id.md`, `benchmarks_framework_compliance.md`, `recommendation_playbook.md` | Upload to `s3://esg-kb-documents-061039769766/benchmarks/` |
| Template updates | All section templates (scope1, scope2, scope3, intensity, social) | `s3://esg-kb-documents-061039769766/prompts/templates/` |
| Lambda #3 update | `handler.py` — RAG query logic | Lambda #3 SectionGen |

## Deploy Order
1. Create 5 benchmark markdown files
2. Upload to S3: `s3://esg-kb-documents-061039769766/benchmarks/`
3. Sync Bedrock KB (re-index to pick up new documents)
4. Update section templates (add Advisory Recommendation Block)
5. Upload updated templates to S3
6. Update Lambda #3 handler.py (dual RAG query)
7. Deploy Lambda #3
8. Test: generate report → verify recommendations appear with bank references

## Acceptance Criteria
1. Each section in generated report includes 2-3 recommendations
2. Each recommendation references a specific bank (BCA, DBS, OCBC, BRI, or Mandiri)
3. Each recommendation includes a numeric benchmark/target
4. Recommendations are contextual (different for improving vs declining metrics)
5. RAG retrieval returns benchmark data when queried
6. No hallucinated bank references (all must exist in KB documents)

## Constraints
- NO architecture changes (same pipeline, same Lambdas)
- NO new Lambda functions
- Benchmark documents must be factual (from actual bank reports in our KB)
- Recommendations must always include "Reference: [Bank Name]" attribution
- Temperature remains 0.0 for deterministic output
- KB sync must complete before testing (allow 5-10 min for indexing)
