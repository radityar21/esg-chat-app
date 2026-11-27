import { useEffect, useState } from 'react'
import { CheckCircle2, Circle, Loader2, XCircle, AlertTriangle, MinusCircle, Download } from 'lucide-react'
import { api } from '../lib/platform'

// Live checkpoints of one run: inner Step Functions steps followed by the AgentCore orchestrator's own steps.
const ICON = {
  done: { icon: CheckCircle2, cls: 'text-esg-green' },
  running: { icon: Loader2, cls: 'text-accent-blue animate-spin' },
  pending: { icon: Circle, cls: 'text-white/20' },
  failed: { icon: XCircle, cls: 'text-esg-red' },
  warning: { icon: AlertTriangle, cls: 'text-esg-amber' },
  skipped: { icon: MinusCircle, cls: 'text-white/25' },
}
const TITLE = { esg_report: 'Report generation', data_sync: 'Data sync from the source database', ghg_inventory: 'GHG inventory' }
const FINAL = { completed: { t: 'Completed', c: 'text-esg-green' }, escalated: { t: 'Completed, needs attention', c: 'text-esg-amber' }, failed: { t: 'Failed', c: 'text-esg-red' }, running: { t: 'In progress', c: 'text-accent-blue' } }
const TERMINAL = new Set(['completed', 'escalated', 'failed'])

const dur = (a, b) => {
  if (!a || !b) return ''
  const s = Math.max(0, Math.round((new Date(b) - new Date(a)) / 1000))
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
}

export default function RunProgress({ executionId, compact = false, onDone }) {
  const [p, setP] = useState(null)
  const [error, setError] = useState(null)
  const [download, setDownload] = useState(null)

  useEffect(() => {
    let stop = false
    let timer
    const load = async () => {
      try {
        const r = await api(`/agent/runs/${encodeURIComponent(executionId)}/progress`)
        if (stop) return
        setP(r)
        setError(null)
        if (TERMINAL.has(r.status)) {
          if (r.pipeline === 'esg_report') {
            const l = await api(`/agent/runs/${encodeURIComponent(executionId)}`).catch(() => null)
            if (!stop && l?.ledger?.result?.download_url) setDownload(l.ledger.result)
          }
          onDone?.(r)
          return
        }
      } catch (e) {
        if (!stop) setError(e.message)
      }
      if (!stop) timer = setTimeout(load, 5000)
    }
    load()
    return () => { stop = true; clearTimeout(timer) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [executionId])

  if (!p) {
    return <div className="text-xs text-white/40 flex items-center gap-2">{error ? `Progress unavailable: ${error}` : <><Loader2 size={12} className="animate-spin" />Loading progress…</>}</div>
  }
  const final = FINAL[p.status] || FINAL.running
  const year = p.params?.reporting_year
  return (
    <div className={compact ? '' : 'rounded-2xl border border-white/[0.08] bg-white/[0.025] px-5 py-4'}>
      {!compact && (
        <div className="flex items-center justify-between gap-3 mb-3">
          <div>
            <div className="text-sm font-semibold text-white">{TITLE[p.pipeline] || p.pipeline}{year ? ` · ${year}` : ''}{p.params?.framework ? ` · ${p.params.framework}` : ''}</div>
            <div className="text-[10px] text-white/35 font-mono">{p.execution_id}</div>
          </div>
          <span className={`text-xs font-medium ${final.c}`}>{final.t}{TERMINAL.has(p.status) && p.started_at && p.stopped_at ? ` · ${dur(p.started_at, p.stopped_at)}` : ''}</span>
        </div>
      )}
      <ol className="space-y-2">
        {p.steps.map((s) => {
          const I = ICON[s.status] || ICON.pending
          return (
            <li key={s.key} className="flex items-start gap-2.5">
              <I.icon size={15} className={`${I.cls} mt-0.5 shrink-0`} />
              <div className="min-w-0 flex-1">
                <div className={`text-xs leading-snug ${s.status === 'pending' || s.status === 'skipped' ? 'text-white/40' : 'text-white/85'}`}>{s.label}</div>
                {(s.detail || (s.started_at && s.ended_at)) && (
                  <div className="text-[10px] text-white/40 mt-0.5">{[s.detail, dur(s.started_at, s.ended_at)].filter(Boolean).join(' · ')}</div>
                )}
              </div>
            </li>
          )
        })}
      </ol>
      {download && (
        <div className="flex gap-2 mt-3">
          <a href={download.download_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-blue/10 text-accent-blue text-xs"><Download size={12} /> DOCX</a>
          {download.download_url_pptx && <a href={download.download_url_pptx} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-esg-amber/10 text-esg-amber text-xs"><Download size={12} /> PPTX</a>}
        </div>
      )}
      {error && <div className="text-[10px] text-esg-amber mt-2">Refresh failed: {error}. Retrying…</div>}
    </div>
  )
}
