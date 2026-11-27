// Sign-in with the Cognito hosted UI (authorization code + PKCE). No client secret, no extra dependency.
// Tokens live in sessionStorage: closing the tab signs the user out.
const DOMAIN = (import.meta.env.VITE_COGNITO_DOMAIN || '').replace(/\/$/, '')
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID || ''
export const authEnabled = Boolean(DOMAIN && CLIENT_ID && import.meta.env.VITE_PLATFORM_API_URL)

const K = { tokens: 'esg.tokens', pkce: 'esg.pkce' }
const redirectUri = () => `${window.location.origin}/`

const b64url = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
const rand = (n = 32) => b64url(crypto.getRandomValues(new Uint8Array(n)))
const sha256 = (s) => crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))

function decode(jwt) {
  try {
    const p = jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(decodeURIComponent(escape(atob(p))))
  } catch { return {} }
}
const load = () => { try { return JSON.parse(sessionStorage.getItem(K.tokens)) } catch { return null } }
const save = (t) => sessionStorage.setItem(K.tokens, JSON.stringify(t))

async function tokenRequest(params) {
  const res = await fetch(`${DOMAIN}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ client_id: CLIENT_ID, ...params }),
  })
  if (!res.ok) throw new Error('Sign-in failed')
  return res.json()
}

export async function login() {
  const verifier = rand(48)
  const state = rand(16)
  sessionStorage.setItem(K.pkce, JSON.stringify({ verifier, state }))
  const q = new URLSearchParams({
    response_type: 'code', client_id: CLIENT_ID, redirect_uri: redirectUri(), scope: 'openid email profile',
    state, code_challenge_method: 'S256', code_challenge: b64url(await sha256(verifier)),
  })
  window.location.assign(`${DOMAIN}/oauth2/authorize?${q}`)
}

/** Call once on page load. Completes the redirect from the hosted UI when ?code= is present. */
let pendingLogin = null
export function completeLogin() {
  pendingLogin ||= doCompleteLogin() // React StrictMode runs effects twice in dev; the code is single-use
  return pendingLogin
}

async function doCompleteLogin() {
  const url = new URLSearchParams(window.location.search)
  const code = url.get('code')
  if (!code) return Boolean(load())
  const saved = JSON.parse(sessionStorage.getItem(K.pkce) || 'null')
  sessionStorage.removeItem(K.pkce)
  window.history.replaceState({}, '', window.location.pathname) // remove ?code=&state= from the address bar
  if (!saved || saved.state !== url.get('state')) throw new Error('Sign-in state mismatch')
  const t = await tokenRequest({ grant_type: 'authorization_code', code, redirect_uri: redirectUri(), code_verifier: saved.verifier })
  save({ access: t.access_token, id: t.id_token, refresh: t.refresh_token, exp: Date.now() + t.expires_in * 1000 })
  return true
}

/** A valid access token, refreshed when it expires within a minute. Returns null when signed out. */
export async function getAccessToken() {
  const t = load()
  if (!t) return null
  if (t.exp - Date.now() > 60000) return t.access
  if (!t.refresh) { signOutLocal(); return null }
  try {
    const n = await tokenRequest({ grant_type: 'refresh_token', refresh_token: t.refresh })
    save({ ...t, access: n.access_token, id: n.id_token || t.id, exp: Date.now() + n.expires_in * 1000 })
    return n.access_token
  } catch { signOutLocal(); return null }
}

export function currentUser() {
  const t = load()
  if (!t) return null
  const c = decode(t.id)
  const groups = c['cognito:groups'] || []
  return { email: c.email || c['cognito:username'] || 'user', groups, isAdmin: groups.includes('admin') }
}

function signOutLocal() { sessionStorage.removeItem(K.tokens) }

export function logout() {
  signOutLocal()
  window.location.assign(`${DOMAIN}/logout?${new URLSearchParams({ client_id: CLIENT_ID, logout_uri: redirectUri() })}`)
}
