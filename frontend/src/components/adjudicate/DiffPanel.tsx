/**
 * 差异清单面板（裁定页与教学比对页共用）：按命题/关系分类展示差异。
 */
import type { ComparePayload, PropDiffItem, RelDiffItem } from '../../types'

interface Props {
  group: ComparePayload['groups'][number] | null
  baseLabel: string
  otherLabel: string
}

const CATEGORY_LABELS: Record<string, string> = {
  identical: '一致', boundary: '边界差异', type: '类型差异', subtype: '子类型差异',
  edited_text: '文字已编辑', only_a: '仅基准有', only_b: '仅此版本有',
  direction: '方向差异', nested: '嵌套差异', missing: '基准缺失', extra: '仅此版本有',
}

export default function DiffPanel({ group, baseLabel, otherLabel }: Props) {
  if (!group) return <div className="empty-hint">加载差异中…</div>

  const propDiffs = (group.prop_diffs as PropDiffItem[]).filter((d) => d.category !== 'identical')
  const relDiffs = (group.relation_diffs as RelDiffItem[])

  if (propDiffs.length === 0 && relDiffs.length === 0) {
    return <div className="diff-panel-ok">✔ 与基准版本完全一致（一致性通过，可直接采用）</div>
  }

  return (
    <div className="diff-panel">
      <div className="diff-head">
        差异清单（{baseLabel} ↔ {otherLabel}）：命题 {propDiffs.length} 处 · 关系 {relDiffs.length} 处
      </div>
      {propDiffs.length > 0 && (
        <>
          <div className="diff-section-title">命题差异</div>
          {propDiffs.map((d, i) => (
            <div key={i} className="diff-item">
              <span className={`diff-cat cat-${d.category}`}>{CATEGORY_LABELS[d.category] ?? d.category}</span>
              <span className="diff-body">
                {d.a_seq != null && (
                  <span className="diff-side">
                    <b>{baseLabel}</b> P{d.a_seq} {d.a_type ?? '（无类型）'}：{d.a_text?.slice(0, 30)}
                  </span>
                )}
                {d.b_seq != null && (
                  <span className="diff-side">
                    <b>{otherLabel}</b> P{d.b_seq} {d.b_type ?? '（无类型）'}：{d.b_text?.slice(0, 30)}
                  </span>
                )}
              </span>
            </div>
          ))}
        </>
      )}
      {relDiffs.length > 0 && (
        <>
          <div className="diff-section-title">关系差异</div>
          {relDiffs.map((d, i) => (
            <div key={i} className="diff-item">
              <span className={`diff-cat cat-${d.category}`}>{CATEGORY_LABELS[d.category] ?? d.category}</span>
              <span className="diff-body">
                {d.a_expr && <code>{d.a_expr}</code>}
                {d.a_expr && d.b_expr && <span className="diff-vs"> vs </span>}
                {d.b_expr && <code>{d.b_expr}</code>}
              </span>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
