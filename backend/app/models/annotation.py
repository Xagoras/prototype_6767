"""标注数据模型：版本、命题、关系。

- annotation_versions：每人每文档一条（unique(document_id, annotator_id, kind)），
  覆盖保存，历史只保留最后提交（需求确认）。
- propositions：命题 = 要素区。type_code 可空即"先建序号后补标签"（UC-02 A4）。
  序号不落库：按 char_start 排序实时计算（Q8：按原文顺序动态生成）。
- relation_nodes：关系树单表存储，args JSON 为 [{kind:"P"|"R", id}] 有序数组，
  树根 = 不被任何其他节点 args 引用的节点。
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base

VERSION_KINDS = ("normal", "reference", "final")
VERSION_STATUSES = ("draft", "submitted")
REL_TYPES = ("S", "A", "J", "M", "I")


class AnnotationVersion(Base):
    __tablename__ = "annotation_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    annotator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # normal（普通标注）/ reference（教师标准答案）/ final（裁定最终版）
    kind: Mapped[str] = mapped_column(String(16), default="normal")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    # 图示拖拽结果：{positions: {visualId: {x, y}}}
    graph_layout: Mapped[dict] = mapped_column(JSON, default=dict)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)


class Proposition(Base):
    __tablename__ = "propositions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("annotation_versions.id"), index=True)
    # 溯源：指向 documents.base_segments 的下标（可空）
    segment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Unicode 码点偏移（相对 reasoning_text）
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    # 非空表示用户编辑过文字（教学"临时文本"场景），比对时标记"文字已编辑"
    edited_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 类型可空：先建序号后补标签；IS/Non 为非命题要素
    type_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    subtype_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class RelationNode(Base):
    __tablename__ = "relation_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("annotation_versions.id"), index=True)
    # S/A/J/M/I
    rel_type: Mapped[str] = mapped_column(String(1))
    # 有序参数列表：[{kind:"P", id}, {kind:"R", id}]；S/A/M 顺序即语义方向
    args: Mapped[list] = mapped_column(JSON, default=list)
    note: Mapped[str] = mapped_column(Text, default="")
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
