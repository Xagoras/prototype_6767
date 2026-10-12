"""任务分配相关的请求/响应模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssignmentBatchCreate(BaseModel):
    """批量分配：文档 × 用户 × 角色。"""
    document_ids: list[int]
    user_ids: list[int]
    roles: list[str]  # annotator / reference / arbiter


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    document_id: int
    user_id: int
    role: str
    assigned_by: int | None
    assigned_at: datetime
    # 展示冗余字段
    username: str | None = None
    display_name: str | None = None
    document_name: str | None = None
