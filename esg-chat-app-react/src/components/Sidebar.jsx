import { LayoutGrid, ShieldCheck, FileStack, Layers, Cpu, Flame, MessageSquare, FileText, BookOpen, Leaf } from 'lucide-react'
import { BANK } from '../data/bank'
import { platformEnabled } from '../lib/platform'
import { authEnabled, currentUser, logout } from '../lib/auth'
import { LogOut } from 'lucide-react'

export const NAV = [
  { group: 'Platform', items: [
    { id: 'home', icon: LayoutGrid, label: 'Command Center' },
    { id: 'compliance', icon: ShieldCheck, label: 'Compliance Intelligence', badge: '1' },
    { id: 'frameworks', icon: FileStack, label: 'Reports & Scenarios', badge: '2' },
    { id: 'portfolio', icon: Layers, label: 'Portfolio Analytics', badge: '3' },
    { id: 'governance', icon: Cpu, label: 'AI Governance & FinOps', badge: '4' },
    { id: 'ghg', icon: Flame, label: 'GHG Inventory' },
  ] },
  { group: 'Workspace', items: [
    { id: 'chat', icon: MessageSquare, label: 'AI Assistant' },
    { id: 'reports', icon: FileText, label: 'Report Runs' },
    { id: 'reference', icon: BookOpen, label: 'Reference' },
  ] },
]

export default function Sidebar({ active, onNavigate }) {
  const user = authEnabled ? currentUser() : null
  return (
    <aside className="w-[272px] shrink-0 h-full flex flex-col relative z-20 bg-dark-800/90 backdrop-blur-xl border-r border-white/[0.06]">
      <div className="px-6 pt-7 pb-6">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-accent-blue to-accent-teal flex items-center justify-center shadow-neon-blue"><Leaf className="w-5 h-5 text-dark-900" /></div>
          <div>
            <div className="font-display font-bold text-white text-[15px] leading-tight">ESG Intelligence</div>
            <div className="text-[11px] text-white/40">{BANK.name}</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-4 space-y-6 overflow-y-auto">
        {NAV.map((g) => (
          <div key={g.group}>
            <div className="eyebrow px-3 mb-2">{g.group}</div>
            <div className="space-y-0.5">
              {g.items.map((it) => {
                const on = active === it.id
                return (
                  <button key={it.id} onClick={() => onNavigate(it.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] transition-all ${on ? 'bg-gradient-to-r from-accent-blue/20 to-accent-teal/10 text-white border border-accent-blue/25' : 'text-white/55 hover:text-white hover:bg-white/[0.04] border border-transparent'}`}>
                    <it.icon size={17} className={on ? 'text-accent-teal' : ''} />
                    <span className="flex-1 text-left">{it.label}</span>
                    {it.badge && <span className={`text-[10px] w-5 h-5 rounded-md flex items-center justify-center ${on ? 'bg-accent-teal/20 text-accent-teal' : 'bg-white/[0.06] text-white/35'}`}>{it.badge}</span>}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="m-4 p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
        <div className="flex items-center gap-2 mb-1.5"><span className="w-2 h-2 rounded-full bg-esg-green animate-pulse" /><span className="text-[11px] text-white/60">{platformEnabled ? 'Platform connected' : 'Demo mode'}</span></div>
        {user && (
          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-white/[0.06]">
            <div className="min-w-0 flex-1"><div className="text-[11px] text-white/70 truncate" title={user.email}>{user.email}</div><div className="text-[10px] text-white/35">{user.isAdmin ? 'Administrator' : 'Viewer'}</div></div>
            <button onClick={logout} title="Sign out" className="p-1.5 rounded-lg text-white/50 hover:text-white hover:bg-white/10"><LogOut size={14} /></button>
          </div>
        )}
        <div className="text-[10px] text-white/30 leading-relaxed">{platformEnabled ? 'Live data from AWS' : 'Synthetic demo data'}<br />Made by Tokaicom Mitra Indonesia</div>
      </div>
    </aside>
  )
}
