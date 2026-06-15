import { LayoutDashboard, MessageSquare, FileText, BookOpen, Leaf, BarChart3 } from 'lucide-react'

const menuItems = [
  { id: 'overview', icon: LayoutDashboard, label: 'Overview' },
  { id: 'analytics', icon: BarChart3, label: 'Analytics' },
  { id: 'chat', icon: MessageSquare, label: 'Chat' },
  { id: 'reports', icon: FileText, label: 'Reports' },
  { id: 'reference', icon: BookOpen, label: 'Reference' },
]

export default function Sidebar({ active, onNavigate }) {
  return (
    <aside className="w-64 bg-dark-800/80 backdrop-blur-xl border-r border-white/[0.06] flex flex-col h-full relative z-20">
      {/* Logo */}
      <div className="p-6 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-blue to-accent-teal flex items-center justify-center shadow-neon-blue">
            <Leaf className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-bold text-sm text-white tracking-wide">Tokaicom Mitra</div>
            <div className="text-[10px] text-white/40 font-medium">ESG Reporting System</div>
          </div>
        </div>
      </div>

      {/* Menu */}
      <nav className="flex-1 py-6 px-4 space-y-1">
        <div className="text-[10px] uppercase tracking-widest text-white/30 font-semibold px-3 mb-3">
          Navigation
        </div>
        {menuItems.map(item => {
          const Icon = item.icon
          const isActive = active === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 ${
                isActive
                  ? 'bg-gradient-to-r from-accent-blue/20 to-accent-teal/10 text-white font-medium border border-accent-blue/20 shadow-neon-blue'
                  : 'text-white/50 hover:bg-white/[0.04] hover:text-white/80'
              }`}
            >
              <Icon className={`w-4.5 h-4.5 ${isActive ? 'text-accent-blue' : ''}`} size={18} />
              {item.label}
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-accent-teal animate-pulse" />
              )}
            </button>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 mx-4 mb-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 rounded-full bg-esg-green animate-pulse" />
          <span className="text-[10px] text-white/50 font-medium">System Online</span>
        </div>
        <div className="text-[10px] text-white/30">
          v2.0 · Powered by Amazon Bedrock
        </div>
      </div>
    </aside>
  )
}
