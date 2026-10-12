"""全局配置：路径与密钥常量。"""
import os
from pathlib import Path

# backend/ 目录（本文件位于 backend/app/config.py）
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
SEED_DIR = BACKEND_DIR / "seed"

# SQLite 数据库文件（测试可用 DB_URL 环境变量覆盖）
DATABASE_URL = os.environ.get("DB_URL", f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}")

# JWT 配置（原型级密钥，生产环境应替换为环境变量）
SECRET_KEY = "prototype-6767-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# 上传限制（裁判文书规模有限，10MB 足够）
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


def ensure_dirs() -> None:
    """确保运行时目录存在。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
