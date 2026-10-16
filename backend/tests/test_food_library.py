import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app.config import Settings
from app.database import connect, init_database
from app.main import create_app
from app.modules.diet.migrations import migrate_diet


class FoodLibraryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'library.db'
        init_database(self.path)
        migrate_diet(self.path)
        with connect(self.path) as db:
            db.execute("INSERT INTO profiles(id,display_name) VALUES(1,'临时测试档案')")
        self.client = TestClient(create_app(Settings('Test', self.path, ())))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def category(self, name='测试分类'):
        result = self.client.post('/api/diet/food-categories', json={'name': name})
        self.assertEqual(result.status_code, 201)
        return result.json()

    def food(self, **changes):
        payload = {'name': '演示食物 A', 'source_type': 'example', 'source_note': '仅用于测试，非真实营养数据', 'calories_per_100g': 123.5, 'protein_g_per_100g': 0, 'fat_g_per_100g': None}
        response = self.client.post('/api/diet/foods', json=payload | changes)
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_category_crud_and_duplicate(self):
        first = self.category('  谷物  ')
        path = f"/api/diet/food-categories/{first['id']}"
        self.assertEqual(first['name'], '谷物')
        self.assertNotIn('name_key', first)
        self.assertEqual(self.client.get(path).json(), first)
        self.assertEqual(self.client.get('/api/diet/food-categories').json()['items'], [first])
        self.assertEqual(self.client.post('/api/diet/food-categories', json={'name':'谷物'}).status_code,409)
        changed = self.client.put(path,json={'name':'早餐类'})
        self.assertEqual(changed.status_code,200)
        self.assertEqual(changed.json()['created_at'],first['created_at'])
        self.assertNotEqual(changed.json()['updated_at'],first['updated_at'])
        deleted = self.client.delete(path)
        self.assertEqual(deleted.status_code,204)
        self.assertEqual(deleted.content,b'')
        self.assertEqual(self.client.get(path).status_code,404)

    def test_category_casefold_and_conflicting_rename(self):
        a=self.category('Fruit')
        b=self.category('蔬菜')
        self.assertEqual(self.client.post('/api/diet/food-categories',json={'name':'FRUIT'}).status_code,409)
        response=self.client.put(f"/api/diet/food-categories/{b['id']}",json={'name':'fruit'})
        self.assertEqual(response.json()['code'],'CATEGORY_NAME_EXISTS')
        self.assertEqual(self.client.get(f"/api/diet/food-categories/{a['id']}").json()['name'],'Fruit')

    def test_food_crud_archive_and_full_replace_defaults(self):
        item=self.food(category_id=self.category()['id'])
        path=f"/api/diet/foods/{item['id']}"
        self.assertEqual(self.client.get(path).json(),item)
        self.assertTrue(item['is_example'])
        self.assertEqual(item['protein_g_per_100g'],0)
        self.assertIsNone(item['fat_g_per_100g'])
        response=self.client.put(path,json={'name':'手工未知资料'})
        self.assertEqual(response.status_code,200)
        changed=response.json()
        self.assertIsNone(changed['category_id'])
        self.assertIsNone(changed['calories_per_100g'])
        self.assertFalse(changed['is_example'])
        self.assertEqual(changed['created_at'],item['created_at'])
        self.assertNotEqual(changed['updated_at'],item['updated_at'])
        deleted=self.client.delete(path)
        self.assertEqual(deleted.status_code,204)
        self.assertEqual(deleted.content,b'')
        self.assertEqual(self.client.get('/api/diet/foods').json(),{'items':[]})
        self.assertEqual(self.client.get(path).status_code,404)
        self.assertEqual(self.client.put(path,json={'name':'不可编辑'}).status_code,404)
        self.assertEqual(self.client.delete(path).status_code,404)
        with connect(self.path) as db:
            row=db.execute('SELECT * FROM food_items WHERE id=?',(item['id'],)).fetchone()
            self.assertIsNotNone(row['deleted_at'])
            self.assertTrue(row['deleted_at'].endswith('Z'))
            self.assertIsNone(row['calories_per_100g'])

    def test_category_in_use_and_archived_food_preserved(self):
        category=self.category(); item=self.food(category_id=category['id'])
        path=f"/api/diet/food-categories/{category['id']}"
        result=self.client.delete(path)
        self.assertEqual(result.status_code,409)
        self.assertEqual(result.json()['code'],'CATEGORY_IN_USE')
        self.client.delete(f"/api/diet/foods/{item['id']}")
        self.assertEqual(self.client.delete(path).status_code,204)
        with connect(self.path) as db:
            row=db.execute('SELECT * FROM food_items WHERE id=?',(item['id'],)).fetchone()
            self.assertIsNone(row['category_id'])
            self.assertEqual(row['calories_per_100g'],123.5)

    def test_search_category_and_literal_wildcards(self):
        a=self.category('A'); b=self.category('B')
        first=self.food(name='演示苹果 A',category_id=a['id'])
        self.food(name='演示苹果 B',category_id=b['id'])
        special=self.food(name='演示 100%_特殊')
        result=self.client.get('/api/diet/foods',params={'q':'苹果','category_id':a['id']})
        self.assertEqual([item['id'] for item in result.json()['items']],[first['id']])
        result=self.client.get('/api/diet/foods',params={'q':'%_'})
        self.assertEqual([item['id'] for item in result.json()['items']],[special['id']])
        self.assertEqual(len(self.client.get('/api/diet/foods?uncategorized=true').json()['items']),1)
        self.assertEqual(self.client.get('/api/diet/foods?q=不存在').json(),{'items':[]})
        self.assertEqual(self.client.get('/api/diet/foods?category_id=1&uncategorized=true').status_code,422)
        self.assertEqual(self.client.get('/api/diet/foods?category_id=0').status_code,422)

    def test_food_invalid_input_and_reference(self):
        invalid=[{'name':''},{'name':'   '},{'name':'a'*101},{'name':'x','calories_per_100g':-1},{'name':'x','protein_g_per_100g':True},{'name':'x','fat_g_per_100g':'NaN'},{'name':'x','carbohydrate_g_per_100g':-1},{'name':'x','category_id':0},{'name':'x','category_id':True},{'name':'x','source_type':'authority'},{'name':'x','source_type':'referenced'},{'name':'x','source_url':'javascript:alert(1)'},{'name':'x','source_url':'file:///private'},{'name':'x','profile_id':2},{'name':'x','is_example':True}]
        item=self.food()
        for payload in invalid:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post('/api/diet/foods',json=payload).status_code,422)
                self.assertEqual(self.client.put(f"/api/diet/foods/{item['id']}",json=payload).status_code,422)
        self.assertEqual(self.client.post('/api/diet/foods',json={'name':'x','category_id':999}).status_code,404)
        self.assertEqual(self.client.post('/api/diet/foods',json={'name':'有来源','source_type':'referenced','source_note':'用户提供的包装资料'}).status_code,201)
        for key in ('calories_per_100g','protein_g_per_100g','fat_g_per_100g','carbohydrate_g_per_100g'):
            response=self.client.post('/api/diet/foods',content='{"name":"test","'+key+'":1e309}',headers={'Content-Type':'application/json'})
            # Non-finite JSON values are invalid; test through schemas separately below
            self.assertEqual(response.status_code,422)

    def test_invalid_category_and_missing_resources(self):
        for payload in ({'name':''},{'name':' '*3},{'name':'x'*51},{'name':'x','id':5}):
            self.assertEqual(self.client.post('/api/diet/food-categories',json=payload).status_code,422)
        for base in ('/api/diet/food-categories','/api/diet/foods'):
            self.assertEqual(self.client.get(base+'/999').status_code,404)
            self.assertEqual(self.client.put(base+'/999',json={'name':'x'}).status_code,404)
            self.assertEqual(self.client.delete(base+'/999').status_code,404)
            self.assertEqual(self.client.get(base+'/abc').status_code,422)

    def test_missing_profile_all_library_endpoints(self):
        with connect(self.path) as db:
            db.execute('DELETE FROM profiles')
        for base in ('/api/diet/food-categories','/api/diet/foods'):
            for method,suffix,kwargs in [('get','',{}),('post','',{'json':{'name':'x'}}),('get','/1',{}),('put','/1',{'json':{'name':'x'}}),('delete','/1',{})]:
                with self.subTest(base=base,method=method):
                    result=getattr(self.client,method)(base+suffix,**kwargs)
                    self.assertEqual(result.status_code,409)
                    self.assertEqual(result.json()['code'],'PROFILE_REQUIRED')

    def test_food_operations_do_not_modify_diet_records(self):
        payload={'record_date':'2026-10-14','meal_type':'lunch','food_name':'历史手动','amount_g':100,'calories_kcal':42.5}
        record=self.client.post('/api/diet-records',json=payload).json()
        item=self.food()
        self.client.put(f"/api/diet/foods/{item['id']}",json={'name':'变更资料','calories_per_100g':999})
        self.client.delete(f"/api/diet/foods/{item['id']}")
        self.assertEqual(self.client.get(f"/api/diet-records/{record['id']}").json(),record)
        self.assertEqual(self.client.get('/api/diet/config').json(),{'time_zone':'Asia/Shanghai'})
