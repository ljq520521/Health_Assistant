"""Actual five-module application acceptance, using new temporary databases only."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.config import Settings, get_settings
from app.database import connect, init_database
from app.modules.diet import migrations as m1, migration_002 as m2, migration_003 as m3, migration_004 as m4, migration_006 as m6
from app.modules.diet import catalog_repository as catalog
from diet_catalog_app import authenticate


class PublicCatalogIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='catalog-full-integration-')
        self.addCleanup(temporary.cleanup)
        self.path=Path(temporary.name).resolve()/'private-test.db'
        environment=patch.dict(os.environ,{'HEALTH_DB_PATH':str(self.path),'DIET_APPLY_MIGRATIONS':'0'})
        environment.start();self.addCleanup(environment.stop)
        # Import the real application only after establishing an isolated path.
        from app.main import create_app
        self.app=create_app(Settings('Actual application, synthetic acceptance only',self.path,()))

    def initialize_001_to_004(self):
        init_database(self.path)
        for migrate in (m1.migrate_diet,m2.migrate_goals,m3.migrate_water,m4.migrate_recipes):
            migrate(self.path)

    def test_public_catalog_before_profile_or_diet_migrations_and_missing_catalog_isolated(self):
        with TestClient(self.app) as client:
            self.assertEqual(client.get('/health').status_code,200)
            self.assertEqual(len(client.get('/api/modules').json()),5)
            self.assertEqual(get_settings().database_path,self.path)
            for resource,count in (('foods',134),('recipes',12)):
                response=client.get('/api/diet/catalog/'+resource)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(len(response.json()['items']),count)
            self.assertEqual(client.get('/api/diet-records').status_code,401)
            authenticate(client)
            self.assertEqual(client.get('/api/diet-records').status_code,409)
            with connect(self.path) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM profiles').fetchone()[0],0)
                self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='food_items'").fetchone())
                self.assertFalse(m6.ready(c))
            with patch.object(catalog,'DEFAULT_PATH',self.path.parent/'absent-catalog.db'):
                response=client.get('/api/diet/catalog/foods')
                self.assertEqual(response.status_code,503)
                self.assertEqual(response.json()['code'],'CATALOG_MISSING')
                self.assertEqual(client.get('/health').status_code,200)
                self.assertEqual(client.get('/api/exercise-records').status_code,409)
                self.assertEqual(client.get('/api/cycle-records').json(),[])

    def test_real_startup_never_applies_006_even_with_old_auto_migration_flag(self):
        self.initialize_001_to_004()
        for value in ('0','1'):
            with self.subTest(DIET_APPLY_MIGRATIONS=value),patch.dict(os.environ,{'DIET_APPLY_MIGRATIONS':value}):
                with TestClient(self.app) as client:
                    self.assertEqual(client.get('/health').status_code,200)
                    self.assertEqual(client.get('/api/diet/catalog/foods').status_code,200)
                    with connect(self.path) as c:
                        self.assertFalse(m6.ready(c))
                        self.assertEqual(c.execute('SELECT count(*) FROM diet_schema_migrations').fetchone()[0],4)
        self.assertTrue(m6.migrate_catalog(self.path))
        with TestClient(self.app) as client:
            self.assertEqual(client.get('/health').status_code,200)
            with connect(self.path) as c:self.assertTrue(m6.ready(c))
        self.assertFalse(m6.migrate_catalog(self.path))

    def test_actual_auth_exercise_cycle_and_public_references_share_only_temporary_database(self):
        self.initialize_001_to_004()
        with TestClient(self.app) as client:
            authenticate(client)
            response=client.put('/api/profile',json={'display_name':'合成集成验收，非真实用户'})
            self.assertEqual(response.status_code,200,response.text)
            exercise=client.post('/api/exercise-records',json={'record_date':'2026-10-20','exercise_type':'synthetic acceptance','duration_minutes':10,'intensity':'low','notes':'non-real test record'})
            self.assertEqual(exercise.status_code,201,exercise.text)
            cycle=client.post('/api/cycle-records',json={'start_date':'2026-09-01','end_date':'2026-09-05','notes':'synthetic acceptance, non-real'})
            self.assertEqual(cycle.status_code,200,cycle.text)
            exercise_before=client.get('/api/exercise-records').json()
            cycle_before=client.get('/api/cycle-records').json()
            with connect(self.path) as c:
                legacy_migrations=[tuple(row) for row in c.execute('SELECT * FROM diet_schema_migrations')]
                profile=[tuple(row) for row in c.execute('SELECT * FROM profiles')]
            self.assertTrue(m6.migrate_catalog(self.path))
            food=client.get('/api/diet/catalog/foods').json()['items'][0]
            reference=client.post('/api/diet/catalog/food-references',json={'food_key':food['food_key']})
            self.assertEqual(reference.status_code,200,reference.text)
            record=client.post('/api/diet-records',json={'record_date':'2026-10-20','meal_type':'lunch','nutrition_mode':'catalog','food_id':reference.json()['id'],'amount_g':100})
            self.assertEqual(record.status_code,201,record.text)
            self.assertEqual(record.json()['calories_kcal'],food['calories_per_100g'])
            recommended=client.post('/api/diet/recipe-recommendations/preview',json={'date':'2026-10-20','limit':50})
            self.assertEqual(recommended.status_code,200,recommended.text)
            self.assertEqual(recommended.json()['eligible_count'],12)
            self.assertEqual(client.get('/api/exercise-records').json(),exercise_before)
            self.assertEqual(client.get('/api/cycle-records').json(),cycle_before)
            self.assertEqual(client.get('/api/cycle-records/report').status_code,200)
            self.assertEqual(client.get('/api/exercise-records/recommendation').status_code,200)
            with connect(self.path) as c:
                self.assertEqual([tuple(row) for row in c.execute('SELECT * FROM diet_schema_migrations')],legacy_migrations)
                self.assertEqual([tuple(row) for row in c.execute('SELECT * FROM profiles')],profile)
                self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])


if __name__=='__main__':unittest.main()
