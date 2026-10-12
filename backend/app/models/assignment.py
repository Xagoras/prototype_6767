"""任务分配表：案例 ↔ 用户 多对多（Q 确认）。

role：annotator（标注员）/ reference（标准答案标注者，教师）/ arbiter（裁定者）。
任务开始后允许增删分配（Q1/Q2 确认：人员可更新、数据可增加）。
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base

ASSIGNMENT_ROLES = ("annotator", "reference", "arbiter")


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        UniqueConstraint("document_id", "user_id", "role", name="uq_doc_user_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
