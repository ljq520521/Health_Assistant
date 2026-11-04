"""Transactional, opt-in diet schema upgrades; never rebuild diet_records."""
import argparse
import hashlib
import os
from pathlib import Path

from app.database import connect, init_database
from app.modules.diet.settings import utc_now

VERSION = "001_food_library"
TABLE_STATEMENTS = (
    """CREATE TABLE food_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 50),
        name_key TEXT NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(profile_id, name_key)
    )""",
    """CREATE TABLE food_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
        category_id INTEGER REFERENCES food_categories(id) ON DELETE SET NULL,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100),
        calories_per_100g REAL CHECK(calories_per_100g >= 0),
        protein_g_per_100g REAL CHECK(protein_g_per_100g >= 0),
        fat_g_per_100g REAL CHECK(fat_g_per_100g >= 0),
        carbohydrate_g_per_100g REAL CHECK(carbohydrate_g_per_100g >= 0),
        source_type TEXT NOT NULL DEFAULT 'user_entered' CHECK(source_type IN ('user_entered','referenced','example')),
        source_note TEXT NOT NULL DEFAULT '', source_url TEXT NOT NULL DEFAULT '',
        is_example INTEGER NOT NULL DEFAULT 0 CHECK(is_example IN (0,1)),
        deleted_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        CHECK((source_type = 'example') = (is_example = 1))
    )""",
)
DIET_COLUMNS = (
    ("food_id", "INTEGER REFERENCES food_items(id) ON DELETE SET NULL"),
    ("nutrition_mode", "TEXT NOT NULL DEFAULT 'manual' CHECK(nutrition_mode IN ('manual','catalog'))"),
    ("protein_g", "REAL CHECK(protein_g >= 0)"),
    ("fat_g", "REAL CHECK(fat_g >= 0)"),
    ("carbohydrate_g", "REAL CHECK(carbohydrate_g >= 0)"),
    ("snapshot_calories_per_100g", "REAL CHECK(snapshot_calories_per_100g >= 0)"),
    ("snapshot_protein_g_per_100g", "REAL CHECK(snapshot_protein_g_per_100g >= 0)"),
    ("snapshot_fat_g_per_100g", "REAL CHECK(snapshot_fat_g_per_100g >= 0)"),
    ("snapshot_carbohydrate_g_per_100g", "REAL CHECK(snapshot_carbohydrate_g_per_100g >= 0)"),
    ("food_version_at", "TEXT"),
    ("nutrition_source_note", "TEXT NOT NULL DEFAULT ''"),
    ("is_example", "INTEGER NOT NULL DEFAULT 0 CHECK(is_example IN (0,1))"),
)
INDEX_STATEMENTS = (
    "CREATE INDEX idx_food_items_profile_active_category ON food_items(profile_id, deleted_at, category_id)",
    "CREATE INDEX idx_food_items_profile_name ON food_items(profile_id, name)",
    "CREATE INDEX idx_diet_profile_food ON diet_records(profile_id, food_id)",
)
STATEMENTS = TABLE_STATEMENTS + tuple(f"ALTER TABLE diet_records ADD COLUMN {name} {definition}" for name, definition in DIET_COLUMNS) + INDEX_STATEMENTS
CHECKSUM = hashlib.sha256("\n".join(STATEMENTS).encode()).hexdigest()


def _tables(connection):
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _verify_schema(connection):
    expected = {
        "food_categories": {"id", "profile_id", "name", "name_key", "created_at", "updated_at"},
        "food_items": {"id", "profile_id", "category_id", "name", "calories_per_100g", "protein_g_per_100g", "fat_g_per_100g", "carbohydrate_g_per_100g", "source_type", "source_note", "source_url", "is_example", "deleted_at", "created_at", "updated_at"},
        "diet_records": {name for name, _ in DIET_COLUMNS},
    }
    for table, names in expected.items():
        actual = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        if not names <= actual:
            raise RuntimeError(f"饮食数据库结构异常：{table} 缺少字段 {sorted(names - actual)}")
    foreign_keys = list(connection.execute("PRAGMA foreign_key_list(diet_records)"))
    if not any(row[2] == 'food_items' and row[3] == 'food_id' and row[4] == 'id' and row[6] == 'SET NULL' for row in foreign_keys):
        raise RuntimeError("diet_records.food_id 外键结构异常")
    index_names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    if not {"idx_food_items_profile_active_category", "idx_food_items_profile_name", "idx_diet_profile_food"} <= index_names:
        raise RuntimeError("饮食数据库缺少索引")


def migration_ready(connection) -> bool:
    if "diet_schema_migrations" not in _tables(connection):
        return False
    rows = list(connection.execute("SELECT version, checksum FROM diet_schema_migrations"))
    if not rows:
        return False
    from app.modules.diet.migration_002 import VERSION as V2, CHECKSUM as C2, verify_schema
    from app.modules.diet.migration_003 import VERSION as V3, CHECKSUM as C3, verify_schema as verify_water
    from app.modules.diet.migration_004 import VERSION as V4, CHECKSUM as C4, verify_schema as verify_recipes
    versions = {row['version']: row['checksum'] for row in rows}
    if versions.get(VERSION) != CHECKSUM or any(v not in (VERSION, V2, V3, V4) for v in versions) or (V2 in versions and versions[V2] != C2) or (V3 in versions and (versions[V3] != C3 or V2 not in versions)) or (V4 in versions and (versions[V4] != C4 or V3 not in versions)):
        raise RuntimeError("饮食迁移版本或校验和不匹配，请勿自动覆盖")
    _verify_schema(connection)
    if V2 in versions:
        verify_schema(connection)
    if V3 in versions:
        verify_water(connection)
    if V4 in versions:
        verify_recipes(connection)
    return True


def migrate_diet(database_path: Path) -> bool:
    """Explicitly apply pending migration to an initialized database.

    connect() owns commit/rollback. DDL must be inside BEGIN IMMEDIATE;
    executescript() is intentionally NOT used because it may commit early.
    Returns True only when this call applied the migration.
    """
    with connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        tables = _tables(connection)
        if not {"profiles", "diet_records"} <= tables:
            raise RuntimeError("请先运行现有数据库初始化入口")
        if migration_ready(connection):
            return False
        current_columns = {row[1] for row in connection.execute("PRAGMA table_info(diet_records)")}
        if {"food_categories", "food_items"} & tables or current_columns & {name for name, _ in DIET_COLUMNS}:
            raise RuntimeError("存在未登记的饮食扩展结构，停止迁移以保护现有数据")
        connection.execute("""CREATE TABLE IF NOT EXISTS diet_schema_migrations (
            version TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL
        )""")
        for statement in STATEMENTS:
            connection.execute(statement)
        _verify_schema(connection)
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise RuntimeError("迁移后外键检查失败")
        connection.execute("INSERT INTO diet_schema_migrations(version,checksum,applied_at) VALUES(?,?,?)", (VERSION, CHECKSUM, utc_now()))
    return True


def initialize_diet_schema(database_path: Path) -> bool:
    """Startup is read-only unless the operator explicitly opts in."""
    if os.getenv("DIET_APPLY_MIGRATIONS") == "1":
        migrate_diet(database_path)
    with connect(database_path) as connection:
        return migration_ready(connection)


def main():
    parser = argparse.ArgumentParser(description="饮食迁移：默认仅检查；备份并确认后使用 --apply")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    path = args.database.resolve()
    if not path.is_file():
        parser.error("数据库不存在；请先对目标临时库运行初始化")
    if args.apply:
        print("迁移完成" if migrate_diet(path) else "数据库已是当前版本，无需重复迁移")
    else:
        with connect(path) as connection:
            print("已迁移" if migration_ready(connection) else "待迁移（未进行任何更改）")


if __name__ == "__main__":
    main()
