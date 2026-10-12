"""用户接口：用户列表（分配任务时选择标注员/裁定者）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """所有登录用户均可查看用户列表（原型简化，分配任务需要）。"""
    return db.query(User).order_by(User.id).all()
