"""任务分配接口：案例 ↔ 用户 多对多（阶段一：任务分配）。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, get_task_or_404, require_task_creator
from ..database import get_db
from ..models import Assignment, Document, Task, User
from ..models.assignment import ASSIGNMENT_ROLES
from ..schemas.assignment import AssignmentBatchCreate, AssignmentOut

router = APIRouter(prefix="", tags=["assignments"])


def _assign_out(db: Session, a: Assignment) -> AssignmentOut:
    out = AssignmentOut.model_validate(a)
    u = db.get(User, a.user_id)
    d = db.get(Document, a.document_id)
    out.username = u.username if u else None
    out.display_name = u.display_name if u else None
    out.document_name = d.name if d else None
    return out


@router.post("/tasks/{task_id}/assignments", response_model=list[AssignmentOut])
def batch_assign(task_id: int, body: AssignmentBatchCreate,
                 db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """批量分配（管理员手动将待标注数据分配给选定的标注者）。"""
    task = get_task_or_404(db, task_id)
    require_task_creator(task, user)
    for role in body.roles:
        if role not in ASSIGNMENT_ROLES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"角色无效：{role}")
    docs = db.query(Document).filter(Document.id.in_(body.document_ids),
                                     Document.task_id == task_id).all()
    if len(docs) != len(set(body.document_ids)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "部分文档不存在或不属于该任务")
    users = db.query(User).filter(User.id.in_(body.user_ids)).all()
    if len(users) != len(set(body.user_ids)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "部分用户不存在")

    created: list[Assignment] = []
    for doc in docs:
        for uid in body.user_ids:
            for role in body.roles:
                exists = (
                    db.query(Assignment)
                    .filter(Assignment.document_id == doc.id,
                            Assignment.user_id == uid,
                            Assignment.role == role)
                    .first()
                )
                if exists:
                    continue  # 幂等：重复分配跳过
                a = Assignment(task_id=task_id, document_id=doc.id,
                               user_id=uid, role=role, assigned_by=user.id)
                db.add(a)
                created.append(a)
        if doc.status == "CREATED":
            doc.status = "ASSIGNED"
    db.commit()
    return [_assign_out(db, a) for a in created]


@router.get("/tasks/{task_id}/assignments", response_model=list[AssignmentOut])
def list_assignments(task_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """分配总览（创建者/管理员可见全部；普通用户仅见自己）。"""
    task = get_task_or_404(db, task_id)
    q = db.query(Assignment).filter(Assignment.task_id == task_id)
    if not (user.is_admin or task.created_by == user.id):
        q = q.filter(Assignment.user_id == user.id)
    return [_assign_out(db, a) for a in q.order_by(Assignment.id).all()]


@router.delete("/assignments/{assignment_id}")
def delete_assignment(assignment_id: int, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """撤销分配（任务开始后允许人员更新，Q1）。"""
    a = db.get(Assignment, assignment_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "分配记录不存在")
    task = get_task_or_404(db, a.task_id)
    require_task_creator(task, user)
    db.delete(a)
    db.commit()
    return {"ok": True}


@router.get("/me/assignments", response_model=list[AssignmentOut])
def my_assignments(db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """我的待标注队列（标注人员无需自己上传，点击"下一条"即可获取分配任务）。"""
    rows = (
        db.query(Assignment)
        .filter(Assignment.user_id == user.id)
        .order_by(Assignment.id)
        .all()
    )
    return [_assign_out(db, a) for a in rows]
