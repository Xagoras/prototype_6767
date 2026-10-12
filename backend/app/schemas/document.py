"""文档（案例/文书）相关的请求/响应模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Segment(BaseModel):
    """颗粒度切割片段。"""
    start: int
    end: int
    text: str


class TextDocumentCreate(BaseModel):
    """粘贴文本创建文档（小样本/测试）。"""
    name: str = Field(min_length=1, max_length=255)
    doc_type: str = "judgment"
    text: str = Field(min_length=10)


class DocumentUpdate(BaseModel):
    name: str | None = None
    doc_type: str | None = None
    case_info: dict | None = None


class ReasoningUpdate(BaseModel):
    """人工校正裁判理由范围（相对 original_text 的码点偏移）。"""
    start: int
    end: int


class SegmentsUpdate(BaseModel):
    """人工调整后的切割结果（相对 reasoning_text）。"""
    segments: list[Segment]


class UploadResult(BaseModel):
    """单个文件上传处理结果。"""
    filename: str
    ok: bool
    error: str | None = None
    document_id: int | None = None
    extraction_method: str | None = None  # auto / manual_required


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    name: str
    doc_type: str
    source_filename: str
    original_text: str
    reasoning_text: str
    reasoning_start: int | None
    reasoning_end: int | None
    extraction_method: str
    case_info: dict
    base_segments: list
    guide_version_snapshot: str
    status: str
    created_at: datetime
    # 展示冗余字段
    task_name: str | None = None
    task_status: str | None = None
    guide_version: str | None = None
    my_role: str | None = None  # 当前用户在该文档上的角色（annotator/reference/arbiter/creator）
