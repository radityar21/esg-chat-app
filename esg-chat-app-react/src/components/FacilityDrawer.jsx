import { useState } from 'react'
import { X, Loader2, FileCheck2, AlertTriangle } from 'lucide-react'
import { Pill, Tabs } from './ui'
import SourceBadge from './SourceBadge'
import { useDataHub, t, REGION_LABELS, TYPE_LABELS } from '../lib/datahub'

// Audit trail of one facility: every activity record, the factor applied and the resulting emissions.
export default function FacilityDrawer({ facilityId, year, efSet = 'ID_NATIONAL', onClose }) {
  const d = useDataHub('facility', { year, facility_id: facilityId, ef_set: efSet })
  const [tab, setTab] = useState('summary')
  const f = d.data?.facility
  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50" />
      <aside className="relative w-[760px] max-w-full h-full overflow-y-auto bg-dark-900 border-l border-white/10 p-7" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            <div className="eyebrow text-accent-teal mb-1">Facility audit trail · {year}</div>
            <h2 className="text-xl font-display font-bold text-white">{f?.facility_name || facilityId}</h2>
            {f && <div className="text-xs text-white/50 mt-1">{facilityId} · {f.entity_name} · {TYPE_LABELS[f.facility_type] || f.facility_type} · {f.province} ({REGION_LABELS[f.grid_region] || f.grid_region} grid) · {t(f.floor_area_m2)} m² · {t(f.headcount)} people</div>}
          </div>
          <div className="flex items-center gap-2"><SourceBadge status={d.status} error={d.error} /><button onClick={onClose} className="text-white/40 hover:text-white"><X size={18} /></button></div>
        </div>
        {d.status === 'loading' && <Loader2 className="w-5 h-5 animate-spin text-accent-blue" />}
        {!d.data && d.status !== 'loading' && <p className="text-sm text-white/50">Record-level data for this facility is only available with the live platform API{d.error ? ` (${d.error})` : ''}.</p>}
        {d.data && (
          <>
            <div className="mb-4"><Tabs value={tab} onChange={setTab} tabs={[{ id: 'summary', label: 'By activity' }, { id: 'records', label: `Records · ${d.data.records.length}` }]} /></div>
            {tab === 'summary' ? (
              <table className="w-full text-xs">
                <thead><tr className="text-left text-white/40 uppercase tracking-wider text-[10px]">{['Activity', 'Scope', 'Quantity', 'Factor (kgCO2e/unit)', 'tCO2e', 'Months', 'Estimated'].map((h) => <th key={h} className="py-2 pr-3 font-semibold">{h}</th>)}</tr></thead>
                <tbody>
                  {d.data.activities.map((a) => (
                    <tr key={a.activity_type} className="border-t border-white/[0.05]">
                      <td className="py-2 pr-3 text-white/85">{a.activity_label}<div className="text-[10px] text-white/35">{a.ef_source}</div></td>
                      <td className="py-2 pr-3"><Pill tone={a.scope === 1 ? 'red' : a.scope === 2 ? 'blue' : 'purple'}>Scope {a.scope}</Pill></td>
                      <td className="py-2 pr-3 text-white/70 tabular-nums">{t(a.quantity, 1)} {a.unit}</td>
                      <td className="py-2 pr-3 text-white/70 tabular-nums">{t(a.factor_kgco2e, 4)}</td>
                      <td className="py-2 pr-3 text-white font-semibold tabular-nums">{t(a.tco2e_market, 2)}</td>
                      <td className={`py-2 pr-3 tabular-nums ${a.months < 12 && a.scope !== 1 ? 'text-esg-amber' : 'text-white/60'}`}>{a.months}</td>
                      <td className="py-2 pr-3 text-white/60">{a.estimated ? <span className="text-esg-amber">{a.estimated}</span> : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <table className="w-full text-[11px]">
                <thead><tr className="text-left text-white/40 uppercase tracking-wider text-[10px]">{['Month', 'Activity', 'Quantity', '× Factor', '= tCO2e', 'Source', 'Evidence'].map((h) => <th key={h} className="py-2 pr-2 font-semibold">{h}</th>)}</tr></thead>
                <tbody>
                  {d.data.records.map((r) => (
                    <tr key={r.activity_id} className="border-t border-white/[0.04]">
                      <td className="py-1.5 pr-2 text-white/60">{r.month}</td>
                      <td className="py-1.5 pr-2 text-white/80">{r.activity_label}</td>
                      <td className="py-1.5 pr-2 tabular-nums text-white/70">{t(r.quantity, 1)} {r.unit}{r.instrument_qty ? <div className="text-[10px] text-accent-teal">REC {t(r.instrument_qty)} kWh</div> : null}</td>
                      <td className="py-1.5 pr-2 tabular-nums text-white/60">{t(r.factor_kgco2e, 4)}</td>
                      <td className="py-1.5 pr-2 tabular-nums text-white">{t(r.tco2e_market, 3)}</td>
                      <td className="py-1.5 pr-2 text-white/50">{r.estimated ? <span className="inline-flex items-center gap-1 text-esg-amber"><AlertTriangle size={10} />estimate</span> : r.data_source}</td>
                      <td className="py-1.5 pr-2 text-white/40 font-mono text-[10px]"><FileCheck2 size={10} className="inline mr-1" />{r.evidence_ref || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <p className="text-[10px] text-white/35 mt-4">tCO2e = quantity × (CO2 + CH4 × GWP + N2O × GWP + direct CO2e) ÷ 1000. Market-based Scope 2 deducts certificate-covered electricity (REC) first. Factor set: {d.data.ef_set}.</p>
          </>
        )}
      </aside>
    </div>
  )
}
