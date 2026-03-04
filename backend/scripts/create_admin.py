"""
创建初始管理员用户

使用方式:
    cd backend
    uv run python -m scripts.create_admin

或指定用户名密码:
    uv run python -m scripts.create_admin --username admin --password your_password
"""

import sys
import argparse
from pathlib import Path
from getpass import getpass

# 添加 backend 目录到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import create_db_and_tables, engine
from src.models.user import User
from src.auth.security import hash_password

from sqlmodel import Session, select


def create_admin(username: str, password: str):
    create_db_and_tables()

    with Session(engine) as session:
        # 检查是否已存在
        existing = session.exec(select(User).where(User.username == username)).first()
        if existing:
            print(f"用户 '{username}' 已存在 (id={existing.id}, role={existing.role})")
            if existing.role != "admin":
                existing.role = "admin"
                session.add(existing)
                session.commit()
                print(f"已将 '{username}' 角色更新为 admin")
            return

        user = User(
            username=username,
            password_hash=hash_password(password),
            role="admin",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        print(f"管理员用户创建成功:")
        print(f"  用户名: {username}")
        print(f"  ID: {user.id}")
        print(f"  角色: admin")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="创建管理员用户")
    parser.add_argument("--username", default="admin", help="用户名 (默认: admin)")
    parser.add_argument("--password", default=None, help="密码 (不提供则交互输入)")
    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass("请输入管理员密码: ")
        if not password:
            print("密码不能为空")
            sys.exit(1)
        confirm = getpass("确认密码: ")
        if password != confirm:
            print("两次输入的密码不一致")
            sys.exit(1)

    create_admin(args.username, password)
