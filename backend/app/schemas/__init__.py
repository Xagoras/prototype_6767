"""Pydantic 请求/响应模型汇总。"""
from .assignment import AssignmentBatchCreate, AssignmentOut
from .auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from .document import DocumentOut, DocumentUpdate, ReasoningUpdate, SegmentsUpdate, TextDocumentCreate, UploadResult
from .guide import GuideCreate, GuideOut, GuidePreview
from .task import TaskCreate, TaskOut, TaskStatusAction, TaskUpdate

__all__ = [
    "LoginRequest", "RegisterRequest", "TokenResponse", "UserOut",
    "GuideCreate", "GuideOut", "GuidePreview",
    "TaskCreate", "TaskOut", "TaskStatusAction", "TaskUpdate",
    "DocumentOut", "DocumentUpdate", "ReasoningUpdate", "SegmentsUpdate",
    "TextDocumentCreate", "UploadResult",
    "AssignmentBatchCreate", "AssignmentOut",
]
