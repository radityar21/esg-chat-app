import { useState, useEffect } from 'react'
import { getHistory } from '../api'
import { AreaChart, Area, PieChart, Pie, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { FileText, CheckCircle2, XCircle, Clock, ArrowRight, Sparkles, TrendingUp, Download, BookOpen } from 'lucide-react'

const CHART_COLORS = ['#06d6a0', '#4f8cf7', '#7c5cfc', '#fbbf24']

export default function Overview({ onNavigate }) {
  const [stats, setStats] = useState({ succeeded: 0, failed: 0, running: 0 })
  const [recent, setRecent] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadData() }, [])

  async function loadData() {
    try {
      const data = await getHistory(5)
      console.log('Overview API response:', data)
      if (data) {
        setStats({
          succeeded: data.total_succeeded || 0,
          failed: data.total_failed || 0,
          running: data.total_running || 0
        })
        setRecent(data.executions || [])
      }
    } catch (e) { console.error('Overview loadData error:', e) }
    setLoading(false)
  }

  const total = stats.succeeded + stats.failed + stats.running
  const pieData = [
    { name: 'Succeeded', value: stats.succeeded },
    { name: 'Failed', value: stats.failed },
    { name: 'Running', value: stats.running },
  ].filter(d => d.value > 0)

  // If no data yet, show placeholder
  const showPie = pieData.length > 0

  // Mock trend data for visual appeal
  const trendData = [
    { month: 'Jan', reports: 2 },
    { month: 'Feb', reports: 3 },
    { month: 'Mar', reports: 5 },
    { month: 'Apr', reports: 4 },
    { month: 'May', reports: 7 },
    { month: 'Jun', reports: total || 6 },
  ]

  return (
    <div className="flex-1 overflow-y-auto p-8 animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
          <div className="px-3 py-1 rounded-full bg-accent-teal/10 border border-accent-teal/20">
            <span className="text-xs font-medium text-accent-teal">Live</span>
          </div>
        </div>
        <p className="text-sm text-white/40">ESG Sustainability Reporting — AI-Powered Analytics</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-5 mb-8">
        <StatCard
          icon={FileText} label="Total Reports" value={total}
          gradient="from-accent-blue/20 to-accent-blue/5"
          iconColor="text-accent-blue" glow="stat-glow-blue"
        />
        <StatCard
          icon={CheckCircle2} label="Succeeded" value={stats.succeeded}
          gradient="from-esg-green/20 to-esg-green/5"
          iconColor="text-esg-green" glow="stat-glow-green"
        />
        <StatCard
          icon={XCircle} label="Failed" value={stats.failed}
          gradient="from-esg-red/20 to-esg-red/5"
          iconColor="text-esg-red" glow="stat-glow-red"
        />
        <StatCard
          icon={Clock} label="In Progress" value={stats.running}
          gradient="from-esg-amber/20 to-esg-amber/5"
          iconColor="text-esg-amber" glow="stat-glow-amber"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-5 mb-8">
        {/* Trend Chart */}
        <div className="col-span-2 glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Report Generation Trend</h3>
              <p className="text-xs text-white/40 mt-0.5">Monthly overview</p>
            </div>
            <TrendingUp className="w-4 h-4 text-accent-teal" />
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={trendData}>
              <defs>
                <linearGradient id="colorReports" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4f8cf7" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#4f8cf7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#1a2240', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: '#fff', fontSize: '12px' }}
              />
              <Area type="monotone" dataKey="reports" stroke="#4f8cf7" strokeWidth={2} fill="url(#colorReports)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Pie Chart */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Status Breakdown</h3>
              <p className="text-xs text-white/40 mt-0.5">All time</p>
            </div>
          </div>
          {showPie ? (
            <>
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%" cy="50%"
                    innerRadius={40} outerRadius={60}
                    dataKey="value"
                    strokeWidth={0}
                  >
                    {pieData.map((_, index) => (
                      <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#1a2240', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: '#fff', fontSize: '12px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex justify-center gap-4 mt-2">
                {pieData.map((entry, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: CHART_COLORS[i] }} />
                    <span className="text-[10px] text-white/50">{entry.name}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-[150px] text-xs text-white/30">
              Loading data...
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-5 mb-8">
        <QuickAction
          icon={Sparkles}
          title="Generate Report"
          desc="Create new ESG sustainability report with AI"
          onClick={() => onNavigate('chat')}
          accentColor="accent-blue"
        />
        <QuickAction
          icon={Download}
          title="View Reports"
          desc="Download previous DOCX & PPTX reports"
          onClick={() => onNavigate('reports')}
          accentColor="accent-teal"
        />
        <QuickAction
          icon={BookOpen}
          title="Reference Library"
          desc="GRI, IFRS S2, ESRS E1, OJK PSPK"
          onClick={() => onNavigate('reference')}
          accentColor="accent-purple"
        />
      </div>

      {/* Recent Activity */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-white">Recent Activity</h3>
            <p className="text-xs text-white/40 mt-0.5">Latest report generations</p>
          </div>
          <button onClick={() => onNavigate('reports')} className="text-xs text-accent-blue hover:text-accent-teal transition-colors flex items-center gap-1">
            View all <ArrowRight size={12} />
          </button>
        </div>

        {recent.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-12 h-12 rounded-full bg-white/[0.03] border border-white/[0.08] flex items-center justify-center mx-auto mb-3">
              <FileText className="w-5 h-5 text-white/20" />
            </div>
            <p className="text-sm text-white/30">No reports generated yet</p>
            <p className="text-xs text-white/20 mt-1">Click "Generate Report" to get started</p>
          </div>
        ) : (
          <div className="space-y-2">
            {recent.map((ex, i) => (
              <div key={i} className="flex items-center justify-between py-3 px-4 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-all animate-slide-up" style={{ animationDelay: `${i * 50}ms` }}>
                <div className="flex items-center gap-3">
                  <div className={`w-2.5 h-2.5 rounded-full ${
                    ex.status === 'SUCCEEDED' ? 'bg-esg-green shadow-neon-green' :
                    ex.status === 'FAILED' ? 'bg-esg-red' :
                    'bg-esg-amber animate-pulse'
                  }`} />
                  <div>
                    <div className="text-sm font-medium text-white/90">{ex.framework || 'Report'}</div>
                    <div className="text-xs text-white/30">{ex.start_time ? new Date(ex.start_time).toLocaleString() : '—'}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold ${
                    ex.status === 'SUCCEEDED' ? 'bg-esg-green/10 text-esg-green border border-esg-green/20' :
                    ex.status === 'FAILED' ? 'bg-esg-red/10 text-esg-red border border-esg-red/20' :
                    'bg-esg-amber/10 text-esg-amber border border-esg-amber/20'
                  }`}>{ex.status}</span>
                  {ex.download_url && (
                    <a href={ex.download_url} target="_blank" rel="noopener" className="p-1.5 rounded-lg bg-accent-blue/10 text-accent-blue hover:bg-accent-blue/20 transition-colors">
                      <Download size={12} />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, gradient, iconColor, glow }) {
  return (
    <div className={`glass-card p-5 ${glow} animate-slide-up`}>
      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center mb-3`}>
        <Icon className={`w-5 h-5 ${iconColor}`} />
      </div>
      <div className="text-2xl font-bold text-white mb-0.5">{value}</div>
      <div className="text-xs text-white/40 font-medium">{label}</div>
    </div>
  )
}

function QuickAction({ icon: Icon, title, desc, onClick, accentColor }) {
  return (
    <button
      onClick={onClick}
      className="glass-card-hover p-5 text-left group"
    >
      <div className={`w-10 h-10 rounded-xl bg-${accentColor}/10 border border-${accentColor}/20 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}>
        <Icon className={`w-5 h-5 text-${accentColor}`} />
      </div>
      <div className="font-semibold text-sm text-white mb-1">{title}</div>
      <div className="text-xs text-white/40 leading-relaxed">{desc}</div>
      <div className="flex items-center gap-1 mt-3 text-xs text-white/30 group-hover:text-accent-blue transition-colors">
        Open <ArrowRight size={10} />
      </div>
    </button>
  )
}


