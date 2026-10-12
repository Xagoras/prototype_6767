/**
 * 任务创建向导（阶段一完整链路）：
 * 0 基本信息（名称/指南/每文档人数）→ 1 上传或粘贴 → 2 提取校正 →
 * 3 切割确认 → 4 案例信息 + 分配
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, errMsg } from '../api/client'
import ExtractionPreview from '../components/common/ExtractionPreview'
import SegmentationEditor from '../components/common/SegmentationEditor'
import UploadDropzone from '../components/common/UploadDropzone'
import type { Document, Guide, UploadResult, User } from '../types'

const STEPS = ['基本信息', '上传文档', '提取校正', '切割确认', '信息与分配']

/** 原始判决书的案例信息字段 */
const JUDGMENT_FIELDS = ['案号', '裁判法院', '法院层级', '审级', '裁判日期', '案件性质', '案由', '裁判结果类型']
/** 指导性/参考案例的案例信息字段 */
const CASE_FIELDS = ['案例类型', '案件名称', '发布时间', '入库编号', '案件类型', '相关法条', '裁判要点', '裁判要旨']

export default function TaskCreatePage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [guides, setGuides] = useState<Guide[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [taskId, setTaskId] = useState<number | null>(null)
  const [docs, setDocs] = useState<Document[]>([])
  const [currentDoc, setCurrentDoc] = useState(0)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // 步骤 0 表单
  const [name, setName] = useState('')
  const [guideId, setGuideId] = useState<number | null>(null)
  const [annotatorsPerDoc, setAnnotatorsPerDoc] = useState(2)

  // 步骤 1
  const [pasteText, setPasteText] = useState('')
  const [pasteName, setPasteName] = useState('')
  const [uploadResults, setUploadResults] = useState<string[]>([])

  // 步骤 4：每文档的案例信息与分配（key: docId）
  const [caseInfos, setCaseInfos] = useState<Record<number, Record<string, string>>>({})
  const [assignMap, setAssignMap] = useState<Record<number, Record<string, Set<number>>>>({})

  useEffect(() => {
    api.get<Guide[]>('/guides').then((r) => setGuides(r.data)).catch((e) => setError(errMsg(e)))
    api.get<User[]>('/users').then((r) => setUsers(r.data)).catch(() => {})
  }, [])

  const createTask = async () => {
    setBusy(true)
    setError('')
    try {
      const r = await api.post('/tasks', { name, guide_id: guideId, annotators_per_doc: annotatorsPerDoc })
      setTaskId(r.data.id)
      setStep(1)
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }

  const refreshDoc = async (docId: number) => {
    const r = await api.get<Document>(`/documents/${docId}`)
    setDocs((prev) => prev.map((d) => (d.id === docId ? r.data : d)))
    return r.data
  }

  const handleUpload = async (files: File[]) => {
    if (!taskId) return
    setBusy(true)
    setError('')
    try {
      const form = new FormData()
      files.forEach((f) => form.append('files', f))
      const r = await api.post(`/tasks/${taskId}/documents/upload`, form)
      const results: UploadResult[] = r.data
      const msgs: string[] = []
      for (const res of results) {
        if (!res.ok || !res.document_id) {
          msgs.push(`✕ ${res.filename}: ${res.error}`)
        } else {
          msgs.push(`✓ ${res.filename}（${res.extraction_method === 'auto' ? '自动提取成功' : '需人工校正'}）`)
          const doc = await api.get<Document>(`/documents/${res.document_id}`)
          setDocs((prev) => [...prev, doc.data])
        }
      }
      setUploadResults(msgs)
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }

  const handlePaste = async () => {
    if (!taskId || !pasteText.trim() || !pasteName.trim()) return
    setBusy(true)
    setError('')
    try {
      const r = await api.post<Document>(`/tasks/${taskId}/documents/text`,
        { name: pasteName, text: pasteText, doc_type: 'judgment' })
      setDocs((prev) => [...prev, r.data])
      setUploadResults((prev) => [...prev, `✓ 已创建文本文档「${pasteName}」`])
      setPasteText(''); setPasteName('')
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }

  const saveReasoning = async (docId: number, start: number, end: number) => {
    await api.put(`/documents/${docId}/reasoning`, { start, end })
    await refreshDoc(docId)
  }

  const saveSegments = async (docId: number, segments: { start: number; end: number; text: string }[]) => {
    await api.put(`/documents/${docId}/segments`, { segments })
    await refreshDoc(docId)
  }

  const activeDoc = docs[currentDoc]

  const saveInfoAndAssign = async () => {
    if (!taskId) return
    setBusy(true)
    setError('')
    try {
      for (const doc of docs) {
        const info = caseInfos[doc.id]
        if (info && Object.keys(info).length > 0) {
          await api.patch(`/documents/${doc.id}`, { case_info: info })
        }
      }
      // 分配：收集所有文档的标注员/裁定者/标准答案标注者
      const annotatorIds = new Set<number>()
      const arbiterIds = new Set<number>()
      const referenceIds = new Set<number>()
      for (const doc of docs) {
        const m = assignMap[doc.id] || {}
        for (const role of ['annotator', 'arbiter', 'reference'] as const) {
          for (const uid of m[role] || []) {
            if (role === 'annotator') annotatorIds.add(Number(uid))
            if (role === 'arbiter') arbiterIds.add(Number(uid))
            if (role === 'reference') referenceIds.add(Number(uid))
          }
        }
      }
      const docIds = docs.map((d) => d.id)
      // 全局一致的分配（原型简化：所有文档同一批标注员/裁定者；reference 从各文档选择）
      if (annotatorIds.size > 0) {
        await api.post(`/tasks/${taskId}/assignments`, {
          document_ids: docIds, user_ids: [...annotatorIds], roles: ['annotator'],
        })
      }
      if (arbiterIds.size > 0) {
        await api.post(`/tasks/${taskId}/assignments`, {
          document_ids: docIds, user_ids: [...arbiterIds], roles: ['arbiter'],
        })
      }
      if (referenceIds.size > 0) {
        await api.post(`/tasks/${taskId}/assignments`, {
          document_ids: docIds, user_ids: [...referenceIds], roles: ['reference'],
        })
      }
      navigate(`/tasks/${taskId}`)
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }

  const toggleAssign = (docId: number, role: string, uid: number) => {
    setAssignMap((prev) => {
      const m = prev[docId] || {}
      const set = new Set(m[role] || [])
      if (set.has(uid)) set.delete(uid)
      else set.add(uid)
      return { ...prev, [docId]: { ...m, [role]: set } }
    })
  }

  const setInfo = (docId: number, field: string, value: string) => {
    setCaseInfos((prev) => ({ ...prev, [docId]: { ...(prev[docId] || {}), [field]: value } }))
  }

  const fields = useMemo(() => {
    if (!activeDoc) return []
    return activeDoc.doc_type === 'judgment' ? JUDGMENT_FIELDS : CASE_FIELDS
  }, [activeDoc])

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <a href="/">法律论证标注系统</a> · 创建任务
        </div>
        <a href="/" className="link-btn">返回工作台</a>
      </header>

      <main className="page-body narrow">
        <div className="wizard-steps">
          {STEPS.map((s, i) => (
            <span key={s} className={`wizard-step${i === step ? ' active' : ''}${i < step ? ' done' : ''}`}>
              {i + 1}. {s}
            </span>
          ))}
        </div>

        {step === 0 && (
          <div className="wizard-panel">
            <div className="form-row">
              <label>任务名称</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="如：2026 秋 法律论证标注任务" />
            </div>
            <div className="form-row">
              <label>标注指南（任务创建后不可更换）</label>
              <select value={guideId ?? ''} onChange={(e) => setGuideId(Number(e.target.value))}>
                <option value="">请选择</option>
                {guides.map((g) => (
                  <option key={g.id} value={g.id}>{g.version} — {g.name || '未命名'}{g.is_active ? '（激活）' : ''}</option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <label>每份文档的独立标注人数（双人独立标注默认 2）</label>
              <input type="number" min={1} max={10} value={annotatorsPerDoc}
                onChange={(e) => setAnnotatorsPerDoc(Number(e.target.value))} />
            </div>
            <button className="primary" disabled={busy || !name.trim() || !guideId} onClick={createTask}>
              创建任务并继续
            </button>
          </div>
        )}

        {step === 1 && (
          <div className="wizard-panel">
            <h2>上传裁判文书</h2>
            <UploadDropzone multiple onFiles={handleUpload} hint="批量上传 PDF / Word / 纯文本（可多选）" />
            <h2 style={{ marginTop: 20 }}>或粘贴文本</h2>
            <div className="form-row">
              <label>文档名称</label>
              <input value={pasteName} onChange={(e) => setPasteName(e.target.value)} placeholder="如：文书一（劳务合同纠纷）" />
            </div>
            <div className="form-row">
              <textarea rows={8} value={pasteText} onChange={(e) => setPasteText(e.target.value)}
                placeholder="粘贴裁判文书全文…" />
            </div>
            <button className="link-btn" disabled={busy || !pasteText.trim() || !pasteName.trim()} onClick={handlePaste}>
              添加文本文档
            </button>
            {uploadResults.length > 0 && (
              <div className="upload-results">{uploadResults.map((m, i) => <div key={i}>{m}</div>)}</div>
            )}
            <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
              <button className="link-btn" onClick={() => setStep(0)}>上一步</button>
              <button className="primary" disabled={docs.length === 0} onClick={() => setStep(2)}>
                下一步：提取校正（{docs.length} 篇）
              </button>
            </div>
          </div>
        )}

        {step === 2 && activeDoc && (
          <div className="wizard-panel">
            <h2>提取校正 — {activeDoc.name}</h2>
            <div className="doc-switch">
              {docs.map((d, i) => (
                <button key={d.id} className={`link-btn${i === currentDoc ? ' active' : ''}`} onClick={() => setCurrentDoc(i)}>
                  {d.name}
                </button>
              ))}
            </div>
            {activeDoc.extraction_method === 'manual_required' && (
              <div className="warn-box">未自动识别到"裁判理由"，请手动设置提取范围</div>
            )}
            <ExtractionPreview
              text={activeDoc.original_text}
              start={activeDoc.reasoning_start ?? 0}
              end={activeDoc.reasoning_end ?? activeDoc.original_text.length}
              method={activeDoc.extraction_method}
              onSave={(s, e) => saveReasoning(activeDoc.id, s, e)}
            />
            <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
              <button className="link-btn" onClick={() => setStep(1)}>上一步</button>
              <button className="primary" onClick={() => setStep(3)}>下一步：切割确认</button>
            </div>
          </div>
        )}

        {step === 3 && activeDoc && (
          <div className="wizard-panel">
            <h2>切割确认 — {activeDoc.name}</h2>
            <div className="doc-switch">
              {docs.map((d, i) => (
                <button key={d.id} className={`link-btn${i === currentDoc ? ' active' : ''}`} onClick={() => setCurrentDoc(i)}>
                  {d.name}
                </button>
              ))}
            </div>
            <SegmentationEditor
              segments={activeDoc.base_segments}
              reasoningText={activeDoc.reasoning_text}
              onSave={(segs) => saveSegments(activeDoc.id, segs)}
            />
            <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
              <button className="link-btn" onClick={() => setStep(2)}>上一步</button>
              <button className="primary" onClick={() => setStep(4)}>下一步：信息与分配</button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="wizard-panel">
            <h2>案例信息与任务分配</h2>
            <div className="doc-switch">
              {docs.map((d, i) => (
                <button key={d.id} className={`link-btn${i === currentDoc ? ' active' : ''}`} onClick={() => setCurrentDoc(i)}>
                  {d.name}
                </button>
              ))}
            </div>
            {activeDoc && (
              <>
                <h3>案例信息（{activeDoc.doc_type === 'judgment' ? '原始判决书' : '指导性/参考案例'}）</h3>
                <div className="info-grid">
                  {fields.map((f) => (
                    <div className="form-row" key={f}>
                      <label>{f}</label>
                      <input value={caseInfos[activeDoc.id]?.[f] || ''}
                        onChange={(e) => setInfo(activeDoc.id, f, e.target.value)} />
                    </div>
                  ))}
                </div>
                <h3>分配（案例 ↔ 用户 多对多）</h3>
                <div className="assign-matrix">
                  <div className="assign-col">
                    <b>标注员</b>
                    {users.filter((u) => !u.is_admin).map((u) => (
                      <label key={u.id} className="assign-item">
                        <input type="checkbox"
                          checked={assignMap[activeDoc.id]?.['annotator']?.has(u.id) || false}
                          onChange={() => toggleAssign(activeDoc.id, 'annotator', u.id)} />
                        {u.display_name || u.username}
                      </label>
                    ))}
                  </div>
                  <div className="assign-col">
                    <b>裁定者</b>
                    {users.filter((u) => !u.is_admin).map((u) => (
                      <label key={u.id} className="assign-item">
                        <input type="checkbox"
                          checked={assignMap[activeDoc.id]?.['arbiter']?.has(u.id) || false}
                          onChange={() => toggleAssign(activeDoc.id, 'arbiter', u.id)} />
                        {u.display_name || u.username}
                      </label>
                    ))}
                  </div>
                  <div className="assign-col">
                    <b>标准答案标注者</b>
                    {users.filter((u) => !u.is_admin).map((u) => (
                      <label key={u.id} className="assign-item">
                        <input type="checkbox"
                          checked={assignMap[activeDoc.id]?.['reference']?.has(u.id) || false}
                          onChange={() => toggleAssign(activeDoc.id, 'reference', u.id)} />
                        {u.display_name || u.username}
                      </label>
                    ))}
                  </div>
                </div>
              </>
            )}
            {error && <div className="error">{error}</div>}
            <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
              <button className="link-btn" onClick={() => setStep(3)}>上一步</button>
              <button className="primary" disabled={busy} onClick={saveInfoAndAssign}>
                {busy ? '保存中…' : '完成：保存信息并分配'}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
