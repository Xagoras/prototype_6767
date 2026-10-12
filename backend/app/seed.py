"""演示数据种子脚本。

用法：
    python -m app.seed            # 重置数据库并导入演示数据
    python -m app.seed --keep     # 已存在数据时跳过（幂等）

演示账号（密码统一 demo123）：admin / teacher / stu1 / stu2 / arbiter
"""
import argparse
import json
import sys
from pathlib import Path

from .auth import hash_password
from .config import SEED_DIR
from .database import Base, SessionLocal, engine
from .models import Guide, User
from .services.taxonomy import default_taxonomy

DEMO_USERS = [
    ("admin", "管理员", True),
    ("teacher", "王老师", False),
    ("stu1", "学生甲", False),
    ("stu2", "学生乙", False),
    ("arbiter", "裁定员", False),
]
DEMO_PASSWORD = "demo123"


def seed_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for username, display_name, is_admin in DEMO_USERS:
        u = User(
            username=username,
            password_hash=hash_password(DEMO_PASSWORD),
            display_name=display_name,
            is_admin=is_admin,
        )
        db.add(u)
        users[username] = u
    db.flush()  # 获得 id
    return users


def seed_guide(db, user: User) -> Guide:
    """导入预置指南 v1.1（正文 + taxonomy）。"""
    path = SEED_DIR / "guide_v1_1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    g = Guide(
        version=data["version"],
        name=data["name"],
        source_filename="guide_v1_1.json（内置）",
        content_text=data["content_text"],
        taxonomy=default_taxonomy(),
        imported_by=user.id,
        is_active=True,
    )
    db.add(g)
    db.flush()
    return g


def run(reset: bool) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() > 0 and not reset:
            print("数据库已有数据，跳过导入（使用 --reset 可重建）")
            return
        users = seed_users(db)
        guide = seed_guide(db, users["admin"])
        db.commit()
        print(f"种子完成：用户 {len(users)} 个；指南 {guide.version}（id={guide.id}）")
        print("演示账号（密码均为 demo123）：admin / teacher / stu1 / stu2 / arbiter")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="演示数据种子")
    parser.add_argument("--reset", action="store_true", help="重建数据库（默认）")
    parser.add_argument("--keep", action="store_true", help="幂等模式：已有数据则跳过")
    args = parser.parse_args()
    run(reset=not args.keep)
    sys.exit(0)
