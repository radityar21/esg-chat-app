import { ShieldCheck, FileStack, Layers, Cpu, ArrowUpRight, Radar, Leaf, TrendingDown, Sparkles } from 'lucide-react'
import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts'
import { demoModel, liveModel } from '../data/home'
import { CountUp, Pill, tooltipProps, axisTick, C, fmt } from '../components/ui'
import SourceBadge from '../components/SourceBadge'
import { platformEnabled, useLive, useDebouncedPost } from '../lib/platform'

// A number that shows a dash until its data has arrived.
const Num = ({ v, d = 0, pre, suf }) => (v == null ? <span className="text-white/30">—</span> : <CountUp value={v} decimals={d} prefix={pre} suffix={suf} />)

export default function Home({ onNavigate }) {
  const ghg = useLive('/ghg/inventory?year=2024')
  const ghgBase = useLive('/ghg/inventory?year=2023')
  const readiness = useLive('/compliance/readiness?year=2024')
  const portfolio = useLive('/portfolio?year=2024')
  const alerts = useLive('/compliance/alerts')
  const finops = useLive('/governance/finops?days=14')
  const scenario = useDebouncedPost('/scenario', { year: 2024 }, { delay: 0 })
  const all = [ghg, ghgBase, readiness, portfolio, alerts, finops, scenario]
  const status = !platformEnabled ? 'demo' : all.some((x) => x.status === 'error') ? 'error' : all.some((x) => x.status === 'loading') ? 'loading' : 'live'
  const M = platformEnabled
    ? liveModel({ ghg: ghg.data, ghgBase: ghgBase.data, readiness: readiness.data, portfolio: portfolio.data, alerts: alerts.data, finops: finops.data, scenario: scenario.data })
    : demoModel()
  const sev = { high: 'red', medium: 'amber', low: 'blue' }

  const caps = [
    { id: 'compliance', icon: ShieldCheck, tone: C.teal, tag: 'Capability 1', title: 'Compliance Intelligence', line: 'Always-on PSPK readiness and regulatory change detection.', stat: <Num v={M.readiness} suf="%" />, statLabel: 'ready for PSPK' },
    { id: 'frameworks', icon: FileStack, tone: C.blue, tag: 'Capability 2', title: 'Reports & Scenarios', line: 'One dataset, four frameworks, mandatory climate scenarios.', stat: <Num v={M.framework.value} d={M.framework.decimals || 0} pre={M.framework.prefix} suf={M.framework.suffix} />, statLabel: M.framework.label },
    { id: 'portfolio', icon: Layers, tone: C.purple, tag: 'Capability 3', title: 'Portfolio Analytics', line: 'PCAF data quality, TKBI green ratio and peer position.', stat: <Num v={M.pcaf} d={1} />, statLabel: 'weighted PCAF score (1 = best)' },
    { id: 'governance', icon: Cpu, tone: C.amber, tag: 'Capability 4', title: 'AI Governance & FinOps', line: 'PII masked before the LLM. Every token accounted for.', stat: <Num v={M.governance.value} suf={M.governance.suffix} />, statLabel: M.governance.label },
  ]

  return (
    <div className="flex-1 overflow-y-auto animate-fade-in">
      {/* HERO */}
      <div className="relative h-[430px] overflow-hidden">
        <img src="/img/city-night.jpg" alt="" className="absolute inset-0 w-full h-full object-cover" style={{ objectPosition: 'center 40%' }} />
        <div className="absolute inset-0 bg-gradient-to-r from-dark-900 via-dark-900/80 to-dark-900/10" />
        <div className="absolute inset-0 bg-gradient-to-t from-dark-900 via-transparent to-dark-900/40" />
        <div className="relative h-full px-12 flex flex-col justify-center max-w-4xl">
          <div className="flex items-center gap-2 mb-5">
            {M.live && <Pill tone="green"><span className="w-1.5 h-1.5 rounded-full bg-esg-green animate-pulse" /> Live monitoring</Pill>}
            <Pill tone="slate">{M.name}{M.period ? ` · ${M.period}` : ''}</Pill>
            <SourceBadge status={status} />
          </div>
          <h1 className="font-display font-extrabold text-[52px] leading-[1.05] text-white tracking-tight">
            Know where you stand.<br />
            <span className="text-gradient">Before the regulator asks.</span>
          </h1>
          <p className="text-white/65 text-base mt-5 max-w-xl leading-relaxed">
            ESG compliance, climate scenarios and financed-emissions analytics in one AI-governed platform, built on Amazon Bedrock.
          </p>
          <div className="flex gap-3 mt-7">
            <button onClick={() => onNavigate('compliance')} className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-accent-blue to-accent-teal text-dark-900 font-semibold text-sm shadow-neon-blue hover:brightness-110 transition">Open readiness score</button>
            <button onClick={() => onNavigate('governance')} className="px-5 py-2.5 rounded-xl bg-white/10 border border-white/15 text-white text-sm hover:bg-white/15 transition backdrop-blur">See AI governance live</button>
          </div>
        </div>
      </div>

      <div className="px-10 -mt-16 pb-12 relative z-10">
        {/* KPI strip */}
        <div className="grid grid-cols-4 gap-5 mb-8">
          {[
            { icon: ShieldCheck, label: 'PSPK readiness', v: M.readiness, s: '%', sub: M.openItems == null ? 'loading' : `${M.openItems} open items`, c: 'text-accent-teal' },
            { icon: TrendingDown, label: 'Financed emissions share', v: M.finShare, d: 1, s: '%', sub: M.finMt == null ? 'loading' : `${fmt(M.finMt, 2)} MtCO2e · Scope 3 Cat 15`, c: 'text-accent-blue' },
            { icon: Leaf, label: 'Green finance ratio', v: M.green, d: 1, s: '%', sub: 'TKBI-style classification of the lending book', c: 'text-esg-green' },
            { icon: Sparkles, label: `Emissions vs ${M.baseYear ?? ''} base`, v: M.change == null ? null : Math.abs(M.change), d: 1, s: '%', pre: M.change != null && M.change < 0 ? '−' : '+', sub: 'Total inventory, Scope 1-3', c: 'text-accent-purple' },
          ].map((k) => (
            <div key={k.label} className="panel p-5 backdrop-blur-2xl">
              <div className="flex items-center gap-2 mb-3"><k.icon size={15} className={k.c} /><span className="eyebrow">{k.label}</span></div>
              <div className="font-display text-[34px] font-bold text-white leading-none"><Num v={k.v} d={k.d || 0} pre={k.pre} suf={k.s} /></div>
              <div className="text-xs text-white/45 mt-2">{k.sub}</div>
            </div>
          ))}
        </div>

        {/* Capabilities */}
        <div className="eyebrow mb-3">Platform capabilities</div>
        <div className="grid grid-cols-4 gap-5 mb-8">
          {caps.map((c) => (
            <button key={c.id} onClick={() => onNavigate(c.id)} className="panel p-6 text-left group hover:border-white/20 transition-all hover:-translate-y-1 relative overflow-hidden">
              <div className="absolute -right-10 -top-10 w-36 h-36 rounded-full blur-3xl opacity-25 group-hover:opacity-50 transition" style={{ background: c.tone }} />
              <div className="flex items-center justify-between mb-5">
                <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: c.tone + '22', border: `1px solid ${c.tone}44` }}><c.icon size={20} style={{ color: c.tone }} /></div>
                <ArrowUpRight size={18} className="text-white/30 group-hover:text-white transition" />
              </div>
              <div className="eyebrow mb-1" style={{ color: c.tone }}>{c.tag}</div>
              <div className="font-display font-semibold text-white text-lg leading-snug mb-2">{c.title}</div>
              <p className="text-xs text-white/50 leading-relaxed mb-5 min-h-[34px]">{c.line}</p>
              <div className="font-display text-3xl font-bold text-white">{c.stat}</div>
              <div className="text-[11px] text-white/40 mt-0.5">{c.statLabel}</div>
            </button>
          ))}
        </div>

        <div className="grid grid-cols-5 gap-5">
          <div className="panel col-span-3 p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-semibold text-white">Greenhouse gas inventory{M.trend.length ? `, ${M.trend[0].year} to ${M.trend[M.trend.length - 1].year}` : ''}</h3>
                <p className="text-xs text-white/45 mt-0.5">Operational (Scope 1 + 2) emissions in tCO2e</p>
              </div>
              {M.trend.length > 1 && (M.trend[M.trend.length - 1].s12 <= M.trend[0].s12 ? <Pill tone="green">Declining</Pill> : <Pill tone="amber">Rising</Pill>)}
            </div>
            <div className="h-52">
              <ResponsiveContainer>
                <AreaChart data={M.trend}>
                  <defs>
                    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.teal} stopOpacity={0.5} /><stop offset="100%" stopColor={C.teal} stopOpacity={0} /></linearGradient>
                  </defs>
                  <XAxis dataKey="year" tick={axisTick} axisLine={false} tickLine={false} />
                  <YAxis tick={axisTick} axisLine={false} tickLine={false} tickFormatter={(v) => (v >= 1000 ? v / 1000 + 'k' : v)} width={40} />
                  <Tooltip {...tooltipProps} formatter={(v) => fmt(v) + ' tCO2e'} />
                  <Area type="monotone" dataKey="s12" stroke={C.teal} strokeWidth={2.5} fill="url(#g1)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="panel col-span-2 p-6">
            <div className="flex items-center gap-2 mb-4">
              <Radar size={16} className="text-accent-teal" />
              <h3 className="font-semibold text-white">Regulatory radar</h3>
            </div>
            <div className="space-y-3">
              {M.alertsEmpty && <div className="text-xs text-white/45 leading-relaxed">No regulatory changes detected yet. An administrator can run a scan from the compliance page; scans also run daily.</div>}
              {M.alerts.map((a) => (
                <div key={a.id} className="flex gap-3 items-start">
                  <Pill tone={sev[a.severity] || 'slate'} className="mt-0.5 shrink-0">{a.severity}</Pill>
                  <div>
                    <div className="text-[13px] text-white/85 leading-snug">{a.title}</div>
                    <div className="text-[11px] text-white/35 mt-0.5">{a.source} · {a.date}</div>
                  </div>
                </div>
              ))}
            </div>
            <button onClick={() => onNavigate('compliance')} className="mt-5 text-xs text-accent-teal hover:underline">Open compliance engine →</button>
          </div>
        </div>
        <p className="text-[11px] text-white/25 mt-8 text-center">{M.footnote}</p>
      </div>
    </div>
  )
}
