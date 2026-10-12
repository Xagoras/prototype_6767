/**
 * 教学比对页（学生视角）：我的标注 vs 标准答案/最终版差异展示。
 * 需求 7.2 场景1：学生的结果与标准结果可以比对；Q7：查看最终裁定完的结果。
 */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, errMsg } from '../api/client'
import DiffPanel from '../components/adjudicate/DiffPanel'
import type { AnnotationVersion, ComparePayload, Document } from '../types'

export default function ComparePage() {
  const { documentId } = useParams()
  const [doc, setDoc] = useState<Document | null>(null)
  const [compare, setCompare] = useState<ComparePayload | null>(null)
  const [myVersion, setMyVersion] = useState<AnnotationVersion | null>(null)
  const [target, setTarget] = useState<'reference' | 'final'>('final')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!documentId) return
    const did = Number(documentId)
    setLoading(true)
    Promise.all([
      api.get<Document>(`/documents/${did}`),
      api.get<AnnotationVersion>(`/documents/${did}/my-version`).catch(() => null),
    ]).then(([d, mv]) => {
      setDoc(d.data)
      setMyVersion(mv ? mv.data : null)
      // 基准选择：final（最终版）或 reference（标准答案）
      return api.get<ComparePayload>(`/documents/${did}/compare`, { params: { base_kind: target } })
    }).then((r) => setCompare(r.data))
      .catch((e) => setError(errMsg(e)))
      .finally(() => setLoading(false))
  }, [documentId, target])

  if (loading) return <div className="page"><main className="page-body"><div className="empty-hint">加载中…</div></main></div>

  if (!doc || !compare) {
    return (
      <div className="page">
        <main className="page-body">
          <div className="error">{error || '暂无可比对的数据'}</div>
          <Link to="/" className="link-btn">返回工作台</Link>
        </main>
      </div>
    )
  }

  // 找到与"我的版本"对应的组
  const myGroup = myVersion
    ? compare.groups.find((g) => g.version_id === myVersion.id)
    : null
  const baseGroup = compare.groups.find((g) => g.version_id === compare.base_version_id)

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <Link to="/">法律论证标注系统</Link> · 标注比对 · {doc.name}
        </div>
        <div className="topbar-right">
          <div className="compare-target-switch">
            <button className={`link-btn${target === 'final' ? ' active' : ''}`}
              onClick={() => setTarget('final')}>与最终版比对</button>
            <button className={`link-btn${target === 'reference' ? ' active' : ''}`}
              onClick={() => setTarget('reference')}>与标准答案比对</button>
          </div>
          <Link to={`/tasks/${doc.task_id}`} className="link-btn">返回任务</Link>
        </div>
      </header>

      <main className="page-body narrow">
        {doc.status === 'ADJUDICATED' || doc.status === 'OUTPUT' ? (
          myGroup && (
            <>
              <h2>我的标注 vs {baseGroup ? `${baseGroup.annotator_name}（${baseGroup.kind === 'final' ? '最终版' : '标准答案'}）` : '基准'}</h2>
              <DiffPanel
                group={myGroup}
                baseLabel={baseGroup?.annotator_name ?? '基准'}
                otherLabel="我的标注"
              />
              {myGroup.granularity_rate != null && (
                <div className="compare-rate">
                  颗粒度差异率：{Math.round(myGroup.granularity_rate * 100)}%
                  {myGroup.granularity_rate > 0.1 ? '（超过 10% 阈值，请关注切割范围）' : ''}
                </div>
              )}
            </>
          )
        ) : (
          <div className="empty-hint">
            裁定完成后可在此查看自己的标注与最终版/标准答案的差异（需求 Q7）。
          </div>
        )}
      </main>
    </div>
  )
}
