import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diet_test_runtime import TestClient
from app.config import Settings
from app.database import connect,init_database
from diet_test_runtime import create_app
from app.modules.diet import migrations as m1,migration_002 as m2,migration_003 as m3,migration_004 as m4

class RecipeFixture(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='recipe-test-');self.addCleanup(temp.cleanup);self.path=Path(temp.name)/'test.db'
        init_database(self.path);m1.migrate_diet(self.path);m2.migrate_goals(self.path);m3.migrate_water(self.path);m4.migrate_recipes(self.path)
        with connect(self.path) as c:c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'临时验收档案')")
        self.client=TestClient(create_app(Settings('Test',self.path,())))
        self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None)
    def food(self,name='测试食材',**changes):
        r=self.client.post('/api/diet/foods',json={'name':name,'calories_per_100g':100,'protein_g_per_100g':10,'fat_g_per_100g':0,**changes})
        self.assertEqual(r.status_code,201,r.text);return r.json()
    def recipe(self,food=None,**changes):
        f=food or self.food()
        payload={'name':'临时测试食谱','servings':2,'ingredients':[{'food_id':f['id'],'amount_g':200}],'steps':['测试步骤'],**changes}
        r=self.client.post('/api/diet/recipes',json=payload);self.assertEqual(r.status_code,201,r.text);return r.json(),payload

class RecipeTests(RecipeFixture):
    def test_crud_category_and_archive(self):
        cat=self.client.post('/api/diet/recipe-categories',json={'name':'测试分类'});self.assertEqual(cat.status_code,201)
        cid=cat.json()['id'];r,p=self.recipe(category_id=cid)
        self.assertEqual(self.client.get('/api/diet/recipes',params={'q':'临时','category_id':cid}).json()['items'][0]['id'],r['id'])
        self.assertEqual(self.client.delete(f'/api/diet/recipe-categories/{cid}').status_code,409)
        response=self.client.put(f"/api/diet/recipes/{r['id']}",json=p|{'name':'修改','revision':r['revision']})
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['revision'],2)
        self.assertEqual(self.client.put(f"/api/diet/recipes/{r['id']}",json=p|{'revision':1}).status_code,409)
        self.assertEqual(self.client.delete(f"/api/diet/recipes/{r['id']}").status_code,204)
        self.assertEqual(self.client.get(f"/api/diet/recipes/{r['id']}").status_code,404)
        self.assertEqual(self.client.get('/api/diet/recipes').json()['items'],[])
        self.assertEqual(self.client.delete(f'/api/diet/recipe-categories/{cid}').status_code,204)
    def test_weight_servings_unknown_zero(self):
        r,_=self.recipe()
        self.assertEqual(r['nutrition']['calories_kcal']['total'],200)
        self.assertEqual(r['per_serving']['calories_kcal']['total'],100)
        self.assertEqual(r['per_serving']['fat_g']['total'],0)
        self.assertIsNone(r['nutrition']['carbohydrate_g']['total'])
        self.assertEqual(r['nutrition']['carbohydrate_g']['unknown_count'],1)
    def test_snapshot_stable_and_explicit_refresh(self):
        f=self.food();r,p=self.recipe(f)
        self.client.put('/api/diet/foods/'+str(f['id']),json={'name':'修改食材','calories_per_100g':300})
        self.assertEqual(self.client.get('/api/diet/recipes/'+str(r['id'])).json()['nutrition']['calories_kcal']['total'],200)
        p['ingredients'][0]['amount_g']=100
        edited=self.client.put('/api/diet/recipes/'+str(r['id']),json=p|{'revision':1}).json()
        self.assertEqual(edited['nutrition']['calories_kcal']['total'],100)
        fresh=self.client.post(f"/api/diet/recipes/{r['id']}/refresh-nutrition",json={'revision':2})
        self.assertEqual(fresh.status_code,200,fresh.text);self.assertEqual(fresh.json()['nutrition']['calories_kcal']['total'],300)
    def test_manual_nutrition_and_validation(self):
        r,p=self.recipe(nutrition_mode='manual',manual_calories_kcal=400,source_note='用户估计，测试')
        self.assertEqual(r['per_serving']['calories_kcal']['total'],200)
        for change in [{'servings':0},{'steps':[]},{'ingredients':[]},{'manual_calories_kcal':-1},{'source_note':''}]:
            self.assertEqual(self.client.post('/api/diet/recipes',json=p|change).status_code,422)
    def test_partial_nutrition_known_sum(self):
        a=self.food();b=self.food('未知',calories_per_100g=None)
        r,_=self.recipe(a,ingredients=[{'food_id':a['id'],'amount_g':100},{'food_id':b['id'],'amount_g':100}])
        self.assertIsNone(r['nutrition']['calories_kcal']['total']);self.assertEqual(r['nutrition']['calories_kcal']['known_sum'],100)
    def test_atomic_invalid_food_and_no_profile(self):
        r,p=self.recipe();before=self.client.get('/api/diet/recipes').json()
        self.assertEqual(self.client.put('/api/diet/recipes/'+str(r['id']),json=p|{'revision':1,'ingredients':[{'food_id':999,'amount_g':1}]}).status_code,404)
        self.assertEqual(self.client.get('/api/diet/recipes').json(),before)
        with connect(self.path) as c:c.execute('DELETE FROM profiles')
        self.assertEqual(self.client.get('/api/diet/recipes').status_code,409)

class RecipeMigrationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.path=Path(temp.name)/'db'
        init_database(self.path);m1.migrate_diet(self.path);m2.migrate_goals(self.path);m3.migrate_water(self.path)
    def test_repeat_and_original_tables(self):
        with connect(self.path) as c:
            c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'旧档案')")
            c.execute("INSERT INTO diet_records(record_date,meal_type,food_name,amount_g,calories_kcal) VALUES('2026-10-14','lunch','旧数据',100,123)")
            before=[tuple(r) for r in c.execute('SELECT * FROM diet_records')]
            root=c.execute("SELECT rootpage FROM sqlite_master WHERE name='diet_records'").fetchone()[0]
        self.assertTrue(m4.migrate_recipes(self.path));self.assertFalse(m4.migrate_recipes(self.path))
        with connect(self.path) as c:
            self.assertTrue(m4.ready(c));self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM diet_records')],before)
            self.assertEqual(c.execute("SELECT rootpage FROM sqlite_master WHERE name='diet_records'").fetchone()[0],root)
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
    def test_failure_rollback(self):
        with patch.object(m4,'STATEMENTS',m4.STATEMENTS+('INVALID SQL',)):
            with self.assertRaises(sqlite3.Error):m4.migrate_recipes(self.path)
        with connect(self.path) as c:
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='diet_recipes'").fetchone())
            self.assertEqual(c.execute('SELECT COUNT(*) FROM diet_schema_migrations').fetchone()[0],3)
    def test_unmigrated_app_compatibility(self):
        with connect(self.path) as c:c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'旧档案')")
        with TestClient(create_app(Settings('Test',self.path,()))) as client:
            self.assertEqual(client.get('/api/diet/recipes').status_code,503)
            self.assertEqual(client.post('/api/diet/recipe-recommendations/preview',json={'date':'2026-10-14'}).status_code,503)
            for url in ['/health','/api/diet-records','/api/diet/foods','/api/diet/water-records','/api/diet/goals?date=2026-10-14']:
                self.assertEqual(client.get(url).status_code,200,url)
        with connect(self.path) as c:self.assertFalse(m4.ready(c))
    def test_version_checksum_and_schema_drift_rejected(self):
        m4.migrate_recipes(self.path)
        with connect(self.path) as c:c.execute("UPDATE diet_schema_migrations SET checksum='bad' WHERE version=?",(m4.VERSION,))
        with self.assertRaises(RuntimeError):m4.migrate_recipes(self.path)
        with connect(self.path) as c:
            c.execute('UPDATE diet_schema_migrations SET checksum=? WHERE version=?',(m4.CHECKSUM,m4.VERSION))
            c.execute('DROP INDEX idx_recipe_food')
        with self.assertRaises(RuntimeError):m4.migrate_recipes(self.path)
    def test_all_legacy_rows_unchanged(self):
        with TestClient(create_app(Settings('Legacy',self.path,()))) as client:
            with connect(self.path) as c:c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'旧档案')")
            self.assertEqual(client.post('/api/diet/foods',json={'name':'历史食材','calories_per_100g':123}).status_code,201)
            self.assertEqual(client.post('/api/diet-records',json={'record_date':'2026-10-14','meal_type':'lunch','food_name':'历史手工','amount_g':150,'calories_kcal':88}).status_code,201)
            self.assertEqual(client.put('/api/diet/goals',json={'effective_from':'2026-10-14','calories_kcal':2000,'water_ml':1800}).status_code,200)
            self.assertEqual(client.post('/api/diet/water-records',json={'drank_at':'2026-10-14T01:00:00Z','amount_ml':250}).status_code,201)
        with connect(self.path) as c:
            tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            before={t:[tuple(r) for r in c.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in tables}
        m4.migrate_recipes(self.path);self.assertFalse(m4.migrate_recipes(self.path))
        with connect(self.path) as c:
            for t in tables:
                after=[tuple(r) for r in c.execute('SELECT * FROM '+t+' ORDER BY rowid')]
                self.assertEqual(after[:3] if t=='diet_schema_migrations' else after,before[t],t)
    def test_new_table_constraints(self):
        m4.migrate_recipes(self.path)
        with connect(self.path) as c:
            c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'测试')")
            c.execute("INSERT INTO food_items(profile_id,name,source_type,created_at,updated_at) VALUES(1,'食物','user_entered','t','t')")
            for food,quantity in ((999,100),(1,-1)):
                with self.assertRaises(sqlite3.IntegrityError):c.execute("INSERT INTO diet_inventory_items(profile_id,food_id,quantity_g,created_at,updated_at) VALUES(1,?,?,'t','t')",(food,quantity))
            with self.assertRaises(sqlite3.IntegrityError):c.execute("INSERT INTO diet_food_preferences(profile_id,rule_type,created_at,updated_at) VALUES(1,'allergy','t','t')")
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
