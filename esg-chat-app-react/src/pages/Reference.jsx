import { useState, useEffect, useMemo } from 'react'
import { getDocuments } from '../api'
import { BookOpen, FileText, Loader2, Database, Globe, Shield, Landmark, Search } from 'lucide-react'
import { PageHeader, Panel } from '../components/ui'
import { api, platformEnabled } from '../lib/platform'

// Static class strings: Tailwind cannot see class names that are assembled at runtime.
const TONES = {
  green: { box: 'bg-esg-green/10 border-esg-green/20', text: 'text-esg-green' },
  blue: { box: 'bg-accent-blue/10 border-accent-blue/20', text: 'text-accent-blue' },
  purple: { box: 'bg-accent-purple/10 border-accent-purple/20', text: 'text-accent-purple' },
  amber: { box: 'bg-esg-amber/10 border-esg-amber/20', text: 'text-esg-amber' },
  teal: { box: 'bg-accent-teal/10 border-accent-teal/20', text: 'text-accent-teal' },
  slate: { box: 'bg-white/5 border-white/10', text: 'text-white/60' },
}
const CATEGORY_CONFIG = {
  gri: { icon: Globe, tone: 'green', label: 'GRI Standards' },
  ifrs: { icon: Landmark, tone: 'blue', label: 'IFRS S2' },
  esrs: { icon: Shield, tone: 'purple', label: 'ESRS / CSRD' },
  csrd: { icon: Shield, tone: 'purple', label: 'ESRS / CSRD' },
  ghg_methodology: { icon: Database, tone: 'blue', label: 'GHG methodology (GHG Protocol, PCAF, IPCC)' },
  style_reference: { icon: FileText, tone: 'teal', label: 'Sample sustainability reports' },
  ojk: { icon: Database, tone: 'amber', label: 'OJK PSPK' },
  benchmarks: { icon: FileText, tone: 'teal', label: 'Benchmarks' },
  default: { icon: FileText, tone: 'slate', label: 'Documents' },
}
const FRAMEWORKS = [
  { label: 'GRI 305', desc: 'Greenhouse Gas Emissions', icon: Globe, tone: 'green' },
  { label: 'IFRS S2', desc: 'Climate-related Disclosures', icon: Landmark, tone: 'blue' },
  { label: 'ESRS E1', desc: 'Climate Change (CSRD)', icon: Shield, tone: 'purple' },
  { label: 'OJK PSPK', desc: 'Indonesian regulation', icon: Database, tone: 'amber' },
]

function IconBox({ icon: Icon, tone, size = 'w-9 h-9' }) {
  const t = TONES[tone]
  return <div className={`${size} rounded-xl border flex items-center justify-center shrink-0 ${t.box}`}><Icon className={t.text} size={16} /></div>
}

export default function Reference() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')

  useEffect(() => {
    (platformEnabled ? api('/reference/documents') : getDocuments()).then((d) => setDocs(d.documents || [])).catch((e) => console.error(e)).finally(() => setLoading(false))
  }, [])

  const grouped = useMemo(() => docs
    .filter((d) => !q || d.filename.toLowerCase().includes(q.toLowerCase()))
    .reduce((acc, d) => { const c = d.category || 'other'; (acc[c] ||= []).push(d); return acc }, {}), [docs, q])

  return (
    <div className="flex-1 overflow-y-auto p-10 animate-fade-in">
      <PageHeader eyebrow="Workspace · Reference library" title="The standards behind every number"
        desc="Framework documents indexed in the Knowledge Base. The report generator retrieves from these sources and cites them in each section."
        image="/img/city-night.jpg" pos="center 70%">
        <div className="relative">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/35" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search documents" className="w-64 bg-black/30 border border-white/10 rounded-xl pl-9 pr-4 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-accent-teal/50" />
        </div>
      </PageHeader>

      <div className="grid grid-cols-4 gap-5 mb-6">
        {FRAMEWORKS.map((fw) => (
          <div key={fw.label} className="panel p-5">
            <IconBox icon={fw.icon} tone={fw.tone} />
            <div className="font-display font-semibold text-white mt-3">{fw.label}</div>
            <div className="text-xs text-white/45 mt-0.5">{fw.desc}</div>
          </div>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-16"><Loader2 className="w-6 h-6 text-accent-blue animate-spin mx-auto mb-3" /><span className="text-sm text-white/40">Loading documents from the Knowledge Base…</span></div>
      ) : Object.keys(grouped).length === 0 ? (
        <div className="text-center py-16">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4 bg-white/[0.03] border border-white/[0.08]"><BookOpen className="w-6 h-6 text-white/25" /></div>
          <p className="text-sm text-white/40">{q ? 'No document matches your search' : 'No documents found in the Knowledge Base'}</p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-5">
          {Object.entries(grouped).map(([category, files]) => {
            const cfg = CATEGORY_CONFIG[category] || CATEGORY_CONFIG.default
            return (
              <Panel key={category} title={cfg.label} subtitle={`${files.length} document${files.length > 1 ? 's' : ''}`} right={<IconBox icon={cfg.icon} tone={cfg.tone} />}>
                <div className="space-y-1.5">
                  {files.map((file) => (
                    <div key={file.filename} className="flex items-center justify-between gap-2 py-2 px-3 rounded-lg bg-white/[0.03] border border-white/[0.05] hover:bg-white/[0.06] transition-colors">
                      <div className="flex items-center gap-2 min-w-0"><FileText className="w-3.5 h-3.5 shrink-0 text-white/30" /><span className="text-xs truncate text-white/70" title={file.filename}>{file.filename}</span></div>
                      <span className="text-[10px] shrink-0 text-white/30">{file.size_kb} KB</span>
                    </div>
                  ))}
                </div>
              </Panel>
            )
          })}
        </div>
      )}
    </div>
  )
}
