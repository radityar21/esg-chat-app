// Capability 1 — ESG Compliance Intelligence (synthetic demo data)
export const PILLARS = [
  { id: 'gov', name: 'Governance', color: '#4f8cf7' },
  { id: 'str', name: 'Strategy', color: '#7c5cfc' },
  { id: 'rsk', name: 'Risk Management', color: '#fbbf24' },
  { id: 'met', name: 'Metrics & Targets', color: '#06d6a0' },
]

// status: ready | partial | gap — w = weight (1-3)
export const CHECKLIST = [
  // Governance
  { id: 'G1', pillar: 'gov', req: 'Board oversight of climate-related risks and opportunities', status: 'ready', w: 3, system: 'Corporate Secretary', rec: '' },
  { id: 'G2', pillar: 'gov', req: "Management's role and competence on climate topics", status: 'ready', w: 2, system: 'HR System', rec: '' },
  { id: 'G3', pillar: 'gov', req: 'Sustainability committee meetings with climate agenda', status: 'ready', w: 2, system: 'GRC Platform', rec: '' },
  { id: 'G4', pillar: 'gov', req: 'Remuneration linked to ESG / climate KPIs', status: 'partial', w: 1, system: 'HR / Payroll', rec: 'Export 2025 Director KPI scorecards with ESG weighting from the HR performance module.' },
  { id: 'G5', pillar: 'gov', req: 'Independent assurance over the sustainability report', status: 'gap', w: 3, system: 'Internal Audit + external assurer', rec: 'Engage an assurer and collect the assurance scope letter. Core Banking trial balance is not needed; Internal Audit workpapers are.' },
  // Strategy
  { id: 'S1', pillar: 'str', req: 'Climate risks and opportunities by time horizon', status: 'ready', w: 3, system: 'Risk Management', rec: '' },
  { id: 'S2', pillar: 'str', req: 'Impact on business model and value chain', status: 'ready', w: 2, system: 'Strategy Office', rec: '' },
  { id: 'S3', pillar: 'str', req: 'Transition plan and net-zero commitment', status: 'gap', w: 3, system: 'Strategy Office', rec: 'Collect Board-approved decarbonisation roadmap and sector-level financed-emissions targets (2030 / 2050).' },
  { id: 'S4', pillar: 'str', req: 'Scenario analysis: 1.5°C, 2°C and higher', status: 'partial', w: 3, system: 'Risk Management', rec: 'Run the Scenario Engine and attach output to the Risk Management section (available in Reports & Scenarios).' },
  { id: 'S5', pillar: 'str', req: 'Financial effects on position, performance, cash flow', status: 'gap', w: 2, system: 'Finance / Core Banking', rec: 'Pull ECL by sector from Core Banking and map the scenario ΔECL to the financial statements.' },
  // Risk management
  { id: 'R1', pillar: 'rsk', req: 'Process to identify and assess climate risks', status: 'ready', w: 2, system: 'Risk Management', rec: '' },
  { id: 'R2', pillar: 'rsk', req: 'Integration into enterprise risk management', status: 'ready', w: 3, system: 'Risk Management', rec: '' },
  { id: 'R3', pillar: 'rsk', req: 'Physical risk exposure of collateral (geo-tagged)', status: 'gap', w: 3, system: 'Core Banking · Collateral Register', rec: 'Collateral register lacks latitude/longitude for 31% of property collateral. Request geocoding from Collateral Management.' },
  { id: 'R4', pillar: 'rsk', req: 'Transition risk heatmap by sector', status: 'ready', w: 2, system: 'Risk Management', rec: '' },
  { id: 'R5', pillar: 'rsk', req: 'Sector exposure limits in Risk Appetite Statement', status: 'ready', w: 2, system: 'Risk Management', rec: '' },
  // Metrics & targets
  { id: 'M1', pillar: 'met', req: 'Scope 1 GHG emissions', status: 'ready', w: 3, system: 'Energy API / Facilities', rec: '' },
  { id: 'M2', pillar: 'met', req: 'Scope 2 GHG emissions (location and market based)', status: 'ready', w: 3, system: 'Energy API / Utility', rec: '' },
  { id: 'M3', pillar: 'met', req: 'Scope 3 Category 15 financed emissions (PCAF)', status: 'partial', w: 3, system: 'Core Banking · Loan Book', rec: 'Commercial real estate and project finance are at PCAF score 4. Request borrower energy data to reach score 2-3.' },
  { id: 'M4', pillar: 'met', req: 'GHG emissions intensity', status: 'ready', w: 2, system: 'Finance', rec: '' },
  { id: 'M5', pillar: 'met', req: 'Climate targets and progress tracking', status: 'ready', w: 3, system: 'Sustainability Office', rec: '' },
  { id: 'M6', pillar: 'met', req: 'Green finance ratio vs. sustainable finance action plan', status: 'ready', w: 2, system: 'Core Banking · Loan Book', rec: '' },
  { id: 'M7', pillar: 'met', req: 'Internal carbon price', status: 'partial', w: 1, system: 'Risk / Treasury', rec: 'Document the shadow carbon price used in credit appraisal for high-emission sectors.' },
]

// Items with status "unknown" (the check itself failed) are left out of the score instead of counting as gaps.
export const score = (items, fixed = new Set()) => {
  const known = items.filter((i) => fixed.has(i.id) || i.status !== 'unknown')
  const cov = (i) => (fixed.has(i.id) ? 1 : i.status === 'ready' ? 1 : i.status === 'partial' ? 0.5 : 0)
  const tot = known.reduce((a, i) => a + i.w, 0)
  return tot ? (known.reduce((a, i) => a + i.w * cov(i), 0) / tot) * 100 : null
}

export const pillarScores = (fixed = new Set(), items = CHECKLIST) =>
  PILLARS.map((p) => ({ ...p, score: score(items.filter((i) => i.pillar === p.id), fixed) }))

// ── Regulatory change detection (simulated feed) ──────────────────────────
export const SOURCES = [
  { id: 'ojk', name: 'OJK — Regulations & Consultations', icon: 'ojk' },
  { id: 'dsak', name: 'DSAK IAI — Sustainability Standards', icon: 'dsak' },
  { id: 'ifrs', name: 'IFRS Foundation / ISSB', icon: 'ifrs' },
  { id: 'efrag', name: 'EFRAG — ESRS Implementation', icon: 'efrag' },
]

export const ALERTS_BASE = [
  {
    id: 'A-0912', date: '2026-11-18', source: 'DSAK IAI', severity: 'medium',
    title: 'Technical clarification on Scope 3 Category 15 measurement for financial institutions',
    impact: ['Metrics & Targets', 'Scope 3 PCAF section'], checklist: 'M3',
    action: 'Align PCAF data-quality disclosure wording with the clarification.',
  },
  {
    id: 'A-0897', date: '2026-11-06', source: 'IFRS Foundation / ISSB', severity: 'low',
    title: 'ISSB amendments to IFRS S2 for GHG emissions disclosures: transition relief',
    impact: ['IFRS S2 overlay'], checklist: 'M2',
    action: 'Update IFRS S2 overlay prompt; no change to numerical outputs.',
  },
  {
    id: 'A-0871', date: '2026-10-22', source: 'EFRAG', severity: 'low',
    title: 'ESRS E1 implementation guidance: transition plan datapoints',
    impact: ['CSRD E1 overlay', 'Strategy'], checklist: 'S3',
    action: 'Add transition-plan datapoints to the CSRD E1 template.',
  },
]

export const ALERT_NEW = {
  id: 'A-0923', date: '2026-11-27', source: 'OJK', severity: 'high', isNew: true,
  title: 'OJK finalises rule requiring independent assurance of sustainability reports',
  impact: ['Governance', 'Assurance statement', 'Report template'], checklist: 'G5',
  action: 'Add an Assurance Statement section and update the Governance template.',
  templateBefore: 'Governance. The Board of Directors oversees climate-related risks through the Sustainability Committee, which met 6 times in the reporting year.',
  templateAfter: 'Governance. The Board of Directors oversees climate-related risks through the Sustainability Committee, which met 6 times in the reporting year.\n+ Assurance. The sustainability report has been subject to independent limited assurance by [Assurer Name] under [Standard]. The assurance statement is presented in Section 9. [NEW: required by OJK final rule]',
}
