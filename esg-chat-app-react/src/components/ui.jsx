import { useEffect, useRef, useState } from 'react'

export const C = {
  blue: '#4f8cf7',
  teal: '#06d6a0',
  purple: '#7c5cfc',
  cyan: '#22d3ee',
  amber: '#fbbf24',
  red: '#ef4444',
  slate: '#64748b',
}

export const tooltipProps = {
  contentStyle: {
    background: 'rgba(13,18,37,0.96)',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 12,
    color: '#fff',
    fontSize: 12,
    boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
  },
  labelStyle: { color: 'rgba(255,255,255,0.6)' },
  itemStyle: { color: '#fff' },
  cursor: { fill: 'rgba(255,255,255,0.04)' },
}

export const axisTick = { fill: 'rgba(255,255,255,0.45)', fontSize: 11 }

export function useCountUp(target, ms = 1100, decimals = 0) {
  const [val, setVal] = useState(0)
  const from = useRef(0)
  useEffect(() => {
    const start = performance.now()
    const a = from.current
    let raf
    const tick = (t) => {
      const p = Math.min(1, (t - start) / ms)
      const e = 1 - Math.pow(1 - p, 3)
      setVal(a + (target - a) * e)
      if (p < 1) raf = requestAnimationFrame(tick)
      else from.current = target
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return Number(val.toFixed(decimals))
}

export function CountUp({ value, decimals = 0, prefix = '', suffix = '', ms }) {
  const v = useCountUp(value, ms, decimals)
  return (
    <span>
      {prefix}
      {v.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {suffix}
    </span>
  )
}

export function Panel({ title, subtitle, right, children, className = '', pad = true }) {
  return (
    <section className={`panel ${className}`}>
      {(title || right) && (
        <header className="flex items-start justify-between gap-4 px-6 pt-5 pb-3">
          <div>
            {title && <h3 className="text-[15px] font-semibold text-white tracking-tight">{title}</h3>}
            {subtitle && <p className="text-xs text-white/45 mt-0.5">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className={pad ? 'px-6 pb-6' : ''}>{children}</div>
    </section>
  )
}

const tones = {
  green: 'bg-esg-green/10 text-esg-green border-esg-green/25',
  amber: 'bg-esg-amber/10 text-esg-amber border-esg-amber/25',
  red: 'bg-esg-red/10 text-esg-red border-esg-red/25',
  blue: 'bg-accent-blue/10 text-accent-blue border-accent-blue/25',
  purple: 'bg-accent-purple/10 text-accent-purple border-accent-purple/25',
  slate: 'bg-white/5 text-white/60 border-white/10',
}

export function Pill({ tone = 'slate', children, className = '' }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${tones[tone]} ${className}`}>
      {children}
    </span>
  )
}

export function Stat({ icon: Icon, label, value, decimals = 0, prefix, suffix, sub, tone = 'blue' }) {
  const col = { blue: 'text-accent-blue', teal: 'text-accent-teal', purple: 'text-accent-purple', amber: 'text-esg-amber', red: 'text-esg-red' }[tone]
  return (
    <div className="panel p-5 relative overflow-hidden group">
      <div className={`absolute -right-6 -top-6 w-24 h-24 rounded-full blur-2xl opacity-20 ${col.replace('text', 'bg')}`} />
      <div className="flex items-center gap-2 mb-3">
        {Icon && <Icon size={16} className={col} />}
        <span className="eyebrow">{label}</span>
      </div>
      <div className="text-3xl font-display font-bold text-white tracking-tight">
        <CountUp value={value} decimals={decimals} prefix={prefix} suffix={suffix} />
      </div>
      {sub && <div className="text-xs text-white/45 mt-1.5">{sub}</div>}
    </div>
  )
}

export function Gauge({ value, size = 220, label = 'Readiness', sublabel }) {
  const v = useCountUp(value, 1400, 0)
  const r = size / 2 - 16
  const circ = 2 * Math.PI * r
  const arc = circ * 0.75
  const off = arc * (1 - Math.min(100, v) / 100)
  const tone = value >= 80 ? C.teal : value >= 60 ? C.blue : C.amber
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-[225deg]">
        <defs>
          <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={C.blue} />
            <stop offset="100%" stopColor={tone} />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="14" strokeLinecap="round" strokeDasharray={`${arc} ${circ}`} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="url(#gaugeGrad)" strokeWidth="14" strokeLinecap="round" strokeDasharray={`${arc} ${circ}`} strokeDashoffset={off} style={{ filter: `drop-shadow(0 0 10px ${tone}88)` }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-6xl font-display font-extrabold text-white leading-none">{v}<span className="text-2xl text-white/50">%</span></div>
        <div className="text-xs uppercase tracking-[0.18em] text-white/50 mt-2">{label}</div>
        {sublabel && <div className="text-[11px] text-white/35 mt-1">{sublabel}</div>}
      </div>
    </div>
  )
}

export function PageHeader({ eyebrow, title, desc, image = '/img/forest-aerial-2.jpg', children, pos = 'center', badge }) {
  return (
    <div className="relative rounded-3xl overflow-hidden mb-8 border border-white/[0.07]">
      <img src={image} alt="" className="absolute inset-0 w-full h-full object-cover opacity-50" style={{ objectPosition: pos }} />
      <div className="absolute inset-0 bg-gradient-to-r from-dark-900 via-dark-900/85 to-dark-900/30" />
      <div className="relative px-9 py-9 flex items-end justify-between gap-6">
        <div className="max-w-2xl">
          <div className="flex items-center gap-3 mb-2"><div className="eyebrow text-accent-teal">{eyebrow}</div>{badge}</div>
          <h1 className="text-[34px] leading-tight font-display font-bold text-white tracking-tight">{title}</h1>
          {desc && <p className="text-sm text-white/60 mt-2.5 leading-relaxed">{desc}</p>}
        </div>
        {children}
      </div>
    </div>
  )
}

export function Button({ children, onClick, icon: Icon, variant = 'primary', disabled, className = '' }) {
  const styles = {
    primary: 'bg-gradient-to-r from-accent-blue to-accent-teal text-dark-900 font-semibold shadow-neon-blue hover:brightness-110',
    ghost: 'bg-white/[0.05] text-white/80 border border-white/10 hover:bg-white/10',
    danger: 'bg-esg-red/15 text-esg-red border border-esg-red/30 hover:bg-esg-red/25',
  }[variant]
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm whitespace-nowrap transition-all disabled:opacity-40 disabled:cursor-not-allowed ${styles} ${className}`}
    >
      {Icon && <Icon size={15} />}
      {children}
    </button>
  )
}

export function Slider({ label, value, onChange, min, max, step = 1, unit = '', hint }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-white/70">{label}</span>
        <span className="font-semibold text-white tabular-nums">{value}{unit}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-accent-teal" />
      {hint && <div className="text-[10px] text-white/35 mt-0.5">{hint}</div>}
    </div>
  )
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="inline-flex p-1 rounded-xl bg-white/[0.04] border border-white/[0.07]">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${value === t.id ? 'bg-accent-blue/20 text-white shadow-sm' : 'text-white/50 hover:text-white/80'}`}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

export const fmt = (n, d = 0) => Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })
