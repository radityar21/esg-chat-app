import { useEffect, useState } from 'react'
import { Play, ScanSearch, Wand2, CheckCircle2, AlertTriangle, FileText, XCircle, RotateCcw, Loader2, Download, Bot, RefreshCw } from 'lucide-react'
import { api, platformEnabled } from '../lib/platform'
import { Pill } from './ui'

const EV = {
  pipeline_started: { icon: Play, color: 'text-accent-blue' },
  still_running: { icon: Loader2, color: 'text-white/40' },
  pipeline_succeeded: { icon: CheckCircle2, color: 'text-esg-green' },
  pipeline_failed: { icon: XCircle, color: 'text-esg-red' },
  pipeline_restarted: { icon: RotateCcw, color: 'text-esg-amber' },
  validation_review: { icon: ScanSearch, color: 'text-accent-purple' },
  regenerating: { icon: Wand2, color: 'text-accent-teal' },
  regeneration_error: { icon: AlertTriangle, color: 'text-esg-amber' },
  revalidated: { icon: CheckCircle2, color: 'text-accent-blue' },
  reassembling: { icon: FileText, color: 'text-white/50' },
  reassembled: { icon: FileText, color: 'text-esg-green' },
  completed: { icon: CheckCircle2, color: 'text-esg-green' },
  escalated: { icon: AlertTriangle, color: 'text-esg-amber' },
}
const TONE = { completed: 'green', running: 'blue', escalated: 'amber', failed: 'red', pending: 'slate' }
const timeOf = (iso) => (iso ? new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '')

/** Live view of what the AgentCore orchestrator did for each report run (reads the S3 ledger through the platform API). */
export default function AgentActivity({ focusId, compact = false }) {
  const [runs, setRuns] = useState([])
  const [sel, setSel] = useState(null)
  const [ledger, setLedger] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!platformEnabled) return undefined
    let stop = false
    const load = () => api('/agent/runs?limit=8').then((r) => { if (!stop) { setRuns(r.runs); setError(null) } }).catch((e) => !stop && setError(e.message))
    load()
    const t = setInterval(load, 10000)
    return () => { stop = true; clearInterval(t) }
  }, [])
  useEffect(() => { if (focusId) setSel(focusId) }, [focusId])
  useEffect(() => { if (!sel && runs[0]) setSel(runs[0].execution_id) }, [runs, sel])
  useEffect(() => {
    if (!sel || !platformEnabled) return undefined
    let stop = false
    const load = () => api(`/agent/runs/${encodeURIComponent(sel)}`).then((r) => !stop && setLedger(r.found ? r.ledger : null)).catch(() => {})
    load()
    const t = setInterval(load, 8000)
    return () => { stop = true; clearInterval(t) }
  }, [sel])

  if (!platformEnabled) {
    return <div className="text-xs text-white/40 leading-relaxed">Agent activity appears here once the platform API is configured (VITE_PLATFORM_API_URL).</div>
  }
  const sections = ledger ? Object.entries(ledger.sections || {}) : []
  return (
    <div className="space-y-4">
      {error && <div className="text-[11px] text-esg-amber">Cannot read agent runs: {error}</div>}
      {runs.length === 0 && !error && <div className="text-xs text-white/40">No agent runs yet. Ask the assistant to generate a report.</div>}
      <div className="space-y-1.5">
        {runs.map((r) => (
          <button key={r.execution_id} onClick={() => setSel(r.execution_id)}
            className={`w-full text-left rounded-xl px-3 py-2 border transition ${sel === r.execution_id ? 'border-accent-teal/40 bg-accent-teal/[0.07]' : 'border-white/[0.07] bg-white/[0.025] hover:bg-white/[0.05]'}`}>
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-[11px] text-white/70 truncate">{(r.execution_id || '').slice(0, 13)}</span>
              <Pill tone={TONE[r.status] || 'slate'}>{r.status}</Pill>
            </div>
            <div className="text-[10px] text-white/35 mt-1">{r.pipeline || 'pipeline'} · {r.healed ? `${r.healed} section(s) auto-repaired` : 'no repairs'}{r.escalated ? ` · ${r.escalated} escalated` : ''}</div>
          </button>
        ))}
      </div>

      {ledger && (
        <div>
          <div className="flex items-center gap-2 mb-2"><Bot size={14} className="text-accent-teal" /><span className="eyebrow">Orchestrator timeline</span></div>
          {sections.length > 0 && !compact && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {sections.map(([tid, s]) => <span key={tid} title={(s.explanations || []).join(' ')} className={`text-[10px] px-2 py-0.5 rounded-md border ${s.status === 'healed' ? 'border-esg-green/30 text-esg-green' : s.status === 'ok' ? 'border-white/10 text-white/40' : 'border-esg-amber/30 text-esg-amber'}`}>{tid}{s.attempts ? ` · ${s.attempts}x` : ''}</span>)}
            </div>
          )}
          <ol className="relative border-l border-white/10 ml-2 space-y-3">
            {(ledger.events || []).slice(-14).map((e, i) => {
              const m = EV[e.type] || { icon: RefreshCw, color: 'text-white/40' }
              return (
                <li key={i} className="pl-4 relative">
                  <m.icon size={13} className={`absolute -left-[7px] top-0.5 bg-dark-900 rounded-full ${m.color}`} />
                  <div className="text-xs text-white/80 leading-snug">{e.message}</div>
                  <div className="text-[10px] text-white/30 mt-0.5">{timeOf(e.ts)}</div>
                </li>
              )
            })}
          </ol>
          {ledger.result?.download_url && (
            <div className="flex gap-2 mt-4">
              <a href={ledger.result.download_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-blue/10 text-accent-blue text-xs"><Download size={12} /> DOCX</a>
              {ledger.result.download_url_pptx && <a href={ledger.result.download_url_pptx} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-esg-amber/10 text-esg-amber text-xs"><Download size={12} /> PPTX</a>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
