"""指南接口（UC-01 从文件导入标注指南）。

流程：上传文件 → 解析返回预览（版本/正文/taxonomy 校对/重复提示）→ 确认保存。
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import MAX_UPLOAD_SIZE
from ..database import get_db
from ..models import Guide, User
from ..schemas.guide import GuideCreate, GuideOut, GuidePreview
from ..services.parser import parse_file
from ..services.taxonomy import default_taxonomy, extract_version

router = APIRouter(prefix="/guides", tags=["guides"])


def _guide_out(g: Guide) -> GuideOut:
    return GuideOut.model_validate(g)


@router.post("/import", response_model=GuidePreview)
async def import_preview(
    file: UploadFile,
    user: User = Depends(get_current_user),
):
    """上传指南文件 → 解析并返回预览（UC-01 基本流程 1-5）。"""
    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "文件超过 10MB 限制")
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "缺少文件名")
    try:
        text = parse_file(file.filename, data)
    except Exception:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "文件格式不支持或文件损坏，请重新选择（UC-01 异常流程 A1）")
    if not text.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "导入内容无法完整解析，请检查文件（UC-01 异常流程 A2）")
    return GuidePreview(
        version=extract_version(text, file.filename),
        name=file.filename.rsplit(".", 1)[0],
        source_filename=file.filename,
        text_preview=text[:2000],
        content_text=text,
        taxonomy=default_taxonomy(),
        duplicate_warning=None,  # 保存时才校验重复（预览阶段不落库）
    )


@router.post("", response_model=GuideOut)
def create_guide(body: GuideCreate, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """确认保存指南（UC-01 基本流程 6-7）。"""
    existing = db.query(Guide).filter(Guide.version == body.version).first()
    if existing and not body.overwrite:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"版本 {body.version} 已存在，请选择覆盖、另存为新版本或取消（UC-01 异常流程 A3）",
        )
    if existing:
        # 覆盖：更新原记录（保留 id，版本追溯不中断）
        existing.name = body.name
        existing.source_filename = body.source_filename
        existing.content_text = body.content_text
        existing.taxonomy = body.taxonomy
        db.commit()
        db.refresh(existing)
        return _guide_out(existing)
    guide = Guide(
        version=body.version,
        name=body.name,
        source_filename=body.source_filename,
        content_text=body.content_text,
        taxonomy=body.taxonomy,
        imported_by=user.id,
        is_active=False,
    )
    db.add(guide)
    db.commit()
    db.refresh(guide)
    return _guide_out(guide)


@router.get("", response_model=list[GuideOut])
def list_guides(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_guide_out(g) for g in
            db.query(Guide).order_by(Guide.created_at.desc()).all()]


@router.get("/{guide_id}", response_model=GuideOut)
def get_guide(guide_id: int, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    g = db.get(Guide, guide_id)
    if g is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "指南不存在")
    return _guide_out(g)


@router.post("/{guide_id}/activate", response_model=GuideOut)
def activate_guide(guide_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """设为默认激活版本（取消其他激活）。"""
    g = db.get(Guide, guide_id)
    if g is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "指南不存在")
    db.query(Guide).update({Guide.is_active: False})
    g.is_active = True
    db.commit()
    db.refresh(g)
    return _guide_out(g)
