"""
系统配置键值对模型
"""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class SystemConfig(SQLModel, table=True):
    """系统配置表（键值对存储）"""

    __tablename__ = "system_config"

    key: str = Field(primary_key=True, max_length=100)
    value: str = Field(default="")
    description: Optional[str] = Field(default=None, max_length=500)
    updated_at: datetime = Field(default_factory=datetime.now)
