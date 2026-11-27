import { useEffect, useMemo, useState } from 'react'
import { Play, Save, Trash2, Loader2, FileText, Bot, CheckCircle2, History, Upload, Pencil, X, AlertTriangle, RotateCcw } from 'lucide-react'
import { PageHeader, Panel, Pill, Button, Tabs } from '../components/ui'
import RunProgress from '../components/RunProgress'
import { api, platformEnabled, useLive, waitAgent } from '../lib/platform'
import { authEnabled, currentUser } from '../lib/auth'

// Report Builder: choose framework, year, language and sections, save the configuration, generate through the
// AgentCore orchestrator, and (administrators) edit the versioned section templates the generator uses.
const RUN_KEY = 'esg.builder.run.v1' // the running generation survives a page change
const loadRun = () => { try { return JSON.parse(sessionStorage.getItem(RUN_KEY) || 'null') } catch { return null } }
const saveRun = (r) => { if (r) sessionStorage.setItem(RUN_KEY, JSON.stringify(r)); else sessionStorage.removeItem(RUN_KEY) }
const when = (s) => (s ? new Date(s).toLocaleString() : '')

export default function ReportBuilder() {
  if (!platformEnabled) {
    return (
      <div className="flex-1 overflow-y-auto p-10 animate-fade-in">
        <PageHeader eyebrow="Workspace · Report Builder" title="Configure a report before it is generated" image="/img/forest-aerial-2.jpg" />
        <Panel><p className="text-sm text-white/60 py-4">The Report Builder needs the platform API (VITE_PLATFORM_API_URL). In demo mode, ask the assistant to generate a report instead.</p></Panel>
      </div>
    )
  }
  return <Builder />
}

function Builder() {
  const isAdmin = !authEnabled || Boolean(currentUser()?.isAdmin) // without sign-in (local) the API decides
  const cat = useLive('/reports/catalog')
  const cfgs = useLive('/reports/configs')
  const [framework, setFramework] = useState('GRI_305')
  const [year, setYear] = useState(2024)
  const [language, setLanguage] = useState('en')
  const [sections, setSections] = useState(null) // null = all sections of the framework
  const [configId, setConfigId] = useState('')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState(null)
  const [run, setRun] = useState(loadRun) // {job_id} while queued, then {execution_id}
  const [templateKey, setTemplateKey] = useState(null)

  const fw = useMemo(() => cat.data?.frameworks?.find((f) => f.id === framework), [cat.data, framework])
  const chosen = sections ?? (fw?.sections.map((s) => s.id) || [])
  useEffect(() => { if (cat.data?.default_language) setLanguage((l) => l || cat.data.default_language) }, [cat.data])
  useEffect(() => { if (fw && !templateKey) setTemplateKey(fw.sections[0].id) }, [fw, templateKey])

  // resume a queued generation after a page change
  useEffect(() => {
    if (!run?.job_id || run.execution_id) return undefined
    let stop = false
    waitAgent(run.job_id, { maxWaitMs: 180000 })
      .then((r) => {
        if (stop) return
        if (r?.started && r.execution_id) { const n = { execution_id: r.execution_id, label: run.label }; setRun(n); saveRun(n) }
        else { setRun(null); saveRun(null); setMsg({ tone: 'red', text: r?.error || 'The orchestrator did not start the run.' }) }
      })
      .catch((e) => { if (!stop) { setRun(null); saveRun(null); setMsg({ tone: 'red', text: e.message }) } })
    return () => { stop = true }
  }, [run])

  const pickFramework = (id) => { setFramework(id); setSections(null); setConfigId(''); setTemplateKey(null) }
  const toggle = (id) => {
    const set = new Set(chosen)
    if (set.has(id)) set.delete(id); else set.add(id)
    setSections(fw.sections.map((s) => s.id).filter((s) => set.has(s)))
    setConfigId('')
  }
  const applyConfig = (c) => {
    setFramework(c.framework); setSections(c.sections); setLanguage(c.language); setConfigId(c.id); setName(c.name); setTemplateKey(c.sections[0])
  }

  async function generate() {
    setBusy('generate'); setMsg(null)
    try {
      const all = fw && chosen.length === fw.sections.length
      const body = configId ? { config_id: configId, reporting_year: year } : { framework, reporting_year: year, language, sections: all ? null : chosen }
      const job = await api('/reports/generate', { method: 'POST', body })
      const r = { job_id: job.job_id, label: `${fw?.label || framework} · ${year} · ${language.toUpperCase()}` }
      setRun(r); saveRun(r)
    } catch (e) { setMsg({ tone: 'red', text: e.message }) }
    setBusy('')
  }
  async function saveConfig() {
    setBusy('save'); setMsg(null)
    try {
      const c = await api('/reports/configs', { method: 'POST', body: { id: configId || undefined, name, framework, language, sections: chosen } })
      setConfigId(c.id); cfgs.reload(); setMsg({ tone: 'green', text: `Saved "${c.name}".` })
    } catch (e) { setMsg({ tone: 'red', text: e.message }) }
    setBusy('')
  }
  async function deleteConfig(c) {
    if (!window.confirm(`Delete the configuration "${c.name}"?`)) return
    try { await api(`/reports/configs/${c.id}/delete`, { method: 'POST', body: {} }); if (configId === c.id) setConfigId(''); cfgs.reload() } catch (e) { setMsg({ tone: 'red', text: e.message }) }
  }

  const configs = cfgs.data?.configs || []
  return (
    <div className="flex-1 overflow-y-auto p-10 animate-fade-in">
      <PageHeader eyebrow="Workspace · Report Builder" title="Configure the report, then let the agent build it"
        desc="Pick the framework, year, language and sections. The AgentCore orchestrator runs the pipeline and repairs failed sections. Section templates are versioned; administrators approve every change, including the ones the AI proposes."
        image="/img/forest-aerial-2.jpg" pos="center 40%" />

      {cat.status === 'error' && <Panel className="mb-5"><p className="text-sm text-esg-red py-3">Could not load the catalog: {cat.error}</p></Panel>}

      <div className="grid grid-cols-12 gap-5">
        <div className="col-span-5 space-y-5">
          <Panel title="Configuration" subtitle={cat.data?.note}>
            {cat.status === 'loading' ? <Loader2 className="w-5 h-5 animate-spin text-accent-blue" /> : fw && (
              <div className="space-y-4">
                <label className="block">
                  <span className="eyebrow">Framework</span>
                  <select value={framework} onChange={(e) => pickFramework(e.target.value)} className="mt-1.5 w-full rounded-xl bg-white/[0.05] border border-white/10 px-3 py-2 text-sm text-white">
                    {cat.data.frameworks.map((f) => <option key={f.id} value={f.id} className="bg-dark-900">{f.label}</option>)}
                  </select>
                </label>
                <div className="flex gap-6">
                  <div><div className="eyebrow mb-1.5">Year</div><Tabs value={year} onChange={setYear} tabs={(cat.data.years || [2023, 2024]).map((y) => ({ id: y, label: String(y) }))} /></div>
                  <div><div className="eyebrow mb-1.5">Language</div><Tabs value={language} onChange={(l) => { setLanguage(l); setConfigId('') }} tabs={cat.data.languages.map((l) => ({ id: l.id, label: l.label }))} /></div>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1.5"><span className="eyebrow">Sections · {chosen.length}/{fw.sections.length}</span>
                    <button className="text-[11px] text-accent-teal hover:underline" onClick={() => { setSections(null); setConfigId('') }}>Select all</button></div>
                  <ul className="space-y-1">
                    {fw.sections.map((s) => (
                      <li key={s.id} className={`flex items-start gap-2.5 rounded-lg px-2.5 py-2 cursor-pointer ${templateKey === s.id ? 'bg-accent-blue/10' : 'hover:bg-white/[0.03]'}`} onClick={() => setTemplateKey(s.id)}>
                        <input type="checkbox" checked={chosen.includes(s.id)} onChange={() => toggle(s.id)} onClick={(e) => e.stopPropagation()} className="mt-0.5 accent-accent-teal" />
                        <div className="min-w-0"><div className="text-sm text-white/85">{s.label}</div><div className="text-[11px] text-white/40">{s.desc}</div></div>
                      </li>
                    ))}
                  </ul>
                </div>
                {language === 'id' && <p className="text-[11px] text-esg-amber/80">Bahasa Indonesia: figures keep the source format so the validator can check them; the prohibited-phrase rules only cover English.</p>}
                {isAdmin && (
                  <div className="flex gap-2">
                    <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Configuration name" className="flex-1 rounded-xl bg-white/[0.05] border border-white/10 px-3 py-2 text-sm text-white" />
                    <Button variant="ghost" icon={Save} onClick={saveConfig} disabled={!name.trim() || busy === 'save'}>{configId ? 'Update' : 'Save'}</Button>
                  </div>
                )}
                <Button icon={busy === 'generate' ? Loader2 : Play} onClick={generate} disabled={!chosen.length || busy === 'generate' || Boolean(run && !run.execution_id)} className="w-full justify-center">Generate report</Button>
                {msg && <p className={`text-xs ${msg.tone === 'red' ? 'text-esg-red' : 'text-esg-green'}`}>{msg.text}</p>}
              </div>
            )}
          </Panel>

          {run && (
            <Panel title="Generation" subtitle={run.label} right={run.execution_id && <button onClick={() => { setRun(null); saveRun(null) }} className="text-white/40 hover:text-white"><X size={14} /></button>}>
              {run.execution_id ? <RunProgress executionId={run.execution_id} /> : <div className="text-xs text-white/50 flex items-center gap-2"><Loader2 size={12} className="animate-spin" />The orchestrator is starting the run…</div>}
            </Panel>
          )}

          <Panel title="Saved configurations" subtitle={isAdmin ? 'Reusable report setups' : 'Set up by administrators'}>
            {cfgs.status === 'loading' ? <Loader2 className="w-4 h-4 animate-spin text-accent-blue" /> : configs.length === 0 ? <p className="text-xs text-white/40">None yet.</p> : (
              <ul className="space-y-1.5">
                {configs.map((c) => (
                  <li key={c.id} className={`flex items-center gap-3 rounded-lg px-3 py-2 ${configId === c.id ? 'bg-accent-teal/10' : 'bg-white/[0.02]'}`}>
                    <button className="flex-1 text-left min-w-0" onClick={() => applyConfig(c)}>
                      <div className="text-sm text-white/85 truncate">{c.name}</div>
                      <div className="text-[11px] text-white/40">{c.framework} · {c.language.toUpperCase()} · {c.sections.length} sections · {when(c.updated_at)}</div>
                    </button>
                    {isAdmin && <button onClick={() => deleteConfig(c)} className="text-white/30 hover:text-esg-red"><Trash2 size={13} /></button>}
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>

        <div className="col-span-7">
          {templateKey && <TemplatePanel key={templateKey} templateKey={templateKey} isAdmin={isAdmin} />}
        </div>
      </div>
    </div>
  )
}

const STATUS_TONE = { published: 'green', draft: 'amber', archived: 'slate' }

function TemplatePanel({ templateKey, isAdmin }) {
  const t = useLive(`/reports/templates/${templateKey}`)
  const [sel, setSel] = useState(null)
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState('')
  const [note, setNote] = useState('')
  const [problems, setProblems] = useState([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const versions = t.data?.versions || []
  const current = versions.find((v) => v.version === (sel || t.data?.published)) || versions[0]

  async function saveDraft() {
    setBusy(true); setProblems([]); setMsg('')
    try {
      const r = await api(`/reports/templates/${templateKey}/draft`, { method: 'POST', body: { text, note } })
      if (!r.saved) setProblems(r.problems || ['Not saved'])
      else { setEditing(false); setSel(r.version); setMsg(`Draft ${r.version} saved. Publish it to use it in reports.`); t.reload() }
    } catch (e) { setProblems([e.message]) }
    setBusy(false)
  }
  async function publish(version) {
    if (!window.confirm(`Publish ${version}? Reports generated from now on use it.`)) return
    setBusy(true); setMsg('')
    try { const r = await api(`/reports/templates/${templateKey}/publish`, { method: 'POST', body: { version } }); setMsg(r.note || `Published ${version}.`); setSel(null); t.reload() } catch (e) { setMsg(e.message) }
    setBusy(false)
  }

  return (
    <Panel title={<span className="flex items-center gap-2"><FileText size={15} className="text-accent-blue" />Section template · {t.data?.label || templateKey}</span>}
      subtitle={t.data ? `${t.data.file} · live version ${t.data.published}` : 'The instructions the section generator follows'}
      right={isAdmin && current && !editing && <Button variant="ghost" icon={Pencil} onClick={() => { setText(current.text); setNote(''); setProblems([]); setEditing(true) }}>Edit</Button>}>
      {t.status === 'loading' && <Loader2 className="w-5 h-5 animate-spin text-accent-blue" />}
      {t.status === 'error' && <p className="text-sm text-esg-red">Could not load the template: {t.error}</p>}
      {t.data && (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-4">
            <div className="eyebrow mb-2 flex items-center gap-1.5"><History size={12} />Versions</div>
            <ul className="space-y-1.5 max-h-[520px] overflow-y-auto pr-1">
              {versions.map((v) => (
                <li key={v.version}>
                  <button onClick={() => { setSel(v.version); setEditing(false) }} className={`w-full text-left rounded-lg px-3 py-2 ${current?.version === v.version ? 'bg-accent-blue/10 border border-accent-blue/25' : 'bg-white/[0.02] border border-transparent hover:bg-white/[0.04]'}`}>
                    <div className="flex items-center gap-2"><span className="text-sm font-semibold text-white">{v.version}</span><Pill tone={STATUS_TONE[v.status]}>{v.status}</Pill>
                      {v.author === 'agent' && <Pill tone="purple"><Bot size={10} />AI proposal</Pill>}</div>
                    <div className="text-[10px] text-white/40 mt-1">{v.author === 'agent' ? 'AgentCore agent' : v.author} · {when(v.created_at)}</div>
                    {v.note && <div className="text-[11px] text-white/55 mt-1 line-clamp-3">{v.note}</div>}
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div className="col-span-8">
            {t.data.placeholders?.length > 0 && <div className="text-[10px] text-white/40 mb-2">Data placeholders (must stay): <span className="font-mono text-white/60">{t.data.placeholders.join(' ')}</span></div>}
            {editing ? (
              <div className="space-y-2">
                <textarea value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} className="w-full h-[420px] rounded-xl bg-black/30 border border-white/10 p-3 text-xs font-mono text-white/85 leading-relaxed" />
                <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="What changed and why (shown in the history)" className="w-full rounded-xl bg-white/[0.05] border border-white/10 px-3 py-2 text-sm text-white" />
                {problems.length > 0 && <ul className="text-xs text-esg-red space-y-1">{problems.map((p) => <li key={p} className="flex gap-1.5"><AlertTriangle size={12} className="mt-0.5 shrink-0" />{p}</li>)}</ul>}
                <div className="flex gap-2"><Button icon={Save} onClick={saveDraft} disabled={busy || !note.trim()}>Save as draft</Button><Button variant="ghost" onClick={() => setEditing(false)}>Cancel</Button></div>
              </div>
            ) : current && (
              <>
                <pre className="h-[420px] overflow-y-auto whitespace-pre-wrap rounded-xl bg-black/30 border border-white/[0.06] p-3 text-xs font-mono text-white/75 leading-relaxed">{current.text}</pre>
                {isAdmin && current.status !== 'published' && (
                  <div className="mt-2"><Button icon={current.status === 'draft' ? Upload : RotateCcw} onClick={() => publish(current.version)} disabled={busy}>{current.status === 'draft' ? `Publish ${current.version}` : `Restore ${current.version}`}</Button></div>
                )}
                {current.status === 'published' && <div className="mt-2 text-[11px] text-esg-green flex items-center gap-1.5"><CheckCircle2 size={12} />Live: the generator uses this version.</div>}
                {!isAdmin && current.status === 'draft' && <div className="mt-2 text-[11px] text-white/40">Waiting for an administrator to publish.</div>}
              </>
            )}
            {msg && <p className="text-xs text-accent-teal mt-2">{msg}</p>}
          </div>
        </div>
      )}
    </Panel>
  )
}

