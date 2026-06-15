import { useState, useEffect } from 'react'
import { getDashboardData } from '../api'
import { useTheme } from '../ThemeContext'
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Legend, CartesianGrid
} from 'recharts'
import {
  RefreshCw, TrendingDown, TrendingUp, Zap, Users, Target, Leaf,
  BarChart3, Award, AlertTriangle
} from 'lucide-react'

const COLORS = {
  blue: '#4f8cf7', teal: '#06d6a0', purple: '#7c5cfc', amber: '#fbbf24',
  red: '#ef4444', cyan: '#22d3ee', pink: '#ec4899', orange: '#f97316',
  lime: '#84cc16', indigo: '#6366f1',
}
const PIE_COLORS = [COLORS.blue, COLORS.teal, COLORS.purple, COLORS.amber, COLORS.red, COLORS.cyan]
const BAR_COLORS = [COLORS.blue, COLORS.teal, COLORS.amber, COLORS.purple, COLORS.pink, COLORS.orange, COLORS.lime, COLORS.cyan, COLORS.indigo, COLORS.red]

export default function Analytics() {
  const { isDark } = useTheme()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const tooltipStyle = {
    contentStyle: {
      background: isDark ? '#1a2240' : '#ffffff',
      border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}`,
      borderRadius: '12px',
      color: isDark ? '#fff' : '#1e293b',
      fontSize: '11px',
      boxShadow: isDark ? 'none' : '0 4px 12px rgba(0,0,0,0.1)',
    },
    itemStyle: { color: isDark ? '#fff' : '#1e293b' },
  }
  const tickColor = isDark ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.5)'
  const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)'
  const legendStyle = { fontSize: '10px', color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' }

  useEffect(() => { loadData() }, [])

  async function loadData() {
    setLoading(true)
    try {
      const result = await getDashboardData(false)
      if (result && !result.error) setData(result)
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  async function handleRefresh() {
    setRefreshing(true)
    try {
      const result = await getDashboardData(true)
      if (result && !result.error) setData(result)
    } catch (e) { console.error(e) }
    setRefreshing(false)
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-accent-blue animate-spin mx-auto mb-3" />
          <p className={`text-sm ${isDark ? 'text-white/40' : 'text-gray-500'}`}>Loading analytics data...</p>
        </div>
      </div>
    )
  }

  if (!data || data.error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center glass-card p-8">
          <AlertTriangle className="w-8 h-8 text-esg-amber mx-auto mb-3" />
          <p className={`text-sm mb-4 ${isDark ? 'text-white/60' : 'text-gray-600'}`}>No dashboard data available yet</p>
          <button onClick={handleRefresh} className="px-4 py-2 rounded-xl bg-accent-blue/20 text-accent-blue text-sm font-medium hover:bg-accent-blue/30 border border-accent-blue/20">
            {refreshing ? 'Querying Athena...' : 'Load Data from Athena'}
          </button>
        </div>
      </div>
    )
  }

  const ghg = data.ghg_summary || {}
  const prior = data.prior_year_summary || {}
  const pcaf = data.pcaf_sectors || []
  const facilities = data.scope1_facilities || []
  const hrList = data.hr_metrics || []
  const hr = hrList[0] || {}
  const hrPrior = hrList[1] || {}

  const totalEmissions = (ghg.scope1_tco2e || 0) + (ghg.scope2_location_tco2e || 0) + (ghg.scope3_cat15_gross_tco2e || 0)

  return (
    <div className="flex-1 overflow-y-auto p-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-800'}`}>ESG Analytics</h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-white/40' : 'text-gray-500'}`}>
            Reporting Year {data.reporting_year} — Last updated: {data.last_updated ? new Date(data.last_updated).toLocaleString() : 'N/A'}
          </p>
        </div>
        <button onClick={handleRefresh} disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-accent-blue/10 border border-accent-blue/20 text-sm text-accent-blue hover:bg-accent-blue/20 disabled:opacity-50 transition-all">
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Refreshing...' : 'Refresh from Athena'}
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-6 gap-4 mb-8">
        <KpiCard icon={Zap} label="Total Emissions" value={fmt(totalEmissions)} unit="tCO₂e" color="blue" />
        <KpiCard icon={ghg.yoy_change_pct > 0 ? TrendingUp : TrendingDown} label="YoY Change" value={`${ghg.yoy_change_pct > 0 ? '+' : ''}${ghg.yoy_change_pct || 0}%`} color={ghg.yoy_change_pct > 0 ? 'red' : 'teal'} />
        <KpiCard icon={Target} label="Intensity/IDR Bn" value={fmt(ghg.intensity_tco2e_per_idr_bn)} unit="tCO₂e" color="purple" />
        <KpiCard icon={Award} label="PCAF Quality" value={(ghg.avg_pcaf_data_quality || 0).toFixed(1)} unit="/5.0" color="amber" />
        <KpiCard icon={Users} label="Total FTE" value={fmt(hr.fte_total)} color="cyan" />
        <KpiCard icon={Users} label="Female %" value={`${hr.fte_female_pct || 0}%`} color="pink" />
      </div>

      {/* Environmental Section */}
      <SectionHeader icon={Leaf} title="Environmental (E)" subtitle="GHG Emissions & Climate Metrics" />

      <div className="grid grid-cols-3 gap-5 mb-8">
        <ChartCard title="Emissions by Scope" subtitle="Total breakdown">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={[
                { name: 'Scope 1', value: ghg.scope1_tco2e || 0 },
                { name: 'Scope 2', value: ghg.scope2_location_tco2e || 0 },
                { name: 'Scope 3', value: ghg.scope3_cat15_gross_tco2e || 0 },
              ]} cx="50%" cy="50%" innerRadius={50} outerRadius={75} dataKey="value" strokeWidth={0}>
                {[0,1,2].map(i => <Cell key={i} fill={PIE_COLORS[i]} />)}
              </Pie>
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={legendStyle} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Scope 1 Sources" subtitle="Natural Gas vs Diesel">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={[
                { name: 'Natural Gas', value: ghg.scope1_natgas_tco2e || 0 },
                { name: 'Diesel', value: ghg.scope1_diesel_tco2e || 0 },
              ]} cx="50%" cy="50%" innerRadius={50} outerRadius={75} dataKey="value" strokeWidth={0}>
                <Cell fill={COLORS.teal} />
                <Cell fill={COLORS.amber} />
              </Pie>
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={legendStyle} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Scope 2 Comparison" subtitle="Location vs Market-based">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={[
              { name: 'Location', value: ghg.scope2_location_tco2e || 0 },
              { name: 'Market', value: ghg.scope2_market_tco2e || 0 },
            ]}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="name" tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <YAxis tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                <Cell fill={COLORS.blue} />
                <Cell fill={COLORS.purple} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid grid-cols-2 gap-5 mb-8">
        <ChartCard title="Year-over-Year Comparison" subtitle={`${data.reporting_year - 1} vs ${data.reporting_year}`}>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={[
              { name: 'Scope 1', current: ghg.scope1_tco2e || 0, prior: prior.scope1_tco2e || 0 },
              { name: 'Scope 2', current: ghg.scope2_location_tco2e || 0, prior: prior.scope2_location_tco2e || 0 },
              { name: 'Scope 3', current: ghg.scope3_cat15_gross_tco2e || 0, prior: prior.scope3_cat15_gross_tco2e || 0 },
            ]}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="name" tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <YAxis tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={legendStyle} />
              <Bar dataKey="prior" name={`${data.reporting_year - 1}`} fill={COLORS.purple} radius={[4, 4, 0, 0]} opacity={0.6} />
              <Bar dataKey="current" name={`${data.reporting_year}`} fill={COLORS.blue} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Emission Intensity" subtitle="Per unit metrics">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={[
              { name: 'Per IDR Bn', current: ghg.intensity_tco2e_per_idr_bn || 0, prior: prior.intensity_tco2e_per_idr_bn || 0 },
              { name: 'Per FTE', current: ghg.intensity_tco2e_per_fte || 0, prior: prior.intensity_tco2e_per_fte || 0 },
            ]}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="name" tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <YAxis tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={legendStyle} />
              <Bar dataKey="prior" name={`${data.reporting_year - 1}`} fill={COLORS.amber} radius={[4, 4, 0, 0]} opacity={0.6} />
              <Bar dataKey="current" name={`${data.reporting_year}`} fill={COLORS.teal} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid grid-cols-2 gap-5 mb-8">
        <ChartCard title="Scope 1 by Facility" subtitle="Top 10 emitters">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={facilities.slice(0, 10).map(f => ({ name: f.facility_id?.replace('FAC_', '') || 'N/A', emissions: f.scope1_tco2e || 0 }))} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis type="number" tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: tickColor, fontSize: 9 }} axisLine={false} width={60} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="emissions" radius={[0, 6, 6, 0]}>
                {facilities.slice(0, 10).map((_, i) => <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="PCAF Financed Emissions" subtitle="Top sectors by tCO₂e">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={pcaf.slice(0, 8).map(s => ({ name: (s.sector_display_name || '').slice(0, 15), emissions: s.financed_emissions_gross_tco2e || 0 }))} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis type="number" tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: tickColor, fontSize: 9 }} axisLine={false} width={100} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="emissions" radius={[0, 6, 6, 0]}>
                {pcaf.slice(0, 8).map((_, i) => <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid grid-cols-3 gap-5 mb-8">
        <ChartCard title="PCAF Data Quality" subtitle="Score by sector (1=best, 5=worst)">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={pcaf.slice(0, 8).map(s => ({ name: (s.sector_display_name || '').slice(0, 12), score: s.avg_pcaf_score || 0 }))}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="name" tick={{ fill: tickColor, fontSize: 8 }} axisLine={false} angle={-20} textAnchor="end" height={50} />
              <YAxis domain={[0, 5]} tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                {pcaf.slice(0, 8).map((s, i) => <Cell key={i} fill={s.avg_pcaf_score <= 2 ? COLORS.teal : s.avg_pcaf_score <= 3.5 ? COLORS.amber : COLORS.red} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Portfolio Concentration" subtitle="% of total portfolio by sector">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pcaf.slice(0, 6).map(s => ({ name: (s.sector_display_name || '').slice(0, 12), value: s.pct_of_total_portfolio || 0 }))} cx="50%" cy="50%" outerRadius={70} dataKey="value" strokeWidth={0}>
                {pcaf.slice(0, 6).map((_, i) => <Cell key={i} fill={BAR_COLORS[i]} />)}
              </Pie>
              <Tooltip {...tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="PCAF Score Distribution" subtitle="Sectors by quality tier">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={getPcafDistribution(pcaf)} cx="50%" cy="50%" innerRadius={45} outerRadius={70} dataKey="value" strokeWidth={0}>
                <Cell fill={COLORS.teal} />
                <Cell fill={COLORS.amber} />
                <Cell fill={COLORS.red} />
              </Pie>
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={legendStyle} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Social Section */}
      <SectionHeader icon={Users} title="Social (S)" subtitle="Workforce & Human Capital Metrics" />

      <div className="grid grid-cols-4 gap-5 mb-8">
        <ChartCard title="Gender Diversity" subtitle="Workforce composition">
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={[
                { name: 'Female', value: hr.fte_female_pct || 0 },
                { name: 'Male', value: 100 - (hr.fte_female_pct || 0) },
              ]} cx="50%" cy="50%" innerRadius={40} outerRadius={65} dataKey="value" strokeWidth={0}>
                <Cell fill={COLORS.pink} />
                <Cell fill={COLORS.blue} />
              </Pie>
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={legendStyle} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Female in Management" subtitle={`${hr.fte_management_female_pct || 0}%`}>
          <div className="flex items-center justify-center h-[180px]">
            <div className="relative w-32 h-32">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="50" fill="none" stroke={isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)'} strokeWidth="12" />
                <circle cx="60" cy="60" r="50" fill="none" stroke={COLORS.pink} strokeWidth="12" strokeLinecap="round"
                  strokeDasharray={`${(hr.fte_management_female_pct || 0) * 3.14} 314`} />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-800'}`}>{hr.fte_management_female_pct || 0}%</span>
              </div>
            </div>
          </div>
        </ChartCard>

        <ChartCard title="Training Hours/FTE" subtitle="Year-over-Year">
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={[
              { name: `${data.reporting_year - 1}`, value: hrPrior.training_hours_per_fte || 0 },
              { name: `${data.reporting_year}`, value: hr.training_hours_per_fte || 0 },
            ]}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="name" tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <YAxis tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                <Cell fill={COLORS.purple} opacity={0.6} />
                <Cell fill={COLORS.purple} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Turnover & Hiring" subtitle="Rate comparison">
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={[
              { name: 'Turnover', value: hr.voluntary_turnover_pct || 0 },
              { name: 'Hiring Rate', value: hr.new_hire_count && hr.fte_total ? Math.round(hr.new_hire_count / hr.fte_total * 100) : 0 },
            ]}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="name" tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <YAxis tick={{ fill: tickColor, fontSize: 10 }} axisLine={false} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                <Cell fill={COLORS.red} />
                <Cell fill={COLORS.teal} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  )
}

function KpiCard({ icon: Icon, label, value, unit, color }) {
  const { isDark } = useTheme()
  const colorMap = { blue: 'accent-blue', teal: 'esg-green', purple: 'accent-purple', amber: 'esg-amber', red: 'esg-red', cyan: 'accent-cyan', pink: 'accent-purple' }
  const c = colorMap[color] || 'accent-blue'
  return (
    <div className="glass-card p-4 animate-slide-up">
      <div className={`w-8 h-8 rounded-lg bg-${c}/10 flex items-center justify-center mb-2`}>
        <Icon className={`w-4 h-4 text-${c}`} size={16} />
      </div>
      <div className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-800'}`}>{value}<span className={`text-xs ml-1 ${isDark ? 'text-white/30' : 'text-gray-400'}`}>{unit}</span></div>
      <div className={`text-[10px] mt-0.5 ${isDark ? 'text-white/40' : 'text-gray-500'}`}>{label}</div>
    </div>
  )
}

function ChartCard({ title, subtitle, children }) {
  const { isDark } = useTheme()
  return (
    <div className="glass-card p-5 animate-slide-up">
      <div className="mb-3">
        <h4 className={`text-xs font-semibold ${isDark ? 'text-white' : 'text-gray-800'}`}>{title}</h4>
        {subtitle && <p className={`text-[10px] mt-0.5 ${isDark ? 'text-white/30' : 'text-gray-400'}`}>{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

function SectionHeader({ icon: Icon, title, subtitle }) {
  const { isDark } = useTheme()
  return (
    <div className="flex items-center gap-3 mb-5 mt-2">
      <div className="w-8 h-8 rounded-lg bg-accent-teal/10 flex items-center justify-center">
        <Icon className="w-4 h-4 text-accent-teal" size={16} />
      </div>
      <div>
        <h3 className={`text-sm font-bold ${isDark ? 'text-white' : 'text-gray-800'}`}>{title}</h3>
        <p className={`text-[10px] ${isDark ? 'text-white/30' : 'text-gray-400'}`}>{subtitle}</p>
      </div>
    </div>
  )
}

function fmt(n) {
  if (!n) return '0'
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`
  return typeof n === 'number' ? n.toLocaleString() : n
}

function getPcafDistribution(pcaf) {
  let good = 0, medium = 0, poor = 0
  pcaf.forEach(s => {
    const score = s.avg_pcaf_score || 3
    if (score <= 2) good++
    else if (score <= 3.5) medium++
    else poor++
  })
  return [
    { name: 'Good (≤2)', value: good || 1 },
    { name: 'Medium (2-3.5)', value: medium || 1 },
    { name: 'Poor (>3.5)', value: poor || 1 },
  ]
}
