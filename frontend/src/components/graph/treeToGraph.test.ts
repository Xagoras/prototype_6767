/**
 * treeToGraph 单元测试：覆盖《指南 v1.1》6.3 全部六类嵌套图示规则。
 */
import { describe, expect, it } from 'vitest'
import type { RelationNode } from '../../types'
import { connectedComponents, relationRoots, treeToGraph } from './treeToGraph'

/** 构造关系列表（args 直接以对象字面量） */
function rels(...defs: { t: string; args: { kind: 'P' | 'R'; id: number }[] }[]): RelationNode[] {
  return defs.map((d, i) => ({
    id: i, version_id: 0, rel_type: d.t as never, args: d.args,
    note: '', flagged: false, flag_note: '',
  }))
}

const props = (n: number) => Array.from({ length: n }, (_, i) => ({ seq: i + 1 }))

describe('基础结构（无嵌套，指南 6.2）', () => {
  it('支持关系 S(p1,p2)：实心圆节点 + 两条边（p1→● 无箭头、●→p2 箭头）', () => {
    const { nodes, edges } = treeToGraph(props(2), rels({ t: 'S', args: [{ kind: 'P', id: 1 }, { kind: 'P', id: 2 }] }))
    const relNodes = nodes.filter((n) => n.type === 'relation')
    expect(relNodes).toHaveLength(1)
    expect(relNodes[0].data).toMatchObject({ relType: 'S', label: '●' })
    expect(edges).toHaveLength(2)
    // p1→● 无箭头；●→p2 有箭头
    const toRel = edges.find((e) => e.source === 'p1' && e.target === relNodes[0].id)
    const fromRel = edges.find((e) => e.source === relNodes[0].id && e.target === 'p2')
    expect(toRel?.markerEnd).toBeUndefined()
    expect(fromRel?.markerEnd?.type).toBe('arrowclosed')
  })

  it('反对关系 A(p1,p2)：空心圆', () => {
    const { nodes } = treeToGraph(props(2), rels({ t: 'A', args: [{ kind: 'P', id: 1 }, { kind: 'P', id: 2 }] }))
    const relNodes = nodes.filter((n) => n.type === 'relation')
    expect(relNodes[0].data).toMatchObject({ relType: 'A', label: '○' })
  })

  it('组合关系 J(p1,p2,p3)：⊕ 节点 + 3 条无向边', () => {
    const { nodes, edges } = treeToGraph(props(3), rels({ t: 'J', args: [{ kind: 'P', id: 1 }, { kind: 'P', id: 2 }, { kind: 'P', id: 3 }] }))
    const relNodes = nodes.filter((n) => n.type === 'relation')
    expect(relNodes[0].data).toMatchObject({ relType: 'J', label: '⊕' })
    expect(edges).toHaveLength(3)
    expect(edges.every((e) => e.markerEnd === undefined)).toBe(true)
  })

  it('匹配关系 M(p1,p2)：⊕ 有向（箭头指向被匹配者 p2）', () => {
    const { nodes, edges } = treeToGraph(props(2), rels({ t: 'M', args: [{ kind: 'P', id: 1 }, { kind: 'P', id: 2 }] }))
    const relNodes = nodes.filter((n) => n.type === 'relation')
    const fromRel = edges.find((e) => e.source === relNodes[0].id)
    expect(fromRel?.target).toBe('p2')
    expect(fromRel?.markerEnd?.type).toBe('arrowclosed')
  })

  it('同一关系 I(p1,p2)：斜杠框节点 + 2 条无向边', () => {
    const { nodes, edges } = treeToGraph(props(2), rels({ t: 'I', args: [{ kind: 'P', id: 1 }, { kind: 'P', id: 2 }] }))
    const idNodes = nodes.filter((n) => n.type === 'identity')
    expect(idNodes).toHaveLength(1)
    expect(idNodes[0].data?.label).toBe('p1 / p2')
    expect(edges.every((e) => e.markerEnd === undefined)).toBe(true)
  })
})

describe('嵌套结构（指南 6.3）', () => {
  it('6.3.1 组合内嵌匹配 M(J(p1,p2),p3)：不新建节点，内层 ⊕ 承担组合与匹配', () => {
    const rs = rels(
      { t: 'J', args: [{ kind: 'P', id: 1 }, { kind: 'P', id: 2 }] },
      { t: 'M', args: [{ kind: 'R', id: 0 }, { kind: 'P', id: 3 }] },
    )
    const { nodes, edges } = treeToGraph(props(3), rs)
    const relNodes = nodes.filter((n) => n.type === 'relation')
    expect(relNodes).toHaveLength(1) // 只有内层 ⊕，M 不新建节点
    expect(relNodes[0].data?.relType).toBe('J')
    // 内层 ⊕ → p3 有箭头
    const toP3 = edges.find((e) => e.target === 'p3')
    expect(toP3?.markerEnd?.type).toBe('arrowclosed')
    expect(toP3?.source).toBe(relNodes[0].id)
  })

  it('6.3.2 匹配内嵌组合 J(M1,M2)：两个匹配节点 + 新 ⊕ 连接', () => {
    const rs = rels(
      { t: 'M', args: [{ kind: 'P', id: 1 }, { kind: 'P', id: 2 }] },
      { t: 'M', args: [{ kind: 'P', id: 3 }, { kind: 'P', id: 4 }] },
      { t: 'J', args: [{ kind: 'R', id: 0 }, { kind: 'R', id: 1 }] },
    )
    const { nodes, edges } = treeToGraph(props(4), rs)
    const relNodes = nodes.filter((n) => n.type === 'relation')
    expect(relNodes).toHaveLength(3)
    const jNode = relNodes.find((n) => n.data?.relType === 'J')!
    // J 节点与两个 M 节点之间的无向边
    const jEdges = edges.filter((e) => e.source === jNode.id || e.target === jNode.id)
    expect(jEdges).toHaveLength(2)
    expect(jEdges.every((e) => e.markerEnd === undefined)).toBe(true)
  })

  it('6.3.3 组合内嵌支持 S(J(p1,p2),p3)：⊕ → ● → p3', () => {
    const rs = rels(
      { t: 'J', args: [{ kind: 'P', id: 1 }, { kind: 'P', id: 2 }] },
      { t: 'S', args: [{ kind: 'R', id: 0 }, { kind: 'P', id: 3 }] },
    )
    const { nodes, edges } = treeToGraph(props(3), rs)
    const jNode = nodes.find((n) => n.type === 'relation' && n.data?.relType === 'J')!
    const sNode = nodes.find((n) => n.type === 'relation' && n.data?.relType === 'S')!
    // 组合节点引出支持节点（无箭头），支持箭头指向 p3
    const jToS = edges.find((e) => e.source === jNode.id && e.target === sNode.id)
    expect(jToS?.markerEnd).toBeUndefined()
    const sToP3 = edges.find((e) => e.source === sNode.id && e.target === 'p3')
    expect(sToP3?.markerEnd?.type).toBe('arrowclosed')
  })

  it('6.3.4 匹配内嵌支持 S(M(p1,p2),p3)：以被匹配的一般判断 p2 为支持起点', () => {
    const rs = rels(
      { t: 'M', args: [{ kind: 'P', id: 1 }, { kind: 'P', id: 2 }] },
      { t: 'S', args: [{ kind: 'R', id: 0 }, { kind: 'P', id: 3 }] },
    )
    const { nodes, edges } = treeToGraph(props(3), rs)
    const sNode = nodes.find((n) => n.type === 'relation' && n.data?.relType === 'S')!
    // 支持关系自 p2（被匹配的一般判断）发出
    const p2ToS = edges.find((e) => e.source === 'p2' && e.target === sNode.id)
    expect(p2ToS).toBeTruthy()
    const sToP3 = edges.find((e) => e.source === sNode.id && e.target === 'p3')
    expect(sToP3?.markerEnd?.type).toBe('arrowclosed')
  })

  it('6.3.5 支持内嵌反对 A(p3, S(p1,p2))：反对箭头指向支持关系节点', () => {
    const rs = rels(
      { t: 'S', args: [{ kind: 'P', id: 1 }, { kind: 'P', id: 2 }] },
      { t: 'A', args: [{ kind: 'P', id: 3 }, { kind: 'R', id: 0 }] },
    )
    const { nodes, edges } = treeToGraph(props(3), rs)
    const aNode = nodes.find((n) => n.type === 'relation' && n.data?.relType === 'A')!
    const sNode = nodes.find((n) => n.type === 'relation' && n.data?.relType === 'S')!
    // ○ → ●（反对指向支持关系节点，箭头）
    const aToS = edges.find((e) => e.source === aNode.id && e.target === sNode.id)
    expect(aToS?.markerEnd?.type).toBe('arrowclosed')
  })

  it('6.3.6 多层嵌套 S(M(J(p1,p2,p3),p4),p5)：自内而外逐层构造', () => {
    const rs = rels(
      { t: 'J', args: [{ kind: 'P', id: 1 }, { kind: 'P', id: 2 }, { kind: 'P', id: 3 }] },
      { t: 'M', args: [{ kind: 'R', id: 0 }, { kind: 'P', id: 4 }] },
      { t: 'S', args: [{ kind: 'R', id: 1 }, { kind: 'P', id: 5 }] },
    )
    const { nodes, edges } = treeToGraph(props(5), rs)
    // 关系节点：内层 ⊕（J，同时承担 M）+ 支持 ●
    const relNodes = nodes.filter((n) => n.type === 'relation')
    expect(relNodes).toHaveLength(2)
    const jNode = relNodes.find((n) => n.data?.relType === 'J')!
    const sNode = relNodes.find((n) => n.data?.relType === 'S')!
    // 支持关系自 p4（被匹配的一般判断）发出
    const p4ToS = edges.find((e) => e.source === 'p4' && e.target === sNode.id)
    expect(p4ToS).toBeTruthy()
    // ● → p5 箭头
    const sToP5 = edges.find((e) => e.source === sNode.id && e.target === 'p5')
    expect(sToP5?.markerEnd?.type).toBe('arrowclosed')
    // 内层 ⊕ → p4 箭头（匹配方向）
    const jToP4 = edges.find((e) => e.source === jNode.id && e.target === 'p4')
    expect(jToP4?.markerEnd?.type).toBe('arrowclosed')
  })
})

describe('多子图与根识别', () => {
  it('文书一 R1-R10 结构：两个独立论证子图', () => {
    // 论证1：R1-R7（P4,P5,P2,P6 与 P7,P8,P6,P3,P9）……简化为两个独立 S
    const rs = rels(
      { t: 'S', args: [{ kind: 'P', id: 1 }, { kind: 'P', id: 2 }] },
      { t: 'S', args: [{ kind: 'P', id: 3 }, { kind: 'P', id: 4 }] },
    )
    const { nodes, edges } = treeToGraph(props(4), rs)
    expect(relationRoots(rs)).toEqual([0, 1])
    const comps = connectedComponents(nodes, edges)
    expect(comps).toHaveLength(2)
  })

  it('独立命题（无关系）各自成子图', () => {
    const { nodes, edges } = treeToGraph(props(3), [])
    const comps = connectedComponents(nodes, edges)
    expect(comps).toHaveLength(3)
  })
})
