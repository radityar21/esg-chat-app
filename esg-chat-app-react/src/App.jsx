import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Overview from './pages/Overview'
import Analytics from './pages/Analytics'
import Chat from './pages/Chat'
import Reports from './pages/Reports'
import Reference from './pages/Reference'

export default function App() {
  const [activePage, setActivePage] = useState('overview')

  const pages = {
    overview: <Overview onNavigate={setActivePage} />,
    analytics: <Analytics />,
    chat: <Chat />,
    reports: <Reports />,
    reference: <Reference />,
  }

  return (
    <div className="flex h-screen bg-dark-900 overflow-hidden">
      {/* Background gradient orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-accent-blue/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-accent-teal/5 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent-purple/3 rounded-full blur-3xl" />
      </div>

      <Sidebar active={activePage} onNavigate={setActivePage} />
      <main className="flex-1 overflow-hidden flex flex-col relative z-10">
        {pages[activePage]}
      </main>
    </div>
  )
}
