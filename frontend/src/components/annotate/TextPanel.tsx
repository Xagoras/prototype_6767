/**
 * 原文展示区（左栏上）：保留格式渲染裁判理由，支持选区高亮与命题序号角标。
 *
 * - 按行渲染，每行 <span data-start=行起点码点>（选区偏移计算的锚点）
 * - 已标注命题区间：按类型着色高亮 + 上标序号
 * - 鼠标划选后弹出浮动工具条：选择类型直接创建命题（或仅建序号）
 */
import { useMemo, useRef, useState } from 'react'
import { codePointLength, codePointSlice, lineStarts, selectionToRange } from '../../utils/charIndex'
import { useAnnotationStore } from '../../stores/annotationStore'
import type { ElementDef, Proposition } from '../../types'

/** 类型着色映射 */
const TYPE_COLORS: Record<string, string> = {
  SF: 'var(--sf)', GF: 'var(--gf)', SM: 'var(--sm)', GM: 'var(--gm)',
  IS: 'var(--is)', Non: 'var(--non)',
}

interface Props {
  text: string
  propositions: Proposition[]
  readOnly?: boolean
}

export default function TextPanel({ text, propositions, readOnly = false }: Props) {
  const store = useAnnotationStore()
  const rootRef = useRef<HTMLDivElement>(null)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; start: number; end: number } | null>(null)

  const lines = useMemo(() => lineStarts(text), [text])
  const guide = store.guide

  /** 一二级标签按钮（浮动工具条用） */
  const topLevel = useMemo(() => {
    if (!guide) return []
    return guide.taxonomy.elements.filter((e) => ['SF', 'GF', 'SM', 'GM', 'IS', 'Non'].includes(e.code))
  }, [guide])

  const onMouseUp = () => {
    if (readOnly || !rootRef.current) return
    const range = selectionToRange(rootRef.current, codePointLength(text))
    if (!range) { setTooltip(null); store.setSelection(null); return }
    // 工具条定位在选区上方（用选区 rect）
    const sel = window.getSelection()
    const rect = sel?.getRangeAt(0).getBoundingClientRect()
    setTooltip({
      x: (rect?.left ?? 0) + window.scrollX,
      y: (rect?.top ?? 0) + window.scrollY - 44,
      start: range.start, end: range.end,
    })
    store.setSelection({ ...range, text: codePointSlice(text, range.start, range.end) })
  }

  const createProp = (code?: string, sub?: string) => {
    if (!tooltip) return
    store.createProp(tooltip.start, tooltip.end, codePointSlice(text, tooltip.start, tooltip.end), code, sub)
    setTooltip(null)
    store.setSelection(null)
    window.getSelection()?.removeAllRanges()
  }

  /** 渲染一行：按命题区间切分，命题片段着色 + 序号角标 */
  const renderLine = (lineStart: number, content: string) => {
    const lineEnd = lineStart + codePointLength(content)
    // 行内命题（与行有交集的）
    const hits = propositions
      .filter((p) => p.char_end > lineStart && p.char_start < lineEnd)
      .sort((a, b) => a.char_start - b.char_start)
    if (hits.length === 0) return content
    const parts: React.ReactNode[] = []
    let cursor = lineStart
    for (const p of hits) {
      const localStart = Math.max(p.char_start, lineStart)
      if (localStart > cursor) {
        parts.push(content.slice(cursor - lineStart, localStart - lineStart))
      }
      const localEnd = Math.min(p.char_end, lineEnd)
      const bg = TYPE_COLORS[p.type_code ?? ''] ?? 'transparent'
      parts.push(
        <mark key={`m${p.char_start}`} className="prop-mark"
          data-seq={p.seq}
          style={{ background: bg }} title={`P${p.seq}${p.type_code ? ` · ${p.type_code}${p.subtype_code ? '-' + p.subtype_code : ''}` : ' · 未标类型'}`}>
          {content.slice(localStart - lineStart, localEnd - lineStart)}
        </mark>,
      )
      cursor = localEnd
    }
    if (cursor < lineEnd) parts.push(content.slice(cursor - lineStart))
    return parts
  }

  const renderTopToolbar = (element: ElementDef) => {
    const sub = element.subtypes
    return (
      <span key={element.code} className="toolbar-type">
        <button title={`${element.name}${sub ? '（点击选子类型）' : ''}`}
          onClick={() => sub && sub.length > 0 ? null : createProp(element.code)}>
          {element.code}
        </button>
        {sub && sub.length > 0 && (
          <span className="toolbar-sub">
            {sub.map((s) => (
              <button key={s.code} title={s.name} onClick={() => createProp(element.code, s.code)}>
                {s.code.split('-')[1] ?? s.code}
              </button>
            ))}
          </span>
        )}
      </span>
    )
  }

  return (
    <div className="text-panel">
      <div className="text-panel-body" ref={rootRef} onMouseUp={onMouseUp}>
        {lines.map((line, i) => (
          <div key={i} className="text-line" data-start={line.start}>
            {line.content === '' ? ' ' : renderLine(line.start, line.content)}
          </div>
        ))}
      </div>
      {tooltip && !readOnly && (
        <div className="selection-toolbar" style={{ left: tooltip.x, top: tooltip.y }}>
          <span className="toolbar-tip">标注为：</span>
          {topLevel.map(renderTopToolbar)}
          <button className="toolbar-create" onClick={() => createProp()}>
            仅建序号
          </button>
        </div>
      )}
    </div>
  )
}
