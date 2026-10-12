"""任务接口：创建、列表、详情、阶段流转。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, get_task_or_404, require_task_creator
from ..database import get_db
from ..models import Assignment, Document, Guide, Task, User
from ..models.task import TASK_STATUSES
from ..schemas.task import TaskCreate, TaskOut, TaskStatusAction, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_out(db: Session, t: Task) -> TaskOut:
    out = TaskOut.model_validate(t)
    guide = db.get(Guide, t.guide_id)
    out.guide_version = guide.version if guide else None
    out.document_count = (
        db.query(Document).filter(Document.task_id == t.id).count()
    )
    return out


@router.get("", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """我相关的任务：我创建的 + 我参与的（有分配记录）。"""
    owned_ids = db.query(Task.id).filter(Task.created_by == user.id)
    joined_ids = (
        db.query(Assignment.task_id)
        .filter(Assignment.user_id == user.id)
        .distinct()
    )
    tasks = (
        db.query(Task)
        .filter(Task.id.in_(owned_ids) | Task.id.in_(joined_ids))
        .order_by(Task.id.desc())
        .all()
    )
    return [_task_out(db, t) for t in tasks]


@router.post("", response_model=TaskOut)
def create_task(body: TaskCreate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """创建标注任务（阶段一入口）。"""
    guide = db.get(Guide, body.guide_id)
    if guide is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "指南不存在")
    task = Task(
        name=body.name,
        guide_id=body.guide_id,
        created_by=user.id,
        annotators_per_doc=body.annotators_per_doc,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_out(db, task)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    task = get_task_or_404(db, task_id)
    return _task_out(db, task)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    task = get_task_or_404(db, task_id)
    require_task_creator(task, user)
    if body.name is not None:
        task.name = body.name
    if body.settings is not None:
        task.settings = body.settings
    db.commit()
    db.refresh(task)
    return _task_out(db, task)


@router.post("/{task_id}/status", response_model=TaskOut)
def change_status(task_id: int, body: TaskStatusAction, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """阶段流转（单向校验）：CREATED → ANNOTATING → ADJUDICATING → OUTPUT。"""
    task = get_task_or_404(db, task_id)
    require_task_creator(task, user)
    mapping = {"start": "ANNOTATING", "to_adjudication": "ADJUDICATING", "finish": "OUTPUT"}
    target = mapping[body.action]
    cur = TASK_STATUSES.index(task.status)
    tgt = TASK_STATUSES.index(target)
    if tgt <= cur:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"流程不可回退：当前阶段 {task.status}，无法流转到 {target}")
    task.status = target
    db.commit()
    db.refresh(task)
    return _task_out(db, task)
