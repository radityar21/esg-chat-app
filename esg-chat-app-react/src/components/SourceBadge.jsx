import { Pill } from './ui'

// Shows where the numbers on a page come from, so nobody mistakes demo data for live data.
const short = (e) => (e.length > 48 ? e.slice(0, 45) + '…' : e)

export default function SourceBadge({ status, error, liveLabel = 'Live · AWS' }) {
  if (status === 'live') return <Pill tone="green">{liveLabel}</Pill>
  if (status === 'loading') return <Pill tone="blue">Loading…</Pill>
  if (status === 'error') return <span title={error || ''}><Pill tone="amber">Demo data · live data failed{error ? `: ${short(error)}` : ''}</Pill></span>
  return <Pill tone="slate">Demo data</Pill>
}
