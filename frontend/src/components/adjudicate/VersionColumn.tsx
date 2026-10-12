/**
 * 单版本并排列：命题表 + 关系表达式列表（裁定页中间并排展示多版本）。
 */
import type { Proposition, RelationNode } from '../../types'

interface Props {
  label: string
  kind: string
  status: string
  propositions: Proposition[]
  relations: RelationNode[]
  isBase?: boolean
  highlightSeq?: Set<number>
}

export default function VersionColumn({
  label, kind, status, propositions, relations, isBase, highlightSeq,
}: Props) {
  const kindLabel = kind === 'reference' ? '标准答案' : kind === 'final' ? '最终版' : '标注'
  return (
    <div className={`version-col${isBase ? ' base' : ''}`}>
      <div className="version-col-head">
        <b>{label}</b>
        <span className="status-badge">{kindLabel}{status === 'submitted' ? '·已提交' : '·草稿'}</span>
      </div>
      <div className="version-col-body">
        {propositions.map((p) => (
          <div key={p.id} className={`vc-prop${highlightSeq?.has(p.seq ?? 0) ? ' highlighted' : ''}`}>
            <span className="prop-num">P{p.seq}</span>
            <span className="vc-prop-text">{p.text.slice(0, 26)}{p.text.length > 26 ? '…' : ''}</span>
            <span className="type-tag" style={{ fontSize: 10 }}>
              {p.type_code ?? '未标'}{p.subtype_code ? `-${p.subtype_code}` : ''}
            </span>
          </div>
        ))}
        {relations.length > 0 && <div className="vc-rel-title">关系</div>}
        {relations.map((r) => (
          <div key={r.id} className="vc-rel"><code>{r.expr}</code></div>
        ))}
      </div>
    </div>
  )
}
