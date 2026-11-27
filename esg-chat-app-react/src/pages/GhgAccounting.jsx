import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, LineChart, Line, ReferenceLine } from 'recharts'
import { Flame, Zap, Plane, Sigma, Scale, Target, Landmark, Sparkles } from 'lucide-react'
import { PageHeader, Panel, Stat, Pill, Button, Tabs, tooltipProps, axisTick } from '../components/ui'
import SourceBadge from '../components/SourceBadge'
import FacilityDrawer from '../components/FacilityDrawer'
import { useDataHub, t, ENTITY_COLORS, SCOPE_COLORS, REGION_LABELS, TYPE_LABELS } from '../lib/datahub'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const delta = (v) => (v === null || v === undefined ? '' : `${v > 0 ? '+' : ''}${v}% vs base year`)

export default function GhgAccounting({ onNavigate }) {
  const [year, setYear] = useState(2024)
  const [approach, setApproach] = useState('control')
  const [efSet, setEfSet] = useState('ID_NATIONAL')
  const [entity, setEntity] = useState('all')
  const [tab, setTab] = useState('inventory')
  const [facility, setFacility] = useState(null)
  const led = useDataHub('ledger', { year, approach, ef_set: efSet, entity: entity === 'all' ? undefined : entity })
  const l = led.data
  // demo snapshot has the whole group only
  const demoEntity = !l || led.status === 'live' || entity === 'all'
  return (
    <div className="flex-1 overflow-y-auto p-10 animate-fade-in">
      <PageHeader eyebrow="Data & Accounting · GHG Accounting" title="Activity-based GHG accounting for the whole group"
        desc="Every activity record is multiplied by a versioned emission factor (CO2, CH4 and N2O with IPCC AR6 GWP). Switch the consolidation approach or the factor set and the inventory is recalculated from the same records."
        image="/img/forest-aerial-2.jpg" pos="center 65%" badge={<SourceBadge status={led.status} error={led.error} />}>
        <Tabs value={tab} onChange={setTab} tabs={[{ id: 'inventory', label: 'Inventory' }, { id: 'factors', label: 'Emission factors' }]} />
      </PageHeader>

      <div className="flex flex-wrap items-center gap-4 mb-6">
        <Tabs value={year} onChange={setYear} tabs={[{ id: 2023, label: '2023' }, { id: 2024, label: '2024' }]} />
        <Tabs value={approach} onChange={setApproach} tabs={[{ id: 'control', label: 'Operational control' }, { id: 'equity', label: 'Equity share' }]} />
        <Tabs value={efSet} onChange={setEfSet} tabs={[{ id: 'ID_NATIONAL', label: 'National grid factor' }, { id: 'ID_REGIONAL', label: 'Regional grid factors' }]} />
        {tab === 'inventory' && (
          <select value={entity} onChange={(e) => setEntity(e.target.value)} className="rounded-xl bg-white/[0.05] border border-white/10 px-3 py-2 text-xs text-white/80">
            <option value="all" className="bg-dark-900">All entities</option>
            {(l?.entities || []).map((e) => <option key={e.id} value={e.id} className="bg-dark-900">{e.name}</option>)}
          </select>
        )}
      </div>

      {tab === 'factors' ? <Factors year={year} efSet={efSet} /> : !l ? (
        <Panel><p className="text-sm text-white/50 py-4">{led.status === 'loading' ? 'Calculating…' : `No data: ${led.error || 'unavailable'}`}</p></Panel>
      ) : (
        <>
          {!demoEntity && <p className="text-xs text-esg-amber mb-4">Demo data covers the whole group only; the entity filter needs the live platform API.</p>}
          <div className="grid grid-cols-5 gap-5 mb-6">
            <Stat icon={Flame} label="Scope 1" value={l.totals.s1} sub={delta(l.change_pct?.s1)} tone="red" />
            <Stat icon={Zap} label="Scope 2 · market" value={l.totals.s2_market} sub={`Location-based ${t(l.totals.s2_location)} t`} tone="blue" />
            <Stat icon={Plane} label="Scope 3 · operations" value={l.totals.s3} sub="Cat. 1, 5, 6, 7" tone="purple" />
            <Stat icon={Sigma} label="Total (market)" value={l.totals.total_market} sub={delta(l.change_pct?.total_market)} tone="teal" />
            <Stat icon={Scale} label="Intensity" value={l.intensity.per_fte || 0} decimals={2} suffix=" t/FTE" sub={`${t(l.intensity.per_m2_kg, 1)} kgCO2e per m² (Scope 1+2)`} tone="amber" />
          </div>

          <div className="grid grid-cols-12 gap-5 mb-5">
            <Panel className="col-span-7" title="By legal entity" subtitle={`${l.approach_label}: ${approach === 'control' ? 'entities without operational control are excluded' : 'each entity at its ownership share'}`}>
              <div className="h-[260px]">
                <ResponsiveContainer>
                  <BarChart data={l.by_entity.map((e) => ({ name: e.name.split(' (')[0], s1: e.s1, s2: e.s2_market, s3: e.s3 }))} layout="vertical" margin={{ left: 40 }}>
                    <CartesianGrid stroke="rgba(255,255,255,0.05)" horizontal={false} />
                    <XAxis type="number" tick={axisTick} /><YAxis type="category" dataKey="name" tick={axisTick} width={150} />
                    <Tooltip {...tooltipProps} formatter={(v) => `${t(v)} tCO2e`} /><Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="s1" name="Scope 1" stackId="a" fill={SCOPE_COLORS.s1} /><Bar dataKey="s2" name="Scope 2 (market)" stackId="a" fill={SCOPE_COLORS.s2_market} />
                    <Bar dataKey="s3" name="Scope 3 ops" stackId="a" fill={SCOPE_COLORS.s3} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">{l.by_entity.map((e) => <Pill key={e.entity_id} tone={e.included ? 'slate' : 'amber'}><span className="w-2 h-2 rounded-full" style={{ background: ENTITY_COLORS[e.entity_id] }} />{e.entity_id.replace('ENT-', '')} · weight {Math.round(e.weight * 1000) / 10}%</Pill>)}</div>
            </Panel>
            <Panel className="col-span-5" title="Monthly profile" subtitle="Seasonality and gaps show up here first">
              <div className="h-[290px]">
                <ResponsiveContainer>
                  <BarChart data={l.by_month.map((m) => ({ ...m, name: MONTHS[m.month - 1] }))}>
                    <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} /><XAxis dataKey="name" tick={axisTick} /><YAxis tick={axisTick} />
                    <Tooltip {...tooltipProps} formatter={(v) => `${t(v)} tCO2e`} />
                    <Bar dataKey="s1" name="Scope 1" stackId="a" fill={SCOPE_COLORS.s1} /><Bar dataKey="s2_market" name="Scope 2" stackId="a" fill={SCOPE_COLORS.s2_market} /><Bar dataKey="s3" name="Scope 3" stackId="a" fill={SCOPE_COLORS.s3} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </div>

          <Panel className="mb-5" title="Inventory by category and activity" subtitle="Quantity × factor = emissions. Weighted by the consolidation approach." pad={false}>
            <table className="w-full text-xs">
              <thead><tr className="text-left text-white/40 text-[10px] uppercase tracking-wider">{['Category', 'Activity', 'Quantity', 'Factor kgCO2e/unit', 'Factor source', 'tCO2e', 'Market tCO2e', 'Estimated', 'Records'].map((h) => <th key={h} className="px-5 py-2.5 font-semibold">{h}</th>)}</tr></thead>
              <tbody>
                {l.by_activity.map((a) => (
                  <tr key={`${a.category}-${a.activity_type}`} className="border-t border-white/[0.04]">
                    <td className="px-5 py-2 text-white/55">{a.category_label}</td>
                    <td className="px-5 py-2 text-white/85">{a.activity_label}</td>
                    <td className="px-5 py-2 tabular-nums text-white/70">{t(a.quantity)} {a.unit}</td>
                    <td className="px-5 py-2 tabular-nums text-white/60">{a.factor_min === a.factor_max ? t(a.factor_min, 4) : `${t(a.factor_min, 4)}–${t(a.factor_max, 4)}`}</td>
                    <td className="px-5 py-2 text-white/40 max-w-[220px] truncate" title={a.ef_source}>{a.ef_source}</td>
                    <td className="px-5 py-2 tabular-nums text-white font-semibold">{t(a.tco2e, 1)}</td>
                    <td className="px-5 py-2 tabular-nums text-white/70">{a.scope === 2 ? t(a.tco2e_market, 1) : '—'}</td>
                    <td className={`px-5 py-2 tabular-nums ${a.estimated_pct > 25 ? 'text-esg-amber' : 'text-white/50'}`}>{t(a.estimated_pct, 0)}%</td>
                    <td className="px-5 py-2 tabular-nums text-white/40">{t(a.records)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>

          <div className="grid grid-cols-12 gap-5 mb-5">
            <Panel className="col-span-4" title="Recalculation: factor sets" subtitle="Same records, different emission factors">
              <div className="space-y-3">
                {Object.entries(l.recalc).map(([k, v]) => (
                  <div key={k} className={`rounded-xl p-3.5 border ${k === efSet ? 'border-accent-blue/40 bg-accent-blue/[0.06]' : 'border-white/[0.07] bg-white/[0.02]'}`}>
                    <div className="text-xs text-white/80 font-medium">{v.label}</div>
                    <div className="grid grid-cols-2 gap-2 mt-2 text-[11px] text-white/50">
                      <div>Scope 2 location<div className="text-white text-sm tabular-nums">{t(v.s2_location)}</div></div>
                      <div>Total market<div className="text-white text-sm tabular-nums">{t(v.total_market)}</div></div>
                    </div>
                  </div>
                ))}
                {l.recalc.ID_NATIONAL && l.recalc.ID_REGIONAL && (
                  <p className="text-[11px] text-white/50">Switching to regional grid factors changes Scope 2 location-based by <span className="text-white">{t(l.recalc.ID_REGIONAL.s2_location - l.recalc.ID_NATIONAL.s2_location)} tCO2e</span> ({t((l.recalc.ID_REGIONAL.s2_location / l.recalc.ID_NATIONAL.s2_location - 1) * 100, 1)}%).</p>
                )}
              </div>
            </Panel>
            <Panel className="col-span-4" title="Target trajectory" subtitle={l.trajectory?.label}>
              {l.trajectory ? (
                <>
                  <div className="h-[200px]">
                    <ResponsiveContainer>
                      <LineChart data={l.trajectory.path}>
                        <CartesianGrid stroke="rgba(255,255,255,0.05)" /><XAxis dataKey="year" tick={axisTick} /><YAxis tick={axisTick} domain={['auto', 'auto']} />
                        <Tooltip {...tooltipProps} formatter={(v) => `${t(v)} tCO2e`} />
                        <Line dataKey="target" name="Target path" stroke="#06d6a0" strokeDasharray="5 4" dot={false} />
                        <Line dataKey="actual" name="Actual" stroke="#4f8cf7" strokeWidth={2} connectNulls />
                        <ReferenceLine x={year} stroke="rgba(255,255,255,0.2)" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="mt-2"><Pill tone={l.trajectory.on_track ? 'green' : 'amber'}><Target size={11} />{l.trajectory.on_track ? 'On track' : 'Above the target path'} in {year}</Pill></div>
                </>
              ) : <p className="text-xs text-white/40">Needs base-year data.</p>}
            </Panel>
            <Panel className="col-span-4" title="By grid region" subtitle="Scope 1 + 2 (market)">
              <div className="space-y-2">
                {l.by_region.map((r) => {
                  const v = r.s1 + r.s2_market
                  const max = Math.max(...l.by_region.map((x) => x.s1 + x.s2_market)) || 1
                  return (
                    <div key={r.grid_region}>
                      <div className="flex justify-between text-xs mb-1"><span className="text-white/70">{REGION_LABELS[r.grid_region]} <span className="text-white/30">· {r.facilities} sites</span></span><span className="text-white tabular-nums">{t(v)}</span></div>
                      <div className="h-1.5 rounded-full bg-white/[0.06]"><div className="h-full rounded-full bg-accent-blue" style={{ width: `${(v / max) * 100}%` }} /></div>
                    </div>
                  )
                })}
              </div>
            </Panel>
          </div>

          <div className="grid grid-cols-12 gap-5">
            <Panel className="col-span-7" title="Top emitting facilities" subtitle="Weighted by consolidation approach. Click for the audit trail." pad={false}>
              <table className="w-full text-xs">
                <thead><tr className="text-left text-white/40 text-[10px] uppercase tracking-wider">{['Facility', 'Type', 'Region', 'Scope 1', 'Scope 2', 'Scope 3', 'kgCO2e/m²'].map((h) => <th key={h} className="px-5 py-2.5 font-semibold">{h}</th>)}</tr></thead>
                <tbody>
                  {l.top_facilities.map((f) => (
                    <tr key={f.facility_id} onClick={() => setFacility(f.facility_id)} className="border-t border-white/[0.04] row-hover cursor-pointer">
                      <td className="px-5 py-2"><div className="text-white/85">{f.facility_name}</div><div className="text-[10px] font-mono text-white/35">{f.facility_id}</div></td>
                      <td className="px-5 py-2 text-white/55">{TYPE_LABELS[f.facility_type]}</td>
                      <td className="px-5 py-2 text-white/55">{REGION_LABELS[f.grid_region]}</td>
                      <td className="px-5 py-2 tabular-nums text-white/80">{t(f.s1, 1)}</td>
                      <td className="px-5 py-2 tabular-nums text-white/80">{t(f.s2_market, 1)}</td>
                      <td className="px-5 py-2 tabular-nums text-white/80">{t(f.s3, 1)}</td>
                      <td className="px-5 py-2 tabular-nums text-white/55">{t(f.kg_per_m2, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>
            <div className="col-span-5 space-y-5">
              <Panel title="Financed emissions (Scope 3 cat. 15)" subtitle="Reported separately from operational emissions (PCAF)">
                <div className="space-y-2">
                  {l.financed.map((f) => (
                    <div key={f.entity_id} className="flex items-center justify-between text-xs rounded-lg bg-white/[0.03] px-3 py-2">
                      <span className="text-white/70"><Landmark size={12} className="inline mr-1.5 text-white/40" />{f.entity_id.replace('ENT-', '')} <span className="text-white/30">· {f.source.replace('esg_raw.', '')}</span></span>
                      <span className="text-white tabular-nums">{t(f.weighted_tco2e)} tCO2e</span>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Reconciliation with the published inventory" subtitle="Ledger vs report pipeline, parent bank">
                {l.reconciliation ? (
                  <>
                    <table className="w-full text-xs">
                      <thead><tr className="text-left text-white/40 text-[10px] uppercase"><th className="py-1.5">Item</th><th>Ledger</th><th>Reported</th><th>Diff</th></tr></thead>
                      <tbody>{l.reconciliation.rows.map((r) => <tr key={r.item} className="border-t border-white/[0.05]"><td className="py-1.5 text-white/70">{r.item}</td><td className="tabular-nums">{t(r.ledger)}</td><td className="tabular-nums">{t(r.reported)}</td><td className={`tabular-nums ${Math.abs(r.diff_pct || 0) > 5 ? 'text-esg-amber' : 'text-esg-green'}`}>{r.diff_pct == null ? '—' : `${r.diff_pct}%`}</td></tr>)}</tbody>
                    </table>
                    <p className="text-[10px] text-white/40 mt-2">{l.reconciliation.explanation}</p>
                  </>
                ) : <p className="text-xs text-white/40">The published inventory (report pipeline) is only available with the live platform API.</p>}
              </Panel>
              {onNavigate && <Button variant="ghost" icon={Sparkles} onClick={() => onNavigate('chat', { prompt: `Explain the ${year} group GHG inventory (${l.approach_label}, ${l.ef_set_label}): what drives the change against the base year, which entities and facilities matter most, and are we on track for the target?` })}>Ask the AI to explain the inventory</Button>}
            </div>
          </div>
        </>
      )}
      {facility && <FacilityDrawer facilityId={facility} year={year} efSet={efSet} onClose={() => setFacility(null)} />}
    </div>
  )
}

function Factors({ year, efSet }) {
  const d = useDataHub('factors', { year })
  const rows = (d.data?.factors || []).filter((r) => r.ef_set === efSet)
  return (
    <Panel title="Emission factor library" subtitle={d.data?.note} right={<SourceBadge status={d.status} error={d.error} />} pad={false}>
      <table className="w-full text-xs">
        <thead><tr className="text-left text-white/40 text-[10px] uppercase tracking-wider">{['Category', 'Activity', 'Region', 'Unit', 'CO2 kg', 'CH4 kg', 'N2O kg', 'Direct CO2e', 'kgCO2e/unit', 'Source'].map((h) => <th key={h} className="px-4 py-2.5 font-semibold">{h}</th>)}</tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.activity_type}-${r.region}`} className="border-t border-white/[0.04]">
              <td className="px-4 py-2 text-white/50">{r.category_label}</td>
              <td className="px-4 py-2 text-white/85">{r.activity_label}</td>
              <td className="px-4 py-2 text-white/55">{r.region === 'all' ? 'All' : REGION_LABELS[r.region] || r.region}</td>
              <td className="px-4 py-2 text-white/55">{r.unit}</td>
              <td className="px-4 py-2 tabular-nums text-white/65">{r.co2_kg ? t(r.co2_kg, 5) : '—'}</td>
              <td className="px-4 py-2 tabular-nums text-white/65">{r.ch4_kg ? t(r.ch4_kg, 7) : '—'}</td>
              <td className="px-4 py-2 tabular-nums text-white/65">{r.n2o_kg ? t(r.n2o_kg, 7) : '—'}</td>
              <td className="px-4 py-2 tabular-nums text-white/65">{r.co2e_kg ? t(r.co2e_kg, 3) : '—'}</td>
              <td className="px-4 py-2 tabular-nums text-white font-semibold">{t(r.factor_kgco2e, 4)}</td>
              <td className="px-4 py-2 text-white/40">{r.source}<div className="text-[10px] text-white/25">{r.gwp_basis} · {r.notes}</div></td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  )
}
