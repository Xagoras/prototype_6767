"""FastAPI 入口：CORS、路由注册、启动建表。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import assignments, auth, documents, guides, tasks, users
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


@app.on_event("startup")
def on_startup() -> None:
    """启动时自动建表（原型简化，不做迁移工具）。"""
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}
