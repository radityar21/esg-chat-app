import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid, LineChart, Line, Legend } from 'recharts'
import { Check, X, Download } from 'lucide-react'
import { DEMO_DATASET, GAS_NAMES, datasetFromApi } from '../data/ghg'
import { useLive } from '../lib/platform'
import SourceBadge from '../components/SourceBadge'
import { PageHeader, Panel, Tabs, Stat, Pill, Button, tooltipProps, axisTick, C, fmt } from '../components/ui'
import { Flame, Scale, Database, ClipboardCheck } from 'lucide-react'

const TABS = [
  { id: 'p1', label: '1 · Descriptive' },
  { id: 'p2', label: '2 · Emissions' },
  { id: 'p4', label: '4 · Methodology' },
  { id: 'p5', label: '5 · Base year' },
  { id: 'p6', label: '6 · Optional' },
]

function download(name, text) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([text], { type: 'text/csv' }))
  a.download = name
  a.click()
}

export default function GhgInventory() {
  const [tab, setTab] = useState('p2')
  const cur = useLive('/ghg/inventory?year=2024')
  const base = useLive('/ghg/inventory?year=2023')
  const ds = cur.status === 'live' && base.status === 'live' ? datasetFromApi(cur.data, base.data) : DEMO_DATASET
  const status = cur.status === 'error' || base.status === 'error' ? 'error' : cur.status === 'loading' || base.status === 'loading' ? 'loading' : cur.status
  const { PART1, PART2, PART3, PART4, GASES, BASE_YEAR, PART6, TREND, YEAR } = ds
  const t = ds.totals
  const cov = ds.part6Coverage

  const exportCsv = () => {
    const rows = [['Scope / category', 'Included', 'Reporting year tCO2e', `Base year ${BASE_YEAR} tCO2e`]]
    PART2.forEach((r) => rows.push([r.label, r.inc ? 'yes' : 'excluded', r.v ?? '', r.base ?? '']))
    download(`ghg_inventory_FY${YEAR}.csv`, rows.map((r) => r.map((c) => `"${c}"`).join(',')).join('\n'))
  }

  return (
    <div className="flex-1 overflow-y-auto p-10 animate-fade-in">
      <PageHeader eyebrow="GHG Inventory · GHG Protocol Corporate Value Chain (Scope 3) template" title="The inventory behind every report" desc="Structured exactly like the GHG Protocol reporting template, so one curated dataset feeds PSPK, GRI, IFRS S2 and CSRD."
        image="/img/forest-aerial-2.jpg" pos="center 70%" badge={<SourceBadge status={status} error={cur.error || base.error} />}>
        <Button variant="ghost" icon={Download} onClick={exportCsv}>Export CSV</Button>
      </PageHeader>

      <div className="grid grid-cols-4 gap-5 mb-6">
        <Stat icon={Flame} label="Total inventory" value={t.total / 1e6} decimals={2} suffix=" MtCO2e" sub="Scope 1 + 2 + included Scope 3" tone="red" />
        <Stat icon={Scale} label="Financed emissions" value={t.finShare} decimals={1} suffix="%" sub="Scope 3 Cat 15 share of total" tone="purple" />
        <Stat icon={Database} label="Change vs base year" value={Math.abs(t.change)} decimals={1} prefix={t.change < 0 ? '−' : '+'} suffix="%" sub={`Base year ${BASE_YEAR}`} tone="teal" />
        <Stat icon={ClipboardCheck} label="Template completeness" value={cov} suffix="%" sub="Part 6 optional items covered" tone="blue" />
      </div>

      <div className="mb-5"><Tabs tabs={TABS} value={tab} onChange={setTab} /></div>

      {tab === 'p1' && (
        <Panel title="Part 1 · Descriptive information" pad={false}>
          <table className="w-full text-sm"><tbody>
            {PART1.map(([k, v]) => <tr key={k} className="border-t border-white/[0.05]"><td className="px-6 py-3 w-1/3 text-white/45 align-top">{k}</td><td className="px-6 py-3 text-white/90">{v}</td></tr>)}
          </tbody></table>
        </Panel>
      )}

      {tab === 'p2' && (
        <div className="grid grid-cols-12 gap-5">
          <Panel className="col-span-7" title="Part 2 · Greenhouse gas emissions data" subtitle={`Metric tons CO2e, reporting year ${YEAR}`} pad={false}>
            <table className="w-full text-sm">
              <tbody>
                {PART2.map((r) => (
                  <tr key={r.k} className="border-t border-white/[0.05] row-hover">
                    <td className="px-6 py-2 text-white/85">{r.label}</td>
                    <td className="px-6 py-2 text-right tabular-nums">{r.inc ? <span className={r.k === 'c15' ? 'text-accent-purple font-semibold' : 'text-white'}>{fmt(r.v)}</span> : <Pill tone="slate">{r.note ? 'not measured' : 'excluded'}</Pill>}</td>
                  </tr>
                ))}
                <tr className="border-t-2 border-white/15"><td className="px-6 py-3 font-semibold text-white">Total</td><td className="px-6 py-3 text-right font-semibold text-white tabular-nums">{fmt(t.total)}</td></tr>
              </tbody>
            </table>
          </Panel>
          <div className="col-span-5 space-y-5">
            <Panel title="Scope 1 and 2 by gas" subtitle="Part 2 (continued), tCO2e">
              <table className="w-full text-xs">
                <thead><tr className="text-white/40"><th className="text-left py-1"></th>{GAS_NAMES.map((g) => <th key={g} className="text-right py-1">{g}</th>)}</tr></thead>
                <tbody>
                  {GASES.map((g) => <tr key={g.scope} className="border-t border-white/[0.05]"><td className="py-2 text-white/70">{g.scope}</td>{(g.vals || GAS_NAMES.map(() => null)).map((v, i) => <td key={i} className="text-right tabular-nums text-white">{v == null ? '–' : fmt(v)}</td>)}</tr>)}
                </tbody>
              </table>
            </Panel>
            <Panel title="Operational Scope 3 (excl. Cat 15)" subtitle="Cat 15 is 99% of the total, so shown separately">
              <div className="h-52">
                <ResponsiveContainer>
                  <BarChart data={PART2.filter((r) => r.inc && r.k !== 'c15' && r.k !== 's1' && r.k !== 's2').map((r) => ({ name: r.label.split('·')[0].trim(), v: r.v }))}>
                    <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="name" tick={axisTick} axisLine={false} tickLine={false} />
                    <YAxis tick={axisTick} axisLine={false} tickLine={false} tickFormatter={(v) => v / 1000 + 'k'} />
                    <Tooltip {...tooltipProps} formatter={(v) => fmt(v) + ' tCO2e'} />
                    <Bar dataKey="v" fill={C.blue} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <Panel title="Part 3 · Biogenic CO2"><p className="text-xs text-white/60 leading-relaxed">{PART3.note}</p></Panel>
          </div>
        </div>
      )}

      {tab === 'p4' && (
        <Panel title="Part 4 · Methodologies and data used" pad={false}>
          <table className="w-full text-xs">
            <thead><tr className="text-left text-white/40"><th className="px-6 py-2">Scope / category</th><th className="px-3 py-2">Methodology</th><th className="px-3 py-2">Data sources</th><th className="px-3 py-2">Data quality</th><th className="px-3 py-2 text-right">% from partners</th></tr></thead>
            <tbody>
              {PART4.map((r) => (
                <tr key={r.scope} className="border-t border-white/[0.05] align-top row-hover">
                  <td className="px-6 py-3 text-white font-medium whitespace-nowrap">{r.scope}</td>
                  <td className="px-3 py-3 text-white/70 leading-relaxed">{r.method}</td>
                  <td className="px-3 py-3 text-white/60 leading-relaxed">{r.data}</td>
                  <td className="px-3 py-3 text-white/70">{r.quality}</td>
                  <td className="px-3 py-3 text-right text-white tabular-nums">{r.supplier}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}

      {tab === 'p5' && (
        <div className="grid grid-cols-12 gap-5">
          <Panel className="col-span-7" title={`Part 5 · Base year ${BASE_YEAR} vs ${YEAR}`} pad={false}>
            <table className="w-full text-sm">
              <thead><tr className="text-left text-white/40 text-xs"><th className="px-6 py-2">Scope / category</th><th className="px-3 py-2 text-right">{BASE_YEAR}</th><th className="px-3 py-2 text-right">{YEAR}</th><th className="px-6 py-2 text-right">Change</th></tr></thead>
              <tbody>
                {PART2.filter((r) => r.inc && r.v != null).map((r) => {
                  const d = r.base ? ((r.v - r.base) / r.base) * 100 : null
                  return <tr key={r.k} className="border-t border-white/[0.05] row-hover"><td className="px-6 py-2 text-white/80">{r.label}</td><td className="px-3 text-right tabular-nums text-white/60">{r.base == null ? '–' : fmt(r.base)}</td><td className="px-3 text-right tabular-nums text-white">{fmt(r.v)}</td><td className={`px-6 text-right tabular-nums ${d == null ? 'text-white/40' : d <= 0 ? 'text-esg-green' : 'text-esg-amber'}`}>{d == null ? '–' : `${d > 0 ? '+' : ''}${d.toFixed(1)}%`}</td></tr>
                })}
              </tbody>
            </table>
          </Panel>
          <Panel className="col-span-5" title="Trajectory since base year" subtitle="Scope 1+2 (tCO2e) and financed emissions (right axis)">
            <div className="h-72">
              <ResponsiveContainer>
                <LineChart data={TREND}>
                  <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="year" tick={axisTick} axisLine={false} tickLine={false} />
                  <YAxis yAxisId="l" tick={axisTick} axisLine={false} tickLine={false} tickFormatter={(v) => v / 1000 + 'k'} />
                  <YAxis yAxisId="r" orientation="right" tick={axisTick} axisLine={false} tickLine={false} tickFormatter={(v) => (v / 1e6).toFixed(1) + 'M'} />
                  <Tooltip {...tooltipProps} formatter={(v) => fmt(v)} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line yAxisId="l" name="Scope 1+2" dataKey="s12" stroke={C.teal} strokeWidth={2.5} dot={{ r: 4 }} />
                  <Line yAxisId="r" name="Cat 15 financed" dataKey="fin" stroke={C.purple} strokeWidth={2.5} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </div>
      )}

      {tab === 'p6' && (
        <Panel title="Part 6 · Optional information coverage" subtitle={`${PART6.filter((p) => p[1]).length} of ${PART6.length} recommended items are covered by the platform`}>
          <div className="grid grid-cols-2 gap-x-8 gap-y-2.5">
            {PART6.map(([k, on]) => (
              <div key={k} className="flex items-start gap-2.5 text-sm">
                {on ? <Check size={16} className="text-esg-green mt-0.5 shrink-0" /> : <X size={16} className="text-white/25 mt-0.5 shrink-0" />}
                <span className={on ? 'text-white/85' : 'text-white/40'}>{k}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  )
}
