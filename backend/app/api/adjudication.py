"""裁定接口（阶段三：冲突解决，UC-03 裁定关系的标注）。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import (
    can_manage_document, get_current_user, get_document_or_404,
    is_document_participant, require_arbiter, require_document_participant,
)
from ..database import get_db
from ..models import (
    Adjudication, AnnotationVersion, Document, Proposition, RelationNode, User,
)
from ..schemas.adjudication import (
    AdjudicateRequest, CompareGroupOut, CompareOut, PropDiffOut, RelDiffOut,
)
from ..schemas.annotation import VersionOut
from ..services.diff import (
    align_map, align_propositions, build_prop_rows, diff_relations, granularity_rate,
)
from ..services.guards import assert_not_locked

router = APIRouter(prefix="", tags=["adjudication"])

GRANULARITY_THRESHOLD = 0.10


def _load_version_content(db: Session, version_id: int):
    """加载版本内容：命题行（含 seq 与表达式）、关系（含 expr）。"""
    props = (
        db.query(Proposition)
        .filter(Proposition.version_id == version_id)
        .order_by(Proposition.char_start)
        .all()
    )
    seq_to_id: dict[int, int] = {}
    prop_dicts = []
    for seq, p in enumerate(props, start=1):
        seq_to_id[seq] = p.id
        prop_dicts.append({"seq": seq, "id": p.id, "start": p.char_start,
                           "end": p.char_end, "text": p.text,
                           "type_code": p.type_code, "subtype_code": p.subtype_code,
                           "edited_text": p.edited_text})
    rels = (
        db.query(RelationNode)
        .filter(RelationNode.version_id == version_id)
        .order_by(RelationNode.id)
        .all()
    )
    id_to_seq = {pid: s for s, pid in seq_to_id.items()}
    rel_dicts = []
    for r in rels:
        parts = []
        for a in r.args:
            if a["kind"] == "P":
                parts.append(f"P{id_to_seq.get(a['id'], '?')}")
            else:
                parts.append(_expr_of_id(a["id"], rels, id_to_seq))
        expr = f"{r.rel_type}({', '.join(parts)})"
        rel_dicts.append({"id": r.id, "rel_type": r.rel_type,
                          "args": r.args, "expr": expr})
    return prop_dicts, rel_dicts


def _expr_of_id(rid: int, rels: list[RelationNode], id_to_seq: dict[int, int]) -> str:
    for r in rels:
        if r.id == rid:
            parts = []
            for a in r.args:
                if a["kind"] == "P":
                    parts.append(f"P{id_to_seq.get(a['id'], '?')}")
                else:
                    parts.append(_expr_of_id(a["id"], rels, id_to_seq))
            return f"{r.rel_type}({', '.join(parts)})"
    return "?"


@router.get("/documents/{document_id}/compare", response_model=CompareOut)
def compare_document(
    document_id: int,
    base_version_id: int | None = None,
    base_kind: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """多版本差异载荷（裁定页与教学比对页共用）。

    base_kind 供教学比对选择基准类型：final（最终版）/ reference（标准答案）。
    访问控制：裁定者/创建者/管理员可见全部版本；被分配的标注员仅可比较"本人版本"，
    且须已提交（原型 2.1：教学入口不得在学生提交前暴露标准答案）。
    """
    doc = get_document_or_404(db, document_id)
    versions = (
        db.query(AnnotationVersion)
        .filter(AnnotationVersion.document_id == document_id)
        .order_by(AnnotationVersion.id)
        .all()
    )
    if not versions:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "该文档还没有任何标注版本")

    is_manager = can_manage_document(db, user, doc)
    if is_manager:
        visible = versions
    else:
        if not is_document_participant(db, user, doc):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "无权查看该文档的比对")
        own = [v for v in versions if v.annotator_id == user.id]
        if not own:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "您还没有可比的标注版本")
        if not any(v.status == "submitted" for v in own) and doc.status not in ("ADJUDICATED", "OUTPUT"):
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "请先提交标注，之后方可与标准答案/最终版比对")
        if base_version_id is not None:
            ok_base = any(v.id == base_version_id and
                          (v.annotator_id == user.id or v.kind in ("reference", "final"))
                          for v in versions)
            if not ok_base:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "无权以该版本为基准比对")
        visible = own

    # 基准：显式指定 id → 指定 kind → reference → final → 第一个
    base = None
    if base_version_id is not None:
        base = next((v for v in versions if v.id == base_version_id), None)
        if base is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "基准版本不存在")
    if base is None and base_kind in ("final", "reference"):
        base = next((v for v in versions if v.kind == base_kind), None)
    if base is None:
        base = next((v for v in versions if v.kind == "reference"), None) \
            or next((v for v in versions if v.kind == "final"), None) \
            or versions[0]

    base_props, base_rels = _load_version_content(db, base.id)
    base_rows = build_prop_rows(
        db.query(Proposition).filter(Proposition.version_id == base.id).all())

    groups: list[CompareGroupOut] = []
    any_exceeded = False
    for v in visible:
        v_props, v_rels = _load_version_content(db, v.id)
        v_rows = build_prop_rows(
            db.query(Proposition).filter(Proposition.version_id == v.id).all())
        rate = granularity_rate(base_rows, v_rows)
        if rate is not None and rate > GRANULARITY_THRESHOLD:
            any_exceeded = True

        # 命题差异（基准 vs 本版本）
        pdiffs: list[PropDiffOut] = []
        for d in align_propositions(base_rows, v_rows):
            a, b = d.get("a"), d.get("b")
            pdiffs.append(PropDiffOut(
                category=d["category"],
                a_seq=a.seq if a else None, b_seq=b.seq if b else None,
                a_text=a.text if a else None, b_text=b.text if b else None,
                a_type=a.type_code if a else None, b_type=b.type_code if b else None,
                a_subtype=a.subtype_code if a else None,
                b_subtype=b.subtype_code if b else None,
            ))

        # 关系差异（基准 → 本版本 的 seq 映射）
        seq_map = align_map(base_rows, v_rows)
        rdiffs: list[RelDiffOut] = []
        for d in diff_relations(base_rels, v_rels, seq_map):
            rdiffs.append(RelDiffOut(category=d["category"],
                                     a_expr=d["a_expr"], b_expr=d["b_expr"]))

        annotator = db.get(User, v.annotator_id)
        groups.append(CompareGroupOut(
            version_id=v.id, annotator_name=(annotator.display_name or annotator.username) if annotator else None,
            kind=v.kind, status=v.status,
            proposition_count=len(v_props), relation_count=len(v_rels),
            granularity_rate=rate, prop_diffs=pdiffs, relation_diffs=rdiffs,
        ))

    return CompareOut(base_version_id=base.id,
                      warn_threshold_exceeded=any_exceeded, groups=groups)


@router.post("/documents/{document_id}/adjudicate", response_model=VersionOut)
def adjudicate(document_id: int, body: AdjudicateRequest,
               db: Session = Depends(get_db),
               user: User = Depends(require_arbiter)):
    """以 base 版本为基础生成最终版（若已编辑过 final 工作副本则保留其内容）。"""
    doc = get_document_or_404(db, document_id)
    assert_not_locked(doc)
    base = db.get(AnnotationVersion, body.base_version_id)
    if base is None or base.document_id != document_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "基准版本不存在")

    # 查找已有 final 工作副本（裁定者重复提交时保留编辑）
    final = (
        db.query(AnnotationVersion)
        .filter(AnnotationVersion.document_id == document_id, AnnotationVersion.kind == "final")
        .order_by(AnnotationVersion.id.desc())
        .first()
    )
    if final is None:
        # 工作副本以草稿创建：裁定者进入标注页编辑（认可+修改），提交时定稿
        final = AnnotationVersion(document_id=document_id, annotator_id=user.id,
                                  kind="final", status="draft")
        db.add(final)
        db.flush()
        # 复制 base 内容（命题与关系 id 重映射）
        prop_id_map: dict[int, int] = {}
        for p in db.query(Proposition).filter(Proposition.version_id == base.id).all():
            np = Proposition(version_id=final.id, char_start=p.char_start,
                             char_end=p.char_end, text=p.text,
                             edited_text=p.edited_text, type_code=p.type_code,
                             subtype_code=p.subtype_code, flagged=p.flagged,
                             flag_note=p.flag_note)
            db.add(np)
            db.flush()
            prop_id_map[p.id] = np.id
        rel_id_map: dict[int, int] = {}
        for r in db.query(RelationNode).filter(RelationNode.version_id == base.id).all():
            nr = RelationNode(version_id=final.id, rel_type=r.rel_type,
                              args=[], note=r.note, flagged=r.flagged,
                              flag_note=r.flag_note)
            db.add(nr)
            db.flush()
            rel_id_map[r.id] = nr.id
        for r in db.query(RelationNode).filter(RelationNode.version_id == base.id).all():
            remapped = []
            for a in r.args:
                if a["kind"] == "P":
                    remapped.append({"kind": "P", "id": prop_id_map.get(a["id"], a["id"])})
                else:
                    remapped.append({"kind": "R", "id": rel_id_map.get(a["id"], a["id"])})
            new_rel = db.get(RelationNode, rel_id_map[r.id])
            new_rel.args = remapped
    else:
        # 已有工作副本：保留其内容与草稿状态（裁定者可继续编辑）
        pass

    db.add(Adjudication(document_id=document_id, adjudicator_id=user.id,
                        final_version_id=final.id,
                        chosen_base_version_id=body.base_version_id,
                        note=body.note))
    db.commit()

    # 复用 annotations 模块的输出组装
    from ..api.annotations import _version_out
    db.refresh(final)
    return _version_out(db, final, user)


@router.get("/documents/{document_id}/final", response_model=VersionOut)
def get_final(document_id: int, db: Session = Depends(get_db),
              user: User = Depends(require_document_participant)):
    """最终版内容（文档参与者/创建者/管理员可见，Q7）。

    与 compare 同规则：非管理者须"本人标注已提交"或文档已裁定/输出，
    否则 403（原型 2.1：不得在学生正式提交前暴露标准答案内容）。
    """
    doc = get_document_or_404(db, document_id)
    if not can_manage_document(db, user, doc):
        # 与 compare 同规则：本人任一版本（normal/reference）已提交即放行——
        # 标准答案作者天然知悉答案内容，无需过滤 kind
        own_submitted = (
            db.query(AnnotationVersion)
            .filter(AnnotationVersion.document_id == doc.id,
                    AnnotationVersion.annotator_id == user.id,
                    AnnotationVersion.status == "submitted")
            .first()
        ) is not None
        if not own_submitted and doc.status not in ("ADJUDICATED", "OUTPUT"):
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "请先提交标注，之后方可查看最终版")
    final = (
        db.query(AnnotationVersion)
        .filter(AnnotationVersion.document_id == document_id, AnnotationVersion.kind == "final")
        .order_by(AnnotationVersion.id.desc())
        .first()
    )
    if final is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "尚未裁定，无最终版本")
    from ..api.annotations import _version_out
    return _version_out(db, final, user)


@router.get("/versions/{version_id}", response_model=VersionOut)
def get_version(version_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """单版本内容（本人标注 / 裁定工作副本 / 教学比对加载指定版本）。

    仅本人、任务创建者、管理员或该文档裁定者可读取，避免越权窥探他人标注。
    """
    v = db.get(AnnotationVersion, version_id)
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "标注版本不存在")
    doc = get_document_or_404(db, v.document_id)
    if v.annotator_id != user.id and not can_manage_document(db, user, doc):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权查看该标注版本")
    from ..api.annotations import _version_out
    return _version_out(db, v, user)
