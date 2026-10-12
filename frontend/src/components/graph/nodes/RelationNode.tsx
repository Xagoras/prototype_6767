/**
 * 关系节点：圆形。实心●=支持、空心○=反对、⊕=组合/匹配（指南 6.2）。
 */
import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { ArgumentNodeData } from '../treeToGraph'

const REL_COLORS: Record<string, string> = {
  S: '#23263b', // 实心圆
  A: '#ffffff', // 空心圆
  J: '#8c2f39', // ⊕ 组合
  M: '#2e6b4f', // ⊕ 匹配
}

export default function RelationNode({ data }: NodeProps) {
  const d = data as ArgumentNodeData
  const t = d.relType ?? 'S'
  const hollow = t === 'A'
  const color = REL_COLORS[t] ?? '#23263b'
  return (
    <div className="g-rel-wrap">
      <Handle type="target" position={Position.Top} className="g-handle" />
      <div
        className={`g-node g-rel${hollow ? ' hollow' : ''}`}
        style={hollow ? { borderColor: color } : { background: color }}
        title={t === 'S' ? '支持关系' : t === 'A' ? '反对关系' : t === 'J' ? '组合关系' : '匹配关系'}
      >
        <span className="g-rel-label" style={{ color: hollow ? color : '#fff' }}>{d.label}</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="g-handle" />
    </div>
  )
}
