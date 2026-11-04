import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.config import Settings
from app.database import connect
from app.modules.diet import demo_environment as demo, import_service as importer
from app.modules.diet.demo_server import create_demo_app
from diet_import_fixtures import fixture


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='diet-demo-test-')
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name).resolve();self.path=self.folder/'demo.db'

    def ready(self):
        demo.initialize_empty(self.path)
        (self.folder/demo.MARKER_FILE).write_text(json.dumps({'database_path':str(self.path),
            'purpose':'pending-validation','status':'ready','approved':False,
            'manifest_sha256':demo.V2_SHA256,'package_review_status':'pending_final_confirmation'}),encoding='utf8')

    def test_initialize_profile_and_foreign_keys(self):
        self.ready()
        with connect(self.path) as c:
            row=c.execute('SELECT * FROM profiles').fetchone()
            self.assertEqual(row['display_name'],demo.PROFILE_NAME)
            self.assertIsNone(row['height_cm']);self.assertIsNone(row['weight_kg'])
            self.assertEqual(row['medical_history'],'')
            self.assertEqual(c.execute('PRAGMA foreign_keys').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM diet_schema_migrations').fetchone()[0],4)
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall())
        self.path.unlink()  # Windows: all handles must already be closed.

    def test_never_reinitialize_existing_file(self):
        self.path.write_bytes(b'unchanged')
        with self.assertRaises(FileExistsError):demo.initialize_empty(self.path)
        self.assertEqual(self.path.read_bytes(),b'unchanged')

    def test_reject_health_name_and_non_temp_path(self):
        with self.assertRaises(ValueError):demo.safe_path(self.folder/'health.db')
        with self.assertRaises(ValueError):demo.safe_path(Path(__file__).parent/'demo.db')

    def test_server_has_no_default_fallback(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError):create_demo_app()
        self.assertFalse(self.path.exists())

    def test_marker_and_profile_required_before_startup(self):
        demo.initialize_empty(self.path)
        with self.assertRaises(FileNotFoundError):demo.read_context(self.path)
        self.ready_marker = self.folder/demo.MARKER_FILE
        self.ready_marker.write_text('{}')
        with self.assertRaises(ValueError):demo.read_context(self.path)

    def test_demo_config_and_normal_config_separate(self):
        from app.main import create_app
        self.ready()
        with patch.dict(os.environ,{'HEALTH_DIET_DEMO_DB':str(self.path)}):
            with TestClient(create_demo_app()) as client:
                data=client.get('/api/diet/config').json()['demo']
                self.assertEqual(data['database_path'],str(self.path))
                self.assertFalse(data['approved']);self.assertEqual(data['notice'],demo.NOTICE)
        with TestClient(create_app(Settings('Test',self.path,()))) as client:
            self.assertNotIn('demo',client.get('/api/diet/config').json())

    def test_labelled_import_keeps_values_and_is_idempotent(self):
        self.ready();root=self.folder/'package';fixture(root)
        package=importer.load_package(root,allow_test_fixtures=True)
        before=package['foods'][0].model_dump()
        factory=importer.food_payload
        with demo.labelled_payloads():
            plan=importer.dry_run(self.path,package)
            importer.apply_package(self.path,package,self.folder/'audit',expected_plan_sha256=plan['plan_sha256'])
            repeat=importer.dry_run(self.path,package)
            self.assertEqual(repeat['counts'],{'add':0,'skip':2,'conflict':0})
            importer.apply_package(self.path,package,self.folder/'audit',expected_plan_sha256=repeat['plan_sha256'])
        self.assertIs(importer.food_payload,factory)
        self.assertEqual(package['foods'][0].model_dump(),before)
        with connect(self.path) as c:
            food=c.execute('SELECT * FROM food_items').fetchone()
            self.assertTrue(food['source_note'].startswith(demo.NOTICE))
            self.assertEqual(food['fat_g_per_100g'],0);self.assertIsNone(food['carbohydrate_g_per_100g'])
            self.assertEqual(importer.marker(food)['key'],before['source_key'])
            recipe=c.execute('SELECT * FROM diet_recipes').fetchone()
            self.assertIn('未经实际试做',recipe['source_note'])

    def test_label_context_failure_rolls_back(self):
        self.ready();root=self.folder/'package';fixture(root)
        package=importer.load_package(root,allow_test_fixtures=True)
        with importer.database(self.path) as c:before=importer.snapshot(c)
        with demo.labelled_payloads():
            plan=importer.dry_run(self.path,package)
            with patch('app.modules.diet.recipe_service.save_in_connection',side_effect=RuntimeError('probe')):
                with self.assertRaises(RuntimeError):
                    importer.apply_package(self.path,package,self.folder/'audit',expected_plan_sha256=plan['plan_sha256'])
        with importer.database(self.path) as c:self.assertEqual(before,importer.snapshot(c))
