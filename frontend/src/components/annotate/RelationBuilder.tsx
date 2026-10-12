/**
 * 关系标注构建器（中栏下）：命题/关系多选 → 选关系类型 → 表达式预览 → 创建。
 * 支持嵌套：参数可为已建关系节点（R），自内而外逐层构造（指南 5.3）。
 */
import { useMemo, useState } from 'react'
import { useAnnotationStore } from '../../stores/annotationStore'
import { allRootExprs, relationExpr } from '../../utils/expr'
import type { RelType } from '../../types'

/** 参数条目：命题（P seq）或关系（R 下标） */
interface ArgItem {
  kind: 'P' | 'R'
  id: number
  label: string // 展示文本
}

const REL_DEFS: { code: RelType; name: string; desc: string; minArgs: number; maxArgs: number }[] = [
  { code: 'S', name: '支持', desc: '为结论的成立提供理由', minArgs: 2, maxArgs: 2 },
  { code: 'A', name: '反对', desc: '为结论的不成立提供理由', minArgs: 2, maxArgs: 2 },
  { code: 'J', name: '组合', desc: '多个命题"缺一不可"的合取结构', minArgs: 2, maxArgs: 99 },
  { code: 'M', name: '匹配', desc: '个别判断与一般判断的对应', minArgs: 2, maxArgs: 2 },
  { code: 'I', name: '同一', desc: '多个命题语义上表达同一判断', minArgs: 2, maxArgs: 99 },
]

export default function RelationBuilder() {
  const store = useAnnotationStore()
  const [picked, setPicked] = useState<ArgItem[]>([])
  const [relType, setRelType] = useState<RelType>('S')
  const [error, setError] = useState('')

  const def = REL_DEFS.find((d) => d.code === relType)!

  /** 可选的命题（未在 picked 中的） */
  const availableProps = useMemo(
    () => store.propositions.filter((p) => !picked.some((x) => x.kind === 'P' && x.id === p.seq)),
    [store.propositions, picked],
  )
  /** 可选的关系（未在 picked 中的，且不造成自引用） */
  const availableRels = useMemo(
    () => store.relations
      .map((_, i) => i)
      .filter((i) => !picked.some((x) => x.kind === 'R' && x.id === i)),
    [store.relations, picked],
  )

  const addProp = (seq: number) => {
    if (picked.length >= def.maxArgs) { setError(`关系 ${relType} 最多 ${def.maxArgs} 个参数`); return }
    setError('')
    setPicked((prev) => [...prev, { kind: 'P', id: seq, label: `P${seq}` }])
  }
  const addRel = (idx: number) => {
    if (picked.length >= def.maxArgs) { setError(`关系 ${relType} 最多 ${def.maxArgs} 个参数`); return }
    setError('')
    setPicked((prev) => [...prev, { kind: 'R', id: idx, label: relationExpr(idx, store.relations) }])
  }
  const removeArg = (i: number) => setPicked((prev) => prev.filter((_, j) => j !== i))
  /** 上移参数（调整 S/A/M 的方向语义） */
  const moveArg = (i: number, dir: -1 | 1) => {
    const j = i + dir
    if (j < 0 || j >= picked.length) return
    setPicked((prev) => {
      const next = [...prev]
      ;[next[i], next[j]] = [next[j], next[i]]
      return next
    })
  }

  // 预览表达式
  const preview = useMemo(() => {
    if (picked.length === 0) return ''
    const args = picked.map((x) => x.label).join(', ')
    return `${relType}(${args})`
  }, [picked, relType])

  const create = () => {
    if (picked.length < def.minArgs) { setError(`关系 ${relType} 至少需要 ${def.minArgs} 个参数`); return }
    const args = picked.map((x) => ({ kind: x.kind, id: x.id }))
    store.addRelation(relType, args)
    setPicked([])
    setError('')
  }

  const toggleFlag = (index: number) => {
    const rel = store.relations[index]
    store.updateRelation(index, { flagged: !rel.flagged })
  }

  return (
    <div className="rel-builder">
      <div className="rel-builder-head">关系标注</div>

      {/* 类型选择 */}
      <div className="rel-types">
        {REL_DEFS.map((d) => (
          <button key={d.code} title={`${d.name}：${d.desc}`}
            className={`rel-type-btn${relType === d.code ? ' active' : ''}`}
            onClick={() => { setRelType(d.code); setError('') }}>
            <b>{d.code}</b> {d.name}
          </button>
        ))}
      </div>

      {/* 参数选择 */}
      <div className="rel-args">
        <div className="rel-args-label">参数（{picked.length}/{def.maxArgs}，点击添加；S/A/M 的顺序即方向）</div>
        {picked.length > 0 && (
          <div className="rel-picked">
            {picked.map((x, i) => (
              <span key={`${x.kind}${x.id}`} className="rel-picked-item">
                <button className="mini-btn" onClick={() => moveArg(i, -1)} title="前移">←</button>
                <code>{x.label}</code>
                <button className="mini-btn" onClick={() => moveArg(i, 1)} title="后移">→</button>
                <button className="mini-btn danger" onClick={() => removeArg(i)}>✕</button>
              </span>
            ))}
          </div>
        )}
        <div className="rel-arg-pool">
          {availableProps.map((p) => (
            <button key={p.seq} className="arg-chip prop-chip" onClick={() => addProp(p.seq!)} title={p.text.slice(0, 40)}>
              P{p.seq}
            </button>
          ))}
          {availableRels.map((i) => (
            <button key={`r${i}`} className="arg-chip rel-chip" title="已建关系（嵌套）"
              onClick={() => addRel(i)}>
              {relationExpr(i, store.relations)}
            </button>
          ))}
          {availableProps.length === 0 && availableRels.length === 0 && (
            <span className="picker-hint">（所有可用参数已选入）</span>
          )}
        </div>
      </div>

      {/* 预览与创建 */}
      {preview && <div className="rel-preview">形式化表达：<code>{preview}</code></div>}
      {error && <div className="error">{error}</div>}
      <div>
        <button className="primary" disabled={!store.editable || picked.length === 0} onClick={create}>
          创建关系
        </button>
      </div>

      {/* 已建关系列表（根关系优先展示） */}
      <div className="rel-list">
        <div className="rel-args-label">已建关系（{store.relations.length}）</div>
        {allRootExprs(store.relations).map(({ index, expr }) => (
          <div key={index} className="rel-item">
            <code>{expr}</code>
            <span className="rel-item-actions">
              {store.editable && (
                <button className="mini-btn" title="标记待讨论（专家裁决留痕）" onClick={() => toggleFlag(index)}>
                  {store.relations[index]?.flagged ? '🔖已标记' : '标记待讨论'}
                </button>
              )}
              {store.editable && (
                <button className="mini-btn danger" title="删除关系"
                  onClick={() => store.deleteRelation(index)}>✕</button>
              )}
            </span>
          </div>
        ))}
        {store.relations.length === 0 && (
          <div className="picker-hint">选择命题与类型后创建第一条关系</div>
        )}
      </div>
    </div>
  )
}
