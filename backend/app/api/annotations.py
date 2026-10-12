"""标注接口（阶段二：标注者进行标注）。

- 版本按人按文档一条（normal/reference），懒创建（首次访问自动建）
- 保存为全量替换（delete + insert），命题序号按 char_start 实时计算
- 关系 args 在保存请求中：P 引用命题序号、R 引用关系下标；落库时转换为实际 id
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, get_document_or_404, get_task_or_404
from ..database import get_db
from ..models import (
    AnnotationVersion, Assignment, Document, Guide, Proposition,
    RelationNode, Task, User,
)
from ..schemas.annotation import (
    PropositionOut, RelationOut, VersionContentIn, VersionMeta, VersionOut,
)
from ..services.expr import build_expr, relation_roots, validate_relations
from ..services.guards import assert_not_locked

router = APIRouter(prefix="", tags=["annotations"])


def _version_kind_for(db: Session, doc: Document, user: User) -> str:
    """按分配角色确定版本 kind：annotator→normal、reference→reference。

    任务创建者/管理员无分配记录时默认 normal。
    """
    assign = (
        db.query(Assignment)
        .filter(Assignment.document_id == doc.id, Assignment.user_id == user.id)
        .first()
    )
    if assign:
        if assign.role == "annotator":
            return "normal"
        if assign.role == "reference":
            return "reference"
        # arbiter 不持有标注版本
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "裁定者不进行标注，请前往裁定页面")
    task = get_task_or_404(db, doc.task_id)
    if task.created_by == user.id or user.is_admin:
        return "normal"
    raise HTTPException(status.HTTP_403_FORBIDDEN, "您未被分配该文档的标注任务")


def _get_or_create_version(db: Session, doc: Document, user: User) -> AnnotationVersion:
    kind = _version_kind_for(db, doc, user)
    v = (
        db.query(AnnotationVersion)
        .filter(AnnotationVersion.document_id == doc.id,
                AnnotationVersion.annotator_id == user.id,
                AnnotationVersion.kind == kind)
        .first()
    )
    if v is None:
        v = AnnotationVersion(document_id=doc.id, annotator_id=user.id, kind=kind)
        db.add(v)
        db.commit()
        db.refresh(v)
    return v


def _version_out(db: Session, v: AnnotationVersion, user: User) -> VersionOut:
    props = (
        db.query(Proposition)
        .filter(Proposition.version_id == v.id)
        .order_by(Proposition.char_start)
        .all()
    )
    # 序号实时计算 + seq→id 映射（表达式生成用）
    seq_to_id: dict[int, int] = {}
    prop_outs: list[PropositionOut] = []
    for seq, p in enumerate(props, start=1):
        seq_to_id[seq] = p.id
        po = PropositionOut.model_validate(p)
        po.seq = seq
        prop_outs.append(po)

    rels = (
        db.query(RelationNode)
        .filter(RelationNode.version_id == v.id)
        .order_by(RelationNode.id)
        .all()
    )
    id_to_idx: dict[int, int] = {r.id: i for i, r in enumerate(rels)}
    # 落库 args 的 P id 为实际命题 id：表达式需要 seq。反向映射 id→seq
    id_to_seq: dict[int, int] = {pid: s for s, pid in seq_to_id.items()}
    rel_outs: list[RelationOut] = []
    for r in rels:
        expr_args = []
        for a in r.args:
            expr_args.append({"kind": a["kind"], "id": a["id"]})
        ro = RelationOut.model_validate(r)
        ro.expr = _expr_of(db, r, id_to_idx, id_to_seq, v)
        rel_outs.append(ro)

    doc = db.get(Document, v.document_id)
    annotator = db.get(User, v.annotator_id)
    out = VersionOut(
        id=v.id, document_id=v.document_id, annotator_id=v.annotator_id,
        kind=v.kind, status=v.status, graph_layout=v.graph_layout, note=v.note,
        created_at=v.created_at, updated_at=v.updated_at, submitted_at=v.submitted_at,
        propositions=prop_outs, relations=rel_outs,
        annotator_name=annotator.display_name or annotator.username if annotator else None,
        document_name=doc.name if doc else None,
        editable=(v.annotator_id == user.id and v.status == "draft"
                  and doc is not None and doc.status != "OUTPUT"),
    )
    return out


def _expr_of(db: Session, node: RelationNode, id_to_idx: dict[int, int],
             id_to_seq: dict[int, int], version: AnnotationVersion) -> str:
    """落库关系节点 → 形式化表达式（P 引用转 seq）。"""
    rels = (
        db.query(RelationNode)
        .filter(RelationNode.version_id == version.id)
        .order_by(RelationNode.id)
        .all()
    )

    def render(rid: int, seen: set[int]) -> str:
        r = rels[id_to_idx[rid]]
        parts = []
        for a in r.args:
            if a["kind"] == "P":
                parts.append(f"P{id_to_seq.get(a['id'], '?')}")
            else:
                parts.append(render(a["id"], seen))
        return f"{r.rel_type}({', '.join(parts)})"

    return render(node.id, set())


def _validate_taxonomy(db: Session, v: AnnotationVersion, payload: VersionContentIn) -> None:
    """按指南 taxonomy 校验命题类型与子类型（找不到指南则跳过）。"""
    doc = db.get(Document, v.document_id)
    task = db.get(Task, doc.task_id) if doc else None
    guide = db.get(Guide, task.guide_id) if task else None
    if guide is None or not guide.taxonomy:
        return
    elements = {e["code"]: e for e in guide.taxonomy.get("elements", [])}
    for p in payload.propositions:
        if p.type_code is None:
            continue
        if p.type_code not in elements:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"命题类型 {p.type_code} 不在当前指南标签体系中")
        if p.subtype_code:
            subtypes = {s["code"] for s in elements[p.type_code].get("subtypes", [])}
            if p.subtype_code not in subtypes:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    f"子类型 {p.subtype_code} 不属于 {p.type_code}")


@router.get("/documents/{document_id}/my-version", response_model=VersionOut)
def my_version(document_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    """我的当前版本（懒创建）：标注页数据源。"""
    doc = get_document_or_404(db, document_id)
    v = _get_or_create_version(db, doc, user)
    return _version_out(db, v, user)


@router.get("/documents/{document_id}/versions", response_model=list[VersionMeta])
def list_versions(document_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """版本元数据：标注员仅见自己的；裁定者/创建者见所有。"""
    doc = get_document_or_404(db, document_id)
    q = db.query(AnnotationVersion).filter(AnnotationVersion.document_id == document_id)
    task = get_task_or_404(db, doc.task_id)
    is_arbiter = (
        db.query(Assignment)
        .filter(Assignment.document_id == document_id, Assignment.user_id == user.id,
                Assignment.role == "arbiter")
        .first()
    ) is not None
    if not (user.is_admin or task.created_by == user.id or is_arbiter):
        q = q.filter(AnnotationVersion.annotator_id == user.id)
    metas = []
    for v in q.order_by(AnnotationVersion.id).all():
        u = db.get(User, v.annotator_id)
        metas.append(VersionMeta(
            id=v.id, document_id=v.document_id, annotator_id=v.annotator_id,
            kind=v.kind, status=v.status, created_at=v.created_at,
            updated_at=v.updated_at, submitted_at=v.submitted_at,
            annotator_name=(u.display_name or u.username) if u else None,
            proposition_count=db.query(Proposition).filter(Proposition.version_id == v.id).count(),
            relation_count=db.query(RelationNode).filter(RelationNode.version_id == v.id).count(),
        ))
    return metas


@router.put("/versions/{version_id}/content", response_model=VersionOut)
def save_content(version_id: int, payload: VersionContentIn,
                 db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """全量保存标注内容（防抖调用；undo/redo 快照恢复也走此端点）。"""
    v = db.get(AnnotationVersion, version_id)
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "标注版本不存在")
    if v.annotator_id != user.id and not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只能编辑自己的标注版本")
    if v.status == "submitted":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "已提交的版本不可修改")
    doc = get_document_or_404(db, v.document_id)
    assert_not_locked(doc)

    # 文本与偏移校验（服务器文本是唯一权威，需求 3.2 字符索引定位）
    for p in payload.propositions:
        if p.char_start < 0 or p.char_end > len(doc.reasoning_text) or p.char_end <= p.char_start:
            raise HTTPException(status.HTTP_409_CONFLICT, "命题偏移超出裁判理由范围，请重新选择")
        server_text = doc.reasoning_text[p.char_start:p.char_end]
        if p.text != server_text:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "命题文本与原文不一致（文本可能已变更），请重新选择标注范围")

    _validate_taxonomy(db, v, payload)

    # 命题保存：先清旧，插入新并建立 seq→id 映射
    db.query(Proposition).filter(Proposition.version_id == v.id).delete()
    db.query(RelationNode).filter(RelationNode.version_id == v.id).delete()
    # 命题按 char_start 排序后分配 seq
    props_sorted = sorted(payload.propositions, key=lambda p: p.char_start)
    seq_to_id: dict[int, int] = {}
    for seq, p in enumerate(props_sorted, start=1):
        row = Proposition(
            version_id=v.id, char_start=p.char_start, char_end=p.char_end,
            text=p.text, edited_text=p.edited_text,
            type_code=p.type_code, subtype_code=p.subtype_code,
            flagged=p.flagged, flag_note=p.flag_note,
        )
        db.add(row)
        db.flush()
        seq_to_id[seq] = row.id

    # 关系校验（payload 层：P 引用 seq、R 引用下标）
    prop_seq_set = set(seq_to_id.keys())
    validate_relations([r.model_dump() for r in payload.relations], prop_seq_set)

    # 关系落库：args 转换为实际 id
    relations: list[RelationNode] = []
    idx_to_db_id: dict[int, int] = {}
    for i, r in enumerate(payload.relations):
        row = RelationNode(
            version_id=v.id, rel_type=r.rel_type,
            args=[], note=r.note, flagged=r.flagged, flag_note=r.flag_note,
        )
        db.add(row)
        db.flush()
        idx_to_db_id[i] = row.id
        relations.append(row)
    for i, r in enumerate(payload.relations):
        args = []
        for a in r.args:
            if a.kind == "P":
                args.append({"kind": "P", "id": seq_to_id[a.id]})
            else:
                args.append({"kind": "R", "id": idx_to_db_id[a.id]})
        relations[i].args = args

    v.graph_layout = payload.graph_layout
    if doc.status in ("CREATED", "ASSIGNED"):
        doc.status = "ANNOTATING"
    db.commit()
    db.refresh(v)
    return _version_out(db, v, user)


@router.post("/versions/{version_id}/submit", response_model=VersionOut)
def submit_version(version_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """提交标注（提交后版本只读）。"""
    v = db.get(AnnotationVersion, version_id)
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "标注版本不存在")
    if v.annotator_id != user.id and not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只能提交自己的标注版本")
    doc = get_document_or_404(db, v.document_id)
    assert_not_locked(doc)
    if v.status == "submitted":
        raise HTTPException(status.HTTP_409_CONFLICT, "版本已提交")
    from datetime import datetime, timezone
    v.status = "submitted"
    v.submitted_at = datetime.now(timezone.utc)
    # 所有 annotator 版本都提交后，文档进入 SUBMITTED（等待裁定）
    if v.kind == "normal":
        all_normal = (
            db.query(AnnotationVersion)
            .filter(AnnotationVersion.document_id == doc.id, AnnotationVersion.kind == "normal")
            .all()
        )
        if all(v2.status == "submitted" for v2 in all_normal) and all_normal:
            doc.status = "SUBMITTED"
    db.commit()
    db.refresh(v)
    return _version_out(db, v, user)
