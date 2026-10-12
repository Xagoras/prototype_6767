"""标注指南表：版本化，taxonomy 快照决定标注界面的标签按钮。"""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Guide(Base):
    __tablename__ = "guides"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(32))  # 如 "v1.1"
    name: Mapped[str] = mapped_column(String(128), default="")
    source_filename: Mapped[str] = mapped_column(String(255), default="")
    # 指南全文（学生标注时查阅）
    content_text: Mapped[str] = mapped_column(Text, default="")
    # 标签体系快照：{"elements":[...], "relations":[...]}
    taxonomy: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
