/**
 * 前端关系表达式生成（本地 relations：args 中 P 引用 seq、R 引用数组下标）。
 * 与后端 services/expr.py 规则一致，用于 RelationBuilder 实时预览。
 */
import type { RelationNode } from '../types'

/** 生成单个关系的表达式（含嵌套），如 S(M(J(P1,P2,P3),P4),P5) */
export function relationExpr(index: number, relations: RelationNode[]): string {
  const rel = relations[index]
  const parts = rel.args.map((a) =>
    a.kind === 'P' ? `P${a.id}` : relationExpr(a.id, relations),
  )
  return `${rel.rel_type}(${parts.join(', ')})`
}

/** 生成全部根关系（含数组下标，供删除/标记操作定位） */
export function allRootExprs(relations: RelationNode[]): { index: number; expr: string }[] {
  const referenced = new Set<number>()
  for (const r of relations) {
    for (const a of r.args) if (a.kind === 'R') referenced.add(a.id)
  }
  return relations
    .map((_, i) => i)
    .filter((i) => !referenced.has(i))
    .map((i) => ({ index: i, expr: relationExpr(i, relations) }))
}

/** 生成单个根关系的嵌套对象树（导出用） */
export function relationTree(index: number, relations: RelationNode[]): Record<string, unknown> {
  const rel = relations[index]
  return {
    type: rel.rel_type,
    args: rel.args.map((a) =>
      a.kind === 'P' ? { proposition_seq: a.id } : relationTree(a.id, relations),
    ),
  }
}
