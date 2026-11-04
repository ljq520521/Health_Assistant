"""Explicit additive catalog links. Released 001-004 definitions stay unchanged."""
import argparse
import hashlib
from pathlib import Path
from app.database import connect
from app.modules.diet.migration_004 import ready as recipes_ready
from app.modules.diet.settings import utc_now

VERSION='006_public_catalog'
STATEMENTS=(
 "CREATE TABLE diet_catalog_food_links (food_id INTEGER PRIMARY KEY REFERENCES food_items(id), profile_id INTEGER NOT NULL REFERENCES profiles(id), food_key TEXT NOT NULL, release_id TEXT NOT NULL, record_sha256 TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(profile_id,food_key))",
 "CREATE TABLE diet_catalog_recipe_origins (recipe_id INTEGER PRIMARY KEY REFERENCES diet_recipes(id), profile_id INTEGER NOT NULL REFERENCES profiles(id), recipe_key TEXT NOT NULL, release_id TEXT NOT NULL, record_sha256 TEXT NOT NULL, created_at TEXT NOT NULL)",
 "CREATE TRIGGER diet_catalog_food_owner BEFORE INSERT ON diet_catalog_food_links BEGIN SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM food_items WHERE id=NEW.food_id AND profile_id=NEW.profile_id) THEN RAISE(ABORT,'catalog owner mismatch') END; END",
 "CREATE TRIGGER diet_catalog_recipe_owner BEFORE INSERT ON diet_catalog_recipe_origins BEGIN SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM diet_recipes WHERE id=NEW.recipe_id AND profile_id=NEW.profile_id) THEN RAISE(ABORT,'catalog owner mismatch') END; END",
 "CREATE TRIGGER diet_catalog_food_readonly BEFORE UPDATE ON food_items WHEN EXISTS(SELECT 1 FROM diet_catalog_food_links WHERE food_id=OLD.id) BEGIN SELECT RAISE(ABORT,'public food is read only'); END",
 "CREATE TRIGGER diet_catalog_food_no_delete BEFORE DELETE ON food_items WHEN EXISTS(SELECT 1 FROM diet_catalog_food_links WHERE food_id=OLD.id) BEGIN SELECT RAISE(ABORT,'public food is read only'); END",
 "CREATE TRIGGER diet_catalog_link_readonly BEFORE UPDATE ON diet_catalog_food_links BEGIN SELECT RAISE(ABORT,'catalog link is immutable'); END",
 "CREATE TRIGGER diet_catalog_link_no_delete BEFORE DELETE ON diet_catalog_food_links BEGIN SELECT RAISE(ABORT,'catalog link is immutable'); END",
)
CHECKSUM=hashlib.sha256('\n'.join(STATEMENTS).encode()).hexdigest()

def ready(c):
    if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='diet_extension_schema_migrations'").fetchone(): return False
    row=c.execute('SELECT checksum FROM diet_extension_schema_migrations WHERE version=?',(VERSION,)).fetchone()
    if row is None: return False
    if row[0]!=CHECKSUM: raise RuntimeError('006 checksum mismatch')
    normalize=lambda x:' '.join(x.split()).lower()
    for sql in STATEMENTS:
        name=sql.split()[2]
        actual=c.execute('SELECT sql FROM sqlite_master WHERE name=?',(name,)).fetchone()
        if not actual or normalize(actual[0])!=normalize(sql): raise RuntimeError('006 schema mismatch: '+name)
    return True

def migrate_catalog(path):
    path=Path(path)
    if not path.is_file(): raise ValueError('Existing initialized database required')
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        if not recipes_ready(c): raise RuntimeError('001-004 required')
        if ready(c): return False
        for sql in STATEMENTS:
            if c.execute('SELECT 1 FROM sqlite_master WHERE name=?',(sql.split()[2],)).fetchone():
                raise RuntimeError('Unregistered catalog object; refusing to overwrite')
        c.execute('CREATE TABLE IF NOT EXISTS diet_extension_schema_migrations (version TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)')
        for sql in STATEMENTS: c.execute(sql)
        c.execute('INSERT INTO diet_extension_schema_migrations VALUES (?,?,?)',(VERSION,CHECKSUM,utc_now()))
        ready(c)
        if c.execute('PRAGMA foreign_key_check').fetchone(): raise RuntimeError('006 foreign key check failed')
    return True

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if not args.database.is_file(): parser.error('Database does not exist')
    if args.apply: print(migrate_catalog(args.database))
    else:
        import sqlite3
        with sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro',uri=True) as c: print('applied' if ready(c) else 'pending (read-only)')
