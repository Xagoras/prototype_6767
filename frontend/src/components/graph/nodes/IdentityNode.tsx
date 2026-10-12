/**
 * 同一关系节点：矩形框内 "/" 分隔（指南 6.2）。
 */
import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { ArgumentNodeData } from '../treeToGraph'

export default function IdentityNode({ data }: NodeProps) {
  const d = data as ArgumentNodeData
  return (
    <div className="g-node g-identity">
      <Handle type="target" position={Position.Top} className="g-handle" />
      <span className="g-identity-label">{d.label}</span>
      <Handle type="source" position={Position.Bottom} className="g-handle" />
    </div>
  )
}
