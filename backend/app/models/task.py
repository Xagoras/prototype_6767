"""标注任务表。任务创建后指南不可换（标签体系不变，Q3）。"""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base

# 任务状态机：CREATED → ANNOTATING → ADJUDICATING → OUTPUT（单向流转）
TASK_STATUSES = ("CREATED", "ANNOTATING", "ADJUDICATING", "OUTPUT")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    guide_id: Mapped[int] = mapped_column(ForeignKey("guides.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(16), default="CREATED")
    # 每份文档的独立标注人数（默认 2，双人独立标注）
    annotators_per_doc: Mapped[int] = mapped_column(Integer, default=2)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
