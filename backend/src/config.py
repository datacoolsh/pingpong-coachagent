"""
应用配置 - 使用 Pydantic Settings 管理环境变量
"""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，从环境变量或 .env 文件加载"""

    # ---- JWT 认证 ----
    JWT_SECRET: str = "change-me-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- 数据库 ----
    DATABASE_URL: str = "sqlite:///./data/coachagent.db"

    # ---- 应用 ----
    BASE_URL: str = ""
    DATA_DIR: str = "./data"
    DEBUG: bool = False

    # ---- AI 服务 ----
    ZHIPU_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""

    # ---- 微信 ----
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def runs_dir(self) -> Path:
        return Path(self.DATA_DIR) / "runs"

    @property
    def db_path(self) -> Path:
        """从 DATABASE_URL 提取数据库文件路径"""
        url = self.DATABASE_URL
        if url.startswith("sqlite:///"):
            return Path(url.replace("sqlite:///", ""))
        return Path("./data/coachagent.db")


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例"""
    return Settings()
