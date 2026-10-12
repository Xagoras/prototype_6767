/**
 * 命题节点：矩形，显示带框的序号（指南 6.1：不表达命题类型信息）。
 */
import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { ArgumentNodeData } from '../treeToGraph'

export default function PropositionNode({ data }: NodeProps) {
  const d = data as ArgumentNodeData
  return (
    <div className="g-node g-prop">
      <Handle type="target" position={Position.Top} className="g-handle" />
      <span className="g-prop-label">{d.label}</span>
      <Handle type="source" position={Position.Bottom} className="g-handle" />
    </div>
  )
}
