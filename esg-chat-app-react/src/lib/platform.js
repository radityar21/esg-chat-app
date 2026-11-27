// Client for the ESG platform API (infra/stacks/platform_stack.py).
// Without VITE_PLATFORM_API_URL every page runs on the bundled demo data and says so ("Demo data" badge).
import { useCallback, useEffect, useRef, useState } from 'react'
import { authEnabled, getAccessToken, login } from './auth'

const clean = (u) => (u || '').replace(/\/$/, '')
export const BASE = clean(import.meta.env.VITE_PLATFORM_API_URL)
export const platformEnabled = Boolean(BASE)

export async function api(path, { method = 'GET', body, timeout = 28000, signal } = {}) {
  const base = BASE
  if (!base) throw new Error('Platform API is not configured')
  const token = authEnabled ? await getAccessToken() : null
  if (authEnabled && !token) { login(); throw new Error('Signed out') }
  const ctl = new AbortController()
  const timer = setTimeout(() => ctl.abort(), timeout)
  signal?.addEventListener('abort', () => ctl.abort())
  try {
    const res = await fetch(base + path, {
      method,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: ctl.signal,
    })
    if (res.status === 401 && authEnabled) { login(); throw new Error('Session expired') }
    const text = await res.text()
    let data
    try { data = text ? JSON.parse(text) : {} } catch { data = { error: text.slice(0, 200) } }
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
    return data
  } finally {
    clearTimeout(timer)
  }
}

/**
 * Load `path` from the platform API.
 * status: 'demo' (API not configured) | 'loading' | 'live' | 'error' (request failed, caller shows demo data)
 */
export function useLive(path, { enabled = true } = {}) {
  const live = platformEnabled && enabled && Boolean(path)
  const [state, setState] = useState({ data: null, status: live ? 'loading' : 'demo', error: null })
  const [tick, setTick] = useState(0)
  useEffect(() => {
    if (!live) { setState({ data: null, status: 'demo', error: null }); return undefined }
    const ctl = new AbortController()
    setState((s) => ({ ...s, status: 'loading', error: null }))
    api(path, { signal: ctl.signal })
      .then((data) => setState({ data, status: 'live', error: null }))
      .catch((e) => { if (!ctl.signal.aborted) setState({ data: null, status: 'error', error: e.message }) })
    return () => ctl.abort()
  }, [path, live, tick])
  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { ...state, reload }
}

/** Debounced POST used by the what-if sliders. */
export function useDebouncedPost(path, body, { enabled = true, delay = 350 } = {}) {
  const live = platformEnabled && enabled
  const [state, setState] = useState({ data: null, status: live ? 'loading' : 'demo', error: null })
  const seq = useRef(0)
  const key = JSON.stringify(body)
  useEffect(() => {
    if (!live) return undefined
    const id = ++seq.current
    const t = setTimeout(() => {
      api(path, { method: 'POST', body })
        .then((data) => { if (id === seq.current) setState({ data, status: 'live', error: null }) })
        .catch((e) => { if (id === seq.current) setState({ data: null, status: 'error', error: e.message }) })
    }, delay)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, key, live, delay])
  return state
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

/** Queue a chat turn for the AgentCore orchestrator. Returns {job_id, session_id}. */
export function submitAgent(prompt, sessionId) {
  return api('/agent/chat', { method: 'POST', body: { prompt, session_id: sessionId } })
}

/** Ask the AgentCore orchestrator. The turn runs asynchronously on the server; this polls until it is done. */
export async function askAgent(prompt, sessionId, opts = {}) {
  const job = await submitAgent(prompt, sessionId)
  return waitAgent(job.job_id, opts)
}

/** Poll a queued chat turn until it has an answer. Safe to call again after a page change (resume). */
export async function waitAgent(jobId, { maxWaitMs = 300000 } = {}) {
  const t0 = Date.now()
  while (Date.now() - t0 < maxWaitMs) {
    await sleep(2000)
    const s = await api(`/agent/chat/${jobId}`)
    if (s.found === false) throw new Error('The request was lost. Please ask again.')
    if (s.status === 'done') return s.result
    if (s.status === 'failed') throw new Error('The agent could not answer. Please try again.')
  }
  throw new Error('The agent is taking longer than expected. Check the Agent activity panel.')
}

/** Start a regulatory scan (administrators) and wait until the alert list shows a newer scan time. */
export async function runScan({ maxWaitMs = 180000 } = {}) {
  const before = (await api('/compliance/alerts')).last_scan
  await api('/compliance/scan', { method: 'POST', body: {} })
  const t0 = Date.now()
  while (Date.now() - t0 < maxWaitMs) {
    await sleep(4000)
    const a = await api('/compliance/alerts')
    if (a.last_scan && a.last_scan !== before) return a
  }
  throw new Error('The scan is still running; refresh in a minute.')
}
