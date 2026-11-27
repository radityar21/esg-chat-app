import { BANK } from './bank'
// Capability 3 — PCAF data quality, TKBI green finance, peer benchmark (synthetic)
export const PCAF_CLASSES = [
  { id: 'corp', name: 'Business loans & unlisted equity', outstanding: 168, dist: [4, 18, 34, 30, 14], action: 'Collect audited borrower emissions for the top 40 borrowers (covers 62% of the class).', target: [10, 30, 34, 18, 8], system: 'Core Banking + borrower portal' },
  { id: 'listed', name: 'Listed equity & corporate bonds', outstanding: 46, dist: [22, 38, 24, 12, 4], action: 'Switch to reported emissions from sustainability reports via the Knowledge Base.', target: [30, 42, 20, 6, 2], system: 'Treasury + KB' },
  { id: 'pf', name: 'Project finance', outstanding: 61, dist: [6, 22, 30, 28, 14], action: 'Require project-level energy and production data in loan covenants.', target: [14, 32, 30, 18, 6], system: 'Core Banking · Project finance desk' },
  { id: 'cre', name: 'Commercial real estate', outstanding: 47, dist: [0, 6, 18, 46, 30], action: 'Request actual building energy data from borrowers to move from score 4 to score 2.', target: [4, 24, 34, 28, 10], system: 'Core Banking + building-energy APIs' },
  { id: 'mort', name: 'Mortgages', outstanding: 112, dist: [0, 0, 8, 22, 70], action: 'Use EPC / building-type averages and regional grid factors to reach score 3-4.', target: [0, 0, 24, 46, 30], system: 'Core Banking' },
  { id: 'mv', name: 'Motor vehicle loans', outstanding: 86, dist: [0, 0, 12, 38, 50], action: 'Use VIN-based fuel-type data from the multifinance subsidiary.', target: [0, 4, 30, 44, 22], system: 'BNS Finance system' },
]

export const weightedScore = (dist) => dist.reduce((a, p, i) => a + p * (i + 1), 0) / dist.reduce((a, p) => a + p, 0)
export const portfolioScore = (useTarget = false, classes = PCAF_CLASSES) => {
  const tot = classes.reduce((a, c) => a + c.outstanding, 0)
  return classes.reduce((a, c) => a + c.outstanding * weightedScore(useTarget ? c.target : c.dist), 0) / tot
}
export const scoreDistribution = (useTarget = false, classes = PCAF_CLASSES) => {
  const tot = classes.reduce((a, c) => a + c.outstanding, 0)
  return [1, 2, 3, 4, 5].map((s, i) => ({
    score: `Score ${s}`,
    pct: classes.reduce((a, c) => a + (c.outstanding * (useTarget ? c.target : c.dist)[i]) / 100, 0) / tot * 100,
  }))
}
export const PCAF_COLORS = ['#06d6a0', '#4f8cf7', '#7c5cfc', '#fbbf24', '#ef4444']

// TKBI-aligned classification of the lending book (IDR trillion)
export const TKBI = [
  { name: 'Green', value: 118, color: '#06d6a0' },
  { name: 'Transition', value: 164, color: '#fbbf24' },
  { name: 'Brown', value: 74, color: '#ef4444' },
  { name: 'Not yet classified', value: 164, color: '#475569' },
]

export const GREEN_TREND = [
  { year: '2021', actual: 8.1, target: 8 },
  { year: '2022', actual: 10.4, target: 11 },
  { year: '2023', actual: 14.2, target: 14 },
  { year: '2024', actual: 18.6, target: 17.5 },
  { year: '2025', actual: 22.7, target: 21 },
  { year: '2026', actual: null, proj: 26.2, target: 24.5 },
  { year: '2027', actual: null, proj: 29.9, target: 28 },
  { year: '2028', actual: null, proj: 33.4, target: 31.5 },
  { year: '2029', actual: null, proj: 36.9, target: 35 },
  { year: '2030', actual: null, proj: 40.1, target: 40 },
]

export const TKBI_SECTORS = [
  { sector: 'Renewable energy', green: 38, transition: 4, brown: 0 },
  { sector: 'Sustainable agriculture', green: 12, transition: 22, brown: 6 },
  { sector: 'Green buildings', green: 21, transition: 18, brown: 3 },
  { sector: 'Transport', green: 14, transition: 28, brown: 9 },
  { sector: 'Industry & manufacturing', green: 18, transition: 46, brown: 22 },
  { sector: 'Mining & energy (fossil)', green: 0, transition: 14, brown: 34 },
]

// Peer benchmark — scores 0-100, pillar weights E35 / S35 / G30. Illustrative.
export const WEIGHTS = { E: 0.35, S: 0.35, G: 0.3 }
export const PEERS = [
  { id: 'bns', name: 'Bank Nusantara Sejahtera', us: true, E: 74, S: 71, G: 78, intensity: 10.4, green: 22.7, fem: 31, y: [58, 61, 64, 68, 74] },
  { id: 'pa', name: 'Domestic Peer A', E: 69, S: 74, G: 81, intensity: 11.8, green: 19.5, fem: 36, y: [60, 62, 65, 67, 71] },
  { id: 'pb', name: 'Domestic Peer B', E: 66, S: 68, G: 76, intensity: 13.1, green: 17.2, fem: 29, y: [55, 58, 61, 64, 67] },
  { id: 'pc', name: 'Domestic Peer C', E: 71, S: 66, G: 74, intensity: 12.2, green: 20.1, fem: 33, y: [57, 60, 62, 66, 70] },
  { id: 'ra', name: 'Regional Peer A', E: 82, S: 79, G: 88, intensity: 7.9, green: 29.4, fem: 41, y: [70, 73, 76, 79, 82] },
  { id: 'rb', name: 'Regional Peer B', E: 78, S: 77, G: 85, intensity: 8.8, green: 26.8, fem: 39, y: [66, 70, 73, 76, 79] },
]
export const composite = (p) => p.E * WEIGHTS.E + p.S * WEIGHTS.S + p.G * WEIGHTS.G

export const DEMO_DATASET = {
  PCAF: PCAF_CLASSES, financedMt: BANK.scope3Cat15 / 1e6, loanTn: 520, TKBI, GREEN_TREND, TKBI_SECTORS, PEERS, target2030: 40, todayYear: '2025', yearLabel: '2025', illustrativeTarget: false,
}

const shiftBetter = (dist, share = 0.3) => {
  const t = [...dist]
  for (let i = 1; i < t.length; i += 1) { const m = t[i] * share; t[i] -= m; t[i - 1] += m }
  return t.map((v) => Math.round(v * 10) / 10)
}

// Adapt GET /portfolio to the dataset shape used by the Portfolio page.
export function datasetFromApi(d) {
  const info = Object.fromEntries(PCAF_CLASSES.map((c) => [c.id, c]))
  const PCAF = d.pcaf.classes.map((c) => ({
    id: c.id, name: c.name, outstanding: c.outstanding_tn, dist: c.dist_pct, target: shiftBetter(c.dist_pct),
    action: info[c.id]?.action || 'Collect borrower-reported emissions to move up one PCAF tier.', system: info[c.id]?.system || 'Core Banking',
  }))
  const k = d.tkbi
  const colors = { Green: '#06d6a0', Transition: '#fbbf24', Brown: '#ef4444' }
  const TKBI_ = [['Green', k.green_tn], ['Transition', k.transition_tn], ['Brown', k.brown_tn]].map(([name, value]) => ({ name, value, color: colors[name] }))
  const pts = d.green_trend.points
  const lastActual = [...pts].reverse().find((p) => p.kind === 'actual')
  const target = d.green_trend.target_2030_pct
  const GREEN = pts.map((p) => ({ year: String(p.year), actual: p.kind === 'actual' ? p.green_ratio_pct : null, proj: p.kind === 'projection' ? p.green_ratio_pct : null, target: p.year >= lastActual.year ? target : null }))
  const rows = d.benchmark.rows
  const PEERS_ = rows.map((r) => ({ id: r.id, name: r.name, us: !!r.us, E: r.E, S: r.S, G: r.G, intensity: r.intensity, green: r.green, c: r.composite }))
  const fin = d.pcaf.classes.reduce((a, c) => a + (c.financed_tco2e || 0), 0) / 1e6
  return {
    PCAF, financedMt: fin, loanTn: d.pcaf.total_outstanding_tn, TKBI: TKBI_, GREEN_TREND: GREEN,
    TKBI_SECTORS: k.sectors.map((s) => ({ sector: s.sector, green: s.green_tn, transition: s.transition_tn, brown: s.brown_tn })),
    PEERS: PEERS_, target2030: target, todayYear: String(lastActual.year), yearLabel: String(d.pcaf.year), illustrativeTarget: true,
    tkbiBasis: k.basis, trendBasis: d.green_trend.basis,
  }
}
