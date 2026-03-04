"""
用户模型
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    """用户表"""

    __tablename__ = "users"

    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    password_hash: str = Field(max_length=255)
    role: str = Field(default="user", max_length=20)  # "user" | "admin"
    is_active: bool = Field(default=True)
    legacy_cookie_id: Optional[str] = Field(
        default=None, index=True, max_length=20
    )  # 兼容旧 cookie user_id
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
