"""多版本差异比对（裁定与教学比对共用，需求 4.1 + 指南 8.2.4）。

- 命题对齐：精确边界优先，剩余 IoU>0.5 贪心模糊匹配
- 关系比对：表达式指纹（seq 经对齐映射归一）集合差
  分类：类型差异 / 方向差异 / 嵌套差异 / missing（仅 A 有）/ extra（仅 B 有）
- 颗粒度差异率：命题覆盖区间的字符级 Jaccard 差异（10% 阈值提示）
"""
from dataclasses import dataclass, field


@dataclass
class PropRow:
    """比对用的命题行（id 为数据库 id）。"""
    id: int
    seq: int
    start: int
    end: int
    text: str
    type_code: str | None
    subtype_code: str | None
    edited_text: str | None = None


def _iou(a: PropRow, b: PropRow) -> float:
    inter = max(0, min(a.end, b.end) - max(a.start, b.start))
    union = max(a.end, b.end) - min(a.start, b.start)
    return inter / union if union > 0 else 0.0


def align_propositions(a: list[PropRow], b: list[PropRow]) -> list[dict]:
    """命题对齐 → 差异列表（按类别分类）。

    类别：identical / boundary / type / subtype / edited_text / only_a / only_b
    """
    used_a: set[int] = set()
    used_b: set[int] = set()
    diffs: list[dict] = []
    # 1. 精确边界匹配
    b_by_span: dict[tuple[int, int], list[int]] = {}
    for j, pb in enumerate(b):
        b_by_span.setdefault((pb.start, pb.end), []).append(j)
    for i, pa in enumerate(a):
        js = b_by_span.get((pa.start, pa.end), [])
        for j in js:
            if j in used_b:
                continue
            diffs.append(_classify(pa, b[j]))
            used_a.add(i)
            used_b.add(j)
            break
    # 2. 剩余 IoU>0.5 贪心模糊匹配（按 IoU 降序）
    candidates = []
    for i, pa in enumerate(a):
        if i in used_a:
            continue
        for j, pb in enumerate(b):
            if j in used_b:
                continue
            v = _iou(pa, pb)
            if v > 0.5:
                candidates.append((v, i, j))
    for _, i, j in sorted(candidates, reverse=True):
        if i in used_a or j in used_b:
            continue
        diffs.append(_classify(a[i], b[j]))
        used_a.add(i)
        used_b.add(j)
    # 3. 未匹配
    for i, pa in enumerate(a):
        if i not in used_a:
            diffs.append({"category": "only_a", "a": pa, "b": None})
    for j, pb in enumerate(b):
        if j not in used_b:
            diffs.append({"category": "only_b", "a": None, "b": pb})
    return diffs


def _classify(pa: PropRow, pb: PropRow) -> dict:
    if pa.edited_text or pb.edited_text:
        cat = "edited_text"
    elif pa.type_code != pb.type_code:
        cat = "type"
    elif pa.subtype_code != pb.subtype_code:
        cat = "subtype"
    elif pa.text != pb.text:
        cat = "boundary"
    else:
        cat = "identical"
    return {"category": cat, "a": pa, "b": pb}


def align_map(a: list[PropRow], b: list[PropRow]) -> dict[int, int]:
    """命题对齐映射：a 的 seq → b 的 seq（仅精确边界匹配）。"""
    b_by_span = {(p.start, p.end): p.seq for p in b}
    return {pa.seq: b_by_span[(pa.start, pa.end)]
            for pa in a if (pa.start, pa.end) in b_by_span}


def _expr_signature(rel: dict, seq_map: dict[int, int]) -> str:
    """关系树 → 归一化指纹（命题 seq 经对齐映射）。"""
    def render(args: list[dict]) -> str:
        parts = []
        for x in args:
            if x["kind"] == "P":
                parts.append(f"P{seq_map.get(x['id'], x['id'])}")
            else:
                parts.append(x["expr"])
        return parts

    # 递归结构已在 expr 字符串中；这里直接对根 expr 做 seq 替换
    expr: str = rel["expr"]
    # 用正则替换 P<num>
    import re
    def repl(m):
        n = int(m.group(1))
        return f"P{seq_map.get(n, n)}"
    return re.sub(r"P(\d+)", repl, expr)


def diff_relations(rels_a: list[dict], rels_b: list[dict],
                   seq_map_a_to_b: dict[int, int]) -> list[dict]:
    """关系差异：指纹集合差（类别 missing/extra/type/direction/nested）。"""
    # 归一化指纹（A 版 seq 映射到 B 版）
    norm_a = [_expr_signature(r, seq_map_a_to_b) for r in rels_a]
    norm_b = [r["expr"] for r in rels_b]
    # 结构与类型分离：指纹去类型化比较结构
    def struct_of(expr: str) -> str:
        return "".join(ch for ch in expr if ch not in "SAJMI")

    result: list[dict] = []
    used_b: set[int] = set()
    for i, ra in enumerate(rels_a):
        sig = norm_a[i]
        # 1) 完全一致（含类型）
        exact = [j for j in range(len(rels_b)) if j not in used_b and norm_b[j] == sig]
        if exact:
            used_b.add(exact[0])
            continue
        # 2) 结构一致但类型不同 / 方向不同
        struct = struct_of(sig)
        candidates = [j for j in range(len(rels_b))
                      if j not in used_b and struct_of(norm_b[j]) == struct]
        if candidates:
            j = candidates[0]
            used_b.add(j)
            if rels_b[j]["rel_type"] != ra["rel_type"]:
                result.append({"category": "type", "a_expr": ra["expr"],
                               "b_expr": rels_b[j]["expr"], "a": ra, "b": rels_b[j]})
            elif sig != norm_b[j]:
                result.append({"category": "direction", "a_expr": ra["expr"],
                               "b_expr": rels_b[j]["expr"], "a": ra, "b": rels_b[j]})
            else:
                result.append({"category": "nested", "a_expr": ra["expr"],
                               "b_expr": rels_b[j]["expr"], "a": ra, "b": rels_b[j]})
            continue
        # 3) 仅 A 有
        result.append({"category": "missing", "a_expr": ra["expr"],
                       "b_expr": None, "a": ra, "b": None})
    # 4) 仅 B 有
    for j in range(len(rels_b)):
        if j not in used_b:
            result.append({"category": "extra", "a_expr": None,
                           "b_expr": rels_b[j]["expr"], "a": None, "b": rels_b[j]})
    return result


def granularity_rate(a: list[PropRow], b: list[PropRow]) -> float | None:
    """颗粒度差异率：命题覆盖区间的字符级 Jaccard 差异 1 − |A∩B|/|A∪B|。"""
    if not a and not b:
        return None
    if not a or not b:
        return 1.0
    total_union = 0
    total_inter = 0
    # 逐对区间计算（命题区间一般无重叠；有重叠时近似）
    for pa in a:
        total_union += pa.end - pa.start
        for pb in b:
            total_inter += max(0, min(pa.end, pb.end) - max(pa.start, pb.start))
    for pb in b:
        total_union += pb.end - pb.start
    total_union -= total_inter  # 并集 = A + B − 交
    if total_union <= 0:
        return 0.0
    return round(1 - total_inter / total_union, 4)


def build_prop_rows(propositions: list) -> list[PropRow]:
    """数据库命题列表 → PropRow（seq 按 char_start 排序计算）。"""
    rows = []
    for seq, p in enumerate(sorted(propositions, key=lambda x: x.char_start), start=1):
        rows.append(PropRow(
            id=p.id, seq=seq, start=p.char_start, end=p.char_end,
            text=p.text, type_code=p.type_code, subtype_code=p.subtype_code,
            edited_text=p.edited_text,
        ))
    return rows
