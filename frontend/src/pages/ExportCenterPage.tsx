/**
 * 导出中心（阶段四）：批量导出入口 + 导出记录 + 锁定状态横幅。
 * JSON/Excel 后端生成；PNG/SVG/JPG 在标注页图示区导出。
 */
import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, errMsg, errMsgFromBlob } from '../api/client'
import type { Document, ExportRecord } from '../types'

export default function ExportCenterPage() {
  const { taskId } = useParams()
  const [searchParams] = useSearchParams()
  const focusDocId = searchParams.get('doc')
  const [docs, setDocs] = useState<Document[]>([])
  const [records, setRecords] = useState<Record<number, ExportRecord[]>>({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [customName, setCustomName] = useState('')

  useEffect(() => {
    if (!taskId) return
    api.get<Document[]>(`/tasks/${taskId}/documents`).then((r) => {
      setDocs(r.data)
      // 加载每个文档的导出记录
      for (const d of r.data) {
        api.get<ExportRecord[]>(`/documents/${d.id}/exports`)
          .then((rr) => setRecords((prev) => ({ ...prev, [d.id]: rr.data })))
          .catch(() => {})
      }
    }).catch((e) => setError(errMsg(e)))
  }, [taskId])

  /** 下载文件（axios blob） */
  const download = async (docId: number, format: 'json' | 'excel') => {
    setBusy(true)
    setError('')
    try {
      const doc = docs.find((d) => d.id === docId)
      const name = customName || `${doc?.name || 'document'}_最终版`
      const res = await api.post(`/documents/${docId}/export?format=${format}&filename=${encodeURIComponent(name)}`,
        null, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${name}.${format === 'excel' ? 'xlsx' : 'json'}`
      a.click()
      URL.revokeObjectURL(url)
      // 刷新记录与文档状态
      const [rr, dd] = await Promise.all([
        api.get<ExportRecord[]>(`/documents/${docId}/exports`),
        api.get<Document>(`/documents/${docId}`),
      ])
      setRecords((prev) => ({ ...prev, [docId]: rr.data }))
      setDocs((prev) => prev.map((d) => (d.id === docId ? dd.data : d)))
    } catch (e) {
      // 下载用 responseType:'blob'，错误体需从 Blob 解析 detail（如"最终版尚未定稿"409）
      setError(await errMsgFromBlob(e))
    } finally {
      setBusy(false)
    }
  }

  const lockedCount = docs.filter((d) => d.status === 'OUTPUT').length

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <Link to="/">法律论证标注系统</Link> · 导出中心
        </div>
        <div className="topbar-right">
          {lockedCount > 0 && (
            <span className="warn-chip">🔒 {lockedCount} 篇文档已锁定（导出后不可修改）</span>
          )}
          <Link to={taskId ? `/tasks/${taskId}` : '/'} className="link-btn">返回任务</Link>
        </div>
      </header>

      <main className="page-body narrow">
        <h2>导出最终版数据</h2>
        <div className="form-row">
          <label>自定义导出文件名（可选，需求 5.1.2）</label>
          <input value={customName} onChange={(e) => setCustomName(e.target.value)} placeholder="留空则使用文档名称" />
        </div>
        {error && <div className="error">{error}</div>}
        <table className="simple-table">
          <thead>
            <tr><th>文档</th><th>状态</th><th>指南版本</th><th>JSON</th><th>Excel</th><th>图片（标注页图示区）</th></tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id} className={focusDocId === String(d.id) ? 'row-focus' : ''}>
                <td>{d.name}</td>
                <td>
                  <span className={`status-badge status-${d.status}`}>{d.status}</span>
                </td>
                <td>{d.guide_version_snapshot}</td>
                <td>
                  <button className="link-btn" disabled={busy} onClick={() => download(d.id, 'json')}>
                    导出 JSON
                  </button>
                </td>
                <td>
                  <button className="link-btn" disabled={busy} onClick={() => download(d.id, 'excel')}>
                    导出 Excel
                  </button>
                </td>
                <td>
                  <Link to={`/annotate/${d.id}`} className="link-btn">打开图示</Link>
                </td>
              </tr>
            ))}
            {docs.length === 0 && <tr><td colSpan={6} className="empty-hint">暂无文档</td></tr>}
          </tbody>
        </table>

        <h2 style={{ marginTop: 24 }}>导出记录</h2>
        <table className="simple-table">
          <thead>
            <tr><th>文档</th><th>用户</th><th>格式</th><th>文件名</th><th>指南版本</th><th>时间</th></tr>
          </thead>
          <tbody>
            {docs.flatMap((d) => (records[d.id] ?? []).map((r) => (
              <tr key={r.id}>
                <td>{d.name}</td>
                <td>{r.username}</td>
                <td>{r.format}</td>
                <td>{r.filename}</td>
                <td>{r.guide_version}</td>
                <td>{r.created_at.replace('T', ' ').slice(0, 19)}</td>
              </tr>
            )))}
            {docs.every((d) => (records[d.id] ?? []).length === 0) && (
              <tr><td colSpan={6} className="empty-hint">暂无导出记录</td></tr>
            )}
          </tbody>
        </table>
      </main>
    </div>
  )
}
