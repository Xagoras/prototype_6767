"""通用守卫：文档锁定检查（结果输出阶段不可修改）。"""
from fastapi import HTTPException, status

from ..models import Document


def assert_not_locked(doc: Document) -> None:
    """任一导出记录产生后文档进入 OUTPUT，所有写操作被拒绝（需求 5.3）。"""
    if doc.status == "OUTPUT":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "该文档已进入结果输出阶段，数据可查看但不可修改",
        )
