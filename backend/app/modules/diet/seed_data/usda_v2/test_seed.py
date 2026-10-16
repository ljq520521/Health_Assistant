"""Seed-specific acceptance. Every database is a new TemporaryDirectory fixture."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.modules.diet import import_service as importer
from app.modules.diet.seed_data.usda_v2 import demo_seed as seed
from app.modules.diet.source_mapping import ImportRejected


class SeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = seed.load_seed()

    def setUp(self):
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        temporary = tempfile.TemporaryDirectory(prefix=seed.PREFIX)
        self.addCleanup(temporary.cleanup)
        self.path = seed.prepare_new(temporary.name)

    def snapshot(self):
        with importer.database(self.path) as connection:
            return importer.snapshot(connection)

    def apply(self):
        preview = seed.import_demo(self.path, self.package)
        return seed.import_demo(self.path, self.package, apply=True,
                                expected_plan_sha256=preview['plan_sha256'])

    def client(self):
        os.environ['HEALTH_DIET_SEED_DB'] = str(self.path)
        client = TestClient(seed.create_demo_app())
        client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        return client

    def test_default_preview_cleans_temporary_database(self):
        before = self.snapshot()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(seed.main([]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report['status'], 'dry_run')
        self.assertEqual(report['counts'], {'add': 146, 'skip': 0, 'conflict': 0})
        self.assertTrue(report['temporary_directory_removed'])
        self.assertFalse(Path(report['database_path']).exists())
        self.assertEqual(before, self.snapshot())

    def test_migrations_profile_foreign_keys_and_preview_readonly(self):
        before = self.snapshot()
        preview = seed.import_demo(self.path, self.package)
        self.assertEqual(preview['counts'], {'add': 146, 'skip': 0, 'conflict': 0})
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.path.parent / 'audit').exists())
        with importer.database(self.path) as connection:
            self.assertEqual(connection.execute('PRAGMA foreign_keys').fetchone()[0], 1)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM diet_schema_migrations').fetchone()[0], 4)
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_import_repeat_skip_preserves_other_modules(self):
        with importer.database(self.path, write=True) as connection:
            connection.execute("INSERT INTO cycle_records(start_date,end_date) VALUES('2026-09-01','2026-09-05')")
            connection.execute("INSERT INTO exercise_records(record_date,exercise_type,duration_minutes,intensity) VALUES('2026-09-01','synthetic',10,'low')")
            connection.execute("INSERT INTO sleep_records(sleep_at,wake_at,quality) VALUES('2026-09-01T20:00:00Z','2026-09-02T04:00:00Z',3)")
        before = self.snapshot()
        self.assertEqual(self.apply()['status'], 'committed')
        after = self.snapshot()
        for table in ('profiles', 'cycle_records', 'exercise_records', 'sleep_records', 'health_goals'):
            self.assertEqual(before[table], after[table], table)
        self.assertEqual(len(after['food_items']), 134)
        self.assertEqual(len(after['diet_recipes']), 12)
        repeat = self.apply()
        self.assertEqual(repeat['counts'], {'add': 0, 'skip': 146, 'conflict': 0})
        self.assertEqual(after, self.snapshot())

    def test_source_conflict_stops_without_overwriting_user_row(self):
        food = self.package['foods'][0]
        from app.modules.diet.library_schemas import FoodInput
        from app.modules.diet.library_service import save_food
        save_food(self.path, FoodInput(name='synthetic user food', source_type='referenced',
                                      source_url=food.source_url, source_note='Synthetic conflict fixture'))
        before = self.snapshot()
        preview = seed.import_demo(self.path, self.package)
        self.assertGreater(preview['counts']['conflict'], 0)
        with self.assertRaises(ImportRejected):
            seed.import_demo(self.path, self.package, apply=True, expected_plan_sha256=preview['plan_sha256'])
        self.assertEqual(before, self.snapshot())

    def test_modified_imported_food_conflicts(self):
        self.apply()
        with importer.database(self.path, write=True) as connection:
            connection.execute("UPDATE food_items SET name='synthetic user edit' WHERE id=(SELECT MIN(id) FROM food_items)")
        before = self.snapshot()
        with self.assertRaises(ImportRejected):
            self.apply()
        self.assertEqual(before, self.snapshot())

    def test_stale_plan_rejects_write(self):
        preview = seed.import_demo(self.path, self.package)
        with importer.database(self.path, write=True) as connection:
            connection.execute("INSERT INTO health_goals(title,target_value,unit) VALUES('synthetic',1,'unit')")
        before = self.snapshot()
        with self.assertRaises(ImportRejected):
            seed.import_demo(self.path, self.package, apply=True, expected_plan_sha256=preview['plan_sha256'])
        self.assertEqual(before, self.snapshot())

    def test_regular_import_rejects_pending_package(self):
        before = self.snapshot()
        with self.assertRaises(ImportRejected):
            importer.load_package(seed.PACKAGE)
        self.assertEqual(before, self.snapshot())

    def test_missing_migration_never_auto_upgrades(self):
        with importer.database(self.path, write=True) as connection:
            connection.execute("DELETE FROM diet_schema_migrations WHERE version='004_recipes'")
        before = self.snapshot()
        with self.assertRaises(ImportRejected):
            seed.import_demo(self.path, self.package)
        self.assertEqual(before, self.snapshot())

    def test_missing_demo_profile_rejected(self):
        with importer.database(self.path, write=True) as connection:
            connection.execute('DELETE FROM profiles')
        with self.assertRaises(ImportRejected):
            seed.import_demo(self.path, self.package)

    def test_unlabelled_and_health_db_targets_rejected(self):
        before = self.snapshot()
        marker = self.path.parent / seed.MARKER
        marker.rename(marker.with_suffix('.saved'))
        with self.assertRaises(ImportRejected):
            seed.import_demo(self.path, self.package)
        with self.assertRaises(ValueError):
            seed.import_demo(self.path.parent / 'health.db', self.package)
        self.assertFalse((self.path.parent / 'health.db').exists())
        self.assertEqual(before, self.snapshot())

    def test_real_seed_api_search_nutrition_recommendation_and_cycle(self):
        self.apply()
        client = self.client()
        from app.config import get_settings
        self.assertEqual(get_settings().database_path, self.path)
        self.assertFalse(client.get('/api/diet/config').json()['demo']['approved'])
        foods = client.get('/api/diet/foods').json()['items']
        recipes = client.get('/api/diet/recipes').json()['items']
        self.assertEqual(len(foods), 134)
        self.assertEqual(len(recipes), 12)
        for word in ('米饭', '鸡蛋', '牛奶'):
            response = client.get('/api/diet/foods', params={'q': word})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['items'])
        originals = {r.recipe_key: r for r in self.package['recipes']}
        source_foods = {f.source_key: f for f in self.package['foods']}
        for recipe in recipes:
            self.assertIn('未经实际试做', recipe['source_note'])
            original = originals[importer.marker(recipe)['key']]
            calories = [source_foods[i.food_source_key].calories_per_100g for i in original.ingredients]
            if all(value is not None for value in calories):
                expected = sum(value * ingredient.amount_g / 100 for value, ingredient in zip(calories, original.ingredients))
                self.assertAlmostEqual(recipe['nutrition']['calories_kcal']['total'], expected, places=3)
                self.assertAlmostEqual(recipe['per_serving']['calories_kcal']['total'], expected / original.servings, places=3)
        payload = {'date': '2026-10-15', 'limit': 50}
        response = client.post('/api/diet/recipe-recommendations/preview', json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['eligible_count'], 12)
        self.assertTrue(all(item['score'] is None for item in response.json()['items']))
        ingredient = response.json()['items'][0]['ingredients'][0]
        self.assertEqual(client.post('/api/diet/inventory-items', json={'food_id': ingredient['food_id'], 'quantity_g': ingredient['required_g'] / 2}).status_code, 201)
        self.assertEqual(client.put('/api/diet/goals', json={'effective_from': '2026-10-01', 'calories_kcal': 2000, 'protein_g': 80}).status_code, 200)
        targeted = client.post('/api/diet/recipe-recommendations/preview', json=payload | {'target_ratio': .3}).json()
        self.assertTrue(any(item['scores']['nutrition'] is not None for item in targeted['items']))
        self.assertTrue(any(item['missing_ingredients'] for item in targeted['items']))
        for item in targeted['items']:
            self.assertAlmostEqual(sum(item['weights'].values()), 1)
        self.assertEqual(client.post('/api/cycle-records', json={'start_date': '2026-09-01', 'end_date': '2026-09-05'}).status_code, 200)
        self.assertEqual(len(client.get('/api/cycle-records').json()), 1)
        self.assertEqual(client.get('/api/cycle-records/report').status_code, 200)

    def test_mid_import_failure_rolls_back_all_business_rows(self):
        before = self.snapshot()
        with patch('app.modules.diet.recipe_service.save_in_connection', side_effect=RuntimeError('seed rollback probe')):
            with self.assertRaisesRegex(RuntimeError, 'seed rollback probe'):
                self.apply()
        self.assertEqual(before, self.snapshot())


if __name__ == '__main__':
    unittest.main()
