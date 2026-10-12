/**
 * 标注指南管理页（UC-01 从文件导入标注指南）。
 * 三步：上传 → 预览确认（版本/正文/taxonomy 校对）→ 保存。
 */
import { useEffect, useState } from 'react'
import { api, errMsg } from '../api/client'
import UploadDropzone from '../components/common/UploadDropzone'
import type { Guide, GuidePreview, Taxonomy } from '../types'

type Step = 'upload' | 'preview'

export default function GuideManagePage() {
  const [step, setStep] = useState<Step>('upload')
  const [guides, setGuides] = useState<Guide[]>([])
  const [preview, setPreview] = useState<GuidePreview | null>(null)
  const [version, setVersion] = useState('')
  const [name, setName] = useState('')
  const [taxonomyText, setTaxonomyText] = useState('')
  const [taxonomyError, setTaxonomyError] = useState('')
  const [duplicateWarning, setDuplicateWarning] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const loadGuides = () => {
    api.get<Guide[]>('/guides').then((r) => setGuides(r.data)).catch((e) => setError(errMsg(e)))
  }
  useEffect(loadGuides, [])

  const onUpload = async (files: File[]) => {
    setError('')
    setBusy(true)
    try {
      const form = new FormData()
      form.append('file', files[0])
      const res = await api.post<GuidePreview>('/guides/import', form)
      const p = res.data
      setPreview(p)
      setVersion(p.version)
      setName(p.name)
      setTaxonomyText(JSON.stringify(p.taxonomy, null, 2))
      setDuplicateWarning('')
      setStep('preview')
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }

  const parseTaxonomy = (): Taxonomy | null => {
    try {
      const parsed = JSON.parse(taxonomyText) as Taxonomy
      if (!Array.isArray(parsed.elements) || !Array.isArray(parsed.relations)) {
        setTaxonomyError('taxonomy 需包含 elements 与 relations 两个数组')
        return null
      }
      setTaxonomyError('')
      return parsed
    } catch {
      setTaxonomyError('JSON 格式错误，请检查')
      return null
    }
  }

  const save = async (overwrite = false) => {
    if (!preview) return
    const tax = parseTaxonomy()
    if (!tax) return
    if (!version.trim()) { setError('请填写指南版本号'); return }
    setBusy(true)
    setError('')
    try {
      await api.post('/guides', {
        version: version.trim(),
        name,
        source_filename: preview.source_filename,
        content_text: preview.content_text,
        taxonomy: tax,
        overwrite,
      })
      setStep('upload')
      setPreview(null)
      loadGuides()
    } catch (e) {
      // 409：同版本已存在，提示用户选择覆盖/另存/取消（UC-01 A3）
      if ((e as { response?: { status?: number } }).response?.status === 409) {
        setDuplicateWarning(errMsg(e))
      } else {
        setError(errMsg(e))
      }
    } finally {
      setBusy(false)
    }
  }

  const activate = async (id: number) => {
    await api.post(`/guides/${id}/activate`).then(loadGuides)
  }

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <a href="/">法律论证标注系统</a> · 标注指南
        </div>
        <a href="/" className="link-btn">返回工作台</a>
      </header>

      <main className="page-body narrow">
        {step === 'upload' && (
          <>
            <h2>导入标注指南</h2>
            <UploadDropzone onFiles={onUpload} hint="选择或拖拽指南文件（PDF / Word / 纯文本）" />
            {busy && <div className="empty-hint">正在解析文件…</div>}
            {error && <div className="error">{error}</div>}

            <h2 style={{ marginTop: 24 }}>已有指南版本</h2>
            {guides.length === 0 && <div className="empty-hint">暂无指南，请先导入</div>}
            <div className="card-grid">
              {guides.map((g) => (
                <div className="task-card" key={g.id}>
                  <div className="task-card-title">
                    {g.name || '未命名指南'} <span className={`status-badge status-${g.is_active ? 'ANNOTATING' : 'CREATED'}`}>{g.is_active ? '激活中' : `v${g.version}`}</span>
                  </div>
                  <div className="task-card-meta">
                    <span>版本 {g.version}</span>
                    <span>{g.created_at.slice(0, 10)}</span>
                  </div>
                  <div style={{ marginTop: 10 }}>
                    {!g.is_active && (
                      <button className="link-btn" onClick={() => activate(g.id)}>设为激活版本</button>
                    )}
                    <button className="link-btn" style={{ marginLeft: 8 }}
                      onClick={() => {
                        setPreview({
                          version: g.version, name: g.name, source_filename: g.source_filename,
                          text_preview: g.content_text.slice(0, 2000), content_text: g.content_text,
                          taxonomy: g.taxonomy, duplicate_warning: null,
                        })
                        setVersion(g.version); setName(g.name)
                        setTaxonomyText(JSON.stringify(g.taxonomy, null, 2))
                        setDuplicateWarning('')
                        setStep('preview')
                      }}>
                      查看
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {step === 'preview' && preview && (
          <>
            <h2>导入预览与确认</h2>
            <div className="form-row">
              <label>指南版本（导出数据将引用该版本号）</label>
              <input value={version} onChange={(e) => setVersion(e.target.value)} placeholder="如 v1.1" />
            </div>
            <div className="form-row">
              <label>指南名称</label>
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </div>

            <div className="form-row">
              <label>标签体系 taxonomy（JSON，可校对修改；标注界面的标签按钮由此生成）</label>
              <textarea
                rows={12}
                value={taxonomyText}
                onChange={(e) => setTaxonomyText(e.target.value)}
                style={{ fontFamily: 'Consolas, monospace', fontSize: 12 }}
              />
              {taxonomyError && <div className="error">{taxonomyError}</div>}
            </div>

            <div className="form-row">
              <label>指南正文预览（前 2000 字）</label>
              <div className="text-preview">{preview.text_preview}</div>
            </div>

            {duplicateWarning && (
              <div className="warn-box">
                <div>{duplicateWarning}</div>
                <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
                  <button className="primary" onClick={() => save(true)} disabled={busy}>覆盖原版本</button>
                  <button className="link-btn" onClick={() => { setDuplicateWarning(''); setVersion(version + '.1') }}>另存为新版本（自动加 .1）</button>
                  <button className="link-btn" onClick={() => setDuplicateWarning('')}>取消</button>
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
              <button className="primary" onClick={() => save(false)} disabled={busy}>确认保存</button>
              <button className="link-btn" onClick={() => { setStep('upload'); setPreview(null) }}>返回</button>
            </div>
            {error && <div className="error" style={{ marginTop: 8 }}>{error}</div>}
          </>
        )}
      </main>
    </div>
  )
}
