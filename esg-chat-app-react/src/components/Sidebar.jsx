import { LayoutDashboard, MessageSquare, FileText, BookOpen, Leaf, BarChart3, Sun, Moon } from 'lucide-react'
import { useTheme } from '../ThemeContext'

const menuItems = [
  { id: 'overview', icon: LayoutDashboard, label: 'Overview' },
  { id: 'analytics', icon: BarChart3, label: 'Analytics' },
  { id: 'chat', icon: MessageSquare, label: 'Chat' },
  { id: 'reports', icon: FileText, label: 'Reports' },
  { id: 'reference', icon: BookOpen, label: 'Reference' },
]

export default function Sidebar({ active, onNavigate }) {
  const { isDark, toggleTheme } = useTheme()

  return (
    <aside className={`w-64 backdrop-blur-xl flex flex-col h-full relative z-20 transition-colors duration-300 ${
      isDark
        ? 'bg-dark-800/80 border-r border-white/[0.06]'
        : 'bg-white/90 border-r border-gray-200'
    }`}>
      {/* Logo */}
      <div className={`p-6 border-b ${isDark ? 'border-white/[0.06]' : 'border-gray-100'}`}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-blue to-accent-teal flex items-center justify-center shadow-neon-blue">
            <Leaf className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className={`font-bold text-sm tracking-wide ${isDark ? 'text-white' : 'text-gray-800'}`}>Tokaicom Mitra</div>
            <div className={`text-[10px] font-medium ${isDark ? 'text-white/40' : 'text-gray-400'}`}>ESG Reporting System</div>
          </div>
        </div>
      </div>

      {/* Menu */}
      <nav className="flex-1 py-6 px-4 space-y-1">
        <div className={`text-[10px] uppercase tracking-widest font-semibold px-3 mb-3 ${
          isDark ? 'text-white/30' : 'text-gray-400'
        }`}>
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
                  ? isDark
                    ? 'bg-gradient-to-r from-accent-blue/20 to-accent-teal/10 text-white font-medium border border-accent-blue/20 shadow-neon-blue'
                    : 'bg-gradient-to-r from-accent-blue/10 to-accent-teal/5 text-accent-blue font-medium border border-accent-blue/20 shadow-sm'
                  : isDark
                    ? 'text-white/50 hover:bg-white/[0.04] hover:text-white/80'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
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

      {/* Theme Toggle */}
      <div className="px-4 mb-2">
        <button
          onClick={toggleTheme}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 ${
            isDark
              ? 'text-white/50 hover:bg-white/[0.04] hover:text-white/80'
              : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
          }`}
        >
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
          {isDark ? 'Light Mode' : 'Dark Mode'}
        </button>
      </div>

      {/* Footer */}
      <div className={`p-4 mx-4 mb-4 rounded-xl ${
        isDark
          ? 'bg-white/[0.02] border border-white/[0.05]'
          : 'bg-gray-50 border border-gray-100'
      }`}>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 rounded-full bg-esg-green animate-pulse" />
          <span className={`text-[10px] font-medium ${isDark ? 'text-white/50' : 'text-gray-500'}`}>System Online</span>
        </div>
        <div className={`text-[10px] ${isDark ? 'text-white/30' : 'text-gray-400'}`}>
          v2.0 · Made by Tokaicom Mitra Indonesia
        </div>
      </div>
    </aside>
  )
}
