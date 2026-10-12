/**
 * 命题列表（左栏下）：序号按原文顺序动态生成；显示全文（需求确认"不省略"）。
 * 操作：改类型、编辑文字（教学临时文本）、删除、合并相邻、待讨论标记。
 */
import { useState } from 'react'
import { useAnnotationStore } from '../../stores/annotationStore'
import type { Proposition } from '../../types'

/** 类型着色 */
const TYPE_COLORS: Record<string, string> = {
  SF: 'var(--sf)', GF: 'var(--gf)', SM: 'var(--sm)', GM: 'var(--gm)',
  IS: 'var(--is)', Non: 'var(--non)',
}

interface Props {
  readOnly?: boolean
}

export default function PropositionList({ readOnly = false }: Props) {
  const store = useAnnotationStore()
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [editingSeq, setEditingSeq] = useState<number | null>(null)
  const [editingText, setEditingText] = useState('')

  const guide = store.guide
  const topLevel = guide?.taxonomy.elements.filter((e) => e.kind === 'prop') ?? []
  const nonProp = guide?.taxonomy.elements.filter((e) => e.kind === 'non_prop') ?? []

  const toggle = (seq: number) => {
    const next = new Set(selected)
    if (next.has(seq)) next.delete(seq)
    else next.add(seq)
    setSelected(next)
  }

  const merge = () => {
    const sel = [...selected].sort((a, b) => a - b)
    if (sel.length !== 2) return
    // 必须是相邻序号
    if (sel[1] - sel[0] !== 1) return
    store.mergeProps(sel[0], sel[1])
    setSelected(new Set())
  }

  const startEdit = (p: Proposition) => {
    setEditingSeq(p.seq ?? null)
    setEditingText(p.edited_text ?? p.text)
  }

  const commitEdit = (p: Proposition) => {
    store.editPropText(p.seq!, editingText)
    setEditingSeq(null)
  }

  const labelOf = (p: Proposition) => {
    if (!p.type_code) return <span className="no-type">未标类型</span>
    return (
      <span className="type-tag" style={{ background: TYPE_COLORS[p.type_code] ?? '#eee' }}>
        {p.type_code}
        {p.subtype_code ? `-${p.subtype_code}` : ''}
      </span>
    )
  }

  const renderOptions = () => (
    <>
      <option value="">— 未标类型 —</option>
      {[...topLevel, ...nonProp].map((e) => (
        e.subtypes && e.subtypes.length > 0 ? (
          <optgroup key={e.code} label={e.name}>
            {e.subtypes.map((s) => (
              <option key={s.code} value={`${e.code}|${s.code}`}>
                {e.code}-{s.code} {s.name}
              </option>
            ))}
          </optgroup>
        ) : (
          <option key={e.code} value={`${e.code}|`}>{e.code} {e.name}</option>
        )
      ))}
    </>
  )

  const applyType = (p: Proposition, value: string) => {
    if (!value) {
      store.updateProp(p.seq!, { type_code: null, subtype_code: null })
      return
    }
    const [code, sub] = value.split('|')
    store.updateProp(p.seq!, { type_code: code, subtype_code: sub || null })
  }

  return (
    <div className="prop-list">
      <div className="prop-list-bar">
        <span>命题列表（{store.propositions.length}）</span>
        {!readOnly && (
          <span>
            <button className="link-btn" disabled={selected.size !== 2} onClick={merge}>
              合并选中
            </button>
          </span>
        )}
      </div>
      <div className="prop-items">
        {store.propositions.map((p) => (
          <div key={p.char_start} className={`prop-item${selected.has(p.seq ?? 0) ? ' selected' : ''}`}>
            <div className="prop-item-head" onClick={() => store.setSelectedPropSeq(p.seq ?? null)}>
              {!readOnly && (
                <input type="checkbox" checked={selected.has(p.seq ?? 0)}
                  onClick={(e) => e.stopPropagation()}
                  onChange={() => toggle(p.seq ?? 0)} />
              )}
              <span className="prop-num">P{p.seq}</span>
              {labelOf(p)}
              <span className="prop-actions">
                {!readOnly && (
                  <>
                    <select value={p.type_code ? `${p.type_code}|${p.subtype_code ?? ''}` : ''}
                      onChange={(e) => applyType(p, e.target.value)} title="修改类型">
                      {renderOptions()}
                    </select>
                    <button className="mini-btn" title="编辑文字" onClick={() => startEdit(p)}>✎</button>
                    <button className="mini-btn danger" title="删除命题" onClick={() => store.deleteProp(p.seq!)}>✕</button>
                  </>
                )}
              </span>
            </div>
            {editingSeq === p.seq ? (
              <div className="prop-edit">
                <textarea rows={3} value={editingText} onChange={(e) => setEditingText(e.target.value)} />
                <div>
                  <button className="link-btn" onClick={() => commitEdit(p)}>保存</button>
                  <button className="link-btn" onClick={() => setEditingSeq(null)}>取消</button>
                </div>
              </div>
            ) : (
              <div className="prop-item-text">{p.edited_text ?? p.text}</div>
            )}
          </div>
        ))}
        {store.propositions.length === 0 && (
          <div className="empty-hint">在左侧原文中划选文本，创建第一个命题</div>
        )}
      </div>
    </div>
  )
}
