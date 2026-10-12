"""文档（案例/文书）表。

- doc_type：judgment（原始判决书）/ guiding_case（指导性案例）/ ref_case（参考案例）
- case_info 按 doc_type 存三套字段（见 schemas）
- base_segments：颗粒度切割结果 [{start,end,text}]，供双人 10% 差异与回溯
"""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base

DOC_TYPES = ("judgment", "guiding_case", "ref_case")
# 文档状态机：CREATED → ASSIGNED → ANNOTATING → SUBMITTED → ADJUDICATED → OUTPUT
DOC_STATUSES = ("CREATED", "ASSIGNED", "ANNOTATING", "SUBMITTED", "ADJUDICATED", "OUTPUT")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    doc_type: Mapped[str] = mapped_column(String(16), default="judgment")
    source_filename: Mapped[str] = mapped_column(String(255), default="")
    # 全文（解析后规范化的权威文本）
    original_text: Mapped[str] = mapped_column(Text, default="")
    # 裁判理由正文及其在全文中的偏移（Unicode 码点）
    reasoning_text: Mapped[str] = mapped_column(Text, default="")
    reasoning_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reasoning_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # auto / manual_corrected / manual
    extraction_method: Mapped[str] = mapped_column(String(16), default="auto")
    case_info: Mapped[dict] = mapped_column(JSON, default=dict)
    base_segments: Mapped[list] = mapped_column(JSON, default=list)
    guide_version_snapshot: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="CREATED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
