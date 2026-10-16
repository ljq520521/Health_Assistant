"""Opt-in recipe migration. Application startup must never apply this migration."""
import argparse
import hashlib
from pathlib import Path
from app.database import connect
from app.modules.diet.settings import utc_now

VERSION = '004_recipes'
STATEMENTS = (
    """CREATE TABLE diet_recipe_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 50), name_key TEXT NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(profile_id,name_key), UNIQUE(profile_id,id))""",
    """CREATE TABLE diet_recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        category_id INTEGER, name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100), description TEXT NOT NULL DEFAULT '',
        servings REAL NOT NULL CHECK(servings>0), preparation_minutes INTEGER CHECK(preparation_minutes>=0),
        nutrition_mode TEXT NOT NULL CHECK(nutrition_mode IN ('calculated','manual')),
        manual_calories_kcal REAL CHECK(manual_calories_kcal>=0), manual_protein_g REAL CHECK(manual_protein_g>=0),
        manual_fat_g REAL CHECK(manual_fat_g>=0), manual_carbohydrate_g REAL CHECK(manual_carbohydrate_g>=0),
        source_type TEXT NOT NULL CHECK(source_type IN ('user_entered','referenced','example')),
        source_note TEXT NOT NULL DEFAULT '', source_url TEXT NOT NULL DEFAULT '',
        revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0), archived_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(profile_id,id), FOREIGN KEY(profile_id,category_id) REFERENCES diet_recipe_categories(profile_id,id))""",
    """CREATE TABLE diet_recipe_ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL, recipe_id INTEGER NOT NULL,
        food_id INTEGER NOT NULL REFERENCES food_items(id), amount_g REAL NOT NULL CHECK(amount_g>0), position INTEGER NOT NULL CHECK(position>0),
        food_name_snapshot TEXT NOT NULL, calories_per_100g_snapshot REAL CHECK(calories_per_100g_snapshot>=0),
        protein_g_per_100g_snapshot REAL CHECK(protein_g_per_100g_snapshot>=0), fat_g_per_100g_snapshot REAL CHECK(fat_g_per_100g_snapshot>=0),
        carbohydrate_g_per_100g_snapshot REAL CHECK(carbohydrate_g_per_100g_snapshot>=0),
        food_updated_at_snapshot TEXT NOT NULL, source_snapshot TEXT NOT NULL, is_example INTEGER NOT NULL CHECK(is_example IN (0,1)),
        UNIQUE(recipe_id,food_id), UNIQUE(recipe_id,position),
        FOREIGN KEY(profile_id,recipe_id) REFERENCES diet_recipes(profile_id,id) ON DELETE CASCADE)""",
    """CREATE TABLE diet_recipe_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL, recipe_id INTEGER NOT NULL,
        position INTEGER NOT NULL CHECK(position>0), instruction TEXT NOT NULL CHECK(length(trim(instruction))>0),
        UNIQUE(recipe_id,position), FOREIGN KEY(profile_id,recipe_id) REFERENCES diet_recipes(profile_id,id) ON DELETE CASCADE)""",
    """CREATE TABLE diet_inventory_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        food_id INTEGER NOT NULL REFERENCES food_items(id), quantity_g REAL NOT NULL CHECK(quantity_g>=0), notes TEXT NOT NULL DEFAULT '',
        revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0), created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(profile_id,food_id))""",
    """CREATE TABLE diet_ingredient_terms (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100), name_key TEXT NOT NULL,
        kind TEXT NOT NULL CHECK(kind IN ('ingredient','allergen')), archived_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(profile_id,name_key), UNIQUE(profile_id,id))""",
    """CREATE TABLE diet_ingredient_aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL, term_id INTEGER NOT NULL,
        alias TEXT NOT NULL, alias_key TEXT NOT NULL, UNIQUE(profile_id,alias_key),
        FOREIGN KEY(profile_id,term_id) REFERENCES diet_ingredient_terms(profile_id,id) ON DELETE CASCADE)""",
    """CREATE TABLE diet_food_composition (
        profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE, food_id INTEGER NOT NULL REFERENCES food_items(id),
        ingredient_status TEXT NOT NULL CHECK(ingredient_status IN ('unknown','partial','declared_complete')),
        allergen_status TEXT NOT NULL CHECK(allergen_status IN ('unknown','partial','declared_complete')),
        assessed_food_updated_at TEXT NOT NULL, source_note TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
        PRIMARY KEY(profile_id,food_id))""",
    """CREATE TABLE diet_food_composition_terms (
        profile_id INTEGER NOT NULL, food_id INTEGER NOT NULL, term_id INTEGER NOT NULL,
        relation TEXT NOT NULL CHECK(relation IN ('contains','may_contain')),
        PRIMARY KEY(profile_id,food_id,term_id,relation),
        FOREIGN KEY(profile_id,food_id) REFERENCES diet_food_composition(profile_id,food_id) ON DELETE CASCADE,
        FOREIGN KEY(profile_id,term_id) REFERENCES diet_ingredient_terms(profile_id,id))""",
    """CREATE TABLE diet_food_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        food_id INTEGER REFERENCES food_items(id), term_id INTEGER,
        rule_type TEXT NOT NULL CHECK(rule_type IN ('like','dislike','allergy','forbidden')),
        notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        CHECK((food_id IS NULL) != (term_id IS NULL)),
        FOREIGN KEY(profile_id,term_id) REFERENCES diet_ingredient_terms(profile_id,id),
        UNIQUE(profile_id,food_id,rule_type), UNIQUE(profile_id,term_id,rule_type))""",
    'CREATE INDEX idx_recipe_profile_active_category ON diet_recipes(profile_id,archived_at,category_id)',
    'CREATE INDEX idx_recipe_profile_name ON diet_recipes(profile_id,name)',
    'CREATE INDEX idx_recipe_food ON diet_recipe_ingredients(profile_id,food_id)',
    'CREATE INDEX idx_composition_term ON diet_food_composition_terms(profile_id,term_id)',
)
CHECKSUM = hashlib.sha256('\n'.join(STATEMENTS).encode()).hexdigest()
TABLES = ('diet_recipe_categories','diet_recipes','diet_recipe_ingredients','diet_recipe_steps','diet_inventory_items',
          'diet_ingredient_terms','diet_ingredient_aliases','diet_food_composition','diet_food_composition_terms','diet_food_preferences')

def verify_schema(c):
    # Compare CREATE declarations with the registered migration, including checks/FKs.
    normalize=lambda s:' '.join(s.split()).lower()
    for sql in STATEMENTS:
        name=sql.split()[2]
        stored=c.execute('SELECT sql FROM sqlite_master WHERE name=?',(name,)).fetchone()
        if not stored or normalize(stored[0])!=normalize(sql):
            raise RuntimeError('004 结构与登记定义不符：'+name)

def ready(c):
    from app.modules.diet.migration_003 import ready as water_ready
    if not water_ready(c): return False
    r=c.execute('SELECT checksum FROM diet_schema_migrations WHERE version=?',(VERSION,)).fetchone()
    if r is None: return False
    if r[0]!=CHECKSUM: raise RuntimeError('004 校验和异常')
    verify_schema(c)
    return True

def migrate_recipes(path):
    from app.modules.diet.migration_003 import ready as water_ready
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        if not water_ready(c): raise RuntimeError('请先完成001～003')
        if ready(c): return False
        if any(c.execute('SELECT 1 FROM sqlite_master WHERE name=?',(t,)).fetchone() for t in TABLES):
            raise RuntimeError('存在未登记食谱表，停止升级')
        for sql in STATEMENTS: c.execute(sql)
        verify_schema(c)
        if c.execute('PRAGMA foreign_key_check').fetchone(): raise RuntimeError('004 外键检查失败')
        c.execute('INSERT INTO diet_schema_migrations VALUES(?,?,?)',(VERSION,CHECKSUM,utc_now()))
    return True

def main():
    p=argparse.ArgumentParser(description='004 默认仅检查；正式升级须单独授权和备份')
    p.add_argument('--database',type=Path,required=True);p.add_argument('--apply',action='store_true');args=p.parse_args()
    if not args.database.is_file(): p.error('数据库不存在，拒绝创建')
    if args.apply: print('004 已完成' if migrate_recipes(args.database) else '004 已存在，无操作')
    else:
        with connect(args.database) as c: print('004 已应用' if ready(c) else '004 待升级（未写入）')
if __name__=='__main__': main()
