/**
 * deleteRelation 级联删除单元测试（修复：多层嵌套残留悬空 R 引用）。
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { useAnnotationStore } from './annotationStore'
import type { RelationArg, RelationNode, RelType } from '../types'

function rel(id: number, t: RelType, args: RelationArg[]): RelationNode {
  return { id: -(id + 1), version_id: 0, rel_type: t, args, note: '', flagged: false, flag_note: '' }
}

const P = (id: number): RelationArg => ({ kind: 'P', id })
const R = (id: number): RelationArg => ({ kind: 'R', id })

beforeEach(() => {
  useAnnotationStore.setState({
    relations: [], propositions: [], graphLayout: { positions: {} },
    undoStack: [], redoStack: [], versionId: null, editable: false,
  })
})

describe('deleteRelation 级联删除', () => {
  it('删除被嵌套引用的关系时，间接引用者一并删除（J←M←S 链删 M）', () => {
    useAnnotationStore.setState({ relations: [
      rel(0, 'J', [P(1), P(2)]),
      rel(1, 'M', [R(0), P(3)]),
      rel(2, 'S', [R(1), P(4)]),
      rel(3, 'S', [P(5), P(6)]),
    ] })
    useAnnotationStore.getState().deleteRelation(1)
    const rs = useAnnotationStore.getState().relations
    expect(rs).toHaveLength(2) // r2（S(R1,·) 引用了被删的 M）级联删除
    expect(rs.map((r) => r.rel_type)).toEqual(['J', 'S'])
    expect(rs[1].args).toEqual([P(5), P(6)]) // 独立关系不受影响
  })

  it('删除链根节点时整条链全部删除', () => {
    useAnnotationStore.setState({ relations: [
      rel(0, 'J', [P(1), P(2)]),
      rel(1, 'M', [R(0), P(3)]),
      rel(2, 'S', [R(1), P(4)]),
    ] })
    useAnnotationStore.getState().deleteRelation(0)
    expect(useAnnotationStore.getState().relations).toHaveLength(0)
  })

  it('删除无引用的独立关系只影响自身，其余 R 引用下标正确前移', () => {
    useAnnotationStore.setState({ relations: [
      rel(0, 'S', [P(1), P(2)]),
      rel(1, 'S', [P(3), P(4)]),
      rel(2, 'A', [R(0), P(5)]), // 引用 r0
    ] })
    useAnnotationStore.getState().deleteRelation(1)
    const rs = useAnnotationStore.getState().relations
    expect(rs).toHaveLength(2)
    expect(rs[0].rel_type).toBe('S')
    expect(rs[1].rel_type).toBe('A')
    expect(rs[1].args[0]).toEqual(R(0)) // 仍指向保留的 S（原 r0 → 新下标 0）
  })

  it('删除靠后的关系时，靠前关系的 R 引用下标不变', () => {
    useAnnotationStore.setState({ relations: [
      rel(0, 'S', [P(1), P(2)]),
      rel(1, 'A', [R(0), P(3)]),
      rel(2, 'S', [P(4), P(5)]),
    ] })
    useAnnotationStore.getState().deleteRelation(2)
    const rs = useAnnotationStore.getState().relations
    expect(rs).toHaveLength(2)
    expect(rs[1].args[0]).toEqual(R(0))
  })
})
