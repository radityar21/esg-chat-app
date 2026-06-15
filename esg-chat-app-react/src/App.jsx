import { useState } from 'react'
import { ThemeProvider, useTheme } from './ThemeContext'
import Sidebar from './components/Sidebar'
import Overview from './pages/Overview'
import Analytics from './pages/Analytics'
import Chat from './pages/Chat'
import Reports from './pages/Reports'
import Reference from './pages/Reference'

function AppContent() {
  const [activePage, setActivePage] = useState('overview')
  const { isDark } = useTheme()

  const pages = {
    overview: <Overview onNavigate={setActivePage} />,
    analytics: <Analytics />,
    chat: <Chat />,
    reports: <Reports />,
    reference: <Reference />,
  }

  return (
    <div className={`flex h-screen overflow-hidden transition-colors duration-300 ${
      isDark ? 'bg-dark-900' : 'bg-light-50'
    }`}>
      {/* Background gradient orbs — dark only */}
      {isDark && (
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="absolute -top-40 -right-40 w-96 h-96 bg-accent-blue/5 rounded-full blur-3xl" />
          <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-accent-teal/5 rounded-full blur-3xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent-purple/3 rounded-full blur-3xl" />
        </div>
      )}

      {/* Light mode subtle pattern */}
      {!isDark && (
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-accent-teal/[0.03] rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-accent-blue/[0.03] rounded-full blur-3xl" />
        </div>
      )}

      <Sidebar active={activePage} onNavigate={setActivePage} />
      <main className="flex-1 overflow-hidden flex flex-col relative z-10">
        {pages[activePage]}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  )
}
