"""裁定相关的请求/响应模型。"""
from pydantic import BaseModel


class AdjudicateRequest(BaseModel):
    """提交裁定：以 base 版本为基础生成最终版（可先 PUT 编辑工作副本）。"""
    base_version_id: int
    note: str = ""


class PropDiffOut(BaseModel):
    category: str  # identical/boundary/type/subtype/edited_text/only_a/only_b
    a_seq: int | None
    b_seq: int | None
    a_text: str | None
    b_text: str | None
    a_type: str | None
    b_type: str | None
    a_subtype: str | None
    b_subtype: str | None


class RelDiffOut(BaseModel):
    category: str  # type/direction/nested/missing/extra
    a_expr: str | None
    b_expr: str | None


class CompareGroupOut(BaseModel):
    """某一版本与基准版本的差异。"""
    version_id: int
    annotator_name: str | None
    kind: str
    status: str
    proposition_count: int
    relation_count: int
    granularity_rate: float | None
    prop_diffs: list[PropDiffOut]
    relation_diffs: list[RelDiffOut]


class CompareOut(BaseModel):
    base_version_id: int
    warn_threshold_exceeded: bool
    groups: list[CompareGroupOut]
