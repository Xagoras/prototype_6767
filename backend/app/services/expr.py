"""关系树：形式化表达式生成与结构校验（指南 5.2 / 5.3）。

存储约定（见 models/annotation.py RelationNode.args）：
- args 为有序数组 [{kind:"P", id: seq}, {kind:"R", id: payload 下标}]
  同一保存请求内，P 引用命题序号（按 char_start 排序），R 引用关系在数组中的下标。
- 树根 = 不被任何其他节点 args 引用的节点；每个根即一个独立论证子图。
"""
from fastapi import HTTPException

REL_ARITY = {"S": 2, "A": 2, "M": 2}  # J/I 至少 2


def validate_relations(relations: list[dict], prop_seq_set: set[int]) -> None:
    """校验一次保存请求中的关系列表（payload 层，P 引用 seq、R 引用下标）。

    规则：引用存在、元数（S/A/M 恰 2，J/I ≥2）、无环、叶子必须为命题。
    """
    n = len(relations)
    for i, rel in enumerate(relations):
        t = rel.get("rel_type")
        args = rel.get("args") or []
        if t not in REL_ARITY and t not in ("J", "I"):
            raise HTTPException(422, f"关系类型无效：{t}")
        if t in REL_ARITY and len(args) != 2:
            raise HTTPException(422, f"关系 {t} 需要恰好 2 个参数（表达式括号层级与逻辑层级不一致）")
        if t in ("J", "I") and len(args) < 2:
            raise HTTPException(422, f"关系 {t} 需要至少 2 个参数")
        for a in args:
            if a["kind"] == "P":
                if a["id"] not in prop_seq_set:
                    raise HTTPException(422, f"关系引用了不存在的命题（序号 {a['id']}）")
            elif a["kind"] == "R":
                if not (0 <= a["id"] < n):
                    raise HTTPException(422, "关系引用了不存在的关系节点")
                if a["id"] == i:
                    raise HTTPException(422, "关系不能引用自身")
            else:
                raise HTTPException(422, "关系参数类型无效")

    # 无环校验（DFS）
    visiting: set[int] = set()
    visited: set[int] = set()

    def dfs(idx: int) -> None:
        if idx in visiting:
            raise HTTPException(422, "关系结构存在环")
        if idx in visited:
            return
        visiting.add(idx)
        for a in relations[idx].get("args") or []:
            if a["kind"] == "R":
                dfs(a["id"])
        visiting.remove(idx)
        visited.add(idx)

    for i in range(n):
        dfs(i)

    # 叶子必须为命题：每个关系节点 args 若全为 R 会悬空——检查树根可达且叶子是 P
    # 由 dfs 保证结构；叶子检查：不存在 args 全为 R 且被引用（该情况 DFS 后自然无 P 叶子）
    # 额外检查：所有节点 args 中至少有一个 P（除被引用节点）——由"叶子必须为命题"推导：
    # 对每个关系，其 args 中必须存在 P 或（R 且该 R 自身最终有 P 叶子），DFS 已保证可达性
    # 这里直接验证：每个节点的 args 不允许全部为 R（防止纯关系嵌套无命题落地）
    for i, rel in enumerate(relations):
        args = rel.get("args") or []
        if args and all(a["kind"] == "R" for a in args):
            raise HTTPException(422, "关系节点不能全部由关系组成，叶子必须为命题")


def build_expr(idx: int, relations: list[dict], seq_map: dict[int, int]) -> str:
    """生成形式化表达式，如 S(M(J(P1,P2,P3),P4),P5)。

    idx：关系在列表中的下标；seq_map：命题 seq → 序号（一般恒等，用于差异比对归一）。
    """
    rel = relations[idx]
    parts = []
    for a in rel["args"]:
        if a["kind"] == "P":
            parts.append(f"P{seq_map.get(a['id'], a['id'])}")
        else:
            parts.append(build_expr(a["id"], relations, seq_map))
    return f"{rel['rel_type']}({', '.join(parts)})"


def relation_roots(relations: list[dict]) -> list[int]:
    """返回根关系下标列表（不被任何节点引用者）。"""
    referenced: set[int] = set()
    for rel in relations:
        for a in rel.get("args") or []:
            if a["kind"] == "R":
                referenced.add(a["id"])
    return [i for i in range(len(relations)) if i not in referenced]
