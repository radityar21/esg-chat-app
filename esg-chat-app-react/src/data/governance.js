// Capability 4 — AI governance: PII masking + smart model routing + token FinOps (synthetic)

// ── PII masking ─────────────────────────────────────────────────────────
export const HR_ROWS = [
  { id: 'EMP-0412', nik: '3174051203850004', name: 'Budi Santoso', gender: 'L', dob: '1985-03-12', salary: 28500000, branch: 'Jakarta Pusat', incident: 'Cedera kerja (jatuh)', phone: '081234567890', email: 'budi.santoso@bns.example' },
  { id: 'EMP-0977', nik: '3275014509900002', name: 'Siti Rahayu', gender: 'P', dob: '1990-09-05', salary: 21200000, branch: 'Bekasi', incident: 'Tidak ada', phone: '081298765432', email: 'siti.rahayu@bns.example' },
  { id: 'EMP-1103', nik: '3578062306880001', name: 'Agus Wijaya', gender: 'L', dob: '1988-06-23', salary: 33800000, branch: 'Surabaya', incident: 'Gangguan pendengaran (kerja)', phone: '085711223344', email: 'agus.wijaya@bns.example' },
  { id: 'EMP-1520', nik: '3273116712950003', name: 'Dewi Lestari', gender: 'P', dob: '1995-12-27', salary: 18900000, branch: 'Bandung', incident: 'Tidak ada', phone: '082155667788', email: 'dewi.lestari@bns.example' },
  { id: 'EMP-1844', nik: '1271030101820005', name: 'Rizky Hasibuan', gender: 'L', dob: '1982-01-01', salary: 41200000, branch: 'Medan', incident: 'Tidak ada', phone: '081377889900', email: 'rizky.h@bns.example' },
  { id: 'EMP-2031', nik: '7371054410910006', name: 'Andi Pratiwi', gender: 'P', dob: '1991-10-04', salary: 26700000, branch: 'Makassar', incident: 'Cedera kerja (terpeleset)', phone: '081911223355', email: 'andi.pratiwi@bns.example' },
]

// UU PDP No. 27/2022: specific personal data includes health & personal financial data
export const COLUMN_CLASS = {
  nik: { label: 'Restricted', tone: 'red', kind: 'Identifier', strategy: 'Tokenize' },
  name: { label: 'Restricted', tone: 'red', kind: 'General personal data', strategy: 'Pseudonym' },
  gender: { label: 'Internal', tone: 'blue', kind: 'General personal data', strategy: 'Keep (aggregate use)' },
  dob: { label: 'Confidential', tone: 'amber', kind: 'General personal data', strategy: 'Generalize to age band' },
  salary: { label: 'Restricted', tone: 'red', kind: 'Specific (financial)', strategy: 'Generalize to band' },
  branch: { label: 'Internal', tone: 'blue', kind: 'Non-personal', strategy: 'Keep' },
  incident: { label: 'Restricted', tone: 'red', kind: 'Specific (health)', strategy: 'Category only' },
  phone: { label: 'Confidential', tone: 'amber', kind: 'Contact', strategy: 'Redact' },
  email: { label: 'Confidential', tone: 'amber', kind: 'Contact', strategy: 'Redact' },
}

export function hash4(s) {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) }
  return (h >>> 0).toString(16).toUpperCase().padStart(8, '0').slice(0, 4)
}

const bandSalary = (n) => { const lo = Math.floor(n / 10e6) * 10; return `IDR ${lo}-${lo + 10}M` }
const ageBand = (dob) => { const a = 2025 - Number(dob.slice(0, 4)); const lo = Math.floor(a / 10) * 10; return `${lo}-${lo + 9}` }

export function maskRow(r, mode = 'tokenize') {
  const red = '[REDACTED]'
  return {
    id: r.id,
    nik: mode === 'tokenize' ? `NIK_${hash4(r.nik)}` : red,
    name: mode === 'tokenize' ? `PERSON_${hash4(r.name)}` : red,
    gender: r.gender,
    dob: ageBand(r.dob),
    salary: bandSalary(r.salary),
    branch: r.branch,
    incident: r.incident === 'Tidak ada' ? 'None' : /Cedera/.test(r.incident) ? 'Injury' : 'Health event',
    phone: red,
    email: red,
  }
}

const NAMES = HR_ROWS.map((r) => r.name)

// Detect + mask PII in free text. Returns {out, hits[]}
export function maskText(text, mode = 'tokenize') {
  const hits = []
  const tag = (type, v) => (mode === 'tokenize' ? `[${type}_${hash4(v)}]` : '[REDACTED]')
  let out = text
  const rules = [
    { type: 'NIK', re: /\b\d{16}\b/g },
    { type: 'EMAIL', re: /[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g },
    { type: 'PHONE', re: /(?:\+62|0)8\d{1,2}[-\s]?\d{3,4}[-\s]?\d{3,4}/g },
    { type: 'NPWP', re: /\b\d{2}\.\d{3}\.\d{3}\.\d-\d{3}\.\d{3}\b/g },
  ]
  rules.forEach(({ type, re }) => {
    out = out.replace(re, (m) => { hits.push({ type, value: m }); return tag(type, m) })
  })
  // names: roster match + honorific pattern
  NAMES.forEach((n) => {
    const re = new RegExp(n, 'g')
    out = out.replace(re, (m) => { hits.push({ type: 'PERSON', value: m }); return tag('PERSON', m) })
  })
  out = out.replace(/\b(Bapak|Ibu|Sdr\.?|Sdri\.?)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)/g, (m, h, n) => {
    hits.push({ type: 'PERSON', value: n }); return `${h} ${tag('PERSON', n)}`
  })
  return { out, hits }
}

export const SAMPLE_NOTE = 'Ibu Siti Rahayu (NIK 3275014509900002) melaporkan kecelakaan kerja di cabang Bekasi pada 14 Maret. Hubungi 0812-9876-5432 atau siti.rahayu@bns.example. Atasan: Bapak Hendra Gunawan.'

// ── Smart model routing + FinOps ─────────────────────────────────────────
// USD per 1M tokens (list price, illustrative — verify before quoting externally)
export const MODELS = {
  sonnet: { name: 'Claude Sonnet 4.5', in: 3, out: 15, color: '#7c5cfc' },
  haiku: { name: 'Claude Haiku 4.5', in: 1, out: 5, color: '#06d6a0' },
}

// Per monthly report run for the parent bank
export const TASKS = [
  { id: 'val', name: 'Input validation (21 rules)', route: 'haiku', calls: 40, tin: 4200, tout: 600, cache: false, batch: true },
  { id: 'dq', name: 'Data-quality summarisation', route: 'haiku', calls: 12, tin: 6000, tout: 900, cache: false, batch: true },
  { id: 'nar', name: 'Section narratives (Scope 1/2/3, targets)', route: 'sonnet', calls: 8, tin: 9500, tout: 2800, cache: true, batch: false },
  { id: 'exe', name: 'Executive summary', route: 'sonnet', calls: 1, tin: 14000, tout: 2200, cache: true, batch: false },
  { id: 'reg', name: 'Regulatory cross-check', route: 'haiku', calls: 10, tin: 8000, tout: 1000, cache: false, batch: true },
  { id: 'qa', name: 'Chat Q&A (100 queries)', route: 'haiku', calls: 100, tin: 1800, tout: 450, cache: false, batch: false },
  { id: 'scn', name: 'Scenario narratives', route: 'sonnet', calls: 4, tin: 11000, tout: 3000, cache: true, batch: false },
]

const callCost = (m, tin, tout) => (tin * MODELS[m].in + tout * MODELS[m].out) / 1e6

export function taskCost(t, opts = {}) {
  const model = opts.routed === false ? 'sonnet' : t.route
  let tin = t.tin
  const m = MODELS[model]
  let inCost = (tin * m.in) / 1e6
  if (opts.cache && t.cache) inCost *= 1 - 0.6 * 0.9 // 60% of input is a static prefix, cache reads at 10% price
  let c = inCost + (t.tout * m.out) / 1e6
  if (opts.batch && t.batch) c *= 0.5
  return c * t.calls
}

export function runCosts(opts = {}) {
  const rows = TASKS.map((t) => ({
    ...t,
    baseline: taskCost(t, { routed: false }),
    optimized: taskCost(t, { routed: true, cache: opts.cache, batch: opts.batch }),
  }))
  const baseline = rows.reduce((a, r) => a + r.baseline, 0)
  const optimized = rows.reduce((a, r) => a + r.optimized, 0)
  return { rows, baseline, optimized, savedPct: (1 - optimized / baseline) * 100 }
}

export const singleCall = (t, routed = true, opts = {}) => ({
  model: routed ? t.route : 'sonnet',
  cost: taskCost({ ...t, calls: 1 }, { routed, ...opts }),
  tin: t.tin,
  tout: t.tout,
})
