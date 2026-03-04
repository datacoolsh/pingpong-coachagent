"""
数据迁移脚本：将历史任务从文件系统导入到 SQLite 数据库

扫描 data/runs/ 目录，将已有的任务信息写入 Task 表。

使用方式:
    cd backend
    uv run python -m scripts.migrate_tasks
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加 backend 目录到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import create_db_and_tables, engine
from src.models.task import Task
from src.config import get_settings

from sqlmodel import Session, select


def migrate():
    settings = get_settings()
    runs_dir = settings.runs_dir

    if not runs_dir.exists():
        print(f"数据目录不存在: {runs_dir}")
        return

    # 创建数据库表
    create_db_and_tables()

    migrated = 0
    skipped = 0
    errors = 0

    with Session(engine) as session:
        # 遍历所有用户目录
        for user_dir in runs_dir.iterdir():
            if not user_dir.is_dir():
                continue

            user_id = user_dir.name
            print(f"\n扫描用户目录: {user_id}")

            # 遍历用户目录下的任务
            for task_dir in user_dir.iterdir():
                if not task_dir.is_dir():
                    continue

                task_id = task_dir.name

                # 检查是否已存在
                existing = session.get(Task, task_id)
                if existing:
                    skipped += 1
                    continue

                # 读取 report.json
                report_path = task_dir / "report.json"
                task_name = f"训练视频_{task_id}"
                status = "pending"
                created_at = datetime.now()
                is_public = False

                if report_path.exists():
                    try:
                        with open(report_path, "r", encoding="utf-8") as f:
                            report = json.load(f)
                        task_name = report.get("name", task_name)
                        status = "completed"
                        is_public = report.get("is_public", False)
                        created_at_str = report.get("created_at")
                        if created_at_str:
                            try:
                                created_at = datetime.fromisoformat(created_at_str)
                            except ValueError:
                                pass
                    except Exception as e:
                        print(f"  [错误] 读取 {report_path} 失败: {e}")
                        errors += 1
                        continue

                # 查找视频路径
                video_path = None
                for ext in [".mp4", ".mov", ".avi"]:
                    for candidate in [task_dir / f"input{ext}"] + list(task_dir.glob(f"*{ext}")):
                        if candidate.exists():
                            video_path = str(candidate)
                            break
                    if video_path:
                        break

                task = Task(
                    task_id=task_id,
                    user_id=user_id,
                    name=task_name,
                    status=status,
                    progress=100 if status == "completed" else 0,
                    video_path=video_path,
                    run_dir=str(task_dir),
                    is_public=is_public,
                    created_at=created_at,
                    updated_at=created_at,
                )
                session.add(task)
                migrated += 1
                print(f"  [迁移] {task_id} -> {task_name} ({status})")

        session.commit()

    print(f"\n迁移完成: 新增 {migrated}, 跳过 {skipped}, 错误 {errors}")


if __name__ == "__main__":
    migrate()
