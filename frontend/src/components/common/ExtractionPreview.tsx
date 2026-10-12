/**
 * 裁判理由提取预览与人工校正（需求 2.1.2：提取算法出错时允许人工修正）。
 * 全文按行渲染；自动提取区间高亮；每行悬停可"设为起点/终点"调整边界。
 */
import { useMemo, useState } from 'react'

interface Props {
  text: string
  start: number
  end: number
  method: string // auto / manual_corrected / manual_required
  onSave: (start: number, end: number) => Promise<void>
}

export default function ExtractionPreview({ text, start, end, method, onSave }: Props) {
  const [draftStart, setDraftStart] = useState(start)
  const [draftEnd, setDraftEnd] = useState(end)
  const [busy, setBusy] = useState(false)

  // 按行切分，记录每行的码点偏移
  const lines = useMemo(() => {
    const result: { start: number; end: number; content: string }[] = []
    let pos = 0
    for (const line of text.split('\n')) {
      result.push({ start: pos, end: pos + line.length, content: line })
      pos += line.length + 1
    }
    return result
  }, [text])

  const dirty = draftStart !== start || draftEnd !== end

  const save = async () => {
    setBusy(true)
    try {
      await onSave(draftStart, draftEnd)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="extraction">
      <div className="extraction-bar">
        <span>
          提取范围：<b>{draftStart}</b> → <b>{draftEnd}</b>
          <em className="extraction-method">{method === 'auto' ? '自动提取' : method === 'manual_corrected' ? '人工校正' : '需人工确定'}</em>
        </span>
        <span className="extraction-actions">
          <input type="number" value={draftStart} min={0} max={text.length}
            onChange={(e) => setDraftStart(Number(e.target.value))} title="起点偏移" />
          <input type="number" value={draftEnd} min={0} max={text.length}
            onChange={(e) => setDraftEnd(Number(e.target.value))} title="终点偏移" />
          <button className="link-btn" disabled={!dirty || busy || draftEnd <= draftStart}
            onClick={save}>
            {busy ? '保存中…' : '保存范围'}
          </button>
        </span>
      </div>
      <div className="extraction-text">
        {lines.map((line, i) => {
          // 行与提取区间的重叠判定
          const inRange = line.end > draftStart && line.start < draftEnd
          return (
            <div key={i} className={`extraction-line${inRange ? ' in-range' : ''}`}>
              <span className="line-actions">
                <button title="设为起点"
                  onClick={() => setDraftStart(line.start)}>起</button>
                <button title="设为终点"
                  onClick={() => setDraftEnd(line.end)}>终</button>
              </span>
              <span className="line-content">{line.content || ' '}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
