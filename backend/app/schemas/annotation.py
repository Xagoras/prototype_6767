"""标注内容的请求/响应模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PropositionIn(BaseModel):
    """保存请求中的命题（type_code 可空 = 先建序号后补标签）。"""
    char_start: int
    char_end: int
    text: str
    edited_text: str | None = None
    type_code: str | None = None
    subtype_code: str | None = None
    flagged: bool = False
    flag_note: str = ""


class RelationArgIn(BaseModel):
    """关系参数：P 引用命题序号，R 引用关系在请求数组中的下标。"""
    kind: str = Field(pattern="^[PR]$")
    id: int


class RelationIn(BaseModel):
    rel_type: str = Field(pattern="^[SAJMI]$")
    args: list[RelationArgIn]
    note: str = ""
    flagged: bool = False
    flag_note: str = ""


class VersionContentIn(BaseModel):
    """全量保存标注内容（propositions/relations 整体替换，graph_layout 覆盖）。"""
    propositions: list[PropositionIn]
    relations: list[RelationIn] = []
    graph_layout: dict = Field(default_factory=dict)


class PropositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_id: int
    seq: int = 0  # 按 char_start 排序实时计算的序号（不落库，_version_out 中回填）
    segment_id: int | None = None
    char_start: int
    char_end: int
    text: str
    edited_text: str | None = None
    type_code: str | None = None
    subtype_code: str | None = None
    flagged: bool = False
    flag_note: str = ""


class RelationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_id: int
    rel_type: str
    args: list = []  # 已转换为实际 id（{"kind":"P"|"R","id":db_id}）
    expr: str = ""  # 形式化表达式（如 S(M(J(P1,P2,P3),P4),P5)，_version_out 中回填）
    note: str = ""
    flagged: bool = False
    flag_note: str = ""


class VersionOut(BaseModel):
    """版本 + 内容 + 展示冗余字段。"""
    id: int
    document_id: int
    annotator_id: int
    kind: str
    status: str
    graph_layout: dict
    note: str
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    propositions: list[PropositionOut] = []
    relations: list[RelationOut] = []
    annotator_name: str | None = None
    document_name: str | None = None
    # 当前用户能否编辑该版本（本人草稿 & 文档未锁定）
    editable: bool = False


class VersionMeta(BaseModel):
    """版本元数据（列表用）。"""
    id: int
    document_id: int
    annotator_id: int
    kind: str
    status: str
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    annotator_name: str | None = None
    proposition_count: int = 0
    relation_count: int = 0
