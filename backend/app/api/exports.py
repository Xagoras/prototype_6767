"""导出接口（阶段四：结果输出）。

- JSON/Excel 后端生成文件流返回，同时写导出记录
- PNG/JPG/SVG 由前端生成下载，通过 /exports/record 登记
- 任一导出记录产生 → document.status=OUTPUT 锁定（写端点统一 403，需求 5.2/5.3）
"""
import json
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import (
    get_document_or_404, require_document_exporter, require_document_participant,
)
from ..database import get_db
from ..models import (
    AnnotationVersion, Document, ExportRecord, Proposition, RelationNode, User,
)
from ..schemas.adjudication import AdjudicateRequest  # noqa: F401（避免循环导入干扰）
from ..services.export_excel import build_excel
from ..services.export_json import build_export_json

router = APIRouter(prefix="", tags=["exports"])


class ExportRecordIn(BaseModel):
    format: str  # png / svg / jpg
    filename: str = ""


def _get_final(db: Session, doc: Document) -> AnnotationVersion:
    final = (
        db.query(AnnotationVersion)
        .filter(AnnotationVersion.document_id == doc.id, AnnotationVersion.kind == "final")
        .order_by(AnnotationVersion.id.desc())
        .first()
    )
    # 工作副本（kind=final, status=draft）不算"已定稿"：
    # 裁定者编辑期间导出/登记会把文档锁进 OUTPUT，导致定稿流程无法继续
    if final is None or final.status != "submitted":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "该文档最终版尚未定稿，无法导出")
    return final


def _record_and_lock(db: Session, doc: Document, user: User, fmt: str,
                     filename: str, guide_version: str) -> ExportRecord:
    rec = ExportRecord(document_id=doc.id, task_id=doc.task_id, user_id=user.id,
                       format=fmt, filename=filename, guide_version=guide_version)
    db.add(rec)
    doc.status = "OUTPUT"  # 任一导出 → 锁定（流程不可回退）
    db.commit()
    return rec


@router.post("/documents/{document_id}/export")
def export_document(document_id: int, format: str = "json",
                    filename: str = "",
                    db: Session = Depends(get_db),
                    user: User = Depends(require_document_exporter)):
    """导出最终版：json / excel 文件流（同时写记录并锁定）。"""
    doc = get_document_or_404(db, document_id)
    final = _get_final(db, doc)
    props = (db.query(Proposition).filter(Proposition.version_id == final.id)
             .order_by(Proposition.char_start).all())
    rels = (db.query(RelationNode).filter(RelationNode.version_id == final.id)
            .order_by(RelationNode.id).all())
    guide_version = doc.guide_version_snapshot

    fname = filename or f"{doc.name or 'document'}_{doc.id}"

    def disposition(ext: str) -> str:
        # RFC 5987：中文文件名走 filename*（UTF-8 百分号编码）
        return f"attachment; filename=export.{ext}; filename*=UTF-8''{quote(fname)}.{ext}"

    if format == "json":
        data = build_export_json(final, doc, guide_version, props, rels)
        data["exported_at"] = datetime.now(timezone.utc).isoformat()
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        _record_and_lock(db, doc, user, "json", f"{fname}.json", guide_version)
        return Response(
            content=body, media_type="application/json",
            headers={"Content-Disposition": disposition("json")},
        )
    if format == "excel":
        body = build_excel(doc, guide_version, props, rels)
        _record_and_lock(db, doc, user, "excel", f"{fname}.xlsx", guide_version)
        return Response(
            content=body,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": disposition("xlsx")},
        )
    raise HTTPException(status.HTTP_400_BAD_REQUEST,
                        "格式无效（支持 json / excel；图片导出请在前端图示区操作）")


@router.post("/documents/{document_id}/exports/record")
def record_image_export(document_id: int, body: ExportRecordIn,
                        db: Session = Depends(get_db),
                        user: User = Depends(require_document_exporter)):
    """前端生成的 PNG/SVG/JPG 本地下载后登记记录（同样触发锁定）。"""
    doc = get_document_or_404(db, document_id)
    if body.format not in ("png", "svg", "jpg"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "图片格式无效")
    _get_final(db, doc)  # 仅"已定稿"（kind=final 且 status=submitted）的文档才允许登记并锁定
    rec = _record_and_lock(db, doc, user, body.format, body.filename,
                           doc.guide_version_snapshot)
    return {"ok": True, "id": rec.id}


@router.get("/documents/{document_id}/exports")
def list_exports(document_id: int, db: Session = Depends(get_db),
                 user: User = Depends(require_document_participant)):
    """导出记录列表（谁在何时下载了什么格式）。"""
    get_document_or_404(db, document_id)
    rows = (db.query(ExportRecord)
            .filter(ExportRecord.document_id == document_id)
            .order_by(ExportRecord.id.desc()).all())
    out = []
    for r in rows:
        u = db.get(User, r.user_id)
        out.append({
            "id": r.id, "document_id": r.document_id, "task_id": r.task_id,
            "user_id": r.user_id, "format": r.format, "filename": r.filename,
            "guide_version": r.guide_version,
            "created_at": r.created_at.isoformat(),
            "username": (u.display_name or u.username) if u else None,
        })
    return out
