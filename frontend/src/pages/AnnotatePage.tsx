/**
 * 标注工作台（UC-02 命题标注，三栏布局，比例可调）：
 * 左：原文展示区（选区高亮+序号角标）+ 命题列表
 * 中：标签选择 + 操作工具栏（撤销/重做/提交/保存状态）
 * 右：论证图示区（M4 里程碑接入）
 */
import { useEffect } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import ArgumentGraph from '../components/graph/ArgumentGraph'
import LabelPicker from '../components/annotate/LabelPicker'
import PropositionList from '../components/annotate/PropositionList'
import RelationBuilder from '../components/annotate/RelationBuilder'
import TextPanel from '../components/annotate/TextPanel'
import ResizableTriPanel from '../components/common/ResizableTriPanel'
import { useAnnotationStore } from '../stores/annotationStore'

export default function AnnotatePage() {
  const { documentId } = useParams()
  const [searchParams] = useSearchParams()
  const versionId = searchParams.get('version')
  const store = useAnnotationStore()

  useEffect(() => {
    if (documentId) void store.load(Number(documentId), versionId ? Number(versionId) : undefined)
  }, [documentId, versionId])

  const doc = store.doc

  if (store.loading) return <div className="page"><main className="page-body"><div className="empty-hint">加载中…</div></main></div>
  if (!doc) {
    return (
      <div className="page">
        <main className="page-body">
          <div className="error">{store.lastError || '文档不存在'}</div>
          <Link to="/" className="link-btn">返回工作台</Link>
        </main>
      </div>
    )
  }

  const kindLabel = store.kind === 'reference' ? '标准答案标注' : store.kind === 'final' ? '最终版本' : '独立标注'

  return (
    <div className="page annotate-page">
      <header className="topbar">
        <div className="brand">
          <Link to="/">法律论证标注系统</Link> · {doc.name}
          <span className={`status-badge status-${store.status === 'submitted' ? 'SUBMITTED' : 'ANNOTATING'}`} style={{ marginLeft: 10 }}>
            {store.status === 'submitted' ? '已提交' : '标注中'}
          </span>
          <span className="meta-chip">{kindLabel}</span>
          <span className="meta-chip">指南 {doc.guide_version_snapshot}</span>
        </div>
        <div className="topbar-right">
          {store.saving && <span className="saving-hint">保存中…</span>}
          {store.lastError && <span className="error">{store.lastError}</span>}
          <button className="link-btn" disabled={!store.canUndo} onClick={store.undo} title="Ctrl+Z">撤销</button>
          <button className="link-btn" disabled={!store.canRedo} onClick={store.redo} title="Ctrl+Y">重做</button>
          {store.editable && (
            <button className="primary" onClick={() => void store.submit()}>提交标注</button>
          )}
          <Link to={`/tasks/${doc.task_id}`} className="link-btn">返回任务</Link>
        </div>
      </header>

      {/* 键盘快捷键：Ctrl+Z / Ctrl+Y */}
      <AnnotatePageHotkeys />

      <main className="annotate-main">
        <ResizableTriPanel
          left={
            <div className="col-stack">
              <div className="col-pane grow2">
                <TextPanel
                  text={doc.reasoning_text}
                  propositions={store.propositions}
                  readOnly={!store.editable}
                />
              </div>
              <div className="col-pane grow1">
                <PropositionList readOnly={!store.editable} />
              </div>
            </div>
          }
          middle={
            <div className="col-stack">
              <div className="col-pane">
                <LabelPicker />
              </div>
              <div className="col-pane grow1">
                <RelationBuilder />
              </div>
            </div>
          }
          right={
            <div className="col-pane">
              <ArgumentGraph />
            </div>
          }
        />
      </main>
    </div>
  )
}

/** 撤销/重做快捷键 */
function AnnotatePageHotkeys() {
  const store = useAnnotationStore()
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        if (e.shiftKey) store.redo()
        else store.undo()
        e.preventDefault()
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
        store.redo()
        e.preventDefault()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [store])
  return null
}
