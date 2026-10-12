"""认证与权限：JWT 签发校验、密码哈希、角色断言依赖（原型级，无中间件）。"""
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import ACCESS_TOKEN_EXPIRE_HOURS, ALGORITHM, SECRET_KEY
from .database import get_db
from .models import Assignment, Document, Task, User

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    # bcrypt 限制 72 字节，原型场景超长密码直接截断
    raw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """解析 token 返回当前用户。"""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录凭证无效或已过期")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    return user


def get_document_or_404(db: Session, document_id: int) -> Document:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文档不存在")
    return doc


def get_task_or_404(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "任务不存在")
    return task


def _has_role(db: Session, user_id: int, doc: Document, roles: tuple[str, ...]) -> bool:
    rows = (
        db.query(Assignment)
        .filter(Assignment.document_id == doc.id, Assignment.user_id == user_id)
        .all()
    )
    return any(r.role in roles for r in rows)


def require_task_creator(
    task: Task, user: User = Depends(get_current_user)
) -> User:
    """任务创建者或管理员。"""
    if user.is_admin or task.created_by == user.id:
        return user
    raise HTTPException(status.HTTP_403_FORBIDDEN, "仅任务创建者或管理员可执行此操作")


def require_arbiter(
    document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    """裁定者或任务创建者（创建者有权审核定稿）。"""
    doc = get_document_or_404(db, document_id)
    task = get_task_or_404(db, doc.task_id)
    if user.is_admin or task.created_by == user.id or _has_role(db, user.id, doc, ("arbiter",)):
        return user
    raise HTTPException(status.HTTP_403_FORBIDDEN, "仅裁定者或任务创建者可执行此操作")


def can_manage_document(db: Session, user: User, doc: Document) -> bool:
    """可否管理/导出该文档：管理员、任务创建者、或该文档裁定者。"""
    if user.is_admin:
        return True
    task = db.get(Task, doc.task_id)
    if task is not None and task.created_by == user.id:
        return True
    return _has_role(db, user.id, doc, ("arbiter",))


def is_document_participant(db: Session, user: User, doc: Document) -> bool:
    """是否该文档的参与者：管理员、创建者，或在该文档上有任意分配。"""
    if user.is_admin:
        return True
    task = db.get(Task, doc.task_id)
    if task is not None and task.created_by == user.id:
        return True
    return (
        db.query(Assignment)
        .filter(Assignment.document_id == doc.id, Assignment.user_id == user.id)
        .first()
        is not None
    )


def require_document_exporter(
    document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    """导出/登记该文档：仅管理员、任务创建者或该文档裁定者（需求 5.2/5.3）。"""
    doc = get_document_or_404(db, document_id)
    if can_manage_document(db, user, doc):
        return user
    raise HTTPException(status.HTTP_403_FORBIDDEN, "仅任务创建者、裁定者或管理员可导出该文档")


def require_document_participant(
    document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    """查看该文档相关内容：管理员、创建者或该文档的任一分配人员。"""
    doc = get_document_or_404(db, document_id)
    if is_document_participant(db, user, doc):
        return user
    raise HTTPException(status.HTTP_403_FORBIDDEN, "无权查看该文档")
