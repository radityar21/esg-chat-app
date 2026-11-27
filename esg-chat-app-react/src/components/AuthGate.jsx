import { useEffect, useState } from 'react'
import { Leaf, LogIn, Loader2 } from 'lucide-react'
import { authEnabled, completeLogin, login } from '../lib/auth'

// Shows the sign-in screen until the user has a session. Without Cognito configuration (demo mode) it renders the app directly.
export default function AuthGate({ children }) {
  const [state, setState] = useState(authEnabled ? 'loading' : 'ok')
  const [error, setError] = useState(null)
  useEffect(() => {
    if (!authEnabled) return
    completeLogin().then((ok) => setState(ok ? 'ok' : 'anon')).catch((e) => { setError(e.message); setState('anon') })
  }, [])
  if (state === 'ok') return children
  return (
    <div className="relative h-screen overflow-hidden bg-dark-900 flex items-center justify-center">
      <img src="/img/city-night.jpg" alt="" className="absolute inset-0 w-full h-full object-cover opacity-40" />
      <div className="absolute inset-0 bg-gradient-to-br from-dark-900 via-dark-900/80 to-dark-900/40" />
      <div className="relative w-[420px] panel p-9 text-center">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-accent-blue to-accent-teal flex items-center justify-center shadow-neon-blue mb-5"><Leaf className="w-7 h-7 text-white" /></div>
        <h1 className="font-display text-2xl font-bold text-white tracking-tight">ESG Intelligence</h1>
        <p className="text-sm text-white/50 mt-2 leading-relaxed">Compliance, reporting, portfolio and AI governance in one place. Sign in with your organisation account.</p>
        {state === 'loading' ? (
          <div className="mt-7 flex items-center justify-center gap-2 text-sm text-white/50"><Loader2 className="w-4 h-4 animate-spin" />Signing you in…</div>
        ) : (
          <button onClick={login} className="mt-7 w-full inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white bg-gradient-to-r from-accent-blue to-accent-teal hover:opacity-90 transition">
            <LogIn size={16} />Sign in
          </button>
        )}
        {error && <div className="mt-4 text-xs text-esg-red">{error}. Please try again.</div>}
        <div className="mt-6 text-[11px] text-white/30">Accounts are created by an administrator.</div>
      </div>
    </div>
  )
}
