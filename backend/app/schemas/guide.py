"""指南相关的请求/响应模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GuideCreate(BaseModel):
    """确认保存指南（导入预览后提交）。"""
    version: str = Field(min_length=1, max_length=32)
    name: str = Field(default="", max_length=128)
    source_filename: str = Field(default="", max_length=255)
    content_text: str = ""
    taxonomy: dict = Field(default_factory=dict)
    # 同版本已存在时：True 覆盖原记录，False（默认）返回 409 由前端提示
    overwrite: bool = False


class GuideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: str
    name: str
    source_filename: str
    content_text: str
    taxonomy: dict
    is_active: bool
    created_at: datetime


class GuidePreview(BaseModel):
    """导入预览：不落库，供用户校对后确认保存（UC-01 基本流程 5-6）。"""
    version: str
    name: str
    source_filename: str
    text_preview: str  # 前 2000 字
    content_text: str
    taxonomy: dict
    duplicate_warning: str | None  # 同版本已存在时的提示（UC-01 A3）
