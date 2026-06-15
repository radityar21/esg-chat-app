import { useState, useEffect } from 'react'
import { getDocuments } from '../api'
import { useTheme } from '../ThemeContext'
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
  const { isDark } = useTheme()
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
        <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-800'}`}>Reference Library</h1>
        <p className={`text-sm mt-1 ${isDark ? 'text-white/40' : 'text-gray-500'}`}>Framework documents indexed in Knowledge Base (OpenSearch)</p>
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
              <div className={`font-semibold text-sm ${isDark ? 'text-white' : 'text-gray-800'}`}>{fw.label}</div>
              <div className={`text-xs mt-0.5 ${isDark ? 'text-white/40' : 'text-gray-500'}`}>{fw.desc}</div>
            </div>
          )
        })}
      </div>

      {/* Documents */}
      {loading ? (
        <div className="text-center py-16">
          <Loader2 className="w-6 h-6 text-accent-blue animate-spin mx-auto mb-3" />
          <span className={`text-sm ${isDark ? 'text-white/30' : 'text-gray-400'}`}>Loading documents from Knowledge Base...</span>
        </div>
      ) : Object.keys(grouped).length === 0 ? (
        <div className="text-center py-16">
          <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4 ${
            isDark ? 'bg-white/[0.03] border border-white/[0.08]' : 'bg-gray-50 border border-gray-200'
          }`}>
            <BookOpen className={`w-6 h-6 ${isDark ? 'text-white/20' : 'text-gray-300'}`} />
          </div>
          <p className={`text-sm ${isDark ? 'text-white/30' : 'text-gray-400'}`}>No documents found in Knowledge Base</p>
          <p className={`text-xs mt-1 ${isDark ? 'text-white/20' : 'text-gray-300'}`}>Documents will appear here once synced to OpenSearch</p>
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
                    <div className={`font-semibold text-sm ${isDark ? 'text-white' : 'text-gray-800'}`}>{config.label}</div>
                    <div className={`text-[10px] ${isDark ? 'text-white/30' : 'text-gray-400'}`}>{files.length} document{files.length > 1 ? 's' : ''}</div>
                  </div>
                </div>
                <div className="space-y-2">
                  {files.map((file, i) => (
                    <div key={i} className={`flex items-center justify-between py-2 px-3 rounded-lg transition-colors ${
                      isDark ? 'bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04]' : 'bg-gray-50 border border-gray-100 hover:bg-gray-100'
                    }`}>
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className={`w-3.5 h-3.5 flex-shrink-0 ${isDark ? 'text-white/20' : 'text-gray-400'}`} />
                        <span className={`text-xs truncate ${isDark ? 'text-white/60' : 'text-gray-600'}`} title={file.filename}>{file.filename}</span>
                      </div>
                      <span className={`text-[10px] flex-shrink-0 ml-2 ${isDark ? 'text-white/25' : 'text-gray-300'}`}>{file.size_kb} KB</span>
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
