// Client for the ESG platform API (infra/stacks/platform_stack.py).
// Without VITE_PLATFORM_API_URL every page runs on the bundled demo data and says so ("Demo data" badge).
import { useCallback, useEffect, useRef, useState } from 'react'

const clean = (u) => (u || '').replace(/\/$/, '')
export const BASE = clean(import.meta.env.VITE_PLATFORM_API_URL)
export const CHAT_BASE = clean(import.meta.env.VITE_AGENT_CHAT_URL) || BASE
const KEY = import.meta.env.VITE_PLATFORM_API_KEY || ''
export const platformEnabled = Boolean(BASE)

export async function api(path, { method = 'GET', body, base = BASE, timeout = 28000, signal } = {}) {
  if (!base) throw new Error('Platform API is not configured')
  const ctl = new AbortController()
  const timer = setTimeout(() => ctl.abort(), timeout)
  signal?.addEventListener('abort', () => ctl.abort())
  try {
    const res = await fetch(base + path, {
      method,
      headers: { 'Content-Type': 'application/json', ...(KEY ? { 'x-api-key': KEY } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: ctl.signal,
    })
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
