import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from diet_test_runtime import TestClient
from app.config import Settings
from app.database import connect, init_database
from diet_test_runtime import create_app
from app.modules.diet import migration_002 as m2
from app.modules.diet import migrations as m1
import test_diet
import test_food_library

class NutritionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'test.db'
        init_database(self.path);m1.migrate_diet(self.path);m2.migrate_goals(self.path)
        with connect(self.path) as c:c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'示例测试档案')")
        self.client=TestClient(create_app(Settings('Nutrition tests',self.path,())))
        self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None)
        self.food_data={'name':'示例测试食物','source_type':'example','calories_per_100g':123.4567,'protein_g_per_100g':10,'fat_g_per_100g':0,'carbohydrate_g_per_100g':None}
        self.food=self.client.post('/api/diet/foods',json=self.food_data).json()
        self.catalog={'nutrition_mode':'catalog','food_id':self.food['id'],'record_date':'2026-10-14','meal_type':'lunch','amount_g':150}
    def create(self,**changes):
        r=self.client.post('/api/diet-records',json=self.catalog|changes)
        self.assertEqual(r.status_code,201,r.text);return r.json()
    def manual(self,day,calories=None,**kwargs):
        r=self.client.post('/api/diet-records',json={'record_date':day,'meal_type':'breakfast','food_name':'手动示例','amount_g':100,'calories_kcal':calories}|kwargs)
        self.assertEqual(r.status_code,201,r.text);return r.json()
    def goal(self,day,**changes):
        r=self.client.put('/api/diet/goals',json={'effective_from':day}|changes)
        self.assertEqual(r.status_code,200,r.text);return r.json()
    def summary(self,start='2026-10-14',end='2026-10-14',group='day'):
        r=self.client.get('/api/diet/nutrition-summary',params={'date_from':start,'date_to':end,'group_by':group})
        self.assertEqual(r.status_code,200,r.text);return r.json()
    def test_weight_null_zero_and_snapshot(self):
        row=self.create()
        self.assertEqual(row['calories_kcal'],185.1851)
        self.assertEqual(row['protein_g'],15);self.assertEqual(row['fat_g'],0);self.assertIsNone(row['carbohydrate_g'])
        self.assertEqual(row['snapshot_calories_per_100g'],123.4567);self.assertTrue(row['is_example'])
        with connect(self.path) as c:self.assertIsNone(c.execute('SELECT carbohydrate_g FROM diet_records').fetchone()[0])
    def test_history_edit_weight_and_explicit_refresh(self):
        old=self.create();url=f"/api/diet-records/{old['id']}"
        self.client.put(f"/api/diet/foods/{self.food['id']}",json=self.food_data|{'calories_per_100g':300,'name':'更新示例'})
        self.assertEqual(self.client.get(url).json(),old)
        changed=self.client.put(url,json=self.catalog|{'amount_g':200}).json()
        self.assertEqual(changed['calories_kcal'],246.9134);self.assertEqual(changed['food_name'],old['food_name'])
        meta=self.client.put(url,json=self.catalog|{'amount_g':200,'notes':'修改备注'}).json()
        self.assertEqual(meta['food_version_at'],old['food_version_at']);self.assertEqual(meta['calories_kcal'],changed['calories_kcal'])
        fresh=self.client.put(url,json=self.catalog|{'amount_g':200,'refresh_snapshot':True}).json()
        self.assertEqual(fresh['calories_kcal'],600);self.assertEqual(fresh['food_name'],'更新示例')
    def test_archive_allows_old_snapshot_but_not_refresh(self):
        row=self.create();url=f"/api/diet-records/{row['id']}"
        self.client.delete(f"/api/diet/foods/{self.food['id']}")
        self.assertEqual(self.client.put(url,json=self.catalog|{'amount_g':200}).status_code,200)
        self.assertEqual(self.client.put(url,json=self.catalog|{'refresh_snapshot':True}).status_code,404)
        self.assertEqual(self.client.post('/api/diet-records',json=self.catalog).status_code,404)
    def test_switch_food_or_manual(self):
        old=self.create();url=f"/api/diet-records/{old['id']}"
        food=self.client.post('/api/diet/foods',json=self.food_data|{'calories_per_100g':200}).json()
        changed=self.client.put(url,json=self.catalog|{'food_id':food['id']}).json()
        self.assertEqual(changed['calories_kcal'],300)
        manual=self.client.put(url,json={'record_date':'2026-10-14','meal_type':'lunch','food_name':'手动','amount_g':200,'calories_kcal':80}).json()
        self.assertEqual(manual['nutrition_mode'],'manual');self.assertEqual(manual['calories_kcal'],80);self.assertIsNone(manual['food_id']);self.assertIsNone(manual['snapshot_calories_per_100g'])
    def test_tampered_inputs_and_overflow_do_not_write(self):
        for changes in ({'calories_kcal':1},{'snapshot_protein_g_per_100g':1},{'food_id':True},{'amount_g':0},{'nutrition_mode':'x'},{'refresh_snapshot':'yes'},{'protein_g':5}):
            self.assertEqual(self.client.post('/api/diet-records',json=self.catalog|changes).status_code,422)
        self.client.put(f"/api/diet/foods/{self.food['id']}",json=self.food_data|{'calories_per_100g':1e308})
        self.assertEqual(self.client.post('/api/diet-records',json=self.catalog|{'amount_g':1e308}).status_code,422)
        self.assertEqual(self.client.get('/api/diet-records').json()['items'],[])
    def test_goal_versions_merge_clear_and_water_preserved(self):
        first=self.goal('2026-10-01',calories_kcal=2000,protein_g=100,water_ml=1500)
        second=self.goal('2026-10-10',calories_kcal=1800)
        self.assertEqual(second['protein_g'],100);self.assertEqual(second['water_ml'],1500)
        self.goal('2026-10-10',protein_g=None)
        after=self.client.get('/api/diet/goals?date=2026-10-14').json()['goal']
        self.assertEqual(after['calories_kcal'],1800);self.assertIsNone(after['protein_g']);self.assertEqual(after['water_ml'],1500)
        self.assertEqual(self.client.get('/api/diet/goals?date=2026-10-09').json()['goal'],first)
        self.assertIsNone(self.client.get('/api/diet/goals?date=2026-09-30').json()['goal'])
        self.assertEqual(len(self.client.get('/api/diet/goals/history').json()['items']),2)
    def test_goal_invalid_and_empty_changes(self):
        for value in (0,-1,True,'100','NaN'):
            self.assertEqual(self.client.put('/api/diet/goals',json={'effective_from':'2026-10-14','protein_g':value}).status_code,422)
        for payload in ({'effective_from':'2026-02-30','protein_g':1},{'effective_from':'2026-10-14'},{'effective_from':'2026-10-14','protein_g':1,'profile_id':1}):
            self.assertEqual(self.client.put('/api/diet/goals',json=payload).status_code,422)
        self.assertEqual(self.client.get('/api/diet/goals/history').json()['items'],[])
    def test_zero_unknown_empty_partial_and_over_100(self):
        self.goal('2026-10-01',calories_kcal=100)
        self.manual('2026-10-12',0);self.manual('2026-10-13',None)
        self.manual('2026-10-14',150);self.manual('2026-10-14',None)
        data=self.summary('2026-10-11','2026-10-14')
        values=[d['nutrients']['calories_kcal'] for d in data['daily']]
        self.assertEqual([v['data_status'] for v in values],['no_records','complete','unknown','partial'])
        self.assertEqual([v['known_sum'] for v in values],[None,0,None,150])
        self.assertEqual(values[-1]['achievement_percent'],150);self.assertEqual(values[-1]['ratio_basis'],'known_only')
        self.assertEqual(data['total']['nutrients']['calories_kcal']['target'],400)
        self.assertEqual(data['total']['missing_days'],1)
    def test_week_month_targets_and_partial_period(self):
        self.goal('2026-10-01',calories_kcal=100)
        self.goal('2026-10-15',calories_kcal=200)
        for day in ('2026-10-13','2026-10-14','2026-10-15'):self.manual(day,50)
        weekly=self.summary('2026-10-13','2026-10-15','week')['items'][0]
        self.assertEqual(weekly['period_from'],'2026-10-12');self.assertTrue(weekly['is_partial_period'])
        self.assertEqual(weekly['nutrients']['calories_kcal']['target'],400)
        self.assertEqual(weekly['nutrients']['calories_kcal']['achievement_percent'],37.5)
        monthly=self.summary('2026-10-13','2026-10-15','month')['items'][0]
        self.assertEqual(monthly['period_to'],'2026-10-31');self.assertEqual(monthly['nutrients'],weekly['nutrients'])
    def test_missing_goals_and_leap_year_cross_year(self):
        self.goal('2024-02-29',calories_kcal=100)
        self.manual('2024-02-28',20)
        metric=self.summary('2024-02-28','2024-03-01','month')['total']['nutrients']['calories_kcal']
        self.assertEqual(metric['target_missing_days'],1);self.assertIsNone(metric['target']);self.assertIsNone(metric['achievement_percent'])
        items=self.summary('2025-12-31','2026-01-01','month')['items']
        self.assertEqual(len(items),2);self.assertEqual(items[0]['period_to'],'2025-12-31')
        self.assertEqual(self.summary('9999-12-31','9999-12-31','month')['items'][0]['period_to'],'9999-12-31')
    def test_tiny_positive_target_and_concurrent_merge(self):
        self.goal('2026-10-14',calories_kcal=0.00001)
        self.manual('2026-10-14',0)
        self.assertEqual(self.summary()['total']['nutrients']['calories_kcal']['achievement_percent'],0)
        from app.modules.diet.nutrition_service import save_goal
        from app.modules.diet.nutrition_schemas import GoalChanges
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda d:save_goal(self.path,GoalChanges(**d)),[{'effective_from':'2026-10-14','protein_g':30},{'effective_from':'2026-10-14','fat_g':20}]))
        goal=self.client.get('/api/diet/goals?date=2026-10-14').json()['goal']
        self.assertEqual((goal['protein_g'],goal['fat_g']),(30,20))
    def test_invalid_ranges_and_missing_profile(self):
        for params in ({'date_from':'2026-02-30','date_to':'2026-03-01'},{'date_from':'2026-10-15','date_to':'2026-10-14'},{'date_from':'2020-01-01','date_to':'2026-01-01'},{'date_from':'2026-10-14','date_to':'2026-10-14','group_by':'year'}):
            self.assertEqual(self.client.get('/api/diet/nutrition-summary',params=params).status_code,422)
        with connect(self.path) as c:c.execute('DELETE FROM profiles')
        for url in ('/api/diet/goals?date=2026-10-14','/api/diet/goals/history','/api/diet/nutrition-summary?date_from=2026-10-14&date_to=2026-10-14'):
            self.assertEqual(self.client.get(url).status_code,409)
        self.assertEqual(self.client.put('/api/diet/goals',json={'effective_from':'2026-10-14','protein_g':20}).status_code,409)
    def test_all_nutrient_ratios_and_manual_weight(self):
        row=self.manual('2026-10-14',100,protein_g=30,fat_g=0,carbohydrate_g=20)
        self.goal('2026-10-14',calories_kcal=50,protein_g=15,fat_g=10,carbohydrate_g=40)
        values=self.summary()['total']['nutrients']
        self.assertEqual([values[k]['achievement_percent'] for k in ('calories_kcal','protein_g','fat_g','carbohydrate_g')],[200,200,0,50])
        payload={'record_date':'2026-10-14','meal_type':'lunch','food_name':'手动示例','amount_g':300,'calories_kcal':100,'protein_g':30,'fat_g':0,'carbohydrate_g':20}
        updated=self.client.put(f"/api/diet-records/{row['id']}",json=payload).json()
        self.assertEqual(updated['calories_kcal'],100);self.assertEqual(updated['protein_g'],30)
    def test_edit_earlier_goal_does_not_overwrite_later_version(self):
        self.goal('2026-10-01',calories_kcal=100,protein_g=30)
        later=self.goal('2026-10-10',calories_kcal=200)
        self.goal('2026-10-01',protein_g=40)
        self.assertEqual(self.client.get('/api/diet/goals?date=2026-10-11').json()['goal'],later)
        self.assertEqual(self.client.get('/api/diet/goals?date=2026-10-09').json()['goal']['protein_g'],40)
    def test_record_summary_reacts_to_update_delete(self):
        row=self.manual('2026-10-14',50);self.manual('2026-10-14',None)
        day=self.client.get('/api/diet/record-summary').json()['items'][0]
        self.assertEqual((day['known'],day['knownCount'],day['unknown']),(50,1,1))
        self.client.delete(f"/api/diet-records/{row['id']}")
        self.assertIsNone(self.client.get('/api/diet/record-summary').json()['items'][0]['known'])

class GoalsMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'test.db';init_database(self.path);m1.migrate_diet(self.path)
    def test_preserves_history_and_repeat(self):
        with connect(self.path) as c:
            c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'示例')")
            c.execute("INSERT INTO diet_records(record_date,meal_type,food_name,amount_g,calories_kcal) VALUES('2026-10-14','lunch','历史示例',100,23.123456)")
            before=[dict(r) for r in c.execute('SELECT * FROM diet_records')]
        self.assertTrue(m2.migrate_goals(self.path));self.assertFalse(m2.migrate_goals(self.path));self.assertFalse(m1.migrate_diet(self.path))
        with connect(self.path) as c:
            self.assertEqual(before,[dict(r) for r in c.execute('SELECT * FROM diet_records')])
            self.assertEqual(c.execute('SELECT count(*) FROM diet_schema_migrations').fetchone()[0],2)
    def test_rollback_and_checksum_conflict(self):
        with patch.object(m2,'STATEMENTS',m2.STATEMENTS+('INVALID SQL',)):
            with self.assertRaises(sqlite3.OperationalError):m2.migrate_goals(self.path)
        with connect(self.path) as c:
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='diet_daily_goals'").fetchone())
            self.assertEqual(c.execute('SELECT count(*) FROM diet_schema_migrations').fetchone()[0],1)
        m2.migrate_goals(self.path)
        with connect(self.path) as c:c.execute("UPDATE diet_schema_migrations SET checksum='bad' WHERE version=?",(m2.VERSION,))
        with self.assertRaises(RuntimeError):m2.migrate_goals(self.path)
    def test_concurrent_and_startup_does_not_apply_002(self):
        with patch.dict(os.environ,{'DIET_APPLY_MIGRATIONS':'1'}):
            with TestClient(create_app(Settings('Test',self.path,()))) as client:
                with connect(self.path) as c:
                    self.assertFalse(m2.ready(c));c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'示例')")
                self.assertEqual(client.get('/api/diet/goals?date=2026-10-14').status_code,503)
                self.assertEqual(client.get('/api/diet/foods').status_code,200)
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:m2.migrate_goals(self.path),range(2)))
        self.assertEqual(sorted(results),[False,True])

class FullSchemaDietTests(test_diet.DietTests):
    def setUp(self):
        super().setUp();m1.migrate_diet(self.path);m2.migrate_goals(self.path)
class FullSchemaFoodTests(test_food_library.FoodLibraryTests):
    def setUp(self):
        super().setUp();m2.migrate_goals(self.path)
