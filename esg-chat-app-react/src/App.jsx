import { useState, useEffect } from 'react'
import { ThemeProvider } from './ThemeContext'
import Sidebar, { NAV } from './components/Sidebar'
import Home from './pages/Home'
import Compliance from './pages/Compliance'
import Frameworks from './pages/Frameworks'
import Portfolio from './pages/Portfolio'
import Governance from './pages/Governance'
import GhgInventory from './pages/GhgInventory'
import Chat from './pages/Chat'
import Reports from './pages/Reports'
import Reference from './pages/Reference'
import ReportBuilder from './pages/ReportBuilder'
import AuthGate from './components/AuthGate'

const ORDER = NAV.flatMap((g) => g.items.map((i) => i.id))

function AppContent() {
  const [page, setPageRaw] = useState('home')
  const [chatSeed, setChatSeed] = useState(null) // a prompt another page asks the assistant (for example "analyse finding A-1")
  const setPage = (p, opts = {}) => { if (opts.prompt) setChatSeed({ prompt: opts.prompt, at: Date.now() }); setPageRaw(p) }

  // Presenter shortcuts: keys 1-9 jump between pages
  useEffect(() => {
    const onKey = (e) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName) || e.metaKey || e.ctrlKey) return
      const n = Number(e.key)
      if (n >= 1 && n <= ORDER.length) setPageRaw(ORDER[n - 1])
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const pages = {
    home: <Home onNavigate={setPage} />,
    compliance: <Compliance onNavigate={setPage} />,
    frameworks: <Frameworks />,
    portfolio: <Portfolio />,
    governance: <Governance />,
    ghg: <GhgInventory />,
    chat: <Chat seed={chatSeed} onSeedUsed={() => setChatSeed(null)} />,
    builder: <ReportBuilder />,
    reports: <Reports />,
    reference: <Reference />,
  }

  return (
    <div className="flex h-screen overflow-hidden bg-dark-900">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-[28rem] h-[28rem] bg-accent-blue/[0.07] rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-20 w-[28rem] h-[28rem] bg-accent-teal/[0.06] rounded-full blur-3xl" />
        <div className="absolute top-1/3 left-1/2 w-[34rem] h-[34rem] bg-accent-purple/[0.04] rounded-full blur-3xl" />
      </div>
      <Sidebar active={page} onNavigate={setPage} />
      <main key={page} className="flex-1 overflow-hidden flex flex-col relative z-10">{pages[page]}</main>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthGate>
        <AppContent />
      </AuthGate>
    </ThemeProvider>
  )
}
