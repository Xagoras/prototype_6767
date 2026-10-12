/**
 * 工作台首页：任务卡片 + "我的待标注"队列（M2 后接入真实数据）。
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errMsg } from '../api/client'
import { useAuthStore } from '../stores/authStore'
import type { Task } from '../types'

export default function DashboardPage() {
  const { user, logout } = useAuthStore()
  const [tasks, setTasks] = useState<Task[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .get<Task[]>('/tasks')
      .then((r) => setTasks(r.data))
      .catch((e) => setError(errMsg(e)))
  }, [])

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">法律论证标注系统</div>
        <div className="topbar-right">
          <span className="user-name">
            {user?.display_name || user?.username}
            {user?.is_admin && <em className="admin-tag">管理员</em>}
          </span>
          <Link to="/guides" className="link-btn">标注指南</Link>
          <Link to="/tasks/new" className="link-btn primary-link">＋ 创建任务</Link>
          <button className="link-btn" onClick={() => { logout(); window.location.href = '/login' }}>
            退出
          </button>
        </div>
      </header>

      <main className="page-body">
        <section>
          <h2>标注任务</h2>
          {error && <div className="error">{error}</div>}
          {tasks.length === 0 && !error && (
            <div className="empty-hint">
              暂无任务。<Link to="/tasks/new">创建第一个标注任务</Link>，或等待管理员分配。
            </div>
          )}
          <div className="card-grid">
            {tasks.map((t) => (
              <Link to={`/tasks/${t.id}`} key={t.id} className="task-card">
                <div className="task-card-title">{t.name}</div>
                <div className="task-card-meta">
                  <span className={`status-badge status-${t.status}`}>{t.status}</span>
                  <span>创建于 {t.created_at.slice(0, 10)}</span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section>
          <h2>我的待标注队列</h2>
          <div className="empty-hint">
            （M2 里程碑接入：显示被分配的文档，"点击下一条即可获取分配任务"）
          </div>
        </section>
      </main>
    </div>
  )
}
