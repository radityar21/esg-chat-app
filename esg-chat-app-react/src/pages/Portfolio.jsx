import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, ComposedChart, Line, Area, CartesianGrid, RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend, ReferenceLine } from 'recharts'
import { Gauge as GaugeIcon, Leaf, Trophy, ArrowRight } from 'lucide-react'
import { PCAF_CLASSES, PCAF_COLORS, scoreDistribution, portfolioScore, weightedScore, TKBI, GREEN_TREND, TKBI_SECTORS, PEERS, composite, WEIGHTS } from '../data/portfolio'
import { BANK } from '../data/bank'
import { PageHeader, Panel, Tabs, Stat, Pill, tooltipProps, axisTick, C, CountUp } from '../components/ui'

export default function Portfolio() {
  const [tab, setTab] = useState('pcaf')
  return (
    <div className="flex-1 overflow-y-auto p-10 animate-fade-in">
      <PageHeader eyebrow="Capability 3 · ESG Data Quality & Portfolio Analytics" title="How good is our data, how green is our book, where do we rank?"
        desc="PCAF data-quality scoring, TKBI-aligned green finance tracking and peer benchmarking, in one view for the C-suite."
        image="/img/city-night.jpg" pos="center 60%">
        <Tabs value={tab} onChange={setTab} tabs={[{ id: 'pcaf', label: 'PCAF data quality' }, { id: 'green', label: 'Green finance (TKBI)' }, { id: 'peer', label: 'Peer benchmark' }]} />
      </PageHeader>
      {tab === 'pcaf' && <Pcaf />}
      {tab === 'green' && <Green />}
      {tab === 'peer' && <Peer />}
    </div>
  )
}

function Pcaf() {
  const [upgrade, setUpgrade] = useState(false)
  const cur = portfolioScore(false)
  const tgt = portfolioScore(true)
  const shown = portfolioScore(upgrade)
  const dist = scoreDistribution(upgrade)
  const classRows = PCAF_CLASSES.map((c) => ({ ...c, s: weightedScore(upgrade ? c.target : c.dist) }))
  return (
    <>
      <div className="grid grid-cols-4 gap-5 mb-5">
        <Stat icon={GaugeIcon} label="Weighted PCAF score" value={shown} decimals={1} sub={upgrade ? `improved from ${cur.toFixed(1)}` : '1 = best (audited), 5 = estimated'} tone={upgrade ? 'teal' : 'amber'} />
        <Stat label="Financed emissions" value={BANK.scope3Cat15 / 1e6} decimals={2} suffix=" Mt" sub="99% of the total GHG inventory" tone="purple" />
        <Stat label="Loan book covered" value={520} suffix=" tn" sub="IDR, six PCAF asset classes" tone="blue" />
        <div className="panel p-5 flex flex-col justify-center">
          <div className="eyebrow mb-2">Improvement advisor</div>
          <button onClick={() => setUpgrade(!upgrade)} className={`rounded-xl px-4 py-2.5 text-sm font-semibold transition ${upgrade ? 'bg-esg-green/15 text-esg-green border border-esg-green/30' : 'bg-gradient-to-r from-accent-blue to-accent-teal text-dark-900'}`}>{upgrade ? 'Showing 12-month plan' : 'Apply 12-month upgrade plan'}</button>
          <div className="text-[11px] text-white/40 mt-2">Target score {tgt.toFixed(1)}</div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-5">
        <Panel className="col-span-5" title="Score distribution" subtitle="Share of outstanding balance by PCAF score">
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={dist}>
                <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="score" tick={axisTick} axisLine={false} tickLine={false} />
                <YAxis tick={axisTick} axisLine={false} tickLine={false} unit="%" />
                <Tooltip {...tooltipProps} formatter={(v) => v.toFixed(1) + '%'} />
                <Bar dataKey="pct" radius={[6, 6, 0, 0]}>{dist.map((d, i) => <Cell key={d.score} fill={PCAF_COLORS[i]} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel className="col-span-7" title="By asset class, with concrete next steps" subtitle="Highest-impact upgrades first" pad={false}>
          <div className="divide-y divide-white/[0.05]">
            {[...classRows].sort((a, b) => b.s - a.s).map((c) => (
              <div key={c.id} className="px-6 py-3.5 row-hover">
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <div className="text-sm text-white">{c.name}</div>
                    <div className="text-[11px] text-white/35">IDR {c.outstanding} tn · {c.system}</div>
                  </div>
                  <div className="flex h-2.5 w-40 rounded-full overflow-hidden bg-white/[0.06]">
                    {(upgrade ? c.target : c.dist).map((p, i) => <div key={i} style={{ width: p + '%', background: PCAF_COLORS[i] }} />)}
                  </div>
                  <Pill tone={c.s > 4 ? 'red' : c.s > 3.2 ? 'amber' : c.s > 2.4 ? 'blue' : 'green'}>{c.s.toFixed(1)}</Pill>
                </div>
                <div className="text-xs text-white/55 mt-1.5 flex gap-1.5"><ArrowRight size={12} className="mt-0.5 text-accent-teal shrink-0" />{c.action}</div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </>
  )
}

function Green() {
  const total = TKBI.reduce((a, t) => a + t.value, 0)
  const green = (TKBI[0].value / total) * 100
  const gap2030 = 40 - GREEN_TREND.find((g) => g.year === '2030').proj
  return (
    <>
      <div className="grid grid-cols-4 gap-5 mb-5">
        <Stat icon={Leaf} label="Green finance ratio" value={green} decimals={1} suffix="%" sub="TKBI-green share of lending" tone="teal" />
        <Stat label="Transition lending" value={(TKBI[1].value / total) * 100} decimals={1} suffix="%" sub="Eligible, on a credible path" tone="amber" />
        <Stat label="Brown lending" value={(TKBI[2].value / total) * 100} decimals={1} suffix="%" sub="Candidates for engagement or exit" tone="red" />
        <Stat label="2030 target gap" value={Math.abs(gap2030)} decimals={1} prefix={gap2030 <= 0 ? '+' : '−'} suffix=" pp" sub="Projection vs action-plan target" tone={gap2030 <= 0 ? 'teal' : 'amber'} />
      </div>
      <div className="grid grid-cols-12 gap-5">
        <Panel className="col-span-4" title="Portfolio composition" subtitle="IDR 520 tn lending book">
          <div className="h-56 relative">
            <ResponsiveContainer>
              <PieChart><Pie data={TKBI} dataKey="value" innerRadius={62} outerRadius={92} paddingAngle={3} stroke="none">{TKBI.map((t) => <Cell key={t.name} fill={t.color} />)}</Pie><Tooltip {...tooltipProps} formatter={(v) => `IDR ${v} tn`} /></PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"><div className="font-display text-3xl font-bold text-white">{green.toFixed(1)}%</div><div className="text-[10px] text-white/40 uppercase tracking-wider">green</div></div>
          </div>
          <div className="grid grid-cols-2 gap-1.5 mt-2">{TKBI.map((t) => <div key={t.name} className="text-[11px] text-white/60 flex items-center gap-1.5"><i className="w-2 h-2 rounded-sm" style={{ background: t.color }} />{t.name}</div>)}</div>
        </Panel>
        <Panel className="col-span-8" title="Green ratio trajectory vs action-plan target" subtitle="% of lending book · actual, projection and target path">
          <div className="h-64">
            <ResponsiveContainer>
              <ComposedChart data={GREEN_TREND}>
                <defs><linearGradient id="gg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.teal} stopOpacity={0.4} /><stop offset="100%" stopColor={C.teal} stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="year" tick={axisTick} axisLine={false} tickLine={false} />
                <YAxis tick={axisTick} axisLine={false} tickLine={false} unit="%" />
                <Tooltip {...tooltipProps} formatter={(v) => v + '%'} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area dataKey="actual" name="Actual" stroke={C.teal} strokeWidth={3} fill="url(#gg)" dot={{ r: 4 }} connectNulls />
                <Line dataKey="proj" name="Projection" stroke={C.blue} strokeWidth={2.5} strokeDasharray="6 4" dot={false} />
                <Line dataKey="target" name="Target (RAKB)" stroke={C.amber} strokeWidth={2} dot={false} />
                <ReferenceLine x="2025" stroke="rgba(255,255,255,0.2)" label={{ value: 'today', fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel className="col-span-12" title="TKBI classification by sector" subtitle="IDR tn per category (share of sector lending)">
          <div className="h-60">
            <ResponsiveContainer>
              <BarChart data={TKBI_SECTORS} layout="vertical" margin={{ left: 40 }}>
                <XAxis type="number" tick={axisTick} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="sector" tick={{ ...axisTick, fontSize: 11 }} axisLine={false} tickLine={false} width={160} />
                <Tooltip {...tooltipProps} /><Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="green" name="Green" stackId="a" fill={C.teal} /><Bar dataKey="transition" name="Transition" stackId="a" fill={C.amber} /><Bar dataKey="brown" name="Brown" stackId="a" fill={C.red} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>
    </>
  )
}

function Peer() {
  const ranked = [...PEERS].map((p) => ({ ...p, c: composite(p) })).sort((a, b) => b.c - a.c)
  const us = ranked.findIndex((p) => p.us) + 1
  const best = PEERS.find((p) => p.id === 'ra')
  const bns = PEERS[0]
  const radar = ['E', 'S', 'G'].map((k) => ({ pillar: { E: 'Environment', S: 'Social', G: 'Governance' }[k], BNS: bns[k], Peers: Math.round(PEERS.slice(1).reduce((a, p) => a + p[k], 0) / (PEERS.length - 1)), Leader: best[k] }))
  const metrics = [
    { k: 'intensity', label: 'Carbon intensity (tCO2e / IDR bn lent)', low: true, d: 1 },
    { k: 'green', label: 'Green finance ratio (%)', d: 1 },
    { k: 'fem', label: 'Women in management (%)', d: 0 },
  ]
  return (
    <div className="grid grid-cols-12 gap-5">
      <Panel className="col-span-5" title="Pillar scores vs peers" subtitle={`Weighted E ${WEIGHTS.E * 100}% · S ${WEIGHTS.S * 100}% · G ${WEIGHTS.G * 100}%`}>
        <div className="h-72">
          <ResponsiveContainer>
            <RadarChart data={radar} outerRadius="70%">
              <PolarGrid stroke="rgba(255,255,255,0.1)" />
              <PolarAngleAxis dataKey="pillar" tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }} />
              <Radar name="Leader" dataKey="Leader" stroke={C.amber} fill={C.amber} fillOpacity={0.05} strokeDasharray="4 4" />
              <Radar name="Peer average" dataKey="Peers" stroke={C.purple} fill={C.purple} fillOpacity={0.15} />
              <Radar name="BNS" dataKey="BNS" stroke={C.teal} fill={C.teal} fillOpacity={0.3} strokeWidth={2.5} />
              <Legend wrapperStyle={{ fontSize: 11 }} /><Tooltip {...tooltipProps} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
      <Panel className="col-span-7" title="Ranking" subtitle="Composite ESG score, 2025" right={<Pill tone="green"><Trophy size={11} /> We are #{us} of {PEERS.length}</Pill>} pad={false}>
        <table className="w-full text-sm">
          <thead><tr className="text-white/40 text-xs text-left"><th className="px-6 py-2">#</th><th>Institution</th><th className="text-right">E</th><th className="text-right">S</th><th className="text-right">G</th><th className="text-right px-6">Composite</th></tr></thead>
          <tbody>
            {ranked.map((p, i) => (
              <tr key={p.id} className={`border-t border-white/[0.05] ${p.us ? 'bg-accent-teal/[0.08]' : 'row-hover'}`}>
                <td className="px-6 py-2.5 text-white/40">{i + 1}</td>
                <td className={p.us ? 'text-white font-semibold' : 'text-white/75'}>{p.name}</td>
                <td className="text-right tabular-nums text-white/70">{p.E}</td><td className="text-right tabular-nums text-white/70">{p.S}</td><td className="text-right tabular-nums text-white/70">{p.G}</td>
                <td className="text-right px-6 tabular-nums font-semibold text-white">{p.c.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
      <Panel className="col-span-12" title="Where do we stand on carbon intensity?" subtitle="Key metrics against the peer group">
        <div className="grid grid-cols-3 gap-5">
          {metrics.map((m) => {
            const vals = PEERS.map((p) => p[m.k]); const mx = Math.max(...vals)
            return (
              <div key={m.k}>
                <div className="text-xs text-white/55 mb-3">{m.label}</div>
                <div className="space-y-1.5">
                  {[...PEERS].sort((a, b) => (m.low ? a[m.k] - b[m.k] : b[m.k] - a[m.k])).map((p) => (
                    <div key={p.id} className="flex items-center gap-2 text-[11px]">
                      <span className={`w-28 truncate ${p.us ? 'text-accent-teal font-semibold' : 'text-white/45'}`}>{p.us ? 'BNS' : p.name.replace('Domestic ', 'Dom. ').replace('Regional ', 'Reg. ')}</span>
                      <div className="flex-1 h-2 rounded-full bg-white/[0.06]"><div className="h-full rounded-full" style={{ width: (p[m.k] / mx) * 100 + '%', background: p.us ? C.teal : 'rgba(255,255,255,0.25)' }} /></div>
                      <span className="w-9 text-right tabular-nums text-white/70">{p[m.k].toFixed(m.d)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
        <p className="text-[11px] text-white/30 mt-5">Peer scores are illustrative. Production version reads public sustainability-report data from the Knowledge Base.</p>
      </Panel>
    </div>
  )
}
