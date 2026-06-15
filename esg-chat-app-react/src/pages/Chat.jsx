import { useState, useRef, useEffect } from 'react'
import { sendChat, checkStatus } from '../api'
import { Send, Bot, User, Loader2, CheckCircle2, AlertCircle, Download, Sparkles } from 'lucide-react'

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId] = useState(crypto.randomUUID())
  const [polling, setPolling] = useState(false)
  const [executionId, setExecutionId] = useState(null)
  const chatEnd = useRef(null)

  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  // Polling logic
  useEffect(() => {
    if (!polling || !executionId) return
    const interval = setInterval(async () => {
      try {
        const data = await checkStatus(executionId)
        if (data.status === 'SUCCEEDED') {
          setPolling(false)
          setMessages(prev => [...prev, {
            role: 'system',
            type: 'success',
            text: 'Report generated successfully!',
            download_url: data.download_url,
            download_url_pptx: data.download_url_pptx,
          }])
        } else if (data.status === 'FAILED') {
          setPolling(false)
          setMessages(prev => [...prev, {
            role: 'system',
            type: 'error',
            text: `Report generation failed: ${data.error || 'Unknown error'}`,
          }])
        }
      } catch (e) {}
    }, 30000)
    return () => clearInterval(interval)
  }, [polling, executionId])

  async function send() {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: userMsg }])
    setLoading(true)

    try {
      const data = await sendChat(userMsg, sessionId)
      const reply = data.response || data.message || JSON.stringify(data)
      setMessages(prev => [...prev, { role: 'assistant', text: reply }])

      // Detect execution ID for polling
      const match = reply.match(/Execution ID:\s*([a-f0-9-]+)/i)
      if (match) {
        setExecutionId(match[1])
        setPolling(true)
        setMessages(prev => [...prev, { role: 'system', type: 'info', text: 'Report generation started. Monitoring progress...' }])
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'system', type: 'error', text: `Connection error: ${e.message}` }])
    }
    setLoading(false)
  }

  function handleKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }

  return (
    <div className="flex flex-col h-full animate-fade-in">
      {/* Header */}
      <div className="px-8 py-5 border-b border-white/[0.06] bg-dark-800/50 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">ESG Chat Assistant</h2>
            <p className="text-xs text-white/40">Powered by Amazon Bedrock Agent</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-8 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-blue/20 to-accent-teal/10 border border-white/[0.08] flex items-center justify-center mx-auto mb-4">
              <Bot className="w-7 h-7 text-accent-blue" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Start a Conversation</h3>
            <p className="text-sm text-white/40 max-w-sm mx-auto mb-6">Ask questions about ESG frameworks or generate a sustainability report</p>
            <div className="flex flex-wrap justify-center gap-2">
              {[
                'Generate GRI 305 report for 2024',
                'Create CSRD multi-framework report',
                'What frameworks are supported?',
              ].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(suggestion) }}
                  className="px-4 py-2 rounded-xl bg-white/[0.03] border border-white/[0.08] text-xs text-white/60 hover:bg-white/[0.06] hover:border-accent-blue/30 hover:text-white/80 transition-all"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {loading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-accent-purple/20 flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-accent-purple" />
            </div>
            <div className="glass-card px-4 py-3 rounded-2xl rounded-tl-md">
              <div className="flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 text-accent-blue animate-spin" />
                <span className="text-sm text-white/50">Thinking...</span>
              </div>
            </div>
          </div>
        )}

        {polling && (
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-esg-amber/5 border border-esg-amber/20">
            <Loader2 className="w-4 h-4 text-esg-amber animate-spin" />
            <span className="text-xs text-esg-amber font-medium">Generating report... This may take 2-5 minutes</span>
          </div>
        )}

        <div ref={chatEnd} />
      </div>

      {/* Input */}
      <div className="p-6 border-t border-white/[0.06] bg-dark-800/30 backdrop-blur-sm">
        <div className="flex gap-3 max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about ESG reporting or generate a report..."
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-5 py-3.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-accent-blue/40 focus:ring-1 focus:ring-accent-blue/20 transition-all"
            />
          </div>
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="px-5 py-3.5 rounded-xl bg-gradient-to-r from-accent-blue to-accent-teal text-white text-sm font-medium hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-neon-blue hover:shadow-neon-green"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }) {
  const { role, text, type, download_url, download_url_pptx } = message

  if (role === 'user') {
    return (
      <div className="flex items-start gap-3 justify-end">
        <div className="max-w-[70%] bg-gradient-to-r from-accent-blue/20 to-accent-blue/10 border border-accent-blue/20 rounded-2xl rounded-tr-md px-4 py-3">
          <p className="text-sm text-white/90 whitespace-pre-wrap">{text}</p>
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
                <a href={download_url} target="_blank" rel="noopener"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-blue/10 text-accent-blue text-xs font-medium hover:bg-accent-blue/20 transition-colors border border-accent-blue/20">
                  <Download size={12} /> DOCX
                </a>
              )}
              {download_url_pptx && (
                <a href={download_url_pptx} target="_blank" rel="noopener"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-esg-amber/10 text-esg-amber text-xs font-medium hover:bg-esg-amber/20 transition-colors border border-esg-amber/20">
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

    // Info type
    return (
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
        <Loader2 className="w-3.5 h-3.5 text-accent-blue animate-spin" />
        <span className="text-xs text-white/50">{text}</span>
      </div>
    )
  }

  // Assistant
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-lg bg-accent-purple/20 flex items-center justify-center flex-shrink-0">
        <Bot className="w-4 h-4 text-accent-purple" />
      </div>
      <div className="glass-card px-4 py-3 rounded-2xl rounded-tl-md max-w-[70%]">
        <p className="text-sm text-white/80 whitespace-pre-wrap leading-relaxed">{text}</p>
      </div>
    </div>
  )
}
