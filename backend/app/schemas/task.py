"""任务相关的请求/响应模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    guide_id: int
    annotators_per_doc: int = Field(default=2, ge=1, le=10)


class TaskUpdate(BaseModel):
    name: str | None = None
    settings: dict | None = None


class TaskStatusAction(BaseModel):
    # start（开始标注）/ to_adjudication（进入裁定）/ finish（完成）
    action: str = Field(pattern="^(start|to_adjudication|finish)$")


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    guide_id: int
    created_by: int
    status: str
    annotators_per_doc: int
    settings: dict
    created_at: datetime
    # 展示冗余字段
    guide_version: str | None = None
    document_count: int = 0
