import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from diet_test_runtime import TestClient
from app.config import Settings
from app.database import connect, init_database
from diet_test_runtime import create_app
from app.modules.diet import migrations
import test_diet


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'health.db'
        init_database(self.path)

    def tables(self):
        with connect(self.path) as db:
            return {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    def test_empty_database_and_repeat(self):
        self.assertTrue(migrations.migrate_diet(self.path))
        self.assertFalse(migrations.migrate_diet(self.path))
        with connect(self.path) as db:
            self.assertTrue(migrations.migration_ready(db))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM diet_schema_migrations').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM profiles').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM food_items').fetchone()[0], 0)
            self.assertEqual(list(db.execute('PRAGMA foreign_key_check')), [])

    def test_legacy_rows_and_table_identity_preserved(self):
        with connect(self.path) as db:
            db.execute("INSERT INTO profiles(id,display_name) VALUES(1,'test')")
            for calorie in (None, 0, 123.4567):
                db.execute("INSERT INTO diet_records(record_date,meal_type,food_name,amount_g,calories_kcal,notes) VALUES('2026-10-14','lunch','历史手动记录',90,?,'保留备注')", (calorie,))
            before = [dict(row) for row in db.execute('SELECT * FROM diet_records ORDER BY id')]
            rootpage = db.execute("SELECT rootpage FROM sqlite_master WHERE name='diet_records'").fetchone()[0]
        migrations.migrate_diet(self.path)
        with connect(self.path) as db:
            rows = [dict(row) for row in db.execute('SELECT * FROM diet_records ORDER BY id')]
            self.assertEqual([{key:row[key] for key in before[0]} for row in rows], before)
            self.assertEqual(db.execute("SELECT rootpage FROM sqlite_master WHERE name='diet_records'").fetchone()[0], rootpage)
            for row in rows:
                self.assertEqual(row['nutrition_mode'], 'manual')
                self.assertIsNone(row['food_id'])
                self.assertIsNone(row['protein_g'])
                self.assertEqual(row['is_example'], 0)

    def test_failed_ddl_rolls_back_all_migration_changes(self):
        tables_before = self.tables()
        with patch.object(migrations, 'STATEMENTS', migrations.STATEMENTS + ('INVALID SQL TO FORCE ROLLBACK',)):
            with self.assertRaises(sqlite3.OperationalError):
                migrations.migrate_diet(self.path)
        self.assertEqual(self.tables(), tables_before)
        with connect(self.path) as db:
            self.assertNotIn('food_id', {row[1] for row in db.execute('PRAGMA table_info(diet_records)')})
        self.assertTrue(migrations.migrate_diet(self.path))

    def test_checksum_mismatch_is_not_overwritten(self):
        migrations.migrate_diet(self.path)
        with connect(self.path) as db:
            db.execute("UPDATE diet_schema_migrations SET checksum='tampered'")
        with self.assertRaisesRegex(RuntimeError, '校验和'):
            migrations.migrate_diet(self.path)
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT checksum FROM diet_schema_migrations').fetchone()[0], 'tampered')

    def test_unregistered_structure_is_not_adopted(self):
        with connect(self.path) as db:
            db.execute('ALTER TABLE diet_records ADD COLUMN food_id TEXT')
        with self.assertRaisesRegex(RuntimeError, '未登记'):
            migrations.migrate_diet(self.path)
        self.assertNotIn('food_items', self.tables())

    def test_concurrent_migration_is_idempotent(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: migrations.migrate_diet(self.path), range(2)))
        self.assertEqual(sorted(results), [False, True])

    def test_startup_never_migrates_and_explicit_migration_enables_library(self):
        def schema():
            with connect(self.path) as db:
                return [tuple(row) for row in db.execute(
                    "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name"
                )]

        # A valid temporary profile keeps 409 from masking migration failures.
        with connect(self.path) as db:
            db.execute("INSERT INTO profiles(id,display_name) VALUES(1,'test')")
        before = schema()
        for flag in ('0', '1'):
            with self.subTest(DIET_APPLY_MIGRATIONS=flag):
                with patch.dict(os.environ, {
                    'DIET_APPLY_MIGRATIONS': flag,
                    'HEALTH_DB_PATH': str(self.path),
                }):
                    app = create_app(Settings('Test', self.path, ()))
                    with TestClient(app) as client:
                        self.assertEqual(client.get('/api/diet-records').status_code, 200)
                        response = client.get('/api/diet/foods')
                        self.assertEqual(response.status_code, 503)
                        self.assertEqual(response.json()['code'], 'DIET_MIGRATION_REQUIRED')
                self.assertEqual(schema(), before)
                self.assertNotIn('food_items', self.tables())

        self.assertTrue(migrations.migrate_diet(self.path))
        after_explicit_001 = schema()
        self.assertNotEqual(after_explicit_001, before)
        with patch.dict(os.environ, {
            'DIET_APPLY_MIGRATIONS': '1',
            'HEALTH_DB_PATH': str(self.path),
        }):
            with TestClient(create_app(Settings('Test', self.path, ()))) as client:
                response = client.get('/api/diet/foods')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {'items': []})
        # Restarting after 001 must not silently apply 002, 003 or 004.
        self.assertEqual(schema(), after_explicit_001)
        self.assertIn('food_items', self.tables())


class MigratedDietTests(test_diet.DietTests):
    """Run every first-stage API test against the extended schema as well."""
    def setUp(self):
        super().setUp()
        migrations.migrate_diet(self.path)
