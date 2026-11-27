// View model for the Command Center. Demo mode builds it from the bundled demo data; live mode from the platform API.
import { BANK } from './bank'
import { CHECKLIST, score, ALERTS_BASE, ALERT_NEW } from './compliance'
import { overlapStats } from './frameworks'
import { portfolioScore, TKBI } from './portfolio'
import { runCosts } from './governance'
import { totals, TREND } from './ghg'

export function demoModel() {
  const t = totals()
  const ov = overlapStats()
  const fin = runCosts({ cache: true, batch: true })
  return {
    live: false, name: BANK.name, period: BANK.fy, baseYear: 2022,
    readiness: score(CHECKLIST), openItems: CHECKLIST.filter((i) => i.status !== 'ready').length,
    finShare: t.finShare, finMt: BANK.scope3Cat15 / 1e6, change: t.change,
    green: (TKBI[0].value / BANK.totalLoansIdrTn) * 100, pcaf: portfolioScore(),
    framework: { value: ov.saved, suffix: '%', label: 'duplicate work avoided' },
    governance: { value: fin.savedPct, suffix: '%', label: 'LLM cost saved by routing' },
    trend: TREND.map((r) => ({ year: r.year, s12: r.s12 })), alerts: [ALERT_NEW, ...ALERTS_BASE].slice(0, 3), alertsEmpty: false,
    footnote: 'Demonstration environment · all figures synthetic · fictional institution',
  }
}

const sum = (inv, keys) => (inv ? inv.part2.filter((r) => keys.includes(r.k) && r.v != null).reduce((a, r) => a + r.v, 0) : null)

/** parts: { ghg, ghgBase, readiness, portfolio, alerts, finops, scenario } where each is the raw API response or undefined while loading. */
export function liveModel({ ghg, ghgBase, readiness, portfolio, alerts, finops, scenario }) {
  const t = ghg?.totals
  const base = ghgBase && ghg ? ghgBase.totals : null
  const s2c = scenario?.scenarios?.find((s) => s.scenario_id === 's2')
  const name = ghg?.part1?.[0]?.[1]?.replace(/\s*\(.*\)\s*$/, '') || 'Your institution'
  return {
    live: true, name, period: ghg ? `FY${ghg.year}` : '', baseYear: ghg?.base_year,
    readiness: readiness?.score ?? null, openItems: readiness ? readiness.counts.partial + readiness.counts.gap : null,
    finShare: t?.fin_share ?? null, finMt: t ? t.fin / 1e6 : null, change: t?.change_pct ?? null,
    green: portfolio?.tkbi?.green_ratio_pct ?? null, pcaf: portfolio?.pcaf?.portfolio_score ?? null,
    framework: s2c ? { value: Math.abs(s2c.net_impact_tn), decimals: 2, prefix: s2c.net_impact_tn < 0 ? '−' : '+', label: 'IDR tn net impact, 2°C scenario' } : { value: null, label: 'scenario loading' },
    governance: finops?.has_data
      ? { value: finops.totals.all_sonnet_baseline_usd ? (finops.totals.saved_vs_baseline_usd / finops.totals.all_sonnet_baseline_usd) * 100 : 0, suffix: '%', label: 'LLM cost saved by routing' }
      : { value: null, label: finops ? 'no usage recorded yet' : 'loading' },
    trend: ghg && ghgBase ? [ghgBase, ghg].map((inv) => ({ year: inv.year, s12: sum(inv, ['s1', 's2']) })) : [],
    alerts: (alerts?.alerts || []).slice(0, 3), alertsEmpty: Boolean(alerts) && (alerts.alerts || []).length === 0,
    footnote: ghg ? `Data year ${ghg.year} · read live from the data lake (Athena) · base year ${ghg.base_year}` : 'Loading live data…',
    baseTotals: base,
  }
}
