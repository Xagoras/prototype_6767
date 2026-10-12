"""裁定记录与导出记录。"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Adjudication(Base):
    """一次裁定动作：记录依据（认可了哪个版本）与结果（final 版本）。"""

    __tablename__ = "adjudications"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    adjudicator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    final_version_id: Mapped[int] = mapped_column(ForeignKey("annotation_versions.id"))
    chosen_base_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("annotation_versions.id"), nullable=True
    )
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)


class ExportRecord(Base):
    """导出记录（Q17）：谁在何时下载了什么格式、对应哪个指南版本。

    任一记录产生即触发 document.status → OUTPUT 锁定。
    """

    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # json / excel / png / svg / jpg
    format: Mapped[str] = mapped_column(String(16))
    filename: Mapped[str] = mapped_column(String(255), default="")
    guide_version: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
