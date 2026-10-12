"""文档接口：上传解析、裁判理由提取校正、颗粒度切割（阶段一）。"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, get_document_or_404, get_task_or_404, require_task_creator
from ..config import MAX_UPLOAD_SIZE
from ..database import get_db
from ..models import Assignment, Document, Guide, Task, User
from ..models.document import DOC_TYPES
from ..schemas.document import (
    DocumentOut, DocumentUpdate, ReasoningUpdate, SegmentsUpdate,
    TextDocumentCreate, UploadResult,
)
from ..services.extraction import extract_reasoning
from ..services.guards import assert_not_locked
from ..services.parser import parse_file
from ..services.segmentation import segment_reasoning

router = APIRouter(prefix="", tags=["documents"])


def _doc_out(db: Session, doc: Document, user: User) -> DocumentOut:
    out = DocumentOut.model_validate(doc)
    task = db.get(Task, doc.task_id)
    out.task_name = task.name if task else None
    out.task_status = task.status if task else None
    out.guide_version = doc.guide_version_snapshot
    # 当前用户在该文档上的角色
    assign = (
        db.query(Assignment)
        .filter(Assignment.document_id == doc.id, Assignment.user_id == user.id)
        .first()
    )
    if assign:
        out.my_role = assign.role
    elif task and (task.created_by == user.id or user.is_admin):
        out.my_role = "creator"
    return out


def _build_document(db: Session, task: Task, name: str, doc_type: str,
                    source_filename: str, text: str) -> Document:
    """解析后的文本 → 提取裁判理由 → 自动切割 → 建文档。"""
    guide = db.get(Guide, task.guide_id)
    reasoning_text, start, end, method = extract_reasoning(text, doc_type)
    segments = segment_reasoning(reasoning_text) if reasoning_text else []
    doc = Document(
        task_id=task.id,
        name=name,
        doc_type=doc_type,
        source_filename=source_filename,
        original_text=text,
        reasoning_text=reasoning_text,
        reasoning_start=start,
        reasoning_end=end,
        extraction_method=method,
        base_segments=segments,
        guide_version_snapshot=guide.version if guide else "",
    )
    db.add(doc)
    db.flush()
    return doc


@router.post("/tasks/{task_id}/documents/upload", response_model=list[UploadResult])
async def upload_documents(task_id: int, files: list[UploadFile],
                           doc_type: str = "judgment",
                           db: Session = Depends(get_db),
                           user: User = Depends(get_current_user)):
    """批量上传文档（管理员功能）：解析 + 自动提取裁判理由 + 自动切割。"""
    task = get_task_or_404(db, task_id)
    require_task_creator(task, user)
    if doc_type not in DOC_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "文档类型无效")
    results: list[UploadResult] = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_UPLOAD_SIZE:
            results.append(UploadResult(filename=f.filename or "", ok=False,
                                        error="文件超过 10MB 限制"))
            continue
        try:
            text = parse_file(f.filename or "", data)
        except Exception:
            results.append(UploadResult(filename=f.filename or "", ok=False,
                                        error="文件格式不支持或文件损坏"))
            continue
        if not text.strip():
            results.append(UploadResult(filename=f.filename or "", ok=False,
                                        error="未能从文件中提取到文本"))
            continue
        doc = _build_document(db, task, (f.filename or "未命名").rsplit(".", 1)[0],
                              doc_type, f.filename or "", text)
        results.append(UploadResult(filename=f.filename or "", ok=True,
                                    document_id=doc.id,
                                    extraction_method=doc.extraction_method))
    db.commit()
    return results


@router.post("/tasks/{task_id}/documents/text", response_model=DocumentOut)
def create_text_document(task_id: int, body: TextDocumentCreate,
                         db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    """粘贴文本创建文档（测试或小样本）。"""
    task = get_task_or_404(db, task_id)
    require_task_creator(task, user)
    if body.doc_type not in DOC_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "文档类型无效")
    doc = _build_document(db, task, body.name, body.doc_type, "（手动录入）", body.text)
    db.commit()
    db.refresh(doc)
    return _doc_out(db, doc, user)


@router.get("/tasks/{task_id}/documents", response_model=list[DocumentOut])
def list_task_documents(task_id: int, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """任务内全部文档（创建者/管理员）；普通用户仅见自己被分配到的文档。"""
    task = get_task_or_404(db, task_id)
    if user.is_admin or task.created_by == user.id:
        docs = db.query(Document).filter(Document.task_id == task_id).all()
    else:
        assigned_ids = (
            db.query(Assignment.document_id)
            .filter(Assignment.task_id == task_id, Assignment.user_id == user.id)
        )
        docs = (db.query(Document)
                .filter(Document.task_id == task_id, Document.id.in_(assigned_ids))
                .all())
    return [_doc_out(db, d, user) for d in docs]


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    doc = get_document_or_404(db, document_id)
    return _doc_out(db, doc, user)


@router.patch("/documents/{document_id}", response_model=DocumentOut)
def update_document(document_id: int, body: DocumentUpdate,
                    db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    doc = get_document_or_404(db, document_id)
    task = get_task_or_404(db, doc.task_id)
    require_task_creator(task, user)
    assert_not_locked(doc)
    if body.name is not None:
        doc.name = body.name
    if body.case_info is not None:
        doc.case_info = body.case_info
    if body.doc_type is not None:
        if body.doc_type not in DOC_TYPES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "文档类型无效")
        doc.doc_type = body.doc_type
    db.commit()
    db.refresh(doc)
    return _doc_out(db, doc, user)


@router.put("/documents/{document_id}/reasoning", response_model=DocumentOut)
def update_reasoning(document_id: int, body: ReasoningUpdate,
                     db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """人工校正裁判理由范围（提取算法出错时允许人工修正，需求 6.2）。"""
    doc = get_document_or_404(db, document_id)
    task = get_task_or_404(db, doc.task_id)
    require_task_creator(task, user)
    assert_not_locked(doc)
    if body.start < 0 or body.end > len(doc.original_text) or body.end <= body.start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "提取范围无效")
    doc.reasoning_start = body.start
    doc.reasoning_end = body.end
    doc.reasoning_text = doc.original_text[body.start:body.end]
    doc.extraction_method = "manual_corrected"
    # 范围变化后清空切割结果，需重新切割
    doc.base_segments = []
    db.commit()
    db.refresh(doc)
    return _doc_out(db, doc, user)


@router.post("/documents/{document_id}/segment", response_model=DocumentOut)
def auto_segment(document_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """对裁判理由文本执行自动切割（幂等：覆盖 base_segments）。"""
    doc = get_document_or_404(db, document_id)
    task = get_task_or_404(db, doc.task_id)
    require_task_creator(task, user)
    assert_not_locked(doc)
    doc.base_segments = segment_reasoning(doc.reasoning_text)
    db.commit()
    db.refresh(doc)
    return _doc_out(db, doc, user)


@router.put("/documents/{document_id}/segments", response_model=DocumentOut)
def save_segments(document_id: int, body: SegmentsUpdate,
                  db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """保存人工调整后的切割结果（合并/拆分/删除/新建）。"""
    doc = get_document_or_404(db, document_id)
    task = get_task_or_404(db, doc.task_id)
    require_task_creator(task, user)
    assert_not_locked(doc)
    # 校验：偏移在范围内、不重叠、按序
    prev_end = -1
    cleaned = []
    for s in body.segments:
        if s.start < 0 or s.end > len(doc.reasoning_text) or s.end <= s.start:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "切割片段偏移无效")
        if s.start < prev_end:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "切割片段存在重叠")
        prev_end = s.end
        cleaned.append({"start": s.start, "end": s.end,
                        "text": doc.reasoning_text[s.start:s.end]})
    doc.base_segments = cleaned
    db.commit()
    db.refresh(doc)
    return _doc_out(db, doc, user)
