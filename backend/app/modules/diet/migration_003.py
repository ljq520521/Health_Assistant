"""Explicit, transactional water migration. Never executed at startup."""
import argparse
import hashlib
from pathlib import Path
from app.database import connect
from app.modules.diet.settings import utc_now

VERSION = '003_water'
STATEMENTS = (
    """CREATE TABLE water_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
        drank_at TEXT NOT NULL,
        amount_ml INTEGER NOT NULL CHECK(typeof(amount_ml)='integer' AND amount_ml>0 AND amount_ml<=1000000),
        notes TEXT NOT NULL DEFAULT '' CHECK(length(notes)<=2000),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""",
    'CREATE INDEX idx_water_profile_time ON water_records(profile_id,drank_at)',
    """CREATE TABLE water_reminder_settings (
        profile_id INTEGER PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
        enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
        mode TEXT NOT NULL CHECK(mode IN ('fixed_times','interval')),
        fixed_times_json TEXT NOT NULL DEFAULT '[]',
        interval_minutes INTEGER NOT NULL CHECK(interval_minutes BETWEEN 1 AND 1440),
        active_start TEXT NOT NULL, active_end TEXT NOT NULL CHECK(active_end>active_start),
        pause_when_goal_met INTEGER NOT NULL DEFAULT 1 CHECK(pause_when_goal_met IN (0,1)),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""",
)
CHECKSUM = hashlib.sha256('\n'.join(STATEMENTS).encode()).hexdigest()

def verify_schema(c):
    for table, fields in {
        'water_records': {'id','profile_id','drank_at','amount_ml','notes','created_at','updated_at'},
        'water_reminder_settings': {'profile_id','enabled','mode','fixed_times_json','interval_minutes','active_start','active_end','pause_when_goal_met','created_at','updated_at'},
    }.items():
        if not fields <= {r[1] for r in c.execute(f'PRAGMA table_info({table})')}:
            raise RuntimeError(f'003 表结构异常：{table}')
        if not any(r[2]=='profiles' and r[3]=='profile_id' and r[6]=='CASCADE' for r in c.execute(f'PRAGMA foreign_key_list({table})')):
            raise RuntimeError(f'003 外键异常：{table}')
    if not any(r[1]=='idx_water_profile_time' for r in c.execute('PRAGMA index_list(water_records)')):
        raise RuntimeError('003 缺少饮水时间索引')

def ready(c):
    from app.modules.diet.migration_002 import ready as goals_ready
    if not goals_ready(c):
        return False
    row = c.execute('SELECT checksum FROM diet_schema_migrations WHERE version=?',(VERSION,)).fetchone()
    if row is None:
        return False
    if row[0] != CHECKSUM:
        raise RuntimeError('003 校验和异常')
    verify_schema(c)
    return True

def migrate_water(path):
    from app.modules.diet.migration_002 import ready as goals_ready
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        if not goals_ready(c):
            raise RuntimeError('请先完成 001、002 迁移')
        if ready(c):
            return False
        if c.execute("SELECT 1 FROM sqlite_master WHERE name IN ('water_records','water_reminder_settings')").fetchone():
            raise RuntimeError('存在未登记饮水表，停止升级')
        for sql in STATEMENTS:
            c.execute(sql)
        verify_schema(c)
        if c.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('003 外键检查失败')
        c.execute('INSERT INTO diet_schema_migrations VALUES(?,?,?)',(VERSION,CHECKSUM,utc_now()))
    return True

def main():
    parser=argparse.ArgumentParser(description='003 默认只检查；正式升级前必须备份并获得授权')
    parser.add_argument('--database',required=True,type=Path)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if not args.database.is_file():
        parser.error('数据库不存在，拒绝创建')
    if args.apply:
        print('003 已完成' if migrate_water(args.database) else '003 已存在，无需重复迁移')
    else:
        with connect(args.database) as c:
            print('003 已应用' if ready(c) else '003 未应用（未修改数据库）')

if __name__=='__main__':
    main()
