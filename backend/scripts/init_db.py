"""Run from backend/: python scripts/init_db.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.database import init_database

if __name__ == "__main__":
    path = get_settings().database_path
    init_database(path)
    print(f"数据库初始化完成：{path}")
