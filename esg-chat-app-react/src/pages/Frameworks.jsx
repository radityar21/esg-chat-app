import { useState, useMemo, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine, CartesianGrid } from 'recharts'
import { Check, Minus, FileText, Wand2, Copy } from 'lucide-react'
import { FRAMEWORKS, TOPICS, overlapOf, overlapStats, renderDisclosure, SCENARIOS, runScenario, narrative, scenarioFromApi } from '../data/frameworks'
import { PageHeader, Panel, Tabs, Slider, Pill, Button, Stat, tooltipProps, axisTick, C } from '../components/ui'
import { FileStack, Layers3, CopyCheck } from 'lucide-react'
import SourceBadge from '../components/SourceBadge'
import { useDebouncedPost } from '../lib/platform'

export default function Frameworks() {
  const [tab, setTab] = useState('diff')
  const [scenStatus, setScenStatus] = useState({ status: 'demo' })
  return (
    <div className="flex-1 overflow-y-auto p-10 animate-fade-in">
      <PageHeader
        eyebrow="Capability 2 · Multi-Framework Reporting + Scenario Analysis"
        title="One dataset in. Every framework out."
        desc="PSPK, GRI, IFRS S2 and CSRD sections are generated at once from the same curated data, then forward-looking climate scenarios flow straight into the Risk Management section."
        image="/img/city-night.jpg" pos="center 35%"
        badge={tab === 'scen' ? <SourceBadge status={scenStatus.status} error={scenStatus.error} /> : undefined}
      >
        <Tabs value={tab} onChange={setTab} tabs={[{ id: 'diff', label: 'Regulatory diff view' }, { id: 'scen', label: 'Scenario engine & what-if' }]} />
      </PageHeader>
      {tab === 'diff' ? <DiffView /> : <ScenarioView onStatus={setScenStatus} />}
    </div>
  )
}

function DiffView() {
  const [sel, setSel] = useState('s3')
  const topic = TOPICS.find((t) => t.id === sel)
  const st = overlapStats()
  const [onlyShared, setOnlyShared] = useState(false)
  const rows = TOPICS.filter((t) => !onlyShared || overlapOf(t) >= 3)

  return (
    <>
      <div className="grid grid-cols-3 gap-5 mb-5">
        <Stat icon={FileStack} label="Frameworks generated at once" value={4} sub="PSPK · GRI · IFRS S2 · CSRD" tone="blue" />
        <Stat icon={CopyCheck} label="Shared disclosures" value={st.shared} sub={`${st.shared} of ${st.unique} topics required by 3+ frameworks`} tone="teal" />
        <Stat icon={Layers3} label="Duplicate work avoided" value={st.saved} suffix="%" sub={`${st.total} requirements from ${st.unique} unique data topics`} tone="purple" />
      </div>

      <Panel title="Disclosure overlap matrix" subtitle="Which framework asks for what, from the same underlying data"
        right={<label className="flex items-center gap-2 text-xs text-white/60 cursor-pointer"><input type="checkbox" checked={onlyShared} onChange={(e) => setOnlyShared(e.target.checked)} className="accent-accent-teal" />Only shared (3+)</label>} pad={false}>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left">
              <th className="px-6 py-2 eyebrow font-semibold">Disclosure topic</th>
              {FRAMEWORKS.map((f) => <th key={f.id} className="px-3 py-2 text-center text-[11px] font-semibold" style={{ color: f.color }}>{f.short}</th>)}
              <th className="px-3 py-2 eyebrow text-center">Overlap</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => {
              const n = overlapOf(t)
              return (
                <tr key={t.id} onClick={() => setSel(t.id)} className={`cursor-pointer border-t border-white/[0.05] row-hover ${sel === t.id ? 'bg-accent-blue/[0.08]' : ''}`}>
                  <td className="px-6 py-2.5"><div className="text-white/90">{t.name}</div><div className="text-[10px] text-white/30">{t.pillar}</div></td>
                  {FRAMEWORKS.map((f) => (
                    <td key={f.id} className="px-3 text-center">
                      {t.refs[f.id] ? <span className="inline-flex flex-col items-center"><Check size={14} style={{ color: f.color }} /><span className="text-[9px] text-white/35 mt-0.5 whitespace-nowrap">{t.refs[f.id].split('·').pop().trim()}</span></span> : <Minus size={14} className="text-white/15 mx-auto" />}
                    </td>
                  ))}
                  <td className="px-3 text-center"><Pill tone={n === 4 ? 'green' : n === 3 ? 'blue' : 'slate'}>{n === 4 ? 'All 4' : n === 3 ? '3 of 4' : n + ' of 4'}</Pill></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </Panel>

      <Panel className="mt-5" title={`Side-by-side: ${topic.name}`} subtitle="Same numbers, framework-specific wording and reference"
        right={<Pill tone="slate"><FileText size={11} /> auto-generated sections</Pill>}>
        <div className="grid grid-cols-4 gap-4">
          {FRAMEWORKS.map((f) => {
            const txt = renderDisclosure(topic, f.id)
            return (
              <div key={f.id} className={`rounded-xl p-4 border min-h-[170px] ${txt ? 'bg-white/[0.03] border-white/[0.08]' : 'bg-black/20 border-dashed border-white/10'}`}>
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-xs font-semibold" style={{ color: f.color }}>{f.short}</span>
                  {txt && <span className="text-[10px] text-white/35">{topic.refs[f.id]}</span>}
                </div>
                {txt ? <p className="text-xs text-white/75 leading-relaxed">{txt}</p> : <p className="text-xs text-white/30 italic">Not required by this framework. Section is omitted automatically.</p>}
              </div>
            )
          })}
        </div>
      </Panel>
    </>
  )
}

function ScenarioView({ onStatus }) {
  const [wi, setWi] = useState({ carbon: null, shift: 0, flood: 22, boost: 0 })
  const [pick, setPick] = useState('s2')
  const [inserted, setInserted] = useState(false)
  const opts = { carbonOverride: wi.carbon, shiftPct: wi.shift, flood: wi.flood, greenBoost: wi.boost }
  const changed = wi.carbon != null || wi.shift !== 0 || wi.flood !== 22 || wi.boost !== 0
  // Live: the API runs the same screening model on the loan book. An unchanged baseline is sent without `whatif`, so it is stored as scenario evidence.
  const liveBody = { year: 2024, ...(changed ? { whatif: { ...(wi.carbon != null ? { carbon_override: wi.carbon } : {}), shift_pct: wi.shift, flood_share_pct: wi.flood, green_boost_pp: wi.boost } } : {}) }
  const liveCur = useDebouncedPost('/scenario', liveBody)
  const liveBase = useDebouncedPost('/scenario', { year: 2024 })
  const useLiveData = liveCur.status === 'live' && liveBase.status === 'live'
  useEffect(() => { onStatus({ status: liveCur.status === 'error' || liveBase.status === 'error' ? 'error' : useLiveData ? 'live' : liveCur.status, error: liveCur.error || liveBase.error }) }, [liveCur.status, liveBase.status, liveCur.error, liveBase.error, useLiveData])
  const demoResults = useMemo(() => SCENARIOS.map((s) => runScenario(s, opts)), [wi])
  const demoBase = useMemo(() => SCENARIOS.map((s) => runScenario(s, {})), [])
  const results = useLiveData ? scenarioFromApi(liveCur.data) : demoResults
  const base = useLiveData ? scenarioFromApi(liveBase.data) : demoBase
  const cur = results.find((r) => r.sc.id === pick) || results[0]
  const chart = results.map((r, i) => ({ name: r.sc.short, Transition: -r.transition, Physical: -r.physical, Opportunity: r.opportunity, net: r.net, base: base[i].net }))
  const sectorData = [...cur.bySector].sort((a, b) => b.decl - a.decl).map((s) => ({ name: s.name, decl: Number(s.decl.toFixed(2)) }))

  return (
    <div className="grid grid-cols-12 gap-5">
      <Panel className="col-span-4" title="What-if simulator" subtitle="Interactive levers on top of the three scenarios"
        right={changed && <button className="text-xs text-accent-teal" onClick={() => setWi({ carbon: null, shift: 0, flood: 22, boost: 0 })}>Reset</button>}>
        <div className="space-y-5">
          <div>
            <Slider label="Carbon price override" value={wi.carbon ?? 0} onChange={(v) => setWi({ ...wi, carbon: v === 0 ? null : v })} min={0} max={200} step={5} unit=" USD/t" hint={wi.carbon == null ? 'Using each scenario’s own pathway (130 / 75 / 25)' : 'Applied to all scenarios'} />
          </div>
          <Slider label="Shift away from high-emission sectors" value={wi.shift} onChange={(v) => setWi({ ...wi, shift: v })} min={0} max={50} step={5} unit="%" hint="Coal, oil & gas, power, cement & steel exposure" />
          <Slider label="Collateral in flood-prone zones" value={wi.flood} onChange={(v) => setWi({ ...wi, flood: v })} min={5} max={45} unit="%" hint="Baseline 22% of property collateral" />
          <Slider label="Extra green-loan growth" value={wi.boost} onChange={(v) => setWi({ ...wi, boost: v })} min={0} max={10} unit=" pp / yr" />
        </div>
        <div className="mt-6 pt-5 border-t border-white/[0.07] text-[11px] text-white/35 leading-relaxed">Simplified, transparent model: ΔECL = exposure × carbon-cost share of EBITDA × pass-through. Replace with the bank’s internal models for production.</div>
      </Panel>

      <div className="col-span-8 space-y-5">
        <Panel title="Net financial impact by scenario" subtitle="IDR trillion · transition and physical risk vs green-finance opportunity">
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={chart} stackOffset="sign" barCategoryGap="30%">
                <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="name" tick={axisTick} axisLine={false} tickLine={false} />
                <YAxis tick={axisTick} axisLine={false} tickLine={false} />
                <Tooltip {...tooltipProps} formatter={(v) => v.toFixed(2) + ' tn'} />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.25)" />
                <Bar dataKey="Transition" stackId="a" fill={C.amber} radius={[0, 0, 4, 4]} />
                <Bar dataKey="Physical" stackId="a" fill={C.red} radius={[0, 0, 4, 4]} />
                <Bar dataKey="Opportunity" stackId="a" fill={C.teal} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex gap-5 text-[11px] text-white/50 mt-1 justify-center">
            <span><i className="inline-block w-2 h-2 rounded-sm mr-1.5" style={{ background: C.amber }} />Transition risk</span>
            <span><i className="inline-block w-2 h-2 rounded-sm mr-1.5" style={{ background: C.red }} />Physical risk</span>
            <span><i className="inline-block w-2 h-2 rounded-sm mr-1.5" style={{ background: C.teal }} />Green opportunity</span>
          </div>
          <div className="grid grid-cols-3 gap-3 mt-4">
            {results.map((r, i) => (
              <button key={r.sc.id} onClick={() => setPick(r.sc.id)} className={`rounded-xl p-3.5 text-left border transition ${pick === r.sc.id ? 'border-white/30 bg-white/[0.07]' : 'border-white/[0.07] bg-white/[0.025] hover:bg-white/[0.05]'}`}>
                <div className="text-[11px] font-semibold" style={{ color: r.sc.color }}>{r.sc.name}</div>
                <div className="font-display text-2xl font-bold text-white mt-1">{r.net >= 0 ? '+' : '−'}{Math.abs(r.net).toFixed(Math.abs(r.net) < 10 ? 2 : 1)}<span className="text-xs text-white/40 ml-1">IDR tn</span></div>
                {changed && <div className="text-[10px] text-white/40 mt-0.5">vs baseline {base[i].net.toFixed(Math.abs(base[i].net) < 10 ? 2 : 1)}</div>}
              </button>
            ))}
          </div>
        </Panel>

        <div className="grid grid-cols-2 gap-5">
          <Panel title={`Transition risk by sector`} subtitle={`${cur.sc.short} · additional ECL, IDR tn`}>
            <div className="h-60">
              <ResponsiveContainer>
                <BarChart data={sectorData} layout="vertical" margin={{ left: 40 }}>
                  <XAxis type="number" tick={axisTick} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="name" tick={{ ...axisTick, fontSize: 10 }} axisLine={false} tickLine={false} width={120} />
                  <Tooltip {...tooltipProps} />
                  <Bar dataKey="decl" radius={4}>{sectorData.map((s, i) => <Cell key={s.name} fill={i < 2 ? C.amber : 'rgba(251,191,36,0.4)'} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
          <Panel title="Auto-generated disclosure" subtitle="Risk Management section · narrative"
            right={<Button variant="ghost" icon={inserted ? Check : Wand2} onClick={() => setInserted(true)}>{inserted ? 'Inserted' : 'Insert into report'}</Button>}>
            <p className="text-[13px] text-white/75 leading-relaxed">{cur.text || narrative(cur)}</p>
            {inserted && <div className="mt-3 text-[11px] text-esg-green">Added to “Risk Management → Climate scenario analysis” in the draft PSPK, IFRS S2 and CSRD reports.</div>}
          </Panel>
        </div>
      </div>
    </div>
  )
}
