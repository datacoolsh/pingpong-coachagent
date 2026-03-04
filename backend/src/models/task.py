"""
任务模型
"""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Task(SQLModel, table=True):
    """分析任务表"""

    __tablename__ = "tasks"

    task_id: str = Field(primary_key=True, max_length=100)
    user_id: Optional[str] = Field(default=None, index=True, max_length=50)
    name: str = Field(max_length=200)
    status: str = Field(default="pending", index=True, max_length=30)
    progress: int = Field(default=0)
    stage: Optional[str] = Field(default=None, max_length=100)
    video_path: Optional[str] = Field(default=None, max_length=500)
    run_dir: Optional[str] = Field(default=None, max_length=500)
    error: Optional[str] = Field(default=None)
    is_public: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
