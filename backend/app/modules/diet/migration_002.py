"""Explicit-only goal migration. Never called by application startup."""
import argparse
import hashlib
from pathlib import Path
from app.database import connect
from app.modules.diet.settings import utc_now

VERSION = '002_daily_goals'
STATEMENTS = ("""CREATE TABLE diet_daily_goals (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
 effective_from TEXT NOT NULL,
 calories_kcal REAL CHECK(calories_kcal > 0),
 protein_g REAL CHECK(protein_g > 0),
 fat_g REAL CHECK(fat_g > 0),
 carbohydrate_g REAL CHECK(carbohydrate_g > 0),
 water_ml REAL CHECK(water_ml > 0),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(profile_id,effective_from)
)""",)
CHECKSUM = hashlib.sha256('\n'.join(STATEMENTS).encode()).hexdigest()

def verify_schema(c):
    columns = {row[1] for row in c.execute('PRAGMA table_info(diet_daily_goals)')}
    if not {'id','profile_id','effective_from','calories_kcal','protein_g','fat_g','carbohydrate_g','water_ml','created_at','updated_at'} <= columns:
        raise RuntimeError('002 目标表结构异常')

def ready(c):
    from app.modules.diet.migrations import migration_ready
    if not migration_ready(c):
        return False
    row = c.execute('SELECT checksum FROM diet_schema_migrations WHERE version=?', (VERSION,)).fetchone()
    if row is None:
        return False
    if row[0] != CHECKSUM:
        raise RuntimeError('002 校验和不匹配')
    verify_schema(c)
    return True

def migrate_goals(path):
    from app.modules.diet.migrations import migration_ready
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        if not migration_ready(c):
            raise RuntimeError('请先显式执行 001 迁移')
        if ready(c):
            return False
        if c.execute("SELECT 1 FROM sqlite_master WHERE name='diet_daily_goals'").fetchone():
            raise RuntimeError('存在未登记的目标表，停止迁移')
        for sql in STATEMENTS:
            c.execute(sql)
        verify_schema(c)
        if c.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('外键检查失败')
        c.execute('INSERT INTO diet_schema_migrations VALUES(?,?,?)', (VERSION,CHECKSUM,utc_now()))
    return True

def main():
    parser = argparse.ArgumentParser(description='002 默认只检查，备份并确认后才使用 --apply')
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error('数据库不存在，拒绝创建')
    if args.apply:
        print('002 迁移完成' if migrate_goals(args.database) else '002 已应用，无需重复执行')
    else:
        with connect(args.database) as c:
            print('002 已应用' if ready(c) else '002 尚未应用（未修改数据库）')

if __name__ == '__main__':
    main()
