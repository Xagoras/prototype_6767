/**
 * 颗粒度切割确认与人工调整（指南 2.3）。
 * 操作：合并相邻块（多选）、在标点处拆分、删除块。
 * 同性质子句是否合并由标注员判断——系统只提供切割候选与操作工具。
 */
import { useMemo, useState } from 'react'
import type { Segment } from '../../types'

interface Props {
  segments: Segment[]
  reasoningText: string
  onSave: (segments: Segment[]) => Promise<void>
}

const CLAUSE_PUNCT = '，,；;'

export default function SegmentationEditor({ segments, reasoningText, onSave }: Props) {
  const [items, setItems] = useState<Segment[]>(segments)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [busy, setBusy] = useState(false)

  const sorted = useMemo(() => [...items].sort((a, b) => a.start - b.start), [items])

  const toggle = (start: number) => {
    const next = new Set(selected)
    if (next.has(start)) next.delete(start)
    else next.add(start)
    setSelected(next)
  }

  /** 合并选中的相邻块 */
  const merge = () => {
    const sel = [...selected].sort((a, b) => a - b)
    const idxs = sel.map((s) => sorted.findIndex((x) => x.start === s))
    if (idxs.length < 2) return
    if (Math.max(...idxs) - Math.min(...idxs) !== idxs.length - 1) return // 必须相邻
    const merged: Segment = {
      start: sorted[idxs[0]].start,
      end: sorted[idxs[idxs.length - 1]].end,
      text: reasoningText.slice(sorted[idxs[0]].start, sorted[idxs[idxs.length - 1]].end),
    }
    const removed = new Set(idxs)
    const next = sorted.filter((_, i) => !removed.has(i))
    next.splice(idxs[0], 0, merged)
    setItems(next)
    setSelected(new Set())
  }

  /** 在块内标点（偏移 at = 标点下标 + 1）之后拆分 */
  const splitAt = (seg: Segment, at: number) => {
    const i = sorted.findIndex((x) => x.start === seg.start)
    if (i < 0 || at <= seg.start || at >= seg.end) return
    const next = [...sorted]
    next.splice(i, 1,
      { start: seg.start, end: at, text: reasoningText.slice(seg.start, at) },
      { start: at, end: seg.end, text: reasoningText.slice(at, seg.end) },
    )
    setItems(next)
    setSelected(new Set())
  }

  const remove = (seg: Segment) => {
    setItems(sorted.filter((x) => x.start !== seg.start))
    setSelected(new Set())
  }

  const save = async () => {
    setBusy(true)
    try {
      await onSave(sorted)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="seg-editor">
      <div className="seg-bar">
        <span>共 {sorted.length} 个切割块（切割候选为子句级，同性质子句请手动合并）</span>
        <span className="seg-actions">
          <button className="link-btn" disabled={selected.size < 2 || busy} onClick={merge}>
            合并选中（{selected.size}）
          </button>
          <button className="primary" disabled={busy} onClick={save}>
            {busy ? '保存中…' : '保存切割结果'}
          </button>
        </span>
      </div>
      <div className="seg-list">
        {sorted.map((seg, i) => (
          <div key={seg.start} className={`seg-item${selected.has(seg.start) ? ' selected' : ''}`}>
            <input type="checkbox" checked={selected.has(seg.start)} onChange={() => toggle(seg.start)} />
            <span className="seg-index">{i + 1}</span>
            <span className="seg-text">
              {Array.from(seg.text).map((ch, j) => (
                <span key={j}>
                  {ch}
                  {CLAUSE_PUNCT.includes(ch) && (
                    <button
                      className="split-btn"
                      title="在此标点后拆分"
                      onClick={() => splitAt(seg, seg.start + j + 1)}
                    >
                      ✂
                    </button>
                  )}
                </span>
              ))}
            </span>
            <button className="del-btn" title="删除此块" onClick={() => remove(seg)}>✕</button>
          </div>
        ))}
      </div>
    </div>
  )
}
