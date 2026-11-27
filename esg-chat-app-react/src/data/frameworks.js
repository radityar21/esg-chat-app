// Capability 2 — Multi-framework disclosure mapping + scenario engine (synthetic, illustrative)
import { BANK } from './bank'

export const FRAMEWORKS = [
  { id: 'pspk', name: 'PSPK (OJK/IAI)', short: 'PSPK', color: '#06d6a0' },
  { id: 'gri', name: 'GRI 305 / 201', short: 'GRI', color: '#4f8cf7' },
  { id: 'ifrs', name: 'IFRS S2', short: 'IFRS S2', color: '#7c5cfc' },
  { id: 'csrd', name: 'CSRD · ESRS E1', short: 'CSRD', color: '#fbbf24' },
]

// ref: disclosure reference per framework (null = not required)
export const TOPICS = [
  { id: 'gov', name: 'Climate governance', pillar: 'Governance', refs: { pspk: 'PSPK 2 · Governance', gri: 'GRI 2-9', ifrs: 'S2 ¶5-7', csrd: 'ESRS 2 GOV-1' } },
  { id: 'strat', name: 'Climate strategy & opportunities', pillar: 'Strategy', refs: { pspk: 'PSPK 2 · Strategy', gri: null, ifrs: 'S2 ¶9-12', csrd: 'ESRS E1-SBM / E1-1' } },
  { id: 'tplan', name: 'Transition plan', pillar: 'Strategy', refs: { pspk: 'PSPK 2 · Strategy', gri: null, ifrs: 'S2 ¶14(a)(iv)', csrd: 'ESRS E1-1' } },
  { id: 'scen', name: 'Scenario analysis & resilience', pillar: 'Strategy', refs: { pspk: 'PSPK 2 · Strategy', gri: null, ifrs: 'S2 ¶22', csrd: 'ESRS E1-IRO / SBM-3' } },
  { id: 'fin', name: 'Financial effects of climate risk', pillar: 'Strategy', refs: { pspk: 'PSPK 2 · Strategy', gri: 'GRI 201-2', ifrs: 'S2 ¶15-21', csrd: 'ESRS E1-9' } },
  { id: 'rm', name: 'Climate risk management process', pillar: 'Risk Management', refs: { pspk: 'PSPK 2 · Risk Mgmt', gri: null, ifrs: 'S2 ¶24-26', csrd: 'ESRS 2 IRO-1' } },
  { id: 's1', name: 'Scope 1 GHG emissions', pillar: 'Metrics & Targets', refs: { pspk: 'PSPK 2 · Metrics', gri: 'GRI 305-1', ifrs: 'S2 ¶29(a)(i)', csrd: 'ESRS E1-6' } },
  { id: 's2', name: 'Scope 2 GHG emissions', pillar: 'Metrics & Targets', refs: { pspk: 'PSPK 2 · Metrics', gri: 'GRI 305-2', ifrs: 'S2 ¶29(a)(i)', csrd: 'ESRS E1-6' } },
  { id: 's3', name: 'Scope 3 · Cat 15 financed emissions', pillar: 'Metrics & Targets', refs: { pspk: 'PSPK 2 · Metrics', gri: 'GRI 305-3', ifrs: 'S2 ¶29(a)(iii)', csrd: 'ESRS E1-6' } },
  { id: 'int', name: 'GHG emissions intensity', pillar: 'Metrics & Targets', refs: { pspk: null, gri: 'GRI 305-4', ifrs: 'S2 ¶29(a)', csrd: 'ESRS E1-6' } },
  { id: 'red', name: 'Reduction of GHG emissions', pillar: 'Metrics & Targets', refs: { pspk: 'PSPK 2 · Targets', gri: 'GRI 305-5', ifrs: 'S2 ¶33-36', csrd: 'ESRS E1-4' } },
  { id: 'en', name: 'Energy consumption', pillar: 'Metrics & Targets', refs: { pspk: null, gri: 'GRI 302-1', ifrs: null, csrd: 'ESRS E1-5' } },
  { id: 'icp', name: 'Internal carbon price', pillar: 'Metrics & Targets', refs: { pspk: null, gri: null, ifrs: 'S2 ¶29(f)', csrd: 'ESRS E1-8' } },
]

export const overlapOf = (t) => Object.values(t.refs).filter(Boolean).length
export const overlapStats = () => {
  const total = TOPICS.reduce((a, t) => a + overlapOf(t), 0)
  const unique = TOPICS.length
  const shared = TOPICS.filter((t) => overlapOf(t) >= 3).length
  return { total, unique, shared, saved: Math.round((1 - unique / total) * 100) }
}

const f = (n) => Number(n).toLocaleString('en-US')
const NUMS = {
  s1: f(BANK.scope1) + ' tCO2e',
  s2: `${f(BANK.scope2Location)} tCO2e (location-based) and ${f(BANK.scope2Market)} tCO2e (market-based)`,
  s3: f(BANK.scope3Cat15) + ' tCO2e',
}

// Framework-specific phrasing for the same underlying dataset
export function renderDisclosure(topic, fw) {
  const ref = topic.refs[fw]
  if (!ref) return null
  const val = NUMS[topic.id]
  const subject = val ? `${topic.name}: ${val}` : topic.name
  const lead = {
    pspk: `Sesuai ${ref}, ${BANK.name} mengungkapkan ${subject.toLowerCase()} untuk periode ${BANK.fy}, dengan pendekatan kendali operasional.`,
    gri: `${ref} — ${subject}. Reported in tCO2e, gases included: CO2, CH4, N2O; consolidation: operational control; GWP source: IPCC AR6.`,
    ifrs: `${ref} — ${subject}. Measured under the GHG Protocol Corporate Standard; the entity discloses its measurement approach, inputs and assumptions, and any change from the prior period.`,
    csrd: `${ref} — ${subject}. Reported gross, with a breakdown by scope and, where applicable, the share of estimated data and the methodology applied.`,
  }[fw]
  return lead
}

// ── Scenario engine ───────────────────────────────────────────────────────
export const SCENARIOS = [
  { id: 's15', name: '1.5°C · Net Zero 2050', short: '1.5°C', color: '#06d6a0', carbon: 130, hazard: 1.0, greenCagr: 18 },
  { id: 's2', name: '2°C · Below 2°C', short: '2°C', color: '#4f8cf7', carbon: 75, hazard: 1.4, greenCagr: 12 },
  { id: 's3', name: '3°C+ · Current policies', short: '3°C+', color: '#ef4444', carbon: 25, hazard: 2.2, greenCagr: 6 },
]

// exposure in IDR trillion; sens = share of EBITDA lost per USD100/tCO2e
export const SECTORS = [
  { id: 'coal', name: 'Coal & mining', exposure: 38, sens: 0.55 },
  { id: 'oil', name: 'Oil & gas', exposure: 26, sens: 0.38 },
  { id: 'power', name: 'Power utilities', exposure: 44, sens: 0.34 },
  { id: 'cement', name: 'Cement & steel', exposure: 21, sens: 0.30 },
  { id: 'agri', name: 'Agriculture & palm oil', exposure: 52, sens: 0.12 },
  { id: 'trans', name: 'Transport & logistics', exposure: 33, sens: 0.15 },
  { id: 'cre', name: 'Commercial real estate', exposure: 47, sens: 0.06 },
]

const BASE = { collateralTn: 140, floodShare: 22, haircut: 0.03, greenBaseTn: 62, nim: 0.028, years: 5, passthrough: 0.05 }

// what-if overrides: carbonOverride (USD/t or null), shiftPct (reduce high-emission exposure), flood (%), greenBoost (pp CAGR)
export function runScenario(sc, wi = {}) {
  const carbon = wi.carbonOverride != null ? wi.carbonOverride : sc.carbon
  const shift = (wi.shiftPct ?? 0) / 100
  const flood = wi.flood ?? BASE.floodShare
  const boost = wi.greenBoost ?? 0
  const bySector = SECTORS.map((s) => {
    const exposure = ['coal', 'oil', 'power', 'cement'].includes(s.id) ? s.exposure * (1 - shift) : s.exposure
    const ebitdaHit = Math.min(1, s.sens * (carbon / 100))
    return { ...s, exposure, ebitdaHit, decl: exposure * ebitdaHit * BASE.passthrough }
  })
  const transition = bySector.reduce((a, s) => a + s.decl, 0)
  const physical = BASE.collateralTn * (flood / 100) * sc.hazard * BASE.haircut
  const cagr = (sc.greenCagr + boost) / 100
  const opportunity = BASE.greenBaseTn * (Math.pow(1 + cagr, BASE.years) - 1) * BASE.nim
  const net = opportunity - transition - physical
  return { sc, carbon, bySector, transition, physical, opportunity, net, pctLoans: (transition + physical) / BANK.totalLoansIdrTn * 100 }
}

export function narrative(r) {
  const f1 = (n) => n.toFixed(1)
  const worst = [...r.bySector].sort((a, b) => b.decl - a.decl)[0]
  return `Under the ${r.sc.name} scenario (carbon price USD ${Math.round(r.carbon)}/tCO2e by 2030), ${BANK.name} estimates additional expected credit losses of IDR ${f1(r.transition)} trillion from transition risk, concentrated in ${worst.name.toLowerCase()} (IDR ${f1(worst.decl)} trillion). Physical risk to property collateral adds IDR ${f1(r.physical)} trillion. Growth in green financing is expected to contribute IDR ${f1(r.opportunity)} trillion of incremental net interest income over five years. The net effect is IDR ${f1(r.net)} trillion. Combined transition and physical losses equal ${r.pctLoans.toFixed(2)}% of total loans.`
}
