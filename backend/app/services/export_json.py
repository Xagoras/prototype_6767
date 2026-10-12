"""JSON 导出：结构化数据，包含字符索引位置、标签层级、关系定义（供模型训练）。"""
from ..models import Proposition, RelationNode


def build_export_json(version, doc, guide_version: str, props: list[Proposition],
                      rels: list[RelationNode]) -> dict:
    # 命题按 char_start 排序 → seq
    sorted_props = sorted(props, key=lambda p: p.char_start)
    seq_of_id: dict[int, int] = {p.id: s for s, p in enumerate(sorted_props, start=1)}
    id_to_seq = {p.id: s for s, p in enumerate(sorted_props, start=1)}

    def relation_tree(node: RelationNode) -> dict:
        args = []
        for a in node.args:
            if a["kind"] == "P":
                args.append({"proposition_seq": id_to_seq.get(a["id"], a["id"])})
            else:
                target = next((r for r in rels if r.id == a["id"]), None)
                args.append(relation_tree(target) if target else {"unknown": a["id"]})
        return {"type": node.rel_type, "args": args}

    return {
        "guide_version": guide_version,
        "document": {
            "name": doc.name,
            "doc_type": doc.doc_type,
            "case_info": doc.case_info,
        },
        "reasoning": {
            "text": doc.reasoning_text,
            "start": doc.reasoning_start,
            "end": doc.reasoning_end,
        },
        "propositions": [
            {
                "seq": seq,
                "text": p.text,
                "edited_text": p.edited_text,
                "char_start": p.char_start,
                "char_end": p.char_end,
                "type": p.type_code,
                "subtype": p.subtype_code,
            }
            for seq, p in enumerate(sorted_props, start=1)
        ],
        "relations": [relation_tree(r) for r in _roots(rels)],
        "exported_at": None,  # 由调用方填充
    }


def _is_referenced(node: RelationNode, rels: list[RelationNode]) -> bool:
    return any(a["kind"] == "R" and a["id"] == node.id for r in rels for a in r.args)


def _roots(rels: list[RelationNode]) -> list[RelationNode]:
    return [r for r in rels if not _is_referenced(r, rels)]
