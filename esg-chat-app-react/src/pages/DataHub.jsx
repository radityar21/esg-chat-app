import { useMemo, useState } from 'react'
import { Database, Building2, AlertTriangle, RefreshCw, Search, Sparkles, ArrowRight, ShieldCheck, Factory, Users } from 'lucide-react'
import { PageHeader, Panel, Stat, Pill, Button, Tabs } from '../components/ui'
import SourceBadge from '../components/SourceBadge'
import FacilityDrawer from '../components/FacilityDrawer'
import { useDataHub, t, ENTITY_COLORS, REGION_LABELS, TYPE_LABELS } from '../lib/datahub'

const SEV = { high: 'red', medium: 'amber', low: 'blue' }
const KIND = { not_collected: 'Not collected', coverage: 'Partial coverage', missing_months: 'Missing months', outlier: 'Anomaly', missing_metric: 'Metric not reported',
  estimated: 'Estimated data', missing_factor: 'No emission factor', unit_mismatch: 'Unit mismatch', source: 'Source' }
const CONTRACT = { OK: 'green', WARN: 'amber', FAILED: 'red' }

export default function DataHub({ onNavigate }) {
  const [year, setYear] = useState(2024)
  const [tab, setTab] = useState('overview')
  const [tick, setTick] = useState(0)
  const [facility, setFacility] = useState(null)
  const ov = useDataHub('overview', { year, refresh: tick ? 1 : undefined, _t: tick || undefined })
  const o = ov.data
  return (
    <div className="flex-1 overflow-y-auto p-10 animate-fade-in">
      <PageHeader eyebrow="Data & Accounting · ESG Data Hub" title="Every number, back to the record it came from"
        desc="All source data of the group: five legal entities, their facilities, monthly activity data, emission factors and social, governance and finance metrics. Gaps and anomalies are raised as data alerts instead of being hidden as zeros."
        image="/img/forest-aerial-2.jpg" pos="center 30%" badge={<SourceBadge status={ov.status} error={ov.error} />}>
        <div className="flex flex-col items-end gap-3">
          <Tabs value={year} onChange={setYear} tabs={[{ id: 2023, label: '2023' }, { id: 2024, label: '2024' }]} />
          <Button variant="ghost" icon={RefreshCw} onClick={() => setTick((x) => x + 1)}>Refresh</Button>
        </div>
      </PageHeader>

      {!o ? <Panel><p className="text-sm text-white/50 py-4">{ov.status === 'loading' ? 'Loading the Data Hub… (the first load after a sync runs about ten Athena queries)' : `No data: ${ov.error || 'unavailable'}`}</p></Panel> : (
        <>
          <div className="grid grid-cols-5 gap-5 mb-6">
            <Stat icon={Database} label="Activity records" value={o.records} sub={`${year}, all entities`} tone="blue" />
            <Stat icon={Building2} label="Legal entities" value={o.entities.length} sub={`${o.entities.filter((e) => e.included).length} under operational control`} tone="teal" />
            <Stat icon={Factory} label="Facilities" value={o.entities.reduce((a, e) => a + (e.facilities || 0), 0)} sub="Branches, offices, data centres" tone="purple" />
            <Stat icon={ShieldCheck} label="Metric coverage" value={o.coverage?.pct || 0} decimals={1} suffix="%" sub={`${o.coverage?.reported}/${o.coverage?.applicable} entity-metrics reported`} tone="amber" />
            <Stat icon={AlertTriangle} label="Data alerts" value={(o.alerts.counts.high || 0) + (o.alerts.counts.medium || 0) + (o.alerts.counts.low || 0)} sub={`${o.alerts.counts.high || 0} high · ${o.alerts.counts.medium || 0} medium`} tone="red" />
          </div>
          <div className="mb-5"><Tabs value={tab} onChange={setTab} tabs={[{ id: 'overview', label: 'Entities & datasets' }, { id: 'facilities', label: 'Facility explorer' }, { id: 'alerts', label: `Data alerts · ${(o.alerts.counts.high || 0) + (o.alerts.counts.medium || 0) + (o.alerts.counts.low || 0)}` }, { id: 'lineage', label: 'Lineage' }]} /></div>

          {tab === 'overview' && <Overview o={o} onNavigate={onNavigate} goAlerts={() => setTab('alerts')} />}
          {tab === 'facilities' && <Facilities year={year} onOpen={setFacility} />}
          {tab === 'alerts' && <Alerts year={year} onOpen={setFacility} onNavigate={onNavigate} entities={o.entities} />}
          {tab === 'lineage' && <Lineage o={o} />}
        </>
      )}
      {facility && <FacilityDrawer facilityId={facility} year={year} onClose={() => setFacility(null)} />}
    </div>
  )
}

function Overview({ o, onNavigate, goAlerts }) {
  return (
    <div className="grid grid-cols-12 gap-5">
      <Panel className="col-span-7" title="Organisational boundary" subtitle={`Consolidation: ${o.approach === 'equity' ? 'equity share' : 'operational control'} (GHG Protocol ch. 3) · tCO2e = Scope 1 + 2 (market) + 3 operational`}>
        <div className="space-y-2.5">
          {o.entities.map((e) => (
            <div key={e.entity_id} className={`rounded-xl border px-4 py-3 flex items-center gap-4 ${e.included ? 'border-white/[0.08] bg-white/[0.025]' : 'border-dashed border-white/10 bg-transparent'}`}>
              <div className="w-2 self-stretch rounded-full" style={{ background: ENTITY_COLORS[e.entity_id] }} />
              <div className="flex-1 min-w-0">
                <div className="text-sm text-white font-medium">{e.name}</div>
                <div className="text-[11px] text-white/45">{e.type_label} · {e.ownership_pct}% owned · {e.operational_control ? 'operational control' : 'no operational control (equity share only)'}</div>
              </div>
              <div className="text-right text-[11px] text-white/50 w-24"><div className="text-white/80 text-sm tabular-nums">{t(e.facilities)}</div>facilities</div>
              <div className="text-right text-[11px] text-white/50 w-24"><div className="text-white/80 text-sm tabular-nums">{t(e.headcount)}</div>people</div>
              <div className="text-right text-[11px] text-white/50 w-28"><div className="text-white text-sm font-semibold tabular-nums">{e.included ? t(e.total_market) : 'excluded'}</div>tCO2e</div>
              <button onClick={goAlerts} className={`w-16 text-right text-xs ${e.alerts ? 'text-esg-amber' : 'text-white/30'}`}>{e.alerts} alerts</button>
            </div>
          ))}
        </div>
      </Panel>
      <Panel className="col-span-5" title="Most important data alerts" subtitle="Highest severity first" right={<button className="text-xs text-accent-teal" onClick={goAlerts}>All alerts</button>}>
        <div className="space-y-2">
          {o.alerts.top.map((a) => (
            <div key={a.id} className="rounded-lg bg-white/[0.03] px-3 py-2.5">
              <div className="flex items-center gap-2"><Pill tone={SEV[a.severity]}>{a.severity}</Pill><span className="text-[10px] text-white/40">{KIND[a.kind] || a.kind}</span></div>
              <div className="text-xs text-white/85 mt-1">{a.title}</div>
            </div>
          ))}
        </div>
        {onNavigate && <div className="mt-4"><Button variant="ghost" icon={Sparkles} onClick={() => onNavigate('chat', { prompt: `Review the ${o.year} data alerts in the Data Hub: which gaps matter most for the sustainability report, who must act, and what can be estimated?` })}>Ask the AI to prioritise</Button></div>}
      </Panel>
      <Panel className="col-span-12" title="Datasets" subtitle="Rows in the data lake for the year and the last data-contract check of each table" pad={false}>
        <table className="w-full text-sm">
          <thead><tr className="text-left text-white/40 text-[11px] uppercase tracking-wider">{['Table', 'Content', 'Scope', 'Rows', 'Contract check'].map((h) => <th key={h} className="px-6 py-3 font-semibold">{h}</th>)}</tr></thead>
          <tbody>
            {o.datasets.map((d) => (
              <tr key={d.table} className="border-t border-white/[0.05]">
                <td className="px-6 py-2.5 font-mono text-xs text-white/80">{d.table}</td>
                <td className="px-6 py-2.5 text-white/65 text-xs">{d.label}</td>
                <td className="px-6 py-2.5"><Pill tone={d.group === 'group' ? 'purple' : 'blue'}>{d.group === 'group' ? 'Group' : 'Bank'}</Pill></td>
                <td className="px-6 py-2.5 tabular-nums text-white/80">{d.rows == null ? <span className="text-esg-amber text-xs">not synced</span> : t(d.rows)}</td>
                <td className="px-6 py-2.5 text-xs">{d.contract ? <span className="flex items-center gap-2"><Pill tone={CONTRACT[d.contract.status] || 'slate'}>{d.contract.status}</Pill><span className="text-white/40">{d.contract.warnings ? `${d.contract.warnings} warning(s) · ` : ''}{d.contract.generated_at ? new Date(d.contract.generated_at).toLocaleString() : ''}</span></span> : <span className="text-white/30">no report</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </div>
  )
}

function Facilities({ year, onOpen }) {
  const d = useDataHub('facilities', { year })
  const [q, setQ] = useState('')
  const [ent, setEnt] = useState('all')
  const [type, setType] = useState('all')
  const [region, setRegion] = useState('all')
  const rows = useMemo(() => (d.data?.facilities || []).filter((f) => (ent === 'all' || f.entity_id === ent) && (type === 'all' || f.facility_type === type)
    && (region === 'all' || f.grid_region === region) && (!q || `${f.facility_id} ${f.facility_name} ${f.city} ${f.province}`.toLowerCase().includes(q.toLowerCase()))), [d.data, q, ent, type, region])
  const sel = 'rounded-lg bg-white/[0.05] border border-white/10 px-2.5 py-1.5 text-xs text-white/80'
  return (
    <Panel title="Facility explorer" subtitle="Gross emissions per facility (100 %, before consolidation). Click a facility for its records and factors." pad={false}
      right={<SourceBadge status={d.status} error={d.error} />}>
      <div className="px-6 pb-3 flex flex-wrap gap-2 items-center">
        <div className="relative"><Search size={13} className="absolute left-2.5 top-2 text-white/30" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search id, name, city" className={`${sel} pl-8 w-56`} /></div>
        <select value={ent} onChange={(e) => setEnt(e.target.value)} className={sel}><option value="all" className="bg-dark-900">All entities</option>{(d.data?.entities || []).map((e) => <option key={e.id} value={e.id} className="bg-dark-900">{e.name}</option>)}</select>
        <select value={type} onChange={(e) => setType(e.target.value)} className={sel}><option value="all" className="bg-dark-900">All types</option>{Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k} className="bg-dark-900">{v}</option>)}</select>
        <select value={region} onChange={(e) => setRegion(e.target.value)} className={sel}><option value="all" className="bg-dark-900">All grid regions</option>{Object.entries(REGION_LABELS).map(([k, v]) => <option key={k} value={k} className="bg-dark-900">{v}</option>)}</select>
        <span className="text-xs text-white/40 ml-auto">{rows.length} facilities</span>
      </div>
      <div className="max-h-[620px] overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-dark-800"><tr className="text-left text-white/40 text-[10px] uppercase tracking-wider">{['Facility', 'Entity', 'Type', 'Region', 'Area m²', 'People', 'Scope 1', 'Scope 2 (mkt)', 'Scope 3', 'kgCO2e/m²', 'Estimated', 'Alerts'].map((h) => <th key={h} className="px-4 py-2.5 font-semibold">{h}</th>)}</tr></thead>
          <tbody>
            {rows.slice(0, 400).map((f) => (
              <tr key={f.facility_id} onClick={() => onOpen(f.facility_id)} className="border-t border-white/[0.04] row-hover cursor-pointer">
                <td className="px-4 py-2"><div className="text-white/85">{f.facility_name}</div><div className="text-[10px] text-white/35 font-mono">{f.facility_id}{f.status === 'opened' ? ' · opened this year' : ''}</div></td>
                <td className="px-4 py-2"><span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ background: ENTITY_COLORS[f.entity_id] }} />{f.entity_id.replace('ENT-', '')}</td>
                <td className="px-4 py-2 text-white/60">{TYPE_LABELS[f.facility_type]}</td>
                <td className="px-4 py-2 text-white/60">{REGION_LABELS[f.grid_region]}</td>
                <td className="px-4 py-2 tabular-nums text-white/60">{t(f.floor_area_m2)}</td>
                <td className="px-4 py-2 tabular-nums text-white/60">{t(f.headcount)}</td>
                <td className="px-4 py-2 tabular-nums text-white/80">{t(f.s1, 1)}</td>
                <td className="px-4 py-2 tabular-nums text-white/80">{t(f.s2_market, 1)}</td>
                <td className="px-4 py-2 tabular-nums text-white/80">{t(f.s3, 1)}</td>
                <td className="px-4 py-2 tabular-nums text-white/60">{t(f.kg_per_m2, 1)}</td>
                <td className={`px-4 py-2 tabular-nums ${f.estimated_pct > 25 ? 'text-esg-amber' : 'text-white/50'}`}>{t(f.estimated_pct, 0)}%</td>
                <td className="px-4 py-2">{f.alerts ? <Pill tone="amber">{f.alerts}</Pill> : <span className="text-white/25">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

function Alerts({ year, onOpen, onNavigate, entities }) {
  const d = useDataHub('alerts', { year })
  const [sev, setSev] = useState('all')
  const [kind, setKind] = useState('all')
  const [ent, setEnt] = useState('all')
  const list = (d.data?.alerts || []).filter((a) => (sev === 'all' || a.severity === sev) && (kind === 'all' || a.kind === kind) && (ent === 'all' || a.entity_id === ent))
  const name = Object.fromEntries(entities.map((e) => [e.entity_id, e.name]))
  const sel = 'rounded-lg bg-white/[0.05] border border-white/10 px-2.5 py-1.5 text-xs text-white/80'
  return (
    <Panel title="Data alerts" subtitle="What is wrong, where, why it matters and what to do. Recomputed on every data sync." right={<SourceBadge status={d.status} error={d.error} />}>
      <div className="flex flex-wrap gap-2 mb-4">
        <Tabs value={sev} onChange={setSev} tabs={[{ id: 'all', label: 'All' }, { id: 'high', label: `High · ${d.data?.counts?.high || 0}` }, { id: 'medium', label: `Medium · ${d.data?.counts?.medium || 0}` }, { id: 'low', label: `Low · ${d.data?.counts?.low || 0}` }]} />
        <select value={kind} onChange={(e) => setKind(e.target.value)} className={sel}><option value="all" className="bg-dark-900">All kinds</option>{Object.entries(d.data?.kinds || {}).map(([k, n]) => <option key={k} value={k} className="bg-dark-900">{KIND[k] || k} ({n})</option>)}</select>
        <select value={ent} onChange={(e) => setEnt(e.target.value)} className={sel}><option value="all" className="bg-dark-900">All entities</option>{entities.map((e) => <option key={e.entity_id} value={e.entity_id} className="bg-dark-900">{e.name}</option>)}</select>
      </div>
      <div className="space-y-2.5">
        {list.length === 0 && <p className="text-sm text-white/40 py-6 text-center">No alerts in this view.</p>}
        {list.map((a) => (
          <div key={a.id} className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <Pill tone={SEV[a.severity]}>{a.severity}</Pill><Pill tone="slate">{KIND[a.kind] || a.kind}</Pill>
              {a.entity_id && <span className="text-[11px] text-white/40">{name[a.entity_id] || a.entity_id}</span>}
              <span className="text-[10px] text-white/25 font-mono ml-auto">{a.id}</span>
            </div>
            <div className="text-sm text-white font-medium">{a.title}</div>
            <div className="text-xs text-white/55 mt-1">{a.detail}</div>
            <div className="text-xs text-white/45 mt-1"><span className="text-white/30">Impact:</span> {a.impact}</div>
            <div className="text-xs text-accent-teal/85 mt-1"><span className="text-white/30">Action:</span> {a.action}</div>
            <div className="flex gap-2 mt-3">
              {a.facility_id && <Button variant="ghost" icon={ArrowRight} onClick={() => onOpen(a.facility_id)}>Open {a.facility_id}</Button>}
              {onNavigate && <Button variant="ghost" icon={Sparkles} onClick={() => onNavigate('chat', { prompt: `Explain data alert ${a.id} for ${year} ("${a.title}"): what is the impact on the GHG inventory and the sustainability report, and what should the data owner do?` })}>Ask the AI</Button>}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  )
}

function Lineage({ o }) {
  return (
    <Panel title="Data lineage" subtitle="From the source database to the report. Every step is versioned in the repository.">
      <div className="flex items-stretch gap-2 overflow-x-auto pb-2">
        {o.lineage.map((s, i) => (
          <div key={s.step} className="flex items-center gap-2">
            <div className="w-52 shrink-0 rounded-xl border border-white/[0.08] bg-white/[0.03] p-4 h-full">
              <div className="text-[10px] text-accent-teal mb-1">Step {i + 1}</div>
              <div className="text-sm text-white font-medium">{s.step}</div>
              <div className="text-[11px] text-white/55 mt-1.5 leading-relaxed">{s.detail}</div>
              <div className="text-[10px] text-white/30 font-mono mt-2">{s.where}</div>
            </div>
            {i < o.lineage.length - 1 && <ArrowRight size={16} className="text-white/25 shrink-0" />}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-4 mt-6 text-xs text-white/55 leading-relaxed">
        <div className="rounded-xl bg-white/[0.02] p-4"><Users size={14} className="text-accent-blue mb-2" />Source systems own the data. The platform never edits it: problems are raised as alerts to the data owner.</div>
        <div className="rounded-xl bg-white/[0.02] p-4"><ShieldCheck size={14} className="text-accent-teal mb-2" />A failed contract check (missing column, wrong type, duplicate keys) stops the load before the data lake is overwritten.</div>
        <div className="rounded-xl bg-white/[0.02] p-4"><Database size={14} className="text-accent-purple mb-2" />The ledger is a view: changing an emission factor recalculates every year without reloading data.</div>
      </div>
    </Panel>
  )
}
