import { useState, useEffect } from 'react'
import { getDocuments } from '../api'
import { BookOpen, FileText, Loader2, Database, Globe, Shield, Landmark } from 'lucide-react'

const CATEGORY_CONFIG = {
  gri: { icon: Globe, color: 'esg-green', label: 'GRI Standards' },
  ifrs: { icon: Landmark, color: 'accent-blue', label: 'IFRS S2' },
  esrs: { icon: Shield, color: 'accent-purple', label: 'ESRS / CSRD' },
  ojk: { icon: Database, color: 'esg-amber', label: 'OJK PSPK' },
  benchmarks: { icon: FileText, color: 'accent-teal', label: 'Benchmarks' },
  default: { icon: FileText, color: 'white/50', label: 'Documents' },
}

export default function Reference() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadDocs() }, [])

  async function loadDocs() {
    setLoading(true)
    try {
      const data = await getDocuments()
      setDocs(data.documents || [])
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  // Group by category
  const grouped = docs.reduce((acc, doc) => {
    const cat = doc.category || 'other'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(doc)
    return acc
  }, {})

  return (
    <div className="flex-1 overflow-y-auto p-8 animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <h1 className="text-2xl font-bold text-white">Reference Library</h1>
        </div>
        <p className="text-sm text-white/40">Framework documents indexed in Knowledge Base (OpenSearch)</p>
      </div>

      {/* Framework Overview Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          { label: 'GRI 305', desc: 'Greenhouse Gas Emissions', icon: Globe, color: 'esg-green' },
          { label: 'IFRS S2', desc: 'Climate-related Disclosures', icon: Landmark, color: 'accent-blue' },
          { label: 'ESRS E1', desc: 'Climate Change (CSRD)', icon: Shield, color: 'accent-purple' },
          { label: 'OJK PSPK', desc: 'Indonesian Regulation', icon: Database, color: 'esg-amber' },
        ].map((fw, i) => {
          const Icon = fw.icon
          return (
            <div key={i} className="glass-card p-4 animate-slide-up" style={{ animationDelay: `${i * 50}ms` }}>
              <div className={`w-9 h-9 rounded-xl bg-${fw.color}/10 border border-${fw.color}/20 flex items-center justify-center mb-3`}>
                <Icon className={`w-4 h-4 text-${fw.color}`} size={16} />
              </div>
              <div className="font-semibold text-sm text-white">{fw.label}</div>
              <div className="text-xs text-white/40 mt-0.5">{fw.desc}</div>
            </div>
          )
        })}
      </div>

      {/* Documents */}
      {loading ? (
        <div className="text-center py-16">
          <Loader2 className="w-6 h-6 text-accent-blue animate-spin mx-auto mb-3" />
          <span className="text-sm text-white/30">Loading documents from Knowledge Base...</span>
        </div>
      ) : Object.keys(grouped).length === 0 ? (
        <div className="text-center py-16">
          <div className="w-14 h-14 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center mx-auto mb-4">
            <BookOpen className="w-6 h-6 text-white/20" />
          </div>
          <p className="text-sm text-white/30">No documents found in Knowledge Base</p>
          <p className="text-xs text-white/20 mt-1">Documents will appear here once synced to OpenSearch</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {Object.entries(grouped).map(([category, files]) => {
            const config = CATEGORY_CONFIG[category] || CATEGORY_CONFIG.default
            const Icon = config.icon
            return (
              <div key={category} className="glass-card p-5 animate-slide-up">
                <div className="flex items-center gap-3 mb-4">
                  <div className={`w-9 h-9 rounded-xl bg-${config.color}/10 border border-${config.color}/20 flex items-center justify-center`}>
                    <Icon className={`w-4 h-4 text-${config.color}`} size={16} />
                  </div>
                  <div>
                    <div className="font-semibold text-sm text-white">{config.label}</div>
                    <div className="text-[10px] text-white/30">{files.length} document{files.length > 1 ? 's' : ''}</div>
                  </div>
                </div>
                <div className="space-y-2">
                  {files.map((file, i) => (
                    <div key={i} className="flex items-center justify-between py-2 px-3 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors">
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="w-3.5 h-3.5 text-white/20 flex-shrink-0" />
                        <span className="text-xs text-white/60 truncate" title={file.filename}>{file.filename}</span>
                      </div>
                      <span className="text-[10px] text-white/25 flex-shrink-0 ml-2">{file.size_kb} KB</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
