import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diet_test_runtime import TestClient
from app.config import Settings
from app.database import connect, init_database
from diet_test_runtime import create_app
from app.modules.diet import migrations as m1, migration_002 as m2, migration_003 as m3

class WaterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='health-water-test-');self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'test.db'
        init_database(self.path);m1.migrate_diet(self.path);m2.migrate_goals(self.path);m3.migrate_water(self.path)
        with connect(self.path) as c:c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'临时测试档案')")
        self.client=TestClient(create_app(Settings('Water tests',self.path,())))
        self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None)
        self.payload={'drank_at':'2026-10-14T09:00:00+08:00','amount_ml':250,'notes':'测试'}
    def create(self,**changes):
        r=self.client.post('/api/diet/water-records',json=self.payload|changes)
        self.assertEqual(r.status_code,201,r.text);return r.json()
    def summary(self,day='2026-10-14'):
        r=self.client.get('/api/diet/water-summary',params={'date':day})
        self.assertEqual(r.status_code,200,r.text);return r.json()
    def test_crud_order_and_timestamps(self):
        a=self.create();b=self.create();url='/api/diet/water-records/'+str(a['id'])
        self.assertEqual(self.client.get(url).json(),a)
        self.assertEqual([r['id'] for r in self.client.get('/api/diet/water-records').json()['items']],[b['id'],a['id']])
        changed=self.client.put(url,json=self.payload|{'amount_ml':300,'notes':'更改'}).json()
        self.assertEqual(changed['amount_ml'],300);self.assertEqual(changed['created_at'],a['created_at']);self.assertNotEqual(changed['updated_at'],a['updated_at'])
        self.assertEqual(self.summary()['total_ml'],550)
        self.assertEqual(self.client.delete(url).status_code,204)
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.summary()['total_ml'],250)
    def test_invalid_amounts(self):
        for value in [0,-1,1.5,True,'250',None,1000001]:
            with self.subTest(value=value):self.assertEqual(self.client.post('/api/diet/water-records',json=self.payload|{'amount_ml':value}).status_code,422)
        for value in ['NaN','Infinity']:
            self.assertEqual(self.client.post('/api/diet/water-records',content='{"drank_at":"2026-10-14T09:00:00Z","amount_ml":'+value+'}',headers={'Content-Type':'application/json'}).status_code,422)
    def test_timezone_storage_and_midnight_filter(self):
        a=self.create(drank_at='2026-10-14T00:00:00+08:00')
        self.create(drank_at='2026-10-13T23:59:59+08:00')
        b=self.create(drank_at='2026-10-14T23:59:59+08:00')
        self.create(drank_at='2026-10-15T00:00:00+08:00')
        self.assertEqual(a['drank_at'],'2026-10-13T16:00:00.000000Z')
        rows=self.client.get('/api/diet/water-records?date_from=2026-10-14&date_to=2026-10-14').json()['items']
        self.assertEqual([r['id'] for r in rows],[b['id'],a['id']]);self.assertEqual(self.summary()['total_ml'],500)
        with connect(self.path) as c:self.assertEqual(c.execute('SELECT drank_at FROM water_records WHERE id=?',(a['id'],)).fetchone()[0],a['drank_at'])
    def test_invalid_time_and_filter(self):
        for value in ['2026-02-30T09:00:00Z','2026-10-14T09:00:00','bad',1]:
            self.assertEqual(self.client.post('/api/diet/water-records',json=self.payload|{'drank_at':value}).status_code,422)
        for query in ['date_from=2026-02-30','date_from=2026-10-15&date_to=2026-10-14']:
            self.assertEqual(self.client.get('/api/diet/water-records?'+query).status_code,422)
        self.assertEqual(self.client.get('/api/diet/water-summary?date=9999-12-31').status_code,422)
    def test_goal_versions_preserve_nutrients_and_exceed_target(self):
        self.client.put('/api/diet/goals',json={'effective_from':'2026-10-13','calories_kcal':1800,'protein_g':80})
        self.client.put('/api/diet/goals',json={'effective_from':'2026-10-14','water_ml':200})
        g=self.client.get('/api/diet/goals?date=2026-10-14').json()['goal']
        self.assertEqual(g['calories_kcal'],1800);self.assertEqual(g['protein_g'],80)
        self.create();s=self.summary();self.assertEqual(s['achievement_percent'],125);self.assertEqual(s['progress_percent'],100);self.assertTrue(s['goal_met'])
        self.assertIsNone(self.summary('2026-10-13')['target_ml'])
        self.client.put('/api/diet/goals',json={'effective_from':'2026-10-15','water_ml':500})
        self.assertEqual(self.summary()['target_ml'],200);self.assertEqual(self.summary('2026-10-15')['target_ml'],500)
        self.client.put('/api/diet/goals',json={'effective_from':'2026-10-14','water_ml':None})
        self.assertEqual(self.client.get('/api/diet/goals?date=2026-10-14').json()['goal']['calories_kcal'],1800)
    def test_no_target_and_no_records(self):
        s=self.summary();self.assertEqual(s['data_status'],'no_records');self.assertEqual(s['total_ml'],0);self.assertIsNone(s['achievement_percent'])
        self.create();self.assertIsNone(self.summary()['target_ml'])
    def test_reminder_get_does_not_insert(self):
        r=self.client.get('/api/diet/water-reminder-settings');self.assertEqual(r.status_code,200);self.assertFalse(r.json()['enabled'])
        with connect(self.path) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM water_reminder_settings').fetchone()[0],0)
    def test_reminder_modes_and_toggle(self):
        fixed={'enabled':True,'mode':'fixed_times','fixed_times':['15:00','09:00','09:00'],'active_start':'09:00','active_end':'18:00'}
        r=self.client.put('/api/diet/water-reminder-settings',json=fixed);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['fixed_times'],['09:00','15:00'])
        r=self.client.put('/api/diet/water-reminder-settings',json={'enabled':False,'mode':'interval','interval_minutes':60});self.assertEqual(r.status_code,200);self.assertFalse(r.json()['enabled'])
        self.assertEqual(self.client.get('/api/diet/water-reminder-settings').json(),r.json())
    def test_reminder_invalid_settings(self):
        for data in [{'mode':'bad'},{'enabled':'yes'},{'mode':'fixed_times','fixed_times':[]},{'mode':'fixed_times','fixed_times':['25:00']},{'mode':'fixed_times','fixed_times':['08:00']},{'interval_minutes':0},{'interval_minutes':True},{'interval_minutes':1000},{'active_start':'22:00','active_end':'06:00'}]:
            with self.subTest(data=data):self.assertEqual(self.client.put('/api/diet/water-reminder-settings',json=data).status_code,422)
    def test_missing_record(self):
        for method in ['get','delete']:
            self.assertEqual(getattr(self.client,method)('/api/diet/water-records/999').status_code,404)
        self.assertEqual(self.client.put('/api/diet/water-records/999',json=self.payload).status_code,404)
    def test_no_profile(self):
        with connect(self.path) as c:c.execute('DELETE FROM profiles')
        for url in ['/api/diet/water-records','/api/diet/water-records/1','/api/diet/water-summary?date=2026-10-14','/api/diet/water-reminder-settings']:
            self.assertEqual(self.client.get(url).status_code,409)
        self.assertEqual(self.client.post('/api/diet/water-records',json=self.payload).status_code,409)
        self.assertEqual(self.client.put('/api/diet/water-reminder-settings',json={}).status_code,409)
    def test_constraints(self):
        with connect(self.path) as c:
            for profile,amount in [(99,250),(1,0),(1,-1),(1,1.5)]:
                with self.assertRaises(sqlite3.IntegrityError):
                    c.execute("INSERT INTO water_records(profile_id,drank_at,amount_ml,created_at,updated_at) VALUES(?,'2026-10-14T00:00:00Z',?,'now','now')",(profile,amount))

class WaterMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'test.db';init_database(self.path);m1.migrate_diet(self.path);m2.migrate_goals(self.path)
    def test_repeat_and_preserve(self):
        with connect(self.path) as c:
            c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'历史')")
            c.execute("INSERT INTO diet_records(record_date,meal_type,food_name,amount_g,calories_kcal) VALUES('2026-10-14','lunch','历史',100,123)")
            c.execute("INSERT INTO diet_daily_goals(profile_id,effective_from,calories_kcal,water_ml,created_at,updated_at) VALUES(1,'2026-10-14',1800,1000,'old','old')")
            before={t:[dict(r) for r in c.execute('SELECT * FROM '+t)] for t in ['diet_records','diet_daily_goals','food_items','diet_schema_migrations']}
            rootpage=c.execute("SELECT rootpage FROM sqlite_master WHERE name='diet_records'").fetchone()[0]
        self.assertTrue(m3.migrate_water(self.path));self.assertFalse(m3.migrate_water(self.path))
        with connect(self.path) as c:
            self.assertTrue(m3.ready(c));self.assertTrue(m2.ready(c));self.assertTrue(m1.migration_ready(c))
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(c.execute("SELECT rootpage FROM sqlite_master WHERE name='diet_records'").fetchone()[0],rootpage)
            for t in ['diet_records','diet_daily_goals','food_items']:self.assertEqual([dict(r) for r in c.execute('SELECT * FROM '+t)],before[t])
            versions=[dict(r) for r in c.execute('SELECT * FROM diet_schema_migrations')]
            for r in before['diet_schema_migrations']:self.assertIn(r,versions)
    def test_failure_rollback(self):
        with patch.object(m3,'STATEMENTS',m3.STATEMENTS+('INVALID SQL',)):
            with self.assertRaises(sqlite3.Error):m3.migrate_water(self.path)
        with connect(self.path) as c:
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='water_records'").fetchone())
            self.assertEqual(c.execute('SELECT COUNT(*) FROM diet_schema_migrations').fetchone()[0],2)
        self.assertTrue(m3.migrate_water(self.path))
    def test_startup_does_not_apply_003(self):
        with TestClient(create_app(Settings('Old DB',self.path,()))) as client:
            self.assertEqual(client.get('/health').status_code,200)
            with connect(self.path) as c:c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'测试')")
            self.assertEqual(client.get('/api/diet/water-records').status_code,503)
            self.assertEqual(client.get('/api/diet-records').status_code,200)
            self.assertEqual(client.get('/api/diet/foods').status_code,200)
            self.assertEqual(client.get('/api/diet/goals?date=2026-10-14').status_code,200)
        with connect(self.path) as c:self.assertFalse(m3.ready(c))
    def test_checksum_conflict(self):
        m3.migrate_water(self.path)
        with connect(self.path) as c:c.execute("UPDATE diet_schema_migrations SET checksum='bad' WHERE version='003_water'")
        with self.assertRaises(RuntimeError):m3.migrate_water(self.path)
