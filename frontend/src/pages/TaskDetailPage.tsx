/**
 * 任务详情页：文档列表、分配总览、阶段流转、入口按钮。
 * 文档列表来源：GET /tasks/{id}/assignments 含 document_name + GET 各文档。
 */
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, errMsg } from '../api/client'
import { useAuthStore } from '../stores/authStore'
import type { Assignment, Document, Task } from '../types'

export default function TaskDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [task, setTask] = useState<Task | null>(null)
  const [docs, setDocs] = useState<Document[]>([])
  const [assigns, setAssigns] = useState<Assignment[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const isCreator = task && (task.created_by === user?.id || user?.is_admin)

  const load = () => {
    if (!id) return
    api.get<Task>(`/tasks/${id}`).then((r) => setTask(r.data)).catch((e) => setError(errMsg(e)))
    api.get<Assignment[]>(`/tasks/${id}/assignments`).then((r) => setAssigns(r.data)).catch(() => {})
    api.get<Document[]>(`/tasks/${id}/documents`).then((r) => setDocs(r.data)).catch(() => {})
  }
  useEffect(load, [id])

  const changeStatus = async (action: string) => {
    setBusy(true)
    setError('')
    try {
      const r = await api.post(`/tasks/${id}/status`, { action })
      setTask(r.data)
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }

  const statusLabel: Record<string, string> = {
    CREATED: '任务已创建（未开始）', ANNOTATING: '标注进行中',
    ADJUDICATING: '裁定进行中', OUTPUT: '结果输出（已锁定）',
  }

  const myAssigns = assigns.filter((a) => a.user_id === user?.id)

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <a href="/">法律论证标注系统</a> · {task?.name || '任务'}
        </div>
        <a href="/" className="link-btn">返回工作台</a>
      </header>

      <main className="page-body narrow">
        {task && (
          <div className="task-head">
            <div>
              <span className={`status-badge status-${task.status}`}>{task.status}</span>
              <span style={{ marginLeft: 10, color: 'var(--muted)' }}>{statusLabel[task.status]}</span>
            </div>
            <div>
              <span className="meta-chip">指南 {task.guide_version}</span>
              <span className="meta-chip">每文档 {task.annotators_per_doc} 人</span>
              <span className="meta-chip">文档 {task.document_count} 篇</span>
            </div>
            {isCreator && (
              <div className="task-status-actions">
                {task.status === 'CREATED' && (
                  <button className="primary" disabled={busy} onClick={() => changeStatus('start')}>开始标注</button>
                )}
                {task.status === 'ANNOTATING' && (
                  <button className="primary" disabled={busy} onClick={() => changeStatus('to_adjudication')}>进入裁定</button>
                )}
                {task.status === 'ADJUDICATING' && (
                  <button className="primary" disabled={busy} onClick={() => changeStatus('finish')}>完成并进入结果输出</button>
                )}
              </div>
            )}
          </div>
        )}

        {error && <div className="error">{error}</div>}

        <h2>我的任务</h2>
        {myAssigns.length === 0 && <div className="empty-hint">暂无分配给您的文档</div>}
        <div className="card-grid">
          {myAssigns.map((a) => (
            <div className="task-card" key={a.id}>
              <div className="task-card-title">{a.document_name || `文档 #${a.document_id}`}</div>
              <div className="task-card-meta">
                <span>角色：{a.role === 'annotator' ? '标注员' : a.role === 'arbiter' ? '裁定者' : '标准答案标注'}</span>
              </div>
              <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
                {a.role === 'annotator' && (
                  <button className="link-btn" onClick={() => navigate(`/annotate/${a.document_id}`)}>去标注</button>
                )}
                {a.role === 'reference' && (
                  <button className="link-btn" onClick={() => navigate(`/annotate/${a.document_id}`)}>标注标准答案</button>
                )}
                {a.role === 'arbiter' && (
                  <button className="link-btn" onClick={() => navigate(`/adjudicate/${a.document_id}`)}>去裁定</button>
                )}
              </div>
            </div>
          ))}
        </div>

        {isCreator && (
          <>
            <h2>全部文档</h2>
            <div className="card-grid">
              {docs.map((d) => (
                <div className="task-card" key={d.id}>
                  <div className="task-card-title">{d.name}</div>
                  <div className="task-card-meta">
                    <span className={`status-badge status-${d.status}`}>{d.status}</span>
                    <span>提取：{d.extraction_method === 'auto' ? '自动' : '人工'}</span>
                  </div>
                  <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button className="link-btn" onClick={() => navigate(`/annotate/${d.id}`)}>标注</button>
                    <button className="link-btn" onClick={() => navigate(`/adjudicate/${d.id}`)}>裁定</button>
                    <button className="link-btn" onClick={() => navigate(`/exports/${task?.id}?doc=${d.id}`)}>导出</button>
                  </div>
                </div>
              ))}
              {docs.length === 0 && <div className="empty-hint">暂无文档</div>}
            </div>

            <h2>分配总览</h2>
            <table className="simple-table">
              <thead><tr><th>文档</th><th>用户</th><th>角色</th></tr></thead>
              <tbody>
                {assigns.map((a) => (
                  <tr key={a.id}>
                    <td>{a.document_name || `#${a.document_id}`}</td>
                    <td>{a.display_name || a.username}</td>
                    <td>{a.role === 'annotator' ? '标注员' : a.role === 'arbiter' ? '裁定者' : '标准答案标注'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ marginTop: 12 }}>
              <Link to="/tasks/new" className="link-btn">＋ 新建任务</Link>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
