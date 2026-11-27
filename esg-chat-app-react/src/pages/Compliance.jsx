import { useState, useMemo, useRef } from 'react'
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer } from 'recharts'
import { CheckCircle2, CircleDot, XCircle, ScanSearch, FileDiff, Wrench, Globe2 } from 'lucide-react'
import { CHECKLIST, PILLARS, pillarScores, score, SOURCES, ALERTS_BASE, ALERT_NEW } from '../data/compliance'
import { PageHeader, Panel, Gauge, Pill, Button, Tabs, C } from '../components/ui'
import SourceBadge from '../components/SourceBadge'
import { api, useLive, platformEnabled, CHAT_BASE } from '../lib/platform'

const statusMeta = {
  ready: { icon: CheckCircle2, color: 'text-esg-green', label: 'Ready', tone: 'green' },
  partial: { icon: CircleDot, color: 'text-esg-amber', label: 'Partial', tone: 'amber' },
  gap: { icon: XCircle, color: 'text-esg-red', label: 'Gap', tone: 'red' },
}
const sev = { high: 'red', medium: 'amber', low: 'blue' }

export default function Compliance() {
  const [tab, setTab] = useState('gap')
  const [fixed, setFixed] = useState(new Set())
  const [pillar, setPillar] = useState('all')

  const readiness = useLive('/compliance/readiness?year=2024')
  const alertsLive = useLive('/compliance/alerts')
  const CHECK = readiness.status === 'live' ? readiness.data.items : CHECKLIST
  const base = score(CHECK)
  const now = score(CHECK, fixed)
  const ps = useMemo(() => pillarScores(fixed, CHECK), [fixed, CHECK])
  const open = CHECK.filter((i) => i.status !== 'ready' && !fixed.has(i.id))
  const list = CHECK.filter((i) => pillar === 'all' || i.pillar === pillar)

  const toggle = (id) => setFixed((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })

  // regulatory scan
  const [scanState, setScanState] = useState('idle') // idle | scanning | done
  const [progress, setProgress] = useState(-1)
  const [showDiff, setShowDiff] = useState(false)
  const [scanResult, setScanResult] = useState(null)
  const [scanError, setScanError] = useState(null)
  const timer = useRef()
  const runScan = () => {
    setScanState('scanning'); setProgress(0); setShowDiff(false); setScanError(null)
    let i = 0
    const live = platformEnabled
    // Live: the animation keeps cycling until the API answers. Demo: it plays once and reveals the simulated alert.
    timer.current = setInterval(() => {
      i += 1; setProgress(live ? i % SOURCES.length : i)
      if (!live && i >= SOURCES.length) { clearInterval(timer.current); setTimeout(() => setScanState('done'), 500) }
    }, 650)
    if (live) {
      api('/compliance/scan', { method: 'POST', base: CHAT_BASE, timeout: 120000 })
        .then((r) => { setScanResult(r); alertsLive.reload() })
        .catch((e) => setScanError(e.message))
        .finally(() => { clearInterval(timer.current); setProgress(SOURCES.length); setScanState('done') })
    }
  }
  const liveAlerts = alertsLive.status === 'live' ? alertsLive.data.alerts : null
  const alerts = liveAlerts ?? (scanState === 'done' ? [ALERT_NEW, ...ALERTS_BASE] : ALERTS_BASE)

  return (
    <div className="flex-1 overflow-y-auto p-10 animate-fade-in">
      <PageHeader
        eyebrow="Capability 1 · Compliance Intelligence Engine"
        title="How ready are we for PSPK, and what just changed?"
        desc="Existing curated data is scored against the PSPK 1 & 2 checklist, while regulatory sources are watched continuously for changes that touch your report templates."
        image="/img/forest-aerial-2.jpg"
        badge={<SourceBadge status={readiness.status} error={readiness.error} />}
      >
        <Tabs value={tab} onChange={setTab} tabs={[{ id: 'gap', label: 'Gap Analyzer' }, { id: 'reg', label: 'Regulatory Change Detection' }]} />
      </PageHeader>

      {tab === 'gap' && (
        <>
          <div className="grid grid-cols-12 gap-5 mb-5">
            <Panel className="col-span-4" title="Compliance readiness score" subtitle="Weighted by disclosure criticality">
              <div className="flex flex-col items-center pt-2">
                <Gauge value={Math.round(now)} label="Ready for PSPK" sublabel={fixed.size ? `+${(now - base).toFixed(1)} pts from simulated fixes` : 'Based on current curated data'} />
                <div className="grid grid-cols-3 gap-2 w-full mt-4 text-center">
                  {['ready', 'partial', 'gap'].map((s) => {
                    const n = CHECK.filter((i) => (fixed.has(i.id) ? 'ready' : i.status) === s).length
                    return <div key={s} className="rounded-xl bg-white/[0.04] py-2"><div className={`text-xl font-display font-bold ${statusMeta[s].color}`}>{n}</div><div className="text-[10px] uppercase tracking-wider text-white/40">{statusMeta[s].label}</div></div>
                  })}
                </div>
              </div>
            </Panel>

            <Panel className="col-span-4" title="Readiness by pillar" subtitle="Governance · Strategy · Risk · Metrics">
              <div className="h-[290px]">
                <ResponsiveContainer>
                  <RadarChart data={ps.map((p) => ({ pillar: p.name, score: Math.round(p.score), full: 100 }))} outerRadius="58%">
                    <PolarGrid stroke="rgba(255,255,255,0.1)" />
                    <PolarAngleAxis dataKey="pillar" tick={{ fill: 'rgba(255,255,255,0.65)', fontSize: 11 }} />
                    <Radar dataKey="score" stroke={C.teal} fill={C.teal} fillOpacity={0.3} strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel className="col-span-4" title="Pillar breakdown" subtitle="Click a pillar to filter the checklist">
              <div className="space-y-4 mt-1">
                {ps.map((p) => (
                  <button key={p.id} onClick={() => setPillar(pillar === p.id ? 'all' : p.id)} className="w-full text-left">
                    <div className="flex justify-between text-sm mb-1.5">
                      <span className={pillar === p.id ? 'text-white font-medium' : 'text-white/70'}>{p.name}</span>
                      <span className="font-semibold text-white tabular-nums">{Math.round(p.score)}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-white/[0.07] overflow-hidden"><div className="h-full rounded-full transition-all duration-700" style={{ width: p.score + '%', background: `linear-gradient(90deg, ${p.color}, ${p.color}aa)` }} /></div>
                  </button>
                ))}
              </div>
              <div className="mt-6 rounded-xl border border-esg-amber/25 bg-esg-amber/[0.06] p-3.5">
                <div className="text-xs text-esg-amber font-semibold mb-1">{open.length} items need data</div>
                <div className="text-[11px] text-white/55 leading-relaxed">Largest weight at stake: {[...open].sort((a, b) => b.w - a.w)[0]?.req.toLowerCase() || '—'}.</div>
              </div>
            </Panel>
          </div>

          <Panel title="PSPK 1 & 2 checklist" subtitle="Toggle “Simulate fix” to see the score move once the data is collected" pad={false}
            right={pillar !== 'all' && <button className="text-xs text-accent-teal" onClick={() => setPillar('all')}>Show all pillars</button>}>
            <div className="divide-y divide-white/[0.05]">
              {list.map((i) => {
                const st = fixed.has(i.id) ? 'ready' : i.status
                const M = statusMeta[st]
                const p = PILLARS.find((x) => x.id === i.pillar)
                return (
                  <div key={i.id} className="px-6 py-3.5 flex items-start gap-4 row-hover">
                    <M.icon size={18} className={`${M.color} mt-0.5 shrink-0`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm text-white">{i.req}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: p.color + '22', color: p.color }}>{p.name}</span>
                        <span className="text-[10px] text-white/30">weight {i.w}</span>
                      </div>
                      {i.evidence && <div className="text-[11px] text-white/35 mt-1">Evidence: {i.evidence}</div>}
                      {i.status !== 'ready' && (
                        <div className="mt-1.5 text-xs text-white/55 leading-relaxed">
                          <span className="text-white/35">Source system:</span> <span className="text-accent-blue">{i.system}</span><br />
                          <span className="text-white/35">Recommendation:</span> {i.rec}
                        </div>
                      )}
                    </div>
                    {i.status !== 'ready' && (
                      <button onClick={() => toggle(i.id)} className={`shrink-0 text-xs px-3 py-1.5 rounded-lg border transition ${fixed.has(i.id) ? 'bg-esg-green/15 border-esg-green/30 text-esg-green' : 'bg-white/[0.04] border-white/10 text-white/70 hover:bg-white/10'}`}>
                        <Wrench size={12} className="inline mr-1.5 -mt-0.5" />{fixed.has(i.id) ? 'Fixed (simulated)' : 'Simulate fix'}
                      </button>
                    )}
                    {i.status === 'ready' && <Pill tone="green">Ready</Pill>}
                  </div>
                )
              })}
            </div>
          </Panel>
        </>
      )}

      {tab === 'reg' && (
        <div className="grid grid-cols-12 gap-5">
          <Panel className="col-span-4" title="Monitored sources" subtitle="Scheduled crawler · daily"
            right={<Button icon={ScanSearch} onClick={runScan} disabled={scanState === 'scanning'}>{scanState === 'scanning' ? 'Scanning…' : 'Run scan now'}</Button>}>
            <div className="space-y-2.5">
              {SOURCES.map((s, idx) => {
                const done = scanState !== 'idle' && progress > idx
                const active = scanState === 'scanning' && progress === idx
                return (
                  <div key={s.id} className="relative overflow-hidden rounded-xl bg-white/[0.04] border border-white/[0.06] px-4 py-3 flex items-center gap-3">
                    {active && <div className="absolute inset-x-0 bottom-0 h-px scanline" />}
                    <Globe2 size={16} className={done ? 'text-esg-green' : active ? 'text-accent-teal animate-pulse' : 'text-white/30'} />
                    <span className="text-[13px] text-white/80 flex-1">{s.name}</span>
                    {done && <CheckCircle2 size={15} className="text-esg-green" />}
                  </div>
                )
              })}
            </div>
            {scanError && <div className="mt-4 text-xs text-esg-red">Scan failed: {scanError}</div>}
            {scanResult && <div className="mt-4 text-xs text-white/60">{scanResult.new} new item(s) found{scanResult.errors?.length ? `, ${scanResult.errors.length} source(s) unreachable` : ''}.</div>}
            <div className="mt-5 text-[11px] text-white/35 leading-relaxed">Detected changes are classified by an LLM against the section map of your report templates, then routed to the owning team.</div>
          </Panel>

          <Panel className="col-span-8" title="Change alerts" subtitle="Impact mapped to report sections and checklist items">
            <div className="space-y-3">
              {alerts.map((a) => (
                <div key={a.id} className={`rounded-xl border p-4 ${a.isNew ? 'border-esg-red/40 bg-esg-red/[0.06] ticker-in' : 'border-white/[0.07] bg-white/[0.025]'}`}>
                  <div className="flex items-center gap-2 mb-1.5">
                    <Pill tone={sev[a.severity]}>{a.severity}</Pill>
                    {a.isNew && <Pill tone="red">NEW</Pill>}
                    <span className="text-[11px] text-white/40">{a.source} · {a.date} · {a.id}</span>
                  </div>
                  <div className="text-sm font-medium text-white leading-snug">{a.url ? <a href={a.url} target="_blank" rel="noreferrer" className="hover:underline">{a.title}</a> : a.title}</div>
                  <div className="text-xs text-white/50 mt-1.5">Impacts: {(a.impact || []).join(' · ')} {a.checklist && <span className="text-white/25">| checklist {a.checklist}</span>}</div>
                  <div className="text-xs text-white/70 mt-1">Suggested: {a.action}</div>
                  {a.isNew && a.templateBefore && (
                    <div className="mt-3">
                      <Button variant="ghost" icon={FileDiff} onClick={() => setShowDiff(!showDiff)}>{showDiff ? 'Hide' : 'Preview'} template update</Button>
                      {showDiff && (
                        <div className="grid grid-cols-2 gap-3 mt-3 text-xs">
                          <div className="rounded-lg bg-black/30 p-3 border border-white/10"><div className="eyebrow mb-2">Current template</div><p className="text-white/60 leading-relaxed whitespace-pre-wrap">{a.templateBefore}</p></div>
                          <div className="rounded-lg bg-esg-green/[0.06] p-3 border border-esg-green/25"><div className="eyebrow mb-2 text-esg-green">Proposed by AgentCore</div><p className="text-white/80 leading-relaxed whitespace-pre-wrap">{a.templateAfter}</p></div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Panel>
        </div>
      )}
    </div>
  )
}
