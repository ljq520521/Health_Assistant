import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.config import Settings
from app.database import connect, init_database
from app.modules.diet import migrations as m1, migration_002 as m2, migration_003 as m3, migration_004 as m4, migration_006 as m6
from app.modules.diet import catalog_repository as catalog, catalog_links as links, build_catalog
from app.modules.diet.library_service import LibraryError
from diet_catalog_app import create_app, authenticate

def initialize(path, extension=True):
    init_database(path)
    for migration in (m1.migrate_diet,m2.migrate_goals,m3.migrate_water,m4.migrate_recipes): migration(path)
    if extension: m6.migrate_catalog(path)

class CatalogArtifactTests(unittest.TestCase):
    def test_reproducible_bytes_and_logical_hash(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a/food_catalog.db';b=Path(d)/'b/food_catalog.db'
            ra=build_catalog.build(a);rb=build_catalog.build(b)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            self.assertEqual(a.read_bytes(),catalog.DEFAULT_PATH.read_bytes())
            self.assertEqual(ra,rb)
            with self.assertRaises(ValueError):build_catalog.build(a)

    def test_exact_v3_payload_source_and_approval(self):
        package,foods,recipes,approval,checks=build_catalog.verified_input()
        with catalog.catalog() as c:
            self.assertEqual({r['food_key']:json.loads(r['payload_json']) for r in c.execute('SELECT * FROM catalog_foods')},{f['source_key']:f for f in foods})
            self.assertEqual({r['recipe_key']:json.loads(r['payload_json']) for r in c.execute('SELECT * FROM catalog_recipes')},{r['recipe_key']:r for r in recipes})
            public_approval=json.loads(c.execute('SELECT payload_json FROM catalog_approvals').fetchone()[0])
            self.assertEqual(public_approval,build_catalog.public_approval(approval))
            for key in ('foods','recipes','dependencies','approver','recorded_at','approved_counts','approval_scope','formal_production_use_approved','recipe_origin','trial_evidence','allergen_safety_verification'):
                self.assertEqual(public_approval[key],approval[key])
            self.assertEqual(public_approval['source_approval_file_sha256'],hashlib.sha256((build_catalog.PACKAGE/'approval-record.json').read_bytes()).hexdigest())
            self.assertEqual(public_approval['historical_workbook']['sha256'],approval['historical_workbook']['sha256'])
            for table in (statement.split()[2] for statement in build_catalog.DDL):
                for row in c.execute('SELECT * FROM '+table):
                    self.assertNotRegex(str(tuple(row)),r'[A-Za-z]:[\\/]+Users[\\/]+')
            self.assertEqual(c.execute('SELECT count(*) FROM catalog_recipe_ingredients').fetchone()[0],48)
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_only_public_tables_and_readonly(self):
        with catalog.catalog() as c:
            self.assertEqual({r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")},{sql.split()[2] for sql in build_catalog.DDL})
            with self.assertRaises(sqlite3.OperationalError):c.execute('DELETE FROM catalog_foods')
        for forbidden in ('profiles','users','diet_records','water_records','tokens'):
            self.assertNotIn(forbidden, [s.split()[2] for s in build_catalog.DDL])

    def test_missing_corrupt_version_errors(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'food_catalog.db'
            with self.assertRaises(LibraryError) as e:catalog.foods(path=p)
            self.assertEqual(e.exception.code,'CATALOG_MISSING')
            p.write_bytes(b'bad sqlite')
            shutil.copy(catalog.DEFAULT_PATH.with_name('catalog-release.json'),p.with_name('catalog-release.json'))
            with self.assertRaises(LibraryError) as e:catalog.foods(path=p)
            self.assertEqual(e.exception.code,'CATALOG_CORRUPT')
            shutil.copy(catalog.DEFAULT_PATH,p)
            with connect(p) as c:c.execute("UPDATE catalog_metadata SET value='999' WHERE key='schema_version'")
            with self.assertRaises(LibraryError) as e:catalog.foods(path=p)
            self.assertEqual(e.exception.code,'CATALOG_VERSION_UNSUPPORTED')

    def test_path_independent_of_current_directory(self):
        original=Path.cwd()
        with tempfile.TemporaryDirectory() as d:
            try:os.chdir(d);self.assertEqual(len(catalog.foods()['items']),134)
            finally:os.chdir(original)

class CatalogAPITests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='public-catalog-test-');self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'user.db'
        env=patch.dict(os.environ,{'HEALTH_DB_PATH':str(self.path),'DIET_APPLY_MIGRATIONS':'0'})
        env.start();self.addCleanup(env.stop)
        initialize(self.path)
        self.client=TestClient(create_app(Settings('Temporary catalog tests',self.path,())))
        self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None)
        self.food=catalog.foods()['items'][0];self.recipe=catalog.recipes()['items'][0]

    def login(self,profile=True):
        token=authenticate(self.client)
        if profile:
            r=self.client.put('/api/profile',json={'display_name':'独立临时测试，非真实用户'})
            self.assertEqual(r.status_code,200,r.text)
        return token

    def ref(self,key=None):
        r=self.client.post('/api/diet/catalog/food-references',json={'food_key':key or self.food['food_key']})
        self.assertEqual(r.status_code,200,r.text);return r.json()

    def recommend(self):
        r=self.client.post('/api/diet/recipe-recommendations/preview',json={'date':'2026-10-20','limit':50})
        self.assertEqual(r.status_code,200,r.text);return r.json()

    def test_anonymous_public_browsing_without_database(self):
        self.client.app.state.settings=Settings('Missing private database',self.path.parent/'absent.db',())
        for endpoint,count in [('foods',134),('recipes',12),('food-categories',9),('recipe-categories',4)]:
            r=self.client.get('/api/diet/catalog/'+endpoint);self.assertEqual(r.status_code,200,r.text);self.assertEqual(len(r.json()['items']),count)
        self.assertFalse((self.path.parent/'absent.db').exists())

    def test_search_categories_and_details(self):
        r=self.client.get('/api/diet/catalog/foods',params={'q':str(self.food['fdc_id']),'category':self.food['category_key']})
        self.assertEqual([f['food_key'] for f in r.json()['items']],[self.food['food_key']])
        self.assertEqual(self.client.get('/api/diet/catalog/foods/'+self.food['food_key']).json(),self.food)
        self.assertEqual(self.client.get('/api/diet/catalog/foods/missing').status_code,404)
        r=self.client.get('/api/diet/catalog/recipes/'+self.recipe['recipe_key'])
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['steps'],self.recipe['steps'])
        self.assertGreater(r.json()['per_serving']['calories_kcal']['total'],0)

    def test_public_resources_reject_mutation(self):
        for method in ('put','delete','post'):
            for resource in ('foods/'+self.food['food_key'],'recipes/'+self.recipe['recipe_key']):
                self.assertEqual(getattr(self.client,method)('/api/diet/catalog/'+resource).status_code,405)

    def test_anonymous_private_and_reference_denied(self):
        for url in ('/api/diet/foods','/api/diet-records','/api/diet/reports?date=2026-10-20'):
            self.assertEqual(self.client.get(url).status_code,401)
        self.assertEqual(self.client.post('/api/diet/catalog/food-references',json={'food_key':self.food['food_key']}).status_code,401)

    def test_stale_login_token_does_not_block_public_browsing(self):
        self.client.headers['Authorization']='Bearer expired-or-invalid-test-token'
        self.assertEqual(self.client.get('/api/diet/config').status_code,200)
        self.assertEqual(self.client.get('/api/diet/catalog/foods').status_code,200)
        self.assertEqual(self.client.get('/api/diet/foods').status_code,401)

    def test_profile_required_and_consent_enforced(self):
        self.login(False)
        self.assertEqual(self.client.post('/api/diet/catalog/food-references',json={'food_key':self.food['food_key']}).status_code,409)
        self.client.put('/api/auth/privacy',json={'consent_health_data':False,'mask_sensitive':False,'analytics_consent':False})
        self.assertEqual(self.client.get('/api/diet/foods').status_code,403)
        self.assertEqual(self.client.post('/api/diet/catalog/food-references',json={'food_key':self.food['food_key']}).status_code,403)
        self.assertEqual(self.client.get('/api/diet/catalog/foods').status_code,200)

    def test_viewer_and_masked_privacy(self):
        self.login();credentials={'username':'catalog_viewer','password':'TemporaryViewer2026!'}
        self.assertEqual(self.client.post('/api/auth/register',json=credentials).status_code,201)
        token=self.client.post('/api/auth/login',json=credentials).json()['access_token']
        self.client.headers['Authorization']='Bearer '+token
        self.client.put('/api/auth/privacy',json={'consent_health_data':True,'mask_sensitive':False,'analytics_consent':False})
        self.assertEqual(self.client.get('/api/diet/foods').status_code,200)
        self.assertEqual(self.client.post('/api/diet/catalog/food-references',json={'food_key':self.food['food_key']}).status_code,403)
        self.assertEqual(self.client.post('/api/diet/foods',json={'name':'不可写'}).status_code,403)
        self.client.put('/api/auth/privacy',json={'consent_health_data':True,'mask_sensitive':True,'analytics_consent':False})
        self.assertEqual(self.client.get('/api/diet/foods').status_code,403)
        self.assertEqual(self.client.post('/api/diet/recipe-recommendations/preview',json={'date':'2026-10-20'}).status_code,403)

    def test_lazy_reference_idempotency_and_protection(self):
        self.login()
        self.assertEqual(self.client.get('/api/diet/foods').json()['items'],[])
        self.client.get('/api/diet/catalog/foods')
        self.assertEqual(self.client.get('/api/diet/foods').json()['items'],[])
        a=self.ref();b=self.ref();self.assertEqual(a,b);self.assertFalse(a['editable'])
        self.assertEqual(len(self.client.get('/api/diet/foods').json()['items']),1)
        self.assertEqual(self.client.put('/api/diet/foods/'+str(a['id']),json={'name':'overwrite'}).status_code,403)
        self.assertEqual(self.client.delete('/api/diet/foods/'+str(a['id'])).status_code,403)
        with connect(self.path) as c:
            with self.assertRaises(sqlite3.IntegrityError):c.execute('UPDATE food_items SET name=? WHERE id=?',('overwrite',a['id']))
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_private_food_ids_and_snapshot_stability(self):
        self.login()
        private=self.client.post('/api/diet/foods',json={'name':'私人食品','calories_per_100g':100}).json()
        payload={'nutrition_mode':'catalog','food_id':private['id'],'record_date':'2026-10-20','meal_type':'lunch','amount_g':200}
        r=self.client.post('/api/diet-records',json=payload);self.assertEqual(r.status_code,201,r.text);before=r.json()
        public=self.ref();self.assertNotEqual(private['id'],public['id'])
        self.assertEqual(self.client.put('/api/diet/foods/'+str(private['id']),json={'name':'私人食品','calories_per_100g':300}).status_code,200)
        self.assertEqual(self.client.get('/api/diet-records/'+str(before['id'])).json(),before)
        r=self.client.post('/api/diet-records',json=payload|{'food_id':public['id'],'amount_g':100})
        self.assertEqual(r.status_code,201,r.text);self.assertEqual(r.json()['calories_kcal'],self.food['calories_per_100g'])
        self.assertEqual(self.client.get('/api/diet/foods/'+str(private['id'])).json()['origin'],'private')

    def test_inventory_preferences_public_recommendations(self):
        self.login();a=self.ref(self.recipe['ingredients'][0]['food_source_key'])
        r=self.client.post('/api/diet/inventory-items',json={'food_id':a['id'],'quantity_g':500});self.assertEqual(r.status_code,201,r.text)
        result=self.recommend();self.assertEqual(result['eligible_count'],12)
        candidate=next(r for r in result['items'] if r['recipe']['id']==self.recipe['recipe_key'])
        self.assertEqual(next(i for i in candidate['ingredients'] if i['food_id']==a['food_key'])['available_g'],500)
        r=self.client.post('/api/diet/food-preferences',json={'food_id':a['id'],'rule_type':'forbidden'});self.assertEqual(r.status_code,201,r.text)
        result=self.recommend()
        expected={r['recipe_key'] for r in catalog.recipes()['items'] if any(i['food_source_key']==a['food_key'] for i in r['ingredients'])}
        self.assertEqual({r['recipe_id'] for r in result['excluded']},expected)
        self.assertEqual(result['eligible_count'],12-len(expected))
        self.assertTrue(any('命中' in r['reason'] for r in result['excluded']))
        self.assertTrue(all(not r['composition_verified'] for r in result['items']))

    def test_legacy_source_hard_exclusions_preserved(self):
        self.login();key=self.recipe['ingredients'][0]['food_source_key'];f=catalog.foods(key=key)
        old=self.client.post('/api/diet/foods',json={'name':'旧导入来源','source_type':'referenced','source_url':f['source_url'],'source_note':'旧来源','calories_per_100g':1}).json()
        self.client.post('/api/diet/food-preferences',json={'food_id':old['id'],'rule_type':'allergy'})
        result=self.recommend();r=next(r for r in result['excluded'] if r['recipe_id']==self.recipe['recipe_key'])
        self.assertIn('命中',r['reason'])
        self.assertEqual(self.client.get('/api/diet/foods/'+str(old['id'])).json()['calories_per_100g'],1)

    def test_real_import_marker_preserves_hard_exclusion_without_source_url(self):
        from app.modules.diet.import_service import note
        self.login();key=self.recipe['ingredients'][0]['food_source_key']
        source=catalog.foods(key=key)
        payload={'name':'保留导入标记但来源链接为空','source_type':'referenced','source_url':'','source_note':note('USDA 来源技术核验',key,source,'synthetic-legacy-run'),'calories_per_100g':1}
        response=self.client.post('/api/diet/foods',json=payload)
        self.assertEqual(response.status_code,201,response.text);food=response.json()
        with connect(self.path) as c:self.assertEqual(links.source_identity(c,food['id']),key)
        rule=self.client.post('/api/diet/food-preferences',json={'food_id':food['id'],'rule_type':'forbidden'})
        self.assertEqual(rule.status_code,201,rule.text)
        result=self.recommend()
        excluded=next(row for row in result['excluded'] if row['recipe_id']==self.recipe['recipe_key'])
        self.assertIn('命中',excluded['reason'])

    def test_malformed_user_import_markers_do_not_break_hard_filters(self):
        self.login()
        for index,marker in enumerate(('[]','null','{"source_key":[]}','{"source_key":7}')):
            with self.subTest(marker=marker):
                food=self.client.post('/api/diet/foods',json={'name':f'私人测试食材 {index}','source_note':'私人来源\nHAIMPORT1:'+marker,'calories_per_100g':100})
                self.assertEqual(food.status_code,201,food.text)
                id=food.json()['id']
                recipe=self.client.post('/api/diet/recipes',json={'name':f'私人禁用测试食谱 {index}','servings':1,'ingredients':[{'food_id':id,'amount_g':100}],'steps':['合成测试步骤，不用于食用']})
                self.assertEqual(recipe.status_code,201,recipe.text)
                rule=self.client.post('/api/diet/food-preferences',json={'food_id':id,'rule_type':'forbidden'})
                self.assertEqual(rule.status_code,201,rule.text)
                result=self.recommend()
                excluded=next(row for row in result['excluded'] if row['recipe_id']==recipe.json()['id'])
                self.assertIn('命中',excluded['reason'])

    def test_recipe_copy_preserves_quantities_steps_and_public_bytes(self):
        self.login();before=catalog.DEFAULT_PATH.read_bytes()
        r=self.client.post('/api/diet/catalog/recipe-copies',json={'recipe_key':self.recipe['recipe_key']})
        self.assertEqual(r.status_code,201,r.text);copy=r.json()
        self.assertIsInstance(copy['id'],int);self.assertEqual(copy['steps'],self.recipe['steps']);self.assertEqual(copy['servings'],self.recipe['servings'])
        self.assertEqual([i['amount_g'] for i in copy['ingredients']],[i['amount_g'] for i in self.recipe['ingredients']])
        self.assertIn('后续修改不自动获得',copy['source_note'])
        self.assertEqual(catalog.DEFAULT_PATH.read_bytes(),before)

    def test_all_twelve_copies_preserve_48_dependencies_and_nutrients(self):
        self.login();source_bytes=catalog.DEFAULT_PATH.read_bytes()
        originals=catalog.recipes()['items'];dependencies=0;keys=set()
        for recipe in originals:
            with self.subTest(recipe=recipe['recipe_key']):
                response=self.client.post('/api/diet/catalog/recipe-copies',json={'recipe_key':recipe['recipe_key']})
                self.assertEqual(response.status_code,201,response.text);copy=response.json()
                for key in ('name','description','servings','preparation_minutes','steps'):
                    self.assertEqual(copy[key],recipe[key])
                self.assertEqual(len(copy['ingredients']),len(recipe['ingredients']))
                with connect(self.path) as c:
                    for item,source in zip(copy['ingredients'],recipe['ingredients']):
                        self.assertEqual(item['amount_g'],source['amount_g'])
                        linked=links.link(c,item['food_id'])
                        self.assertEqual(linked['food_key'],source['food_source_key'])
                        keys.add(linked['food_key']);dependencies+=1
                public=self.client.get('/api/diet/catalog/recipes/'+recipe['recipe_key']).json()
                self.assertEqual(copy['nutrition'],public['nutrition'])
                self.assertEqual(copy['per_serving'],public['per_serving'])
        self.assertEqual(len(originals),12);self.assertEqual(dependencies,48)
        with connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM diet_recipes').fetchone()[0],12)
            self.assertEqual(c.execute('SELECT count(*) FROM diet_catalog_food_links').fetchone()[0],len(keys))
            self.assertEqual(c.execute('SELECT count(*) FROM diet_records').fetchone()[0],0)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(catalog.DEFAULT_PATH.read_bytes(),source_bytes)

    def test_public_api_errors_do_not_disable_private_records(self):
        self.login()
        with patch.object(catalog,'DEFAULT_PATH',self.path.parent/'absent.db'):
            r=self.client.get('/api/diet/catalog/foods');self.assertEqual(r.status_code,503);self.assertEqual(r.json()['code'],'CATALOG_MISSING')
            self.assertEqual(self.client.get('/api/diet-records').status_code,200)

    def test_corrupt_and_incompatible_catalog_api_errors(self):
        folder=self.path.parent/'catalog-copy';folder.mkdir()
        target=folder/'food_catalog.db'
        release=target.with_name('catalog-release.json')
        shutil.copy(catalog.DEFAULT_PATH.with_name('catalog-release.json'),release)
        with patch.object(catalog,'DEFAULT_PATH',target):
            target.write_bytes(b'not a database')
            response=self.client.get('/api/diet/catalog/foods')
            self.assertEqual(response.status_code,503)
            self.assertEqual(response.json()['code'],'CATALOG_CORRUPT')
        shutil.copy(catalog.DEFAULT_PATH,target)
        with connect(target) as c:c.execute("UPDATE catalog_metadata SET value='999' WHERE key='schema_version'")
        with patch.object(catalog,'DEFAULT_PATH',target):
            response=self.client.get('/api/diet/catalog/recipes')
            self.assertEqual(response.status_code,503)
            self.assertEqual(response.json()['code'],'CATALOG_VERSION_UNSUPPORTED')
        release.write_text('[]',encoding='utf-8')
        with patch.object(catalog,'DEFAULT_PATH',target):
            response=self.client.get('/api/diet/catalog/status')
            self.assertEqual(response.status_code,503)
            self.assertEqual(response.json()['code'],'CATALOG_CORRUPT')

    def test_public_reference_soft_preference_uses_local_mapping(self):
        self.login();food=self.ref(self.recipe['ingredients'][0]['food_source_key'])
        response=self.client.post('/api/diet/food-preferences',json={'food_id':food['id'],'rule_type':'like'})
        self.assertEqual(response.status_code,201,response.text)
        result=self.recommend()
        item=next(r for r in result['items'] if r['recipe']['recipe_key']==self.recipe['recipe_key'])
        self.assertGreater(item['scores']['preference'],50)
        self.assertEqual(result['eligible_count'],12)

    def test_public_recipe_copy_is_editable_without_changing_catalog(self):
        self.login();before=catalog.DEFAULT_PATH.read_bytes()
        response=self.client.post('/api/diet/catalog/recipe-copies',json={'recipe_key':self.recipe['recipe_key']})
        self.assertEqual(response.status_code,201,response.text);copied=response.json()
        payload={key:copied[key] for key in ('name','description','servings','preparation_minutes','source_type','source_note','source_url','steps','revision')}
        payload['name']='我的私人改编，仅用于测试'
        payload['ingredients']=[{'food_id':i['food_id'],'amount_g':i['amount_g']} for i in copied['ingredients']]
        response=self.client.put('/api/diet/recipes/'+str(copied['id']),json=payload)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['name'],payload['name'])
        self.assertEqual(catalog.recipes(key=self.recipe['recipe_key'])['name'],self.recipe['name'])
        self.assertEqual(catalog.DEFAULT_PATH.read_bytes(),before)

    def test_unknown_public_allergens_cannot_be_approved_by_course_status(self):
        self.login()
        term=self.client.post('/api/diet/ingredient-terms',json={'name':'独立测试过敏原','kind':'allergen'})
        self.assertEqual(term.status_code,201,term.text)
        rule=self.client.post('/api/diet/food-preferences',json={'term_id':term.json()['id'],'rule_type':'allergy'})
        self.assertEqual(rule.status_code,201,rule.text)
        result=self.recommend()
        self.assertEqual(result['eligible_count'],12)
        self.assertEqual(result['excluded'],[])
        self.assertTrue(all(not row['composition_verified'] for row in result['items']))
        self.assertTrue(any('不视为安全核验通过' in warning for warning in result['warnings']))

    def test_pollen_unknown_does_not_block_catalog_but_explicit_egg_term_does(self):
        self.login()
        for name,kind,rule_type in [('花粉','allergen','allergy'),('鸡蛋','ingredient','forbidden')]:
            term=self.client.post('/api/diet/ingredient-terms',json={'name':name,'kind':kind})
            self.assertEqual(term.status_code,201,term.text)
            response=self.client.post('/api/diet/food-preferences',json={'term_id':term.json()['id'],'rule_type':rule_type})
            self.assertEqual(response.status_code,201,response.text)
        result=self.recommend()
        self.assertEqual(result['eligible_count'],9)
        self.assertEqual({row['name'] for row in result['excluded']},{'玉米牛奶鸡蛋组合','番茄鸡蛋盖饭','水煮鸡蛋黄瓜组合'})
        self.assertTrue(all('命中' in row['reason'] for row in result['excluded']))
        self.assertTrue(all(not row['composition_verified'] for row in result['items']))

    def test_concurrent_lazy_reference_creates_one_anchor(self):
        self.login();key=self.food['food_key']
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows=list(pool.map(lambda _:links.reference(self.path,key),range(2)))
        self.assertEqual(rows[0]['id'],rows[1]['id'])
        with connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM diet_catalog_food_links').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT count(*) FROM food_items').fetchone()[0],1)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_invalid_owner_payload_cannot_select_another_profile(self):
        self.login()
        response=self.client.post('/api/diet/catalog/food-references',json={'food_key':self.food['food_key'],'profile_id':2})
        self.assertEqual(response.status_code,422)
        with connect(self.path) as c:self.assertEqual(c.execute('SELECT count(*) FROM diet_catalog_food_links').fetchone()[0],0)

    def test_no_duplicate_routes(self):
        paths=[(r.path,m) for r in self.client.app.routes for m in getattr(r,'methods',[])];self.assertEqual(len(paths),len(set(paths)))

    def test_water_nutrition_reports_regression(self):
        self.login();a=self.ref()
        self.client.post('/api/diet-records',json={'nutrition_mode':'catalog','food_id':a['id'],'record_date':'2026-10-20','meal_type':'lunch','amount_g':100})
        r=self.client.post('/api/diet/water-records',json={'drank_at':'2026-10-20T09:00:00+08:00','amount_ml':250});self.assertEqual(r.status_code,201,r.text)
        self.assertEqual(self.client.get('/api/diet/water-summary?date=2026-10-20').json()['total_ml'],250)
        self.assertEqual(self.client.put('/api/diet/goals',json={'effective_from':'2026-10-20','calories_kcal':2000}).status_code,200)
        for period in ('day','week','month'):
            r=self.client.get('/api/diet/reports',params={'date':'2026-10-20','period':period});self.assertEqual(r.status_code,200,r.text)

class CatalogMigrationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.path=Path(temp.name)/'user.db';initialize(self.path,False)

    def test_idempotent_additive_separate_registry(self):
        with connect(self.path) as c:
            before=[tuple(r) for r in c.execute('SELECT * FROM diet_schema_migrations')]
            tables={r[0]:[tuple(x) for x in c.execute('SELECT * FROM '+r[0])] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        self.assertTrue(m6.migrate_catalog(self.path));self.assertFalse(m6.migrate_catalog(self.path))
        with connect(self.path) as c:
            self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM diet_schema_migrations')],before)
            for name,rows in tables.items():self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM '+name)],rows)
            self.assertTrue(m6.ready(c));self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_failed_ddl_rolls_back(self):
        original=m6.STATEMENTS
        with patch.object(m6,'STATEMENTS',original+('CREATE TABLE deliberate_failure (x NOT_A_VALID_CONSTRAINT()',)):
            with self.assertRaises(sqlite3.Error):m6.migrate_catalog(self.path)
        with connect(self.path) as c:
            self.assertFalse(m6.ready(c));self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='diet_catalog_food_links'").fetchone())
        self.assertTrue(m6.migrate_catalog(self.path))

    def test_006_required_for_reference_only(self):
        with connect(self.path) as c:c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'临时测试')")
        with self.assertRaises(LibraryError) as e:links.reference(self.path,catalog.foods()['items'][0]['food_key'])
        self.assertEqual(e.exception.code,'CATALOG_LINK_MIGRATION_REQUIRED')
        self.assertEqual(len(catalog.foods()['items']),134)

    def test_concurrent_006_and_legacy_health_rows_unchanged(self):
        with connect(self.path) as c:
            c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'合成保护测试档案')")
            c.execute("INSERT INTO cycle_records(start_date,end_date,notes) VALUES('2026-09-01','2026-09-05','synthetic')")
            c.execute("INSERT INTO exercise_records(record_date,exercise_type,duration_minutes,intensity,notes) VALUES('2026-09-01','synthetic',10,'low','synthetic')")
            c.execute("INSERT INTO sleep_records(sleep_at,wake_at,quality,notes) VALUES('2026-09-01T20:00:00Z','2026-09-02T04:00:00Z',3,'synthetic')")
            c.execute("INSERT INTO diet_records(record_date,meal_type,food_name,amount_g,calories_kcal) VALUES('2026-09-01','lunch','synthetic',100,120)")
            c.execute("INSERT INTO health_goals(title,target_value,unit) VALUES('synthetic',1,'test')")
            tables=('profiles','cycle_records','exercise_records','sleep_records','diet_records','health_goals','users','auth_secrets')
            before={name:[tuple(row) for row in c.execute('SELECT * FROM '+name)] for name in tables}
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:m6.migrate_catalog(self.path),range(2)))
        self.assertEqual(sorted(results),[False,True])
        with connect(self.path) as c:
            self.assertEqual({name:[tuple(row) for row in c.execute('SELECT * FROM '+name)] for name in tables},before)
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_006_checksum_conflict_and_unregistered_structure_are_not_overwritten(self):
        with connect(self.path) as c:c.execute(m6.STATEMENTS[0])
        with self.assertRaisesRegex(RuntimeError,'Unregistered'):m6.migrate_catalog(self.path)
        with connect(self.path) as c:
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='diet_extension_schema_migrations'").fetchone())
            c.execute('DROP TABLE diet_catalog_food_links')
        m6.migrate_catalog(self.path)
        with connect(self.path) as c:c.execute("UPDATE diet_extension_schema_migrations SET checksum='bad'")
        with self.assertRaisesRegex(RuntimeError,'checksum mismatch'):m6.migrate_catalog(self.path)
        with connect(self.path) as c:self.assertEqual(c.execute('SELECT checksum FROM diet_extension_schema_migrations').fetchone()[0],'bad')

if __name__=='__main__':unittest.main()
