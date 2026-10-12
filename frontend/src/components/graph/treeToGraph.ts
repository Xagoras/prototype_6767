/**
 * 关系树 → 论证图示节点/边（本系统最核心的纯函数）。
 *
 * 编码《指南 v1.1》第 6 章图示规则：
 * - 命题节点：矩形（仅显示序号）；关系节点：实心圆●=支持、空心圆○=反对、
 *   带"+"圆⊕=组合/匹配；同一关系：矩形框内 p1/p2
 * - 支持/反对/匹配有向（箭头指向被支持/被反对/被匹配者）；组合、同一无向
 * - 嵌套六类（指南 6.3）：
 *   M(J(...),pg)   → ⊕ 节点合并承担组合与匹配，无新建节点
 *   J(M1,M2,...)   → 各匹配独立构造，新 ⊕ 连接各匹配关系节点
 *   S(J(...),pj)   → 组合节点引出支持节点●，●→pj
 *   S(M(ps,pg),pj) → 以被匹配的一般判断 pg 为支持起点（effectiveSource=pg）
 *   A(po,S(...))   → 反对箭头指向被反对的支持关系节点●
 *   多层嵌套       → 自内而外逐层构造，每层关系节点独立
 *
 * 输入 relations 为本地 payload 形式：args 中 {kind:"P",id:seq} / {kind:"R",id:下标}。
 */
import type { Edge, Node } from '@xyflow/react'
import type { RelationNode } from '../../types'

export type ArgumentNodeData = {
  label?: string // 命题序号（pN）或关系符号
  nodeType: 'prop' | 'rel' | 'identity'
  relType?: string // S/A/J/M/I
  seq?: number
  relationIndex?: number
}

/** 展开结果：head = 该关系结构对外暴露的连接点；source = 作为支持者时用哪个节点 */
interface Expanded {
  head: string // 图示中代表该关系的节点 id（关系节点或合并后的内层节点）
  source: string // 该关系作为更高层关系的"来源"时使用的节点 id（指南 6.3.4 effectiveSource）
}

const PROP_PREFIX = 'p'
const REL_PREFIX = 'r'
const IDENTITY_PREFIX = 'i'

const propId = (seq: number) => `${PROP_PREFIX}${seq}`
const relId = (idx: number) => `${REL_PREFIX}${idx}`

/** 递归展开一个关系 */
function expand(
  index: number,
  relations: RelationNode[],
  nodes: Node<ArgumentNodeData>[],
  edges: Edge[],
  edgeCounter: { n: number },
): Expanded {
  const rel = relations[index]
  const t = rel.rel_type
  const mkEdge = (source: string, target: string, arrow: boolean) => {
    edgeCounter.n += 1
    edges.push({
      id: `e${edgeCounter.n}`,
      source, target,
      markerEnd: arrow ? { type: 'arrowclosed' } : undefined,
      type: 'argument',
    })
  }

  // 参数展开为可连接节点：命题 → 命题节点；关系 → 该关系的 head
  const resolve = (arg: { kind: 'P' | 'R'; id: number }): string => {
    if (arg.kind === 'P') return propId(arg.id)
    return expand(arg.id, relations, nodes, edges, edgeCounter).head
  }

  if (t === 'I') {
    // 同一关系：矩形框 "p1 / p2 / …"，无向边连各命题
    const nid = `${IDENTITY_PREFIX}${index}`
    const seqs = rel.args.filter((a) => a.kind === 'P').map((a) => propId(a.id))
    nodes.push({
      id: nid, type: 'identity', position: { x: 0, y: 0 },
      data: { nodeType: 'identity', label: rel.args.filter((a) => a.kind === 'P').map((a) => `p${a.id}`).join(' / ') },
    })
    for (const s of seqs) mkEdge(s, nid, false)
    return { head: nid, source: nid }
  }

  if (t === 'J') {
    // 组合：⊕ 节点，无向连线
    const nid = relId(index)
    nodes.push({
      id: nid, type: 'relation', position: { x: 0, y: 0 },
      data: { nodeType: 'rel', relType: 'J', label: '⊕' },
    })
    for (const a of rel.args) mkEdge(resolve(a), nid, false)
    return { head: nid, source: nid }
  }

  if (t === 'M') {
    const [a1, a2] = rel.args
    if (a1.kind === 'R') {
      // M(J(ps1..psn), pg)：不新建节点，内层 ⊕ 承担组合与匹配（指南 6.3.1）
      const inner = expand(a1.id, relations, nodes, edges, edgeCounter)
      const pg = resolve(a2)
      mkEdge(inner.head, pg, true)
      // effectiveSource = 被匹配的一般判断 pg（指南 6.3.4）
      return { head: inner.head, source: pg }
    }
    // M(ps, pg)：新建 ⊕，ps→⊕（无箭头）、⊕→pg（箭头）
    const nid = relId(index)
    nodes.push({
      id: nid, type: 'relation', position: { x: 0, y: 0 },
      data: { nodeType: 'rel', relType: 'M', label: '⊕' },
    })
    mkEdge(resolve(a1), nid, false)
    mkEdge(nid, resolve(a2), true)
    return { head: nid, source: resolve(a2) }
  }

  // S / A
  const nid = relId(index)
  const circle = t === 'S' ? '●' : '○'
  nodes.push({
    id: nid, type: 'relation', position: { x: 0, y: 0 },
    data: { nodeType: 'rel', relType: t, label: circle },
  })
  const [b1, b2] = rel.args
  // 来源侧：命题 → 命题节点；关系 → effectiveSource
  const src = b1.kind === 'P' ? propId(b1.id)
    : expand(b1.id, relations, nodes, edges, edgeCounter).source
  mkEdge(src, nid, false)
  // 目标侧：命题 → 命题节点；关系 → head（反对关系的目标可为支持关系节点，指南 6.3.5）
  const dst = b2.kind === 'P' ? propId(b2.id)
    : expand(b2.id, relations, nodes, edges, edgeCounter).head
  mkEdge(nid, dst, true)
  return { head: nid, source: nid }
}

/** 关系树根集合（不被任何节点引用者） */
export function relationRoots(relations: RelationNode[]): number[] {
  const referenced = new Set<number>()
  for (const r of relations) {
    for (const a of r.args) {
      if (a.kind === 'R') referenced.add(a.id)
    }
  }
  return relations.map((_, i) => i).filter((i) => !referenced.has(i))
}

/** 入口：关系树 → 节点集合与边集合（含独立命题节点） */
export function treeToGraph(
  propositions: { seq: number }[],
  relations: RelationNode[],
): { nodes: Node<ArgumentNodeData>[]; edges: Edge[] } {
  const nodes: Node<ArgumentNodeData>[] = []
  const edges: Edge[] = []
  const counter = { n: 0 }

  // 命题节点（矩形，仅显示序号）
  for (const p of propositions) {
    nodes.push({
      id: propId(p.seq!), type: 'proposition', position: { x: 0, y: 0 },
      data: { nodeType: 'prop', label: `p${p.seq}`, seq: p.seq },
    })
  }

  // 每个根关系即一个独立论证结构
  for (const root of relationRoots(relations)) {
    expand(root, relations, nodes, edges, counter)
  }
  return { nodes, edges }
}

/** 连通分量分组（子图页签用）：返回节点 id 分组 */
export function connectedComponents(nodes: Node[], edges: Edge[]): string[][] {
  const parent = new Map<string, string>()
  const find = (x: string): string => {
    let r = x
    while (parent.get(r) !== r) r = parent.get(r)!
    // 路径压缩
    let cur = x
    while (parent.get(cur) !== r) {
      const next = parent.get(cur)!
      parent.set(cur, r)
      cur = next
    }
    return r
  }
  const union = (a: string, b: string) => {
    const ra = find(a), rb = find(b)
    if (ra !== rb) parent.set(ra, rb)
  }
  for (const n of nodes) parent.set(n.id, n.id)
  for (const e of edges) union(e.source, e.target)

  const groups = new Map<string, string[]>()
  for (const n of nodes) {
    const r = find(n.id)
    if (!groups.has(r)) groups.set(r, [])
    groups.get(r)!.push(n.id)
  }
  // 按组内命题数降序（默认显示最大论证结构）
  const bySize = (ids: string[]) =>
    ids.filter((x) => x.startsWith(PROP_PREFIX)).length
  return [...groups.values()].sort((a, b) => bySize(b) - bySize(a))
}
