"""
数据库引擎与 Session 依赖注入
"""

import logging
from collections.abc import Generator

from sqlmodel import SQLModel, Session, create_engine

from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# 确保数据库目录存在
settings.db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},  # SQLite 需要
)


def create_db_and_tables():
    """创建所有 SQLModel 表"""
    SQLModel.metadata.create_all(engine)
    logger.info("数据库表已创建/同步")


def get_session() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：获取数据库 Session"""
    with Session(engine) as session:
        yield session
