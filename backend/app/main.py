"""FastAPI 入口：CORS、路由注册、启动建表、心跳（供一键启动脚本检测浏览器状态）。"""
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import adjudication, annotations, assignments, auth, documents, exports, guides, tasks, users
from .config import DATA_DIR
from .database import Base, engine

app = FastAPI(title="法律论证标注系统", version="0.1.0")

# 开发环境 CORS 放行 Vite 开发服务器
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(guides.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(assignments.router, prefix="/api")
app.include_router(annotations.router, prefix="/api")
app.include_router(adjudication.router, prefix="/api")
app.include_router(exports.router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    """启动时自动建表（原型简化，不做迁移工具）。"""
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/heartbeat")
def heartbeat():
    """前端页面每 3 秒调用：记录心跳时间。

    一键启动脚本（start_manager.py）监控此文件：心跳停止 12 秒
    （即网页已关闭）后自动停止前后端服务。无需认证。
    """
    try:
        (DATA_DIR / "heartbeat.txt").write_text(str(time.time()))
    except OSError:
        pass  # 目录不存在等极端情况忽略，不影响业务
    return {"ok": True}
