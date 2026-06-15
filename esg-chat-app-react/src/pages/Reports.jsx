import { useState, useEffect } from 'react'
import { getHistory } from '../api'
import { useTheme } from '../ThemeContext'
import { RefreshCw, Download, FileText, Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react'

export default function Reports() {
  const { isDark } = useTheme()
  const [executions, setExecutions] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  useEffect(() => { loadHistory() }, [])

  async function loadHistory() {
    setLoading(true)
    try {
      const data = await getHistory(20)
      setExecutions(data.executions || [])
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  const filtered = filter === 'all' ? executions : executions.filter(ex => ex.status === filter)
  const statusCounts = {
    all: executions.length,
    SUCCEEDED: executions.filter(e => e.status === 'SUCCEEDED').length,
    FAILED: executions.filter(e => e.status === 'FAILED').length,
    RUNNING: executions.filter(e => e.status === 'RUNNING').length,
  }

  return (
    <div className="flex-1 overflow-y-auto p-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-800'}`}>Reports History</h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-white/40' : 'text-gray-500'}`}>All generated ESG sustainability reports</p>
        </div>
        <button onClick={loadHistory}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm transition-all ${
            isDark ? 'bg-white/[0.04] border border-white/[0.08] text-white/70 hover:bg-white/[0.08] hover:text-white'
                   : 'bg-gray-50 border border-gray-200 text-gray-600 hover:bg-gray-100 hover:text-gray-800'
          }`}>
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-6">
        {[
          { key: 'all', label: 'All', icon: FileText },
          { key: 'SUCCEEDED', label: 'Succeeded', icon: CheckCircle2 },
          { key: 'FAILED', label: 'Failed', icon: XCircle },
          { key: 'RUNNING', label: 'Running', icon: Clock },
        ].map(tab => {
          const Icon = tab.icon
          return (
            <button key={tab.key} onClick={() => setFilter(tab.key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all ${
                filter === tab.key
                  ? 'bg-accent-blue/15 text-accent-blue border border-accent-blue/25'
                  : isDark
                    ? 'bg-white/[0.02] text-white/40 border border-white/[0.06] hover:bg-white/[0.04] hover:text-white/60'
                    : 'bg-gray-50 text-gray-500 border border-gray-200 hover:bg-gray-100 hover:text-gray-700'
              }`}>
              <Icon size={14} />
              {tab.label}
              <span className={`ml-1 px-1.5 py-0.5 rounded-md text-[10px] ${
                filter === tab.key ? 'bg-accent-blue/20' : isDark ? 'bg-white/[0.05]' : 'bg-gray-100'
              }`}>{statusCounts[tab.key]}</span>
            </button>
          )
        })}
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className={`border-b ${isDark ? 'border-white/[0.06]' : 'border-gray-100'}`}>
                {['Date', 'Framework', 'Year', 'Duration', 'Status', 'Download'].map(h => (
                  <th key={h} className={`px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider ${isDark ? 'text-white/40' : 'text-gray-400'}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="6" className="px-6 py-12 text-center">
                  <Loader2 className="w-5 h-5 text-accent-blue animate-spin mx-auto mb-2" />
                  <span className={`text-sm ${isDark ? 'text-white/30' : 'text-gray-400'}`}>Loading reports...</span>
                </td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan="6" className="px-6 py-12 text-center">
                  <FileText className={`w-8 h-8 mx-auto mb-2 ${isDark ? 'text-white/10' : 'text-gray-200'}`} />
                  <span className={`text-sm ${isDark ? 'text-white/30' : 'text-gray-400'}`}>No reports found</span>
                  <p className={`text-xs mt-1 ${isDark ? 'text-white/20' : 'text-gray-300'}`}>Generate your first report from Chat</p>
                </td></tr>
              ) : filtered.map((ex, i) => (
                <tr key={i} className={`border-t transition-colors animate-slide-up ${
                  isDark ? 'border-white/[0.04] hover:bg-white/[0.02]' : 'border-gray-50 hover:bg-gray-50/50'
                }`} style={{ animationDelay: `${i * 30}ms` }}>
                  <td className="px-6 py-4">
                    <span className={isDark ? 'text-white/70' : 'text-gray-700'}>{ex.start_time ? new Date(ex.start_time).toLocaleDateString() : '—'}</span>
                    <div className={`text-[10px] mt-0.5 ${isDark ? 'text-white/30' : 'text-gray-400'}`}>{ex.start_time ? new Date(ex.start_time).toLocaleTimeString() : ''}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-2.5 py-1 rounded-lg bg-accent-purple/10 text-accent-purple text-xs font-medium border border-accent-purple/20">{ex.framework || '—'}</span>
                  </td>
                  <td className={`px-6 py-4 ${isDark ? 'text-white/60' : 'text-gray-600'}`}>{ex.reporting_year || '—'}</td>
                  <td className={`px-6 py-4 ${isDark ? 'text-white/60' : 'text-gray-600'}`}>
                    {ex.duration_seconds ? `${Math.floor(ex.duration_seconds / 60)}m ${ex.duration_seconds % 60}s` : '—'}
                  </td>
                  <td className="px-6 py-4"><StatusBadge status={ex.status} /></td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      {ex.download_url && (
                        <a href={ex.download_url} target="_blank" rel="noopener" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-blue/10 text-accent-blue text-xs font-medium hover:bg-accent-blue/20 transition-colors border border-accent-blue/20">
                          <Download size={11} /> DOCX
                        </a>
                      )}
                      {ex.download_url_pptx && (
                        <a href={ex.download_url_pptx} target="_blank" rel="noopener" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-esg-amber/10 text-esg-amber text-xs font-medium hover:bg-esg-amber/20 transition-colors border border-esg-amber/20">
                          <Download size={11} /> PPTX
                        </a>
                      )}
                      {!ex.download_url && !ex.download_url_pptx && <span className={`text-xs ${isDark ? 'text-white/20' : 'text-gray-300'}`}>—</span>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const config = {
    SUCCEEDED: { icon: CheckCircle2, color: 'esg-green', label: 'Succeeded' },
    FAILED: { icon: XCircle, color: 'esg-red', label: 'Failed' },
    RUNNING: { icon: Loader2, color: 'esg-amber', label: 'Running' },
  }
  const { icon: Icon, color, label } = config[status] || config.RUNNING
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-${color}/10 text-${color} text-xs font-medium border border-${color}/20`}>
      <Icon size={12} className={status === 'RUNNING' ? 'animate-spin' : ''} />
      {label}
    </span>
  )
}
