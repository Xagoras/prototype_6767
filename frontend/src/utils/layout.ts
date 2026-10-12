/**
 * 论证图自动布局（dagre，rankdir=TB：前提在上、结论在下）。
 * 已有手动位置（graph_layout.positions）优先；新增节点采用 dagre 建议位置。
 */
import dagre from '@dagrejs/dagre'
import type { Edge, Node } from '@xyflow/react'
import type { GraphLayout } from '../types'

const PROP_W = 96
const PROP_H = 40
const REL_SIZE = 26
const IDENTITY_H = 40

function dimsOf(node: Node): { width: number; height: number } {
  const d = node.data as { nodeType: string; label?: string } | undefined
  if (d?.nodeType === 'relation') return { width: REL_SIZE, height: REL_SIZE }
  if (d?.nodeType === 'identity') {
    const label = d.label ?? ''
    return { width: Math.max(60, label.length * 13 + 24), height: IDENTITY_H }
  }
  return { width: PROP_W, height: PROP_H }
}

/**
 * 执行 dagre 布局。
 * @param keepPositions 手动保存的位置（visualId → {x,y}），命中则保留不参与布局
 */
export function dagreLayout(
  nodes: Node[],
  edges: Edge[],
  keepPositions?: GraphLayout,
): Node[] {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 28, ranksep: 46, marginx: 24, marginy: 24 })

  const positions = keepPositions?.positions ?? {}
  const fixed = new Set<string>(Object.keys(positions))

  for (const n of nodes) {
    const { width, height } = dimsOf(n)
    g.setNode(n.id, { width, height })
  }
  for (const e of edges) {
    if (fixed.has(e.source) && fixed.has(e.target)) {
      // 两端都已有手动位置：不参与布局连线
      continue
    }
    g.setEdge(e.source, e.target)
  }
  dagre.layout(g)

  return nodes.map((n) => {
    const saved = positions[n.id]
    const { width, height } = dimsOf(n)
    if (saved) return { ...n, position: { x: saved.x, y: saved.y } }
    const pos = g.node(n.id) ?? { x: 0, y: 0 }
    return { ...n, position: { x: pos.x - width / 2, y: pos.y - height / 2 } }
  })
}
