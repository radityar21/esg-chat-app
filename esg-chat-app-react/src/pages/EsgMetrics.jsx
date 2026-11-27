import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { Leaf, Users, Landmark, Scale, ShieldCheck, AlertTriangle } from 'lucide-react'
import { PageHeader, Panel, Stat, Pill, Tabs, tooltipProps, axisTick } from '../components/ui'
import SourceBadge from '../components/SourceBadge'
import { useDataHub, fmtValue, ENTITY_COLORS } from '../lib/datahub'

const PILLARS = [
  { id: 'environment', label: 'Environment', icon: Leaf },
  { id: 'social', label: 'Social', icon: Users },
  { id: 'governance', label: 'Governance', icon: Scale },
  { id: 'finance', label: 'Sustainable finance', icon: Landmark },
]

export default function EsgMetrics({ onNavigate }) {
  const [year, setYear] = useState(2024)
  const [pillar, setPillar] = useState('environment')
  const d = useDataHub('metrics', { year })
  const m = d.data
  const rows = (m?.metrics || []).filter((r) => r.pillar === pillar)
  const missing = (m?.metrics || []).reduce((a, r) => a + r.entities.filter((x) => x.status === 'missing').length, 0)
  const pillarCov = (id) => {
    const xs = (m?.metrics || []).filter((r) => r.pillar === id).flatMap((r) => r.entities.filter((x) => x.applies))
    return xs.length ? Math.round(xs.filter((x) => x.status === 'reported').length / xs.length * 100) : 0
  }
  return (
    <div className="flex-1 overflow-y-auto p-10 animate-fade-in">
      <PageHeader eyebrow="Data & Accounting · ESG Metrics" title="Beyond GHG: energy, water, waste, people, governance, finance"
        desc="Every metric the sustainability report needs (GRI, POJK 51/2017, PCAF), per legal entity. A metric that was not delivered is shown as not reported and raised as a data alert."
        image="/img/forest-aerial-2.jpg" pos="center 45%" badge={<SourceBadge status={d.status} error={d.error} />}>
        <Tabs value={year} onChange={setYear} tabs={[{ id: 2023, label: '2023' }, { id: 2024, label: '2024' }]} />
      </PageHeader>
      {!m ? <Panel><p className="text-sm text-white/50 py-4">{d.status === 'loading' ? 'Loading…' : `No data: ${d.error || 'unavailable'}`}</p></Panel> : (
        <>
          <div className="grid grid-cols-5 gap-5 mb-6">
            <Stat icon={ShieldCheck} label="Coverage" value={m.coverage.pct || 0} decimals={1} suffix="%" sub={`${m.coverage.reported} of ${m.coverage.applicable} entity-metrics`} tone="teal" />
            {PILLARS.map((p) => <Stat key={p.id} icon={p.icon} label={p.label} value={pillarCov(p.id)} suffix="%" sub="reported" tone={pillarCov(p.id) === 100 ? 'blue' : 'amber'} />)}
          </div>
          <div className="flex items-center gap-4 mb-5">
            <Tabs value={pillar} onChange={setPillar} tabs={PILLARS.map((p) => ({ id: p.id, label: p.label }))} />
            {missing > 0 && <button onClick={() => onNavigate?.('datahub')} className="text-xs text-esg-amber inline-flex items-center gap-1.5"><AlertTriangle size={12} />{missing} metric value(s) not reported · see Data alerts</button>}
          </div>

          {pillar === 'finance' && m.kubl?.length > 0 && (
            <Panel className="mb-5" title="Sustainable finance by KUBL category" subtitle="POJK 51/2017 sustainable business activity categories, outstanding at year end">
              <div className="h-[260px]">
                <ResponsiveContainer>
                  <BarChart data={m.kubl.map((k) => ({ name: k.label, ...Object.fromEntries(Object.entries(k.by_entity).map(([e, v]) => [e, v / 1e12])) }))} margin={{ left: 10 }}>
                    <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="name" tick={{ ...axisTick, fontSize: 10 }} interval={0} angle={-15} textAnchor="end" height={60} />
                    <YAxis tick={axisTick} unit=" T" />
                    <Tooltip {...tooltipProps} formatter={(v) => `IDR ${v.toFixed(2)} T`} /><Legend wrapperStyle={{ fontSize: 11 }} />
                    {m.entities.filter((e) => ['bank', 'sharia_bank', 'multifinance'].includes(e.type)).map((e) => <Bar key={e.id} dataKey={e.id} name={e.name.split(' (')[0]} stackId="a" fill={ENTITY_COLORS[e.id]} />)}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          )}

          <Panel title={`${PILLARS.find((p) => p.id === pillar).label} metrics · ${year}`} subtitle={`Change against ${m.base_year} in brackets`} pad={false}>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-white/40 text-[10px] uppercase tracking-wider">
                    <th className="px-5 py-3 font-semibold">Metric</th><th className="px-3 py-3 font-semibold">Standard</th>
                    {m.entities.map((e) => <th key={e.id} className="px-3 py-3 font-semibold"><span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ background: ENTITY_COLORS[e.id] }} />{e.name.split(' (')[0]}</th>)}
                    <th className="px-3 py-3 font-semibold">Coverage</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.id} className="border-t border-white/[0.04] align-top">
                      <td className="px-5 py-2.5"><div className="text-white/85">{r.label}</div><div className="text-[10px] text-white/35">{r.unit}{r.required ? ' · required' : ' · recommended'}</div></td>
                      <td className="px-3 py-2.5 text-white/40 text-[11px]">{r.ref}</td>
                      {r.entities.map((x) => (
                        <td key={x.entity_id} className="px-3 py-2.5 tabular-nums">
                          {x.status === 'not_applicable' ? <span className="text-white/20">n/a</span>
                            : x.status === 'missing' ? <Pill tone={r.required ? 'red' : 'amber'}>Not reported</Pill>
                              : <>
                                <div className="text-white/85">{fmtValue(x.value, r.unit)}</div>
                                {x.change_pct !== null && x.change_pct !== undefined && <div className="text-[10px] text-white/45">({x.change_pct > 0 ? '+' : ''}{x.change_pct}%)</div>}
                                {x.breakdown && r.id === 'headcount' && <div className="text-[10px] text-white/35">F {fmtValue(x.breakdown.female)} · M {fmtValue(x.breakdown.male)}</div>}
                              </>}
                        </td>
                      ))}
                      <td className="px-3 py-2.5"><Pill tone={r.coverage.split('/')[0] === r.coverage.split('/')[1] ? 'green' : 'amber'}>{r.coverage}</Pill></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
          {pillar === 'environment' && <p className="text-[11px] text-white/35 mt-3">Environmental metrics are calculated from the activity records (energy conversion: electricity 0.0036 GJ/kWh, diesel 0.0361 GJ/l, gasoline 0.033 GJ/l). Renewable share counts on-site solar and electricity covered by certificates.</p>}
        </>
      )}
    </div>
  )
}
