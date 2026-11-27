// Data Hub client: live data from /data/* (lambda/platform_api/datahub.py) with a bundled demo snapshot as fallback.
// The snapshot is produced by esg-reporting-poc/scripts/datahub_local.py from the same seed data and the same code.
import { useEffect, useState } from 'react'
import { useLive } from './platform'

let demoPromise
const loadDemo = () => (demoPromise ||= import('../data/datahub_demo.json').then((m) => m.default || m))

function demoView(snap, view, p) {
  const y = snap[String(p.year || 2024)]
  if (!y) return null
  if (view === 'ledger') return y.ledger[`${p.approach || 'control'}|${p.ef_set || 'ID_NATIONAL'}`]
  if (view === 'facility') return y.facility[p.facility_id] || null
  return y[view] || null
}

/** {data, status: 'live'|'loading'|'demo'|'error', error, reload}. On 'error' the data is the demo snapshot. */
export function useDataHub(view, params = {}) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '').map(([k, v]) => [k, String(v)])).toString()
  const live = useLive(`/data/${view}${qs ? `?${qs}` : ''}`)
  const [demo, setDemo] = useState(null)
  const needDemo = live.status === 'demo' || live.status === 'error'
  useEffect(() => {
    if (!needDemo) return undefined
    let stop = false
    loadDemo().then((snap) => { if (!stop) setDemo(demoView(snap, view, params)) })
    return () => { stop = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [needDemo, view, qs])
  if (live.status === 'live') return live
  if (live.status === 'loading') return { ...live, data: null }
  return { ...live, data: demo }
}

export const ENTITY_COLORS = { 'ENT-BANK': '#4f8cf7', 'ENT-SYR': '#06d6a0', 'ENT-MFN': '#fbbf24', 'ENT-SEK': '#7c5cfc', 'ENT-ASR': '#22d3ee' }
export const SCOPE_COLORS = { s1: '#ef4444', s2_market: '#4f8cf7', s2_location: '#93c5fd', s3: '#7c5cfc' }
export const REGION_LABELS = { java_bali: 'Java-Bali', sumatra: 'Sumatra', kalimantan: 'Kalimantan', sulawesi: 'Sulawesi', nusa_tenggara: 'Nusa Tenggara', papua_maluku: 'Papua-Maluku' }
export const TYPE_LABELS = { headquarters: 'Headquarters', regional_office: 'Regional office', data_centre: 'Data centre', branch: 'Branch', warehouse: 'Warehouse' }

const nf = (d) => new Intl.NumberFormat('en-US', { maximumFractionDigits: d, minimumFractionDigits: 0 })

/** Format a value with its unit. Missing values are shown as missing, never as 0. */
export function fmtValue(v, unit) {
  if (v === null || v === undefined) return '—'
  if (unit === 'IDR') {
    const a = Math.abs(v)
    if (a >= 1e12) return `IDR ${nf(1).format(v / 1e12)} T`
    if (a >= 1e9) return `IDR ${nf(1).format(v / 1e9)} bn`
    if (a >= 1e6) return `IDR ${nf(1).format(v / 1e6)} m`
    return `IDR ${nf(0).format(v)}`
  }
  if (unit === 'yes/no') return v ? 'Yes' : 'No'
  if (unit === '%') return `${nf(1).format(v)}%`
  if (unit === 'ratio') return nf(2).format(v)
  const d = Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2
  return `${nf(d).format(v)}${unit ? ` ${unit}` : ''}`
}

export const t = (v, d = 0) => (v === null || v === undefined ? '—' : nf(d).format(v))
