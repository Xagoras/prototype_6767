/**
 * 裁定工作台（UC-03 / 阶段三）：
 * - 顶部：差异摘要条（版本数、颗粒度差异率与 10% 阈值提示）
 * - 中部：2~N 个版本并排列（命题表 + 关系表达式）
 * - 右侧：DiffPanel 分类差异清单
 * - 操作：生成最终版工作副本 → 进入标注页编辑（认可+修改）→ 提交定稿
 *   单一版本也可裁定（列只有一条，需求 4.2 确认）。
 */
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, errMsg } from '../api/client'
import DiffPanel from '../components/adjudicate/DiffPanel'
import VersionColumn from '../components/adjudicate/VersionColumn'
import type { AnnotationVersion, ComparePayload, Document } from '../types'

export default function AdjudicatePage() {
  const { documentId } = useParams()
  const navigate = useNavigate()
  const [doc, setDoc] = useState<Document | null>(null)
  const [compare, setCompare] = useState<ComparePayload | null>(null)
  const [versions, setVersions] = useState<AnnotationVersion[]>([])
  const [selectedGroup, setSelectedGroup] = useState(0)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!documentId) return
    const did = Number(documentId)
    api.get<Document>(`/documents/${did}`).then((r) => setDoc(r.data)).catch((e) => setError(errMsg(e)))
    api.get<ComparePayload>(`/documents/${did}/compare`).then((r) => setCompare(r.data)).catch((e) => setError(errMsg(e)))
  }, [documentId])

  // 每个版本加载完整内容（VersionColumn 展示）
  useEffect(() => {
    if (!compare) return
    Promise.all(
      compare.groups.map((g) =>
        api.get<AnnotationVersion>(`/versions/${g.version_id}`)
          .then((r) => r.data)
          .catch(() => null),
      ),
    ).then((list) => setVersions(list.filter((v): v is AnnotationVersion => v !== null)))
  }, [compare])

  const baseGroup = compare?.groups.find((g) => g.version_id === compare.base_version_id)
  const baseVersion = versions.find((v) => v.id === compare?.base_version_id)
  const selGroup = compare?.groups[Math.min(selectedGroup, (compare?.groups.length ?? 1) - 1)]
  const selVersion = versions.find((v) => v.id === selGroup?.version_id)

  /** 生成最终版工作副本并跳转标注页编辑 */
  const createFinal = async () => {
    if (!documentId || !compare) return
    setBusy(true)
    setError('')
    try {
      const r = await api.post<AnnotationVersion>(`/documents/${documentId}/adjudicate`, {
        base_version_id: compare.base_version_id,
        note: '',
      })
      navigate(`/annotate/${documentId}?version=${r.data.id}&mode=adjudicate`)
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }

  if (!doc || !compare) {
    return (
      <div className="page">
        <main className="page-body">
          {error ? <div className="error">{error}</div> : <div className="empty-hint">加载中…</div>}
          <Link to="/" className="link-btn">返回工作台</Link>
        </main>
      </div>
    )
  }

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <Link to="/">法律论证标注系统</Link> · 裁定 · {doc.name}
          <span className={`status-badge status-${doc.status}`} style={{ marginLeft: 10 }}>{doc.status}</span>
        </div>
        <div className="topbar-right">
          {compare.warn_threshold_exceeded && (
            <span className="warn-chip">⚠ 颗粒度差异超过 10% 阈值</span>
          )}
          <button className="primary" disabled={busy} onClick={createFinal}>
            生成最终版工作副本并编辑 →
          </button>
          <Link to={`/tasks/${doc.task_id}`} className="link-btn">返回任务</Link>
        </div>
      </header>

      <main className="adjudicate-main">
        <div className="adj-summary">
          {compare.groups.map((g) => (
            <span key={g.version_id} className={`adj-chip${g.version_id === compare.base_version_id ? ' base' : ''}`}>
              {g.annotator_name}（{g.kind === 'reference' ? '标准答案' : g.kind === 'final' ? '最终版' : '标注'}）
              {g.version_id === compare.base_version_id && ' · 基准'}
              {g.granularity_rate != null && g.version_id !== compare.base_version_id && (
                <> · 颗粒度差异 {Math.round(g.granularity_rate * 100)}%{g.granularity_rate > 0.1 ? ' ⚠' : ''}</>
              )}
            </span>
          ))}
          <span className="adj-hint">（差异与基准版本对比；10% 阈值仅提示，不阻断）</span>
        </div>

        <div className="adj-columns">
          {compare.groups.map((g, i) => {
            const v = versions.find((x) => x.id === g.version_id)
            return (
              <div key={g.version_id} className={`adj-col${g.version_id === compare.base_version_id ? ' base' : ''}`}
                onClick={() => setSelectedGroup(i)}>
                <VersionColumn
                  label={`${g.annotator_name ?? '版本'} ${g.kind === 'reference' ? '（标准答案）' : ''}`}
                  kind={g.kind}
                  status={g.status}
                  propositions={v?.propositions ?? []}
                  relations={v?.relations ?? []}
                  isBase={g.version_id === compare.base_version_id}
                />
              </div>
            )
          })}
          <div className="adj-diff-col">
            <div className="adj-diff-head">
              差异清单
              <select value={selectedGroup}
                onChange={(e) => setSelectedGroup(Number(e.target.value))}>
                {compare.groups.map((g, i) => (
                  <option key={g.version_id} value={i}>
                    {g.annotator_name}（{g.kind === 'reference' ? '标准答案' : '标注'}）
                  </option>
                ))}
              </select>
            </div>
            <DiffPanel
              group={selGroup ?? null}
              baseLabel={baseGroup ? `${baseGroup.annotator_name}（基准）` : '基准'}
              otherLabel={selGroup ? `${selGroup.annotator_name}` : '此版本'}
            />
            {baseVersion && selVersion && (
              <div className="adj-tip">
                裁定方式：点击上方"生成最终版工作副本并编辑"后，在标注页以基准版本为基础，
                对照差异清单逐条认可或直接修改（需求 Q11：既可认可某版本也可直接修改），
                完成后提交即定稿。
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
