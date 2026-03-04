"""
AI 乒乓球教练 - FastAPI 后端
提供视频上传、分析任务管理、结果查询等 API
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import get_settings
from .database import create_db_and_tables
from .auth.router import router as auth_router
from .routers.upload import router as upload_router
from .routers.analysis import router as analysis_router
from .routers.results import router as results_router
from .routers.tasks import router as tasks_router
from .routers.media import router as media_router
from .routers.wechat import router as wechat_router
from .routers.websocket import router as websocket_router
from .admin.router import router as admin_router

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建数据库表
    create_db_and_tables()
    logger.info("应用启动完成")
    yield
    logger.info("应用关闭")


app = FastAPI(
    title="AI 乒乓球教练 API",
    description="提供视频上传、分析任务管理、结果查询等功能",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(analysis_router)
app.include_router(results_router)
app.include_router(tasks_router)
app.include_router(media_router)
app.include_router(wechat_router)
app.include_router(websocket_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "AI 乒乓球教练 API",
        "version": "2.0.0",
        "status": "running",
    }


# ============ 启动命令 ============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
