"""Explicit weekly-plan extension, installed after 006; never alter released 001-004."""
import argparse
import hashlib
from pathlib import Path
import sqlite3
from app.database import connect
from app.modules.diet.migration_004 import ready as recipes_ready
from app.modules.diet.migration_006 import ready as catalog_ready
from app.modules.diet.settings import utc_now

VERSION = '005_weekly_plans'
STATEMENTS = (
    """CREATE TABLE diet_plan_context_confirmations (
        id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL CHECK(profile_id=1) REFERENCES profiles(id),
        profile_fingerprint TEXT NOT NULL CHECK(length(profile_fingerprint)=64),
        rules_fingerprint TEXT NOT NULL CHECK(length(rules_fingerprint)=64),
        allergy_rule_ids_json TEXT NOT NULL, preference_rule_ids_json TEXT NOT NULL,
        actor_user_id INTEGER NOT NULL REFERENCES users(id), confirmed_at TEXT NOT NULL)""",
    """CREATE TABLE diet_weekly_plans (
        id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL CHECK(profile_id=1) REFERENCES profiles(id),
        start_date TEXT NOT NULL CHECK(length(start_date)=10), portions REAL NOT NULL CHECK(portions>0),
        meal_ratios_json TEXT NOT NULL, selected_goal_ids_json TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision>0), context_hash TEXT NOT NULL CHECK(length(context_hash)=64),
        hard_fingerprint TEXT NOT NULL CHECK(length(hard_fingerprint)=64), profile_fingerprint TEXT NOT NULL,
        profile_updated_at TEXT NOT NULL, context_json TEXT NOT NULL,
        created_by INTEGER NOT NULL REFERENCES users(id), updated_by INTEGER NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(profile_id,id))""",
    """CREATE TABLE diet_plan_items (
        id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL CHECK(profile_id=1), plan_id INTEGER NOT NULL,
        position INTEGER NOT NULL CHECK(position BETWEEN 0 AND 20), plan_date TEXT NOT NULL CHECK(length(plan_date)=10),
        meal_type TEXT NOT NULL CHECK(meal_type IN ('breakfast','lunch','dinner')),
        snapshot_json TEXT NOT NULL, generation_context_hash TEXT NOT NULL,
        generation_hard_fingerprint TEXT NOT NULL, generation_revision INTEGER NOT NULL CHECK(generation_revision>0),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        FOREIGN KEY(profile_id,plan_id) REFERENCES diet_weekly_plans(profile_id,id),
        UNIQUE(profile_id,id), UNIQUE(plan_id,position), UNIQUE(plan_id,plan_date,meal_type))""",
    """CREATE TABLE diet_plan_versions (
        plan_id INTEGER NOT NULL, profile_id INTEGER NOT NULL CHECK(profile_id=1), revision INTEGER NOT NULL CHECK(revision>0),
        context_hash TEXT NOT NULL, hard_fingerprint TEXT NOT NULL, context_json TEXT NOT NULL,
        snapshot_json TEXT NOT NULL, actor_user_id INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL,
        PRIMARY KEY(plan_id,revision), FOREIGN KEY(profile_id,plan_id) REFERENCES diet_weekly_plans(profile_id,id))""",
    """CREATE TABLE diet_plan_feedback (
        item_id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL CHECK(profile_id=1), revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0),
        status TEXT NOT NULL CHECK(status IN ('pending','completed','not_completed','partial','not_applicable')),
        note TEXT NOT NULL DEFAULT '' CHECK(length(note)<=2000), reason TEXT NOT NULL DEFAULT '' CHECK(length(reason)<=2000),
        actor_user_id INTEGER REFERENCES users(id), updated_at TEXT NOT NULL,
        FOREIGN KEY(profile_id,item_id) REFERENCES diet_plan_items(profile_id,id))""",
    """CREATE TABLE diet_plan_feedback_history (
        id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL, profile_id INTEGER NOT NULL CHECK(profile_id=1),
        revision INTEGER NOT NULL CHECK(revision>0), plan_revision_at_submission INTEGER NOT NULL CHECK(plan_revision_at_submission>0),
        item_generation_revision INTEGER NOT NULL CHECK(item_generation_revision>0),
        status TEXT NOT NULL CHECK(status IN ('pending','completed','not_completed','partial','not_applicable')),
        note TEXT NOT NULL CHECK(length(note)<=2000), reason TEXT NOT NULL CHECK(length(reason)<=2000),
        actor_user_id INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL,
        UNIQUE(item_id,revision), FOREIGN KEY(profile_id,item_id) REFERENCES diet_plan_items(profile_id,id))""",
    'CREATE INDEX idx_diet_weekly_profile_start ON diet_weekly_plans(profile_id,start_date,id)',
    'CREATE INDEX idx_diet_feedback_item_revision ON diet_plan_feedback_history(item_id,revision)',
    """CREATE TRIGGER diet_plan_item_identity BEFORE UPDATE ON diet_plan_items
        WHEN NEW.id!=OLD.id OR NEW.profile_id!=OLD.profile_id OR NEW.plan_id!=OLD.plan_id OR NEW.position!=OLD.position
             OR NEW.plan_date!=OLD.plan_date OR NEW.meal_type!=OLD.meal_type
        BEGIN SELECT RAISE(ABORT,'plan item identity is immutable'); END""",
    "CREATE TRIGGER diet_plan_version_no_update BEFORE UPDATE ON diet_plan_versions BEGIN SELECT RAISE(ABORT,'plan version is immutable'); END",
    "CREATE TRIGGER diet_plan_version_no_delete BEFORE DELETE ON diet_plan_versions BEGIN SELECT RAISE(ABORT,'plan version is immutable'); END",
    "CREATE TRIGGER diet_plan_history_no_update BEFORE UPDATE ON diet_plan_feedback_history BEGIN SELECT RAISE(ABORT,'feedback history is immutable'); END",
    "CREATE TRIGGER diet_plan_history_no_delete BEFORE DELETE ON diet_plan_feedback_history BEGIN SELECT RAISE(ABORT,'feedback history is immutable'); END",
    "CREATE TRIGGER diet_plan_confirmation_no_update BEFORE UPDATE ON diet_plan_context_confirmations BEGIN SELECT RAISE(ABORT,'context confirmation is immutable'); END",
    "CREATE TRIGGER diet_plan_confirmation_no_delete BEFORE DELETE ON diet_plan_context_confirmations BEGIN SELECT RAISE(ABORT,'context confirmation is immutable'); END",
)
CHECKSUM = hashlib.sha256('\n'.join(STATEMENTS).encode()).hexdigest()


def ready(c):
    if not c.execute("SELECT 1 FROM sqlite_master WHERE name='diet_extension_schema_migrations' AND type='table'").fetchone():
        return False
    row = c.execute('SELECT checksum FROM diet_extension_schema_migrations WHERE version=?', (VERSION,)).fetchone()
    if row is None:
        return False
    if row[0] != CHECKSUM:
        raise RuntimeError('005 checksum mismatch')
    normalize = lambda value: ' '.join(value.split()).lower()
    for statement in STATEMENTS:
        name = statement.split()[2]
        row = c.execute('SELECT sql FROM sqlite_master WHERE name=?', (name,)).fetchone()
        if not row or normalize(row[0]) != normalize(statement):
            raise RuntimeError('005 schema mismatch: ' + name)
    return True


def migrate_weekly(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError('Existing initialized database required')
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        if not recipes_ready(c) or not catalog_ready(c):
            raise RuntimeError('001-004 and 006 must be explicitly installed before 005')
        if ready(c):
            return False
        for statement in STATEMENTS:
            if c.execute('SELECT 1 FROM sqlite_master WHERE name=?', (statement.split()[2],)).fetchone():
                raise RuntimeError('Unregistered weekly-plan object; refusing to overwrite')
        for statement in STATEMENTS:
            c.execute(statement)
        c.execute('INSERT INTO diet_extension_schema_migrations VALUES (?,?,?)', (VERSION, CHECKSUM, utc_now()))
        ready(c)
        if c.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('005 foreign key check failed')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error('Existing database required')
    if args.apply:
        print('005 applied' if migrate_weekly(args.database) else '005 already applied')
    else:
        c = sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True)
        try:
            print('005 applied' if ready(c) else '005 pending (read-only)')
        finally:
            c.close()
