import { useState, useEffect, useMemo, useRef } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { ShieldAlert, Lock, Cpu, Coins, ArrowRight, Database, ScanEye, EyeOff, Brain, Play, Pause, Zap } from 'lucide-react'
import { HR_ROWS, COLUMN_CLASS, maskRow, maskText, SAMPLE_NOTE, MODELS, TASKS, runCosts, singleCall } from '../data/governance'
import { SUBSIDIARIES } from '../data/bank'
import { PageHeader, Panel, Tabs, Pill, Stat, CountUp, tooltipProps, axisTick, C, fmt } from '../components/ui'

export default function Governance() {
  const [tab, setTab] = useState('pii')
  return (
    <div className="flex-1 overflow-y-auto p-10 animate-fade-in">
      <PageHeader eyebrow="Capability 4 · AI Governance & FinOps Control Plane" title="Responsible AI, with the receipts."
        desc="Employee data is detected and masked before any model sees it (UU PDP), every task is routed to the cheapest model that can do it well, and every token is accounted for."
        image="/img/forest-aerial-2.jpg" pos="center 30%">
        <Tabs value={tab} onChange={setTab} tabs={[{ id: 'pii', label: 'PII masking' }, { id: 'finops', label: 'Routing & token FinOps' }]} />
      </PageHeader>
      {tab === 'pii' ? <Pii /> : <FinOps />}
    </div>
  )
}

const toneCls = { red: 'bg-esg-red/10 text-esg-red', amber: 'bg-esg-amber/10 text-esg-amber', blue: 'bg-accent-blue/10 text-accent-blue' }
const hitColor = { NIK: '#ef4444', PERSON: '#fbbf24', PHONE: '#f97316', EMAIL: '#22d3ee', NPWP: '#7c5cfc' }

function Pii() {
  const [mode, setMode] = useState('tokenize')
  const [note, setNote] = useState(SAMPLE_NOTE)
  const [masked, setMasked] = useState(true)
  const [step, setStep] = useState(0)
  const { out, hits } = useMemo(() => maskText(note, mode), [note, mode])
  const cols = ['id', 'nik', 'name', 'gender', 'dob', 'salary', 'incident', 'phone']

  useEffect(() => {
    const t = setInterval(() => setStep((s) => (s + 1) % 6), 1400)
    return () => clearInterval(t)
  }, [])
  const flow = [
    { icon: Database, t: 'HR system' }, { icon: ScanEye, t: 'Classify' }, { icon: EyeOff, t: 'Mask / tokenize' }, { icon: Lock, t: 'Token vault' }, { icon: Brain, t: 'LLM (masked)' }, { icon: ShieldAlert, t: 'Audit log' },
  ]

  const stats = useMemo(() => {
    const f = HR_ROWS.filter((r) => r.gender === 'P').length
    const avg = HR_ROWS.reduce((a, r) => a + r.salary, 0) / HR_ROWS.length
    return { f: Math.round((f / HR_ROWS.length) * 100), avg: Math.round(avg / 1e6), acc: HR_ROWS.filter((r) => /Cedera/.test(r.incident)).length }
  }, [])

  return (
    <div className="space-y-5">
      <Panel title="Protected data flow" subtitle="Raw HR data never leaves the secure zone; only masked tokens and aggregates reach the model">
        <div className="flex items-center justify-between">
          {flow.map((f, i) => (
            <div key={f.t} className="flex items-center flex-1 last:flex-none">
              <div className={`flex flex-col items-center gap-2 transition-all duration-500 ${i <= step ? 'opacity-100' : 'opacity-35'}`}>
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center border ${i === step ? 'bg-accent-teal/20 border-accent-teal/60 shadow-neon-green' : 'bg-white/[0.04] border-white/10'}`}><f.icon size={20} className={i === step ? 'text-accent-teal' : 'text-white/60'} /></div>
                <span className="text-[11px] text-white/70">{f.t}</span>
              </div>
              {i < flow.length - 1 && <div className="flex-1 h-px mx-3 bg-gradient-to-r from-white/20 to-white/5 relative overflow-hidden">{i === step && <div className="absolute inset-0 scanline" />}</div>}
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Employee records: before and after" subtitle="Social-pillar data (gender, pay, workplace incidents)"
        right={<div className="flex gap-2 items-center">
          <Tabs value={mode} onChange={setMode} tabs={[{ id: 'tokenize', label: 'Tokenize' }, { id: 'redact', label: 'Redact' }]} />
          <button onClick={() => setMasked(!masked)} className={`text-xs px-3 py-2 rounded-xl border ${masked ? 'bg-esg-green/15 border-esg-green/30 text-esg-green' : 'bg-esg-red/15 border-esg-red/30 text-esg-red'}`}>{masked ? 'Masking ON' : 'Masking OFF'}</button>
        </div>} pad={false}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-white/40 text-left">{cols.map((c) => <th key={c} className="px-4 py-2 font-medium">{c}{COLUMN_CLASS[c] && <span className={`ml-1.5 text-[9px] px-1.5 py-0.5 rounded ${toneCls[COLUMN_CLASS[c].tone]}`}>{COLUMN_CLASS[c].label}</span>}</th>)}</tr>
            </thead>
            <tbody>
              {HR_ROWS.map((r) => {
                const row = masked ? maskRow(r, mode) : { ...r, salary: 'IDR ' + fmt(r.salary) }
                return <tr key={r.id} className="border-t border-white/[0.05]">{cols.map((c) => <td key={c} className={`px-4 py-2 font-mono ${masked && ['nik', 'name', 'phone', 'salary', 'dob', 'incident'].includes(c) ? 'text-accent-teal' : !masked && ['nik', 'name', 'phone', 'salary'].includes(c) ? 'text-esg-red' : 'text-white/70'}`}>{row[c]}</td>)}</tr>
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid grid-cols-12 gap-5">
        <Panel className="col-span-7" title="Free-text incident note" subtitle="Edit the text: detection runs live">
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={4} className="w-full bg-black/25 border border-white/10 rounded-xl p-3 text-sm text-white/85 font-mono focus:outline-none focus:border-accent-teal/50" />
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div className="rounded-xl bg-esg-red/[0.06] border border-esg-red/20 p-3"><div className="eyebrow text-esg-red mb-1.5">Without governance → sent to LLM</div><p className="text-xs text-white/70 font-mono leading-relaxed break-words">{note}</p></div>
            <div className="rounded-xl bg-esg-green/[0.06] border border-esg-green/25 p-3"><div className="eyebrow text-esg-green mb-1.5">With governance → sent to LLM</div><p className="text-xs text-white/85 font-mono leading-relaxed break-words">{out}</p></div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3">{hits.map((h, i) => <span key={i} className="text-[10px] px-2 py-1 rounded-md font-mono" style={{ background: hitColor[h.type] + '22', color: hitColor[h.type] }}>{h.type}</span>)}{hits.length === 0 && <span className="text-xs text-white/40">No PII detected</span>}</div>
        </Panel>

        <Panel className="col-span-5" title="What the model actually needs" subtitle="Aggregates computed inside the secure zone">
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="rounded-xl bg-white/[0.04] p-3 text-center"><div className="font-display text-2xl font-bold text-white">{stats.f}%</div><div className="text-[10px] text-white/40">women</div></div>
            <div className="rounded-xl bg-white/[0.04] p-3 text-center"><div className="font-display text-2xl font-bold text-white">{stats.avg}M</div><div className="text-[10px] text-white/40">avg salary</div></div>
            <div className="rounded-xl bg-white/[0.04] p-3 text-center"><div className="font-display text-2xl font-bold text-white">{stats.acc}</div><div className="text-[10px] text-white/40">injuries</div></div>
          </div>
          <div className="space-y-1.5 text-xs">
            {Object.entries(COLUMN_CLASS).slice(0, 7).map(([k, v]) => (
              <div key={k} className="flex items-center gap-2"><span className="w-14 font-mono text-white/70">{k}</span><span className="text-white/40 flex-1">{v.kind}</span><ArrowRight size={11} className="text-white/25" /><span className="w-36 text-right text-accent-teal">{v.strategy}</span></div>
            ))}
          </div>
          <p className="text-[10px] text-white/30 mt-4">Classification follows UU PDP No. 27/2022: health and personal financial data are “specific” personal data.</p>
        </Panel>
      </div>
    </div>
  )
}

function FinOps() {
  const [cache, setCache] = useState(true)
  const [batch, setBatch] = useState(true)
  const [live, setLive] = useState(true)
  const cost = useMemo(() => runCosts({ cache, batch }), [cache, batch])
  const plain = useMemo(() => runCosts({}), [])

  // live usage simulation
  const [usage, setUsage] = useState(() => Object.fromEntries(SUBSIDIARIES.map((s) => [s.id, { base: 0, opt: 0, tokens: 0, calls: 0 }])))
  const [log, setLog] = useState([])
  const seed = useRef(1)
  useEffect(() => {
    if (!live) return
    const rnd = () => { seed.current = (seed.current * 16807) % 2147483647; return seed.current / 2147483647 }
    const id = setInterval(() => {
      const wts = SUBSIDIARIES.map((s) => s.weight)
      let x = rnd() * wts.reduce((a, b) => a + b, 0); let si = 0
      while (x > wts[si]) { x -= wts[si]; si++ }
      const sub = SUBSIDIARIES[si]
      const task = TASKS[Math.floor(rnd() * TASKS.length)]
      const opt = singleCall(task, true, { cache, batch })
      const base = singleCall(task, false)
      setUsage((u) => ({ ...u, [sub.id]: { base: u[sub.id].base + base.cost * 40, opt: u[sub.id].opt + opt.cost * 40, tokens: u[sub.id].tokens + task.tin + task.tout, calls: u[sub.id].calls + 1 } }))
      setLog((l) => [{ k: Math.random(), sub: sub.short, task: task.name, model: opt.model, tok: task.tin + task.tout, cost: opt.cost, color: sub.color }, ...l].slice(0, 7))
    }, 900)
    return () => clearInterval(id)
  }, [live, cache, batch])

  const chart = SUBSIDIARIES.map((s) => ({ name: s.short, 'All Sonnet 4.5': Number(usage[s.id].base.toFixed(2)), 'With smart routing': Number(usage[s.id].opt.toFixed(2)) }))
  const totBase = Object.values(usage).reduce((a, u) => a + u.base, 0)
  const totOpt = Object.values(usage).reduce((a, u) => a + u.opt, 0)
  const totTok = Object.values(usage).reduce((a, u) => a + u.tokens, 0)

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-4 gap-5">
        <Stat icon={Coins} label="Cost per monthly report run" value={cost.optimized} decimals={2} prefix="$" sub={`vs $${cost.baseline.toFixed(2)} on Sonnet only`} tone="teal" />
        <Stat icon={Zap} label="Savings" value={cost.savedPct} decimals={0} suffix="%" sub="Routing + caching + batch" tone="purple" />
        <Stat icon={Cpu} label="Tokens processed (live)" value={totTok / 1000} decimals={0} suffix="k" sub="Across 4 subsidiaries" tone="blue" />
        <Stat icon={Coins} label="Live savings" value={totBase - totOpt} decimals={2} prefix="$" sub={`${totBase ? Math.round((1 - totOpt / totBase) * 100) : 0}% lower than baseline`} tone="amber" />
      </div>

      <div className="grid grid-cols-12 gap-5">
        <Panel className="col-span-7" title="Live cost by subsidiary" subtitle="Simulated usage stream · USD (scaled to a month of runs)"
          right={<button onClick={() => setLive(!live)} className="text-xs flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/10 text-white/70">{live ? <Pause size={12} /> : <Play size={12} />}{live ? 'Pause' : 'Resume'}</button>}>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={chart} barGap={4}>
                <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="name" tick={axisTick} axisLine={false} tickLine={false} />
                <YAxis tick={axisTick} axisLine={false} tickLine={false} tickFormatter={(v) => '$' + v} />
                <Tooltip {...tooltipProps} formatter={(v) => '$' + v} /><Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="All Sonnet 4.5" fill="rgba(255,255,255,0.25)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="With smart routing" fill={C.teal} radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-4 gap-3 mt-4">
            {SUBSIDIARIES.map((s) => {
              const pct = Math.min(100, (usage[s.id].opt / (s.budget / 40)) * 100)
              return <div key={s.id}><div className="flex justify-between text-[11px] mb-1"><span className="text-white/60">{s.short}</span><span className="text-white/40">{usage[s.id].calls} calls</span></div><div className="h-1.5 rounded-full bg-white/[0.07]"><div className="h-full rounded-full" style={{ width: pct + '%', background: s.color }} /></div><div className="text-[10px] text-white/30 mt-1">budget guardrail</div></div>
            })}
          </div>
        </Panel>

        <Panel className="col-span-5" title="Live request stream" subtitle="Router decision per call">
          <div className="space-y-2 min-h-[330px]">
            {log.map((l) => (
              <div key={l.k} className="ticker-in flex items-center gap-2.5 rounded-xl bg-white/[0.035] border border-white/[0.06] px-3 py-2">
                <i className="w-1.5 h-6 rounded-full" style={{ background: l.color }} />
                <div className="flex-1 min-w-0"><div className="text-xs text-white/85 truncate">{l.task}</div><div className="text-[10px] text-white/35">{l.sub} · {fmt(l.tok)} tokens</div></div>
                <span className="text-[10px] px-2 py-0.5 rounded-md font-medium" style={{ background: MODELS[l.model].color + '25', color: MODELS[l.model].color }}>{l.model === 'haiku' ? 'Haiku' : 'Sonnet'}</span>
                <span className="text-xs tabular-nums text-white/70 w-14 text-right">${l.cost.toFixed(4)}</span>
              </div>
            ))}
            {log.length === 0 && <div className="text-xs text-white/40">Waiting for requests…</div>}
          </div>
        </Panel>
      </div>

      <Panel title="Routing policy: the right model for each task" subtitle="Per monthly report run, parent bank"
        right={<div className="flex gap-4 text-xs text-white/70">
          <label className="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" className="accent-accent-teal" checked={cache} onChange={(e) => setCache(e.target.checked)} />Prompt caching</label>
          <label className="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" className="accent-accent-teal" checked={batch} onChange={(e) => setBatch(e.target.checked)} />Batch for validation</label>
        </div>} pad={false}>
        <table className="w-full text-xs">
          <thead><tr className="text-white/40 text-left"><th className="px-6 py-2">Task</th><th>Routed to</th><th className="text-right">Calls</th><th className="text-right">Tokens in / out</th><th className="text-right">All Sonnet</th><th className="text-right px-6">Optimised</th></tr></thead>
          <tbody>
            {cost.rows.map((r) => (
              <tr key={r.id} className="border-t border-white/[0.05] row-hover">
                <td className="px-6 py-2.5 text-white/85">{r.name}</td>
                <td><span className="px-2 py-0.5 rounded-md" style={{ background: MODELS[r.route].color + '25', color: MODELS[r.route].color }}>{MODELS[r.route].name}</span></td>
                <td className="text-right tabular-nums text-white/60">{r.calls}</td>
                <td className="text-right tabular-nums text-white/60">{fmt(r.tin)} / {fmt(r.tout)}</td>
                <td className="text-right tabular-nums text-white/50">${r.baseline.toFixed(2)}</td>
                <td className="text-right px-6 tabular-nums text-esg-green font-semibold">${r.optimized.toFixed(2)}</td>
              </tr>
            ))}
            <tr className="border-t-2 border-white/15"><td colSpan={4} className="px-6 py-3 text-white font-semibold">Total per run</td><td className="text-right text-white/60 tabular-nums">${cost.baseline.toFixed(2)}</td><td className="text-right px-6 text-esg-green font-bold tabular-nums">${cost.optimized.toFixed(2)}</td></tr>
          </tbody>
        </table>
        <p className="text-[10px] text-white/30 px-6 py-3">List prices (USD per 1M tokens): Sonnet 4.5 $3 in / $15 out; Haiku 4.5 $1 in / $5 out. Caching assumes 60% of input is a static prefix read at 10% of price; batch assumes a 50% discount. Illustrative, verify before external use.</p>
      </Panel>
    </div>
  )
}
