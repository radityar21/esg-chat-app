import { useState, useEffect, useMemo } from 'react'
import { getHistory } from '../api'
import { RefreshCw, Download, FileText, Clock, CheckCircle2, XCircle, Loader2, Bot } from 'lucide-react'
import { PageHeader, Panel, Stat, Pill, Button, Tabs } from '../components/ui'
import AgentActivity from '../components/AgentActivity'
import { api, platformEnabled } from '../lib/platform'

const STATUS = {
  SUCCEEDED: { icon: CheckCircle2, tone: 'green', label: 'Succeeded' },
  FAILED: { icon: XCircle, tone: 'red', label: 'Failed' },
  RUNNING: { icon: Loader2, tone: 'amber', label: 'Running' },
}

export default function Reports() {
  const [executions, setExecutions] = useState([])
  const [agentRuns, setAgentRuns] = useState({})
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [focus, setFocus] = useState(null)

  async function loadHistory() {
    setLoading(true)
    try {
      const data = platformEnabled ? await api('/reports/history?limit=20') : await getHistory(20)
      setExecutions(data.executions || [])
    } catch (e) { console.error(e) }
    if (platformEnabled) {
      try {
        const r = await api('/agent/runs?limit=50')
        setAgentRuns(Object.fromEntries(r.runs.map((x) => [x.execution_id, x])))
      } catch (e) { console.error(e) }
    }
    setLoading(false)
  }
  useEffect(() => { loadHistory() }, [])

  const counts = useMemo(() => ({
    all: executions.length,
    SUCCEEDED: executions.filter((e) => e.status === 'SUCCEEDED').length,
    FAILED: executions.filter((e) => e.status === 'FAILED').length,
    RUNNING: executions.filter((e) => e.status === 'RUNNING').length,
  }), [executions])
  const repaired = Object.values(agentRuns).reduce((a, r) => a + (r.healed || 0), 0)
  const filtered = filter === 'all' ? executions : executions.filter((ex) => ex.status === filter)

  return (
    <div className="flex-1 overflow-y-auto p-10 animate-fade-in">
      <PageHeader eyebrow="Workspace · Report history" title="Every report, and what the agent did to get it right"
        desc="Generated sustainability reports with their status. For runs supervised by the AgentCore orchestrator, the number of sections it repaired on its own is shown next to the download."
        image="/img/forest-aerial-2.jpg" pos="center 55%">
        <Button variant="ghost" icon={RefreshCw} onClick={loadHistory}>{loading ? 'Loading…' : 'Refresh'}</Button>
      </PageHeader>

      <div className="grid grid-cols-4 gap-5 mb-6">
        <Stat icon={FileText} label="Runs" value={counts.all} sub="Most recent 20 executions" tone="blue" />
        <Stat icon={CheckCircle2} label="Succeeded" value={counts.SUCCEEDED} sub="Report assembled" tone="teal" />
        <Stat icon={XCircle} label="Failed" value={counts.FAILED} sub="See the agent timeline for the cause" tone="red" />
        <Stat icon={Bot} label="Sections auto-repaired" value={repaired} sub={platformEnabled ? 'By the orchestrator, across runs' : 'Available with the platform API'} tone="purple" />
      </div>

      <div className="mb-5">
        <Tabs value={filter} onChange={setFilter} tabs={[{ id: 'all', label: `All · ${counts.all}` }, { id: 'SUCCEEDED', label: `Succeeded · ${counts.SUCCEEDED}` }, { id: 'FAILED', label: `Failed · ${counts.FAILED}` }, { id: 'RUNNING', label: `Running · ${counts.RUNNING}` }]} />
      </div>

      <div className={`grid gap-5 ${platformEnabled ? 'grid-cols-12' : 'grid-cols-1'}`}>
        <Panel className={platformEnabled ? 'col-span-8' : ''} pad={false}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-white/40 text-[11px] uppercase tracking-wider">
                  {['Date', 'Framework', 'Year', 'Duration', 'Status', ...(platformEnabled ? ['Agent'] : []), 'Download'].map((h) => <th key={h} className="px-6 py-3 font-semibold">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan="7" className="px-6 py-12 text-center"><Loader2 className="w-5 h-5 text-accent-blue animate-spin mx-auto mb-2" /><span className="text-sm text-white/40">Loading reports…</span></td></tr>
                ) : filtered.length === 0 ? (
                  <tr><td colSpan="7" className="px-6 py-12 text-center"><FileText className="w-8 h-8 mx-auto mb-2 text-white/15" /><span className="text-sm text-white/40">No reports found</span><p className="text-xs mt-1 text-white/25">Generate your first report from the assistant</p></td></tr>
                ) : filtered.map((ex, i) => {
                  const st = STATUS[ex.status] || STATUS.RUNNING
                  const run = agentRuns[ex.execution_id]
                  return (
                    <tr key={ex.execution_id || i} className="border-t border-white/[0.05] row-hover">
                      <td className="px-6 py-3.5"><span className="text-white/75">{ex.start_time ? new Date(ex.start_time).toLocaleDateString() : '—'}</span><div className="text-[10px] text-white/30 mt-0.5">{ex.start_time ? new Date(ex.start_time).toLocaleTimeString() : ''}</div></td>
                      <td className="px-6 py-3.5"><Pill tone="purple">{ex.framework || '—'}</Pill></td>
                      <td className="px-6 py-3.5 text-white/60">{ex.reporting_year || '—'}</td>
                      <td className="px-6 py-3.5 text-white/60">{ex.duration_seconds ? `${Math.floor(ex.duration_seconds / 60)}m ${ex.duration_seconds % 60}s` : '—'}</td>
                      <td className="px-6 py-3.5"><Pill tone={st.tone}><st.icon size={11} className={ex.status === 'RUNNING' ? 'animate-spin' : ''} />{st.label}</Pill></td>
                      {platformEnabled && (
                        <td className="px-6 py-3.5">
                          {run ? <button onClick={() => setFocus(run.execution_id)} className="text-xs text-accent-teal hover:underline">{run.healed ? `${run.healed} repaired` : run.status}{run.escalated ? ` · ${run.escalated} escalated` : ''}</button> : <span className="text-white/25 text-xs">—</span>}
                        </td>
                      )}
                      <td className="px-6 py-3.5">
                        <div className="flex gap-2">
                          {ex.download_url && <a href={ex.download_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-blue/10 text-accent-blue text-xs font-medium hover:bg-accent-blue/20"><Download size={11} /> DOCX</a>}
                          {ex.download_url_pptx && <a href={ex.download_url_pptx} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-esg-amber/10 text-esg-amber text-xs font-medium hover:bg-esg-amber/20"><Download size={11} /> PPTX</a>}
                          {!ex.download_url && !ex.download_url_pptx && <span className="text-xs text-white/20">—</span>}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Panel>
        {platformEnabled && (
          <Panel className="col-span-4" title="Agent timeline" subtitle="What the orchestrator did, step by step">
            <AgentActivity focusId={focus} />
          </Panel>
        )}
      </div>
    </div>
  )
}
