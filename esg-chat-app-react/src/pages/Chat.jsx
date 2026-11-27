import { useState, useRef, useEffect } from 'react'
import { sendChat, checkStatus } from '../api'
import { useTheme } from '../ThemeContext'
import { Send, Bot, User, Loader2, CheckCircle2, AlertCircle, Download, Sparkles, SquarePen, History, Trash2 } from 'lucide-react'
import RunProgress from '../components/RunProgress'
import { currentUser } from '../lib/auth'
import AgentActivity from '../components/AgentActivity'
import { Pill } from '../components/ui'
import { api, platformEnabled, submitAgent, waitAgent } from '../lib/platform'

// AgentCore needs a session id of at least 33 characters. crypto.randomUUID only exists in secure contexts (https), so fall back to getRandomValues.
function newSessionId() {
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  return 'esg-' + Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

// The conversation survives page changes: it is kept in sessionStorage (per signed-in user, cleared when the tab closes).
// The AgentCore session id is kept too, so the agent still has the context while its session is alive.
const storeKey = () => `esg.chat.v1.${currentUser()?.email || 'demo'}`
const loadChat = () => { try { return JSON.parse(sessionStorage.getItem(storeKey())) || {} } catch { return {} } }
const EXEC_RE = /Execution ID:\s*`?([A-Za-z0-9_-]{8,})/i
const usedSeeds = new Set() // a prompt sent from another page is asked once, even if the effect runs twice

export default function Chat({ seed, onSeedUsed }) {
  const { isDark } = useTheme()
  const saved = useRef(loadChat()).current
  const [messages, setMessages] = useState(saved.messages || [])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(Boolean(saved.pending))
  const [sessionId, setSessionId] = useState(saved.sessionId || newSessionId())
  const [focusId, setFocusId] = useState(saved.focusId || null)
  const [pending, setPending] = useState(saved.pending || null) // {jobId} of a turn that is still running on the server
  useEffect(() => {
    sessionStorage.setItem(storeKey(), JSON.stringify({ messages: messages.slice(-60), sessionId, focusId, pending }))
  }, [messages, sessionId, focusId, pending])

  function newChat() {
    const sid = newSessionId()
    setMessages([]); setFocusId(null); setPending(null); setLoading(false); setSessionId(sid)
    return sid
  }

  // Conversation history kept on the server (14 days): reopen an earlier chat and continue it.
  const [historyOpen, setHistoryOpen] = useState(false)
  const [history, setHistory] = useState({ status: 'idle', items: [], error: null })
  async function openHistory() {
    const next = !historyOpen
    setHistoryOpen(next)
    if (!next) return
    setHistory((h) => ({ ...h, status: 'loading', error: null }))
    try {
      const r = await api('/agent/conversations')
      setHistory({ status: 'live', items: r.conversations || [], days: r.retention_days, error: null })
    } catch (e) { setHistory({ status: 'error', items: [], error: e.message }) }
  }
  async function openConversation(c) {
    setHistoryOpen(false)
    try {
      const r = await api(`/agent/conversations/${encodeURIComponent(c.id)}`)
      if (r.found === false) throw new Error('This conversation has expired.')
      const msgs = []
      for (const m of r.messages || []) {
        msgs.push({ role: m.role, text: m.text })
        const match = m.role === 'assistant' && m.text.match(EXEC_RE)
        if (match) msgs.push({ role: 'system', type: 'run', executionId: match[1] })
      }
      setMessages(msgs); setSessionId(c.id); setPending(null); setLoading(false)
      const last = [...msgs].reverse().find((m) => m.type === 'run')
      setFocusId(last?.executionId || null)
    } catch (e) {
      setMessages((prev) => [...prev, { role: 'system', type: 'error', text: `Could not open the conversation: ${e.message}` }])
    }
  }
  async function deleteConversation(c) {
    if (!window.confirm(`Delete "${c.title || 'this conversation'}"?`)) return
    try {
      await api(`/agent/conversations/${encodeURIComponent(c.id)}/delete`, { method: 'POST', body: {} })
      setHistory((h) => ({ ...h, items: h.items.filter((x) => x.id !== c.id) }))
      if (c.id === sessionId) newChat()
    } catch (e) { setHistory((h) => ({ ...h, error: e.message })) }
  }
  const [polling, setPolling] = useState(false)
  const [executionId, setExecutionId] = useState(null)
  const chatEnd = useRef(null)

  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, polling])

  // Polling logic — stops and clears indicator on success/failure
  useEffect(() => {
    if (!polling || !executionId) return
    const interval = setInterval(async () => {
      try {
        const data = await checkStatus(executionId)
        if (data.status === 'SUCCEEDED') {
          setPolling(false)
          setExecutionId(null)
          // Remove the polling progress message and add success
          setMessages(prev => {
            const filtered = prev.filter(m => !(m.role === 'system' && (m.type === 'info' || m.type === 'polling')))
            return [...filtered, {
              role: 'system',
              type: 'success',
              text: 'Report generated successfully!',
              download_url: data.download_url,
              download_url_pptx: data.download_url_pptx,
            }]
          })
        } else if (data.status === 'FAILED') {
          setPolling(false)
          setExecutionId(null)
          setMessages(prev => {
            const filtered = prev.filter(m => !(m.role === 'system' && (m.type === 'info' || m.type === 'polling')))
            return [...filtered, {
              role: 'system',
              type: 'error',
              text: `Report generation failed: ${data.error || 'Unknown error'}`,
            }]
          })
        }
      } catch (e) { /* retry next interval */ }
    }, 30000)
    return () => clearInterval(interval)
  }, [polling, executionId])

  async function send() {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    await ask(userMsg, sessionId)
  }

  async function ask(userMsg, sid) {
    setMessages(prev => [...prev, { role: 'user', text: userMsg }])
    setLoading(true)
    try {
      let data
      if (platformEnabled) {
        const job = await submitAgent(userMsg, sid)
        setPending({ jobId: job.job_id })
        data = await waitAgent(job.job_id)
      } else {
        data = await sendChat(userMsg, sid)
      }
      handleReply(data)
    } catch (e) {
      setMessages(prev => [...prev, { role: 'system', type: 'error', text: `Connection error: ${e.message}` }])
    }
    setPending(null)
    setLoading(false)
  }

  // A turn that was still running when the user left the page: pick up its answer.
  useEffect(() => {
    if (!platformEnabled || !saved.pending?.jobId) return undefined
    let stop = false
    waitAgent(saved.pending.jobId)
      .then((data) => { if (!stop) handleReply(data) })
      .catch((e) => { if (!stop) setMessages(prev => [...prev, { role: 'system', type: 'error', text: `Connection error: ${e.message}` }]) })
      .finally(() => { if (!stop) { setPending(null); setLoading(false) } })
    return () => { stop = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // A prompt handed over by another page (for example "Analyze with AI" on a regulatory finding): new chat, ask once.
  useEffect(() => {
    if (!seed?.prompt || usedSeeds.has(seed.at)) return
    usedSeeds.add(seed.at)
    onSeedUsed?.()
    if (loading) { setInput(seed.prompt); return }  // a turn is still running: let the user send it afterwards
    ask(seed.prompt, newChat())
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seed])

  function handleReply(data) {
      const reply = data.response || data.message || JSON.stringify(data)
      setMessages(prev => [...prev, { role: 'assistant', text: reply }])
      // Detect execution ID for polling
      const match = reply.match(EXEC_RE)
      if (match) {
        setFocusId(match[1])
        if (platformEnabled) {
          setMessages(prev => [...prev, { role: 'system', type: 'run', executionId: match[1] }])
        } else {
          setExecutionId(match[1])
          setPolling(true)
          const timeMatch = reply.match(/(\d+)[-–](\d+)\s*menit/i) || reply.match(/(\d+)[-–](\d+)\s*min/i)
          const estTime = timeMatch ? `${timeMatch[1]}-${timeMatch[2]} minutes` : '10-20 minutes'
          setMessages(prev => [...prev, {
            role: 'system',
            type: 'polling',
            text: `Report generation in progress. Estimated time: ~${estTime}. You will be notified automatically when complete.`
          }])
        }
      }
  }

  function handleKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }

  return (
    <div className="flex h-full animate-fade-in">
    <div className="flex flex-col h-full flex-1 min-w-0">
      {/* Header */}
      <div className="relative z-20 px-8 py-5 border-b border-white/[0.06]">
        <img src="/img/city-night.jpg" alt="" className="absolute inset-0 w-full h-full object-cover opacity-25" style={{ objectPosition: 'center 40%' }} />
        <div className="absolute inset-0 bg-gradient-to-r from-dark-900 via-dark-900/90 to-dark-900/60" />
        <div className="relative flex items-center gap-4">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-accent-blue to-accent-teal flex items-center justify-center shadow-lg">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1">
            <div className="eyebrow text-accent-teal mb-0.5">Workspace · Assistant</div>
            <h2 className="text-xl font-display font-bold text-white tracking-tight">Ask, generate, and let the agent fix what fails</h2>
          </div>
          {platformEnabled ? <Pill tone="green">AgentCore Runtime</Pill> : <Pill tone="slate">Bedrock Agent (legacy)</Pill>}
          {platformEnabled && (
            <div className="relative">
              <button onClick={openHistory} disabled={loading} title="Earlier conversations" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/10 text-xs text-white/75 hover:bg-white/10 disabled:opacity-40"><History size={13} />History</button>
              {historyOpen && (
                <div className="absolute right-0 top-full mt-2 w-[360px] max-h-[420px] overflow-y-auto rounded-2xl border border-white/10 bg-dark-900/95 backdrop-blur shadow-2xl z-30 p-2">
                  <div className="px-2 py-1.5 text-[10px] text-white/35">Kept for {history.days || 14} days · personal data is masked</div>
                  {history.status === 'loading' && <div className="px-3 py-4 text-xs text-white/45 flex items-center gap-2"><Loader2 size={12} className="animate-spin" />Loading…</div>}
                  {history.error && <div className="px-3 py-2 text-xs text-esg-red">{history.error}</div>}
                  {history.status === 'live' && history.items.length === 0 && <div className="px-3 py-4 text-xs text-white/40">No earlier conversations.</div>}
                  {history.items.map((c) => (
                    <div key={c.id} className={`group flex items-center gap-2 rounded-xl px-3 py-2 ${c.id === sessionId ? 'bg-accent-blue/10' : 'hover:bg-white/[0.05]'}`}>
                      <button onClick={() => openConversation(c)} className="flex-1 min-w-0 text-left">
                        <div className="text-xs text-white/85 truncate">{c.title || 'Untitled'}</div>
                        <div className="text-[10px] text-white/35">{new Date(c.updated_at).toLocaleString()}</div>
                      </button>
                      <button onClick={() => deleteConversation(c)} title="Delete" className="text-white/25 hover:text-esg-red opacity-0 group-hover:opacity-100"><Trash2 size={12} /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          <button onClick={newChat} disabled={loading} title="Start a new conversation" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/10 text-xs text-white/75 hover:bg-white/10 disabled:opacity-40"><SquarePen size={13} />New chat</button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-8 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-16">
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 ${
              isDark ? 'bg-gradient-to-br from-accent-blue/20 to-accent-teal/10 border border-white/[0.08]' : 'bg-gradient-to-br from-accent-blue/10 to-accent-teal/5 border border-gray-200'
            }`}>
              <Bot className="w-7 h-7 text-accent-blue" />
            </div>
            <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-800'}`}>Start a Conversation</h3>
            <p className={`text-sm max-w-sm mx-auto mb-6 ${isDark ? 'text-white/40' : 'text-gray-500'}`}>Ask about ESG frameworks, compliance readiness, scenarios or GHG data, or generate a sustainability report</p>
            <div className="flex flex-wrap justify-center gap-2">
              {['Generate GRI 305 report for 2024', 'Create a multi-framework report for 2024', 'How ready are we for PSPK?', 'Sync the 2024 data from the database', 'Explain why a section failed validation'].map((suggestion, i) => (
                <button key={i} onClick={() => setInput(suggestion)}
                  className={`px-4 py-2 rounded-xl text-xs transition-all ${
                    isDark
                      ? 'bg-white/[0.03] border border-white/[0.08] text-white/60 hover:bg-white/[0.06] hover:border-accent-blue/30 hover:text-white/80'
                      : 'bg-gray-50 border border-gray-200 text-gray-600 hover:bg-accent-blue/5 hover:border-accent-blue/30 hover:text-gray-800'
                  }`}>
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => <MessageBubble key={i} message={msg} />)}

        {loading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-accent-purple/20 flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-accent-purple" />
            </div>
            <div className="glass-card px-4 py-3 rounded-2xl rounded-tl-md">
              <div className="flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 text-accent-blue animate-spin" />
                <span className={`text-sm ${isDark ? 'text-white/50' : 'text-gray-500'}`}>Thinking...</span>
              </div>
            </div>
          </div>
        )}

        {/* No separate floating bar — polling status shown as chat message above */}
        <div ref={chatEnd} />
      </div>

      {/* Input */}
      <div className={`p-6 border-t backdrop-blur-sm ${
        isDark ? 'border-white/[0.06] bg-dark-800/30' : 'border-gray-100 bg-white/80'
      }`}>
        <div className="flex gap-3 max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKey}
              placeholder="Ask about ESG reporting or generate a report..."
              className={`w-full rounded-xl px-5 py-3.5 text-sm focus:outline-none transition-all ${
                isDark
                  ? 'bg-white/[0.04] border border-white/[0.08] text-white placeholder-white/30 focus:border-accent-blue/40 focus:ring-1 focus:ring-accent-blue/20'
                  : 'bg-gray-50 border border-gray-200 text-gray-800 placeholder-gray-400 focus:border-accent-blue/50 focus:ring-1 focus:ring-accent-blue/20 focus:bg-white'
              }`} />
          </div>
          <button onClick={send} disabled={loading || !input.trim()}
            className="px-5 py-3.5 rounded-xl bg-gradient-to-r from-accent-blue to-accent-teal text-white text-sm font-medium hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-neon-blue hover:shadow-neon-green">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
    {platformEnabled && (
      <aside className="w-[340px] shrink-0 border-l border-white/[0.06] bg-dark-800/40 overflow-y-auto p-5">
        <div className="eyebrow mb-3">Agent activity</div>
        <AgentActivity focusId={focusId} />
      </aside>
    )}
    </div>
  )
}

// ─── Markdown Renderer (simple) ──────────────────────────────────────────────
function renderMarkdown(text) {
  if (!text) return null

  // Split into lines for processing
  const lines = text.split('\n')
  const elements = []

  lines.forEach((line, i) => {
    // Process inline markdown within the line
    const parts = parseInlineMarkdown(line)
    elements.push(
      <span key={i}>
        {parts}
        {i < lines.length - 1 && <br />}
      </span>
    )
  })

  return elements
}

function parseInlineMarkdown(text) {
  // Order matters: bold+italic first, then bold, then italic
  // Pattern: ***text*** or ___text___ → bold italic
  // Pattern: **text** or __text__ → bold
  // Pattern: *text* or _text_ → italic
  const parts = []
  let remaining = text
  let key = 0

  // Regex that matches bold-italic, bold, or italic
  const regex = /(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*)/g
  let lastIndex = 0
  let match

  while ((match = regex.exec(text)) !== null) {
    // Add text before this match
    if (match.index > lastIndex) {
      parts.push(<span key={key++}>{text.slice(lastIndex, match.index)}</span>)
    }

    if (match[2]) {
      // ***bold italic***
      parts.push(<strong key={key++}><em>{match[2]}</em></strong>)
    } else if (match[3]) {
      // **bold**
      parts.push(<strong key={key++}>{match[3]}</strong>)
    } else if (match[4]) {
      // *italic*
      parts.push(<em key={key++}>{match[4]}</em>)
    }

    lastIndex = match.index + match[0].length
  }

  // Add remaining text after last match
  if (lastIndex < text.length) {
    parts.push(<span key={key++}>{text.slice(lastIndex)}</span>)
  }

  // If no matches found, return original text
  if (parts.length === 0) {
    return text
  }

  return parts
}

// ─── Message Bubble ──────────────────────────────────────────────────────────
function MessageBubble({ message }) {
  const { isDark } = useTheme()
  const { role, text, type, download_url, download_url_pptx } = message

  if (role === 'system' && type === 'run') {
    return <div className="max-w-[80%]"><RunProgress executionId={message.executionId} /></div>
  }

  if (role === 'user') {
    return (
      <div className="flex items-start gap-3 justify-end">
        <div className="max-w-[70%] bg-gradient-to-r from-accent-blue/20 to-accent-blue/10 border border-accent-blue/20 rounded-2xl rounded-tr-md px-4 py-3">
          <p className={`text-sm whitespace-pre-wrap ${isDark ? 'text-white/90' : 'text-gray-800'}`}>{text}</p>
        </div>
        <div className="w-8 h-8 rounded-lg bg-accent-blue/20 flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-accent-blue" />
        </div>
      </div>
    )
  }

  if (role === 'system') {
    if (type === 'success') {
      return (
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-esg-green/20 flex items-center justify-center flex-shrink-0">
            <CheckCircle2 className="w-4 h-4 text-esg-green" />
          </div>
          <div className="glass-card px-4 py-3 rounded-2xl rounded-tl-md border-esg-green/20 max-w-[70%]">
            <p className="text-sm text-esg-green font-medium mb-3">{text}</p>
            <div className="flex gap-2">
              {download_url && (
                <a href={download_url} target="_blank" rel="noopener" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-blue/10 text-accent-blue text-xs font-medium hover:bg-accent-blue/20 transition-colors border border-accent-blue/20">
                  <Download size={12} /> DOCX
                </a>
              )}
              {download_url_pptx && (
                <a href={download_url_pptx} target="_blank" rel="noopener" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-esg-amber/10 text-esg-amber text-xs font-medium hover:bg-esg-amber/20 transition-colors border border-esg-amber/20">
                  <Download size={12} /> PPTX
                </a>
              )}
            </div>
          </div>
        </div>
      )
    }
    if (type === 'error') {
      return (
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-esg-red/20 flex items-center justify-center flex-shrink-0">
            <AlertCircle className="w-4 h-4 text-esg-red" />
          </div>
          <div className="glass-card px-4 py-3 rounded-2xl rounded-tl-md border-esg-red/20 max-w-[70%]">
            <p className="text-sm text-esg-red/90 whitespace-pre-wrap">{text}</p>
          </div>
        </div>
      )
    }
    // Info/Polling type (checkpoint alert style in chat)
    return (
      <div className={`flex items-center gap-3 px-5 py-3.5 rounded-2xl border ${
        type === 'polling'
          ? 'bg-esg-amber/5 border-esg-amber/20'
          : isDark ? 'bg-white/[0.02] border-white/[0.06]' : 'bg-gray-50 border-gray-100'
      }`}>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          type === 'polling' ? 'bg-esg-amber/15' : 'bg-accent-blue/10'
        }`}>
          <Loader2 className={`w-4 h-4 animate-spin ${type === 'polling' ? 'text-esg-amber' : 'text-accent-blue'}`} />
        </div>
        <div>
          <span className={`text-xs font-medium ${type === 'polling' ? 'text-esg-amber' : isDark ? 'text-white/60' : 'text-gray-600'}`}>
            {type === 'polling' ? '⏳ Generation In Progress' : 'Processing'}
          </span>
          <p className={`text-[11px] mt-0.5 ${isDark ? 'text-white/40' : 'text-gray-500'}`}>{text}</p>
        </div>
      </div>
    )
  }

  // Assistant — render markdown
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-lg bg-accent-purple/20 flex items-center justify-center flex-shrink-0">
        <Bot className="w-4 h-4 text-accent-purple" />
      </div>
      <div className="glass-card px-4 py-3 rounded-2xl rounded-tl-md max-w-[70%]">
        <div className={`text-sm whitespace-pre-wrap leading-relaxed ${isDark ? 'text-white/80' : 'text-gray-700'}`}>
          {renderMarkdown(text)}
        </div>
      </div>
    </div>
  )
}
