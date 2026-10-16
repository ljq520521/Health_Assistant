import copy
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
from pydantic import ValidationError
from test_recipes import RecipeFixture
from diet_import_fixtures import fixture,write_json,rehash
from app.modules.diet.import_service import load_package,dry_run,apply_package,database,snapshot
from app.modules.diet.source_mapping import ImportRejected,mapped_nutrients,sha
from app.modules.diet.import_data import main

class ImportTests(RecipeFixture):
    def setUp(self):
        super().setUp()
        self.root=self.path.parent/'package';self.audit=self.path.parent/'audit'
        self.food_data,self.recipe_data,self.raw=fixture(self.root)
    def package(self): return load_package(self.root,allow_test_fixtures=True)
    def apply(self,package=None):
        p=package or self.package();preview=dry_run(self.path,p)
        return apply_package(self.path,p,self.audit,expected_plan_sha256=preview['plan_sha256'])
    def rewrite_food(self,**changes):
        self.food_data.update(changes);write_json(self.root/'foods.json',[self.food_data]);rehash(self.root)
    def state(self):
        with database(self.path) as c:return snapshot(c)
    def test_json_import_queries_nutrition_and_audit(self):
        result=self.apply();self.assertEqual(result['status'],'committed')
        foods=self.client.get('/api/diet/foods',params={'q':'夹具'}).json()['items'];self.assertEqual(len(foods),1)
        self.assertEqual(len(self.client.get('/api/diet/foods',params={'category_id':foods[0]['category_id']}).json()['items']),1)
        recipe=self.client.get('/api/diet/recipes').json()['items'][0]
        self.assertEqual(recipe['nutrition']['calories_kcal']['total'],240)
        self.assertEqual(recipe['per_serving']['calories_kcal']['total'],120)
        self.assertEqual(recipe['nutrition']['fat_g']['total'],0)
        self.assertIsNone(recipe['nutrition']['carbohydrate_g']['total'])
        self.assertEqual(len(list(self.audit.glob('*.committed.json'))),1)
        self.assertEqual(len(list(self.audit.glob('*.pending.json'))),1)
    def test_default_dry_run_is_read_only_and_closes(self):
        before=self.path.read_bytes();r=dry_run(self.path,self.package())
        self.assertEqual(r['counts'],{'add':2,'skip':0,'conflict':0});self.assertEqual(self.path.read_bytes(),before)
        probe=self.path.parent/'closure.db'
        with sqlite3.connect(probe) as c:c.execute('CREATE TABLE t(id)')
        c.close()
        with database(probe) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM t').fetchone()[0],0)
        probe.unlink();self.assertFalse(probe.exists())
    def test_repeat_skips_without_data_change(self):
        self.apply();before=self.state();r=self.apply()
        self.assertEqual(r['preview']['counts'],{'add':0,'skip':2,'conflict':0});self.assertEqual(before,self.state())
    def test_csv_equivalent_and_null_preserved(self):
        fixture(self.root,fmt='csv');r=self.apply();self.assertEqual(len(r['added']),2)
        item=self.client.get('/api/diet/foods').json()['items'][0]
        self.assertIsNone(item['carbohydrate_g_per_100g']);self.assertEqual(item['fat_g_per_100g'],0)
    def test_hash_tampering_and_review_anchor(self):
        with self.assertRaises(ImportRejected):load_package(self.root,expected_manifest_sha256='0'*64,allow_test_fixtures=True)
        with (self.root/'foods.json').open('a') as f:f.write(' ')
        with self.assertRaises(ImportRejected):self.package()
    def test_source_archive_hash_tampering(self):
        with (self.root/'source.zip').open('ab') as f:f.write(b'x')
        with self.assertRaises(ImportRejected):self.package()
    def test_fake_official_identity_rejected(self):
        for changes in ({'fdc_id':9},{'original_english_name':'changed'},{'source_url':'https://example.com/food'}):
            with self.subTest(changes=changes):
                fixture(self.root);self.food_data=json.loads((self.root/'foods.json').read_text(encoding='utf-8'))[0]
                self.rewrite_food(**changes)
                with self.assertRaises((ImportRejected,ValidationError)):self.package()
    def test_nutrition_must_equal_original(self):
        self.rewrite_food(calories_per_100g=121)
        with self.assertRaises(ImportRejected):self.package()
    def test_null_must_not_be_replaced_with_zero(self):
        self.rewrite_food(carbohydrate_g_per_100g=0)
        with self.assertRaises(ImportRejected):self.package()
    def test_invalid_unit_bool_number_unknown_field_and_pending(self):
        for changes in ({'energy_unit':'kJ'},{'protein_g_per_100g':-1},{'fat_g_per_100g':101},
                        {'calories_per_100g':True},{'fdc_id':True},{'extra':'x'},{'review_status':'pending'},
                        {'protein_g_per_100g':'8'},{'calories_per_100g':1001}):
            with self.subTest(changes=changes):
                fixture(self.root);self.food_data=json.loads((self.root/'foods.json').read_text(encoding='utf-8'))[0]
                self.rewrite_food(**changes)
                with self.assertRaises((ImportRejected,ValidationError)):self.package()
    def test_duplicate_json_key_rejected(self):
        (self.root/'foods.json').write_text('[{"fdc_id":1,"fdc_id":2}]');rehash(self.root)
        with self.assertRaises(ImportRejected):self.package()
    def test_duplicate_sources_and_orphan_recipe_rejected(self):
        write_json(self.root/'foods.json',[self.food_data,self.food_data]);rehash(self.root)
        with self.assertRaises(ImportRejected):self.package()
        fixture(self.root);self.recipe_data['ingredients'][0]['food_source_key']='usda:fdc:7'
        write_json(self.root/'recipes.json',[self.recipe_data]);rehash(self.root)
        with self.assertRaises(ImportRejected):self.package()
    def test_csv_duplicate_headers_or_positions(self):
        fixture(self.root,fmt='csv')
        p=self.root/'steps.csv';text=p.read_text(encoding='utf-8-sig');p.write_text(text+text.splitlines()[1]+'\n',encoding='utf-8');rehash(self.root)
        with self.assertRaises(ImportRejected):self.package()
        fixture(self.root,fmt='csv');p=self.root/'foods.csv';p.write_text('fdc_id,fdc_id\n1,2\n');rehash(self.root)
        with self.assertRaises(ImportRejected):self.package()
    def test_path_escape_rejected(self):
        m=json.loads((self.root/'manifest.json').read_text(encoding='utf-8'));m['files']['foods']['path']='../other.json'
        write_json(self.root/'manifest.json',m)
        with self.assertRaises(ImportRejected):self.package()
    def test_test_fixture_not_allowed_by_cli(self):
        with self.assertRaises(ImportRejected):load_package(self.root)
        before=self.path.read_bytes()
        with patch('builtins.print'):
            self.assertEqual(main(['--database',str(self.path),'--package',str(self.root)]),2)
        self.assertEqual(self.path.read_bytes(),before)
    def test_source_url_release_and_name_unit_dictionary(self):
        m=json.loads((self.root/'manifest.json').read_text(encoding='utf-8'));m['sources'][0]['url']='https://example.com/source.zip'
        write_json(self.root/'manifest.json',m)
        with self.assertRaises(ImportRejected):self.package()
        raw=copy.deepcopy(self.raw);raw['foodNutrients'][0]['nutrient']['unitName']='kJ'
        with self.assertRaises(ImportRejected):mapped_nutrients(raw)
    def test_foundation_specific_general_and_unknown_energy(self):
        _,_,raw=fixture(self.root,foundation=True)
        self.assertEqual(mapped_nutrients(raw)[0]['calories_per_100g'],120)
        row=raw['foodNutrients'][0];row['nutrient']={'id':2047,'name':'Energy (Atwater General Factors)','unitName':'kcal'}
        self.assertEqual(mapped_nutrients(raw)[1]['energy_nutrient_id'],2047)
        row['nutrient']={'id':1062,'name':'Energy','unitName':'kJ'}
        self.assertIsNone(mapped_nutrients(raw)[0]['calories_per_100g'])
    def test_loq_duplicate_and_nan_source_rejected(self):
        raw=copy.deepcopy(self.raw);raw['foodNutrients'][2]['loq']=.1
        self.assertIsNone(mapped_nutrients(raw)[0]['fat_g_per_100g'])
        raw=copy.deepcopy(self.raw);raw['foodNutrients'].append(raw['foodNutrients'][0])
        with self.assertRaises(ImportRejected):mapped_nutrients(raw)
        raw=copy.deepcopy(self.raw);raw['foodNutrients'][0]['amount']=float('nan')
        with self.assertRaises(ImportRejected):mapped_nutrients(raw)
    def test_failure_rolls_back_categories_foods_recipes_and_audits(self):
        before=self.state()
        with patch('app.modules.diet.recipe_service.save_in_connection',side_effect=RuntimeError('injected failure')):
            with self.assertRaises(RuntimeError):self.apply()
        self.assertEqual(before,self.state())
        failure=json.loads(next(self.audit.glob('*.failed.json')).read_text(encoding='utf-8'))
        self.assertEqual(failure['status'],'rolled_back')
    def test_audit_failure_before_writes(self):
        before=self.state()
        with patch('app.modules.diet.import_service.write_audit',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.apply()
        self.assertEqual(before,self.state())
    def test_postcommit_audit_failure_is_reported_not_restored(self):
        from app.modules.diet.import_service import write_audit
        def fail_final(path,payload):
            if payload['status']=='committed':raise OSError('disk full')
            return write_audit(path,payload)
        with patch('app.modules.diet.import_service.write_audit',side_effect=fail_final):
            with self.assertRaisesRegex(ImportRejected,'已提交'):self.apply()
        self.assertEqual(len(self.client.get('/api/diet/foods').json()['items']),1)
        self.assertEqual(dry_run(self.path,self.package())['counts']['skip'],2)
    def test_modified_user_food_not_overwritten(self):
        self.apply();food=self.client.get('/api/diet/foods').json()['items'][0]
        self.client.put('/api/diet/foods/'+str(food['id']),json={'name':'用户编辑','source_url':food['source_url']})
        before=self.state();self.assertGreater(dry_run(self.path,self.package())['counts']['conflict'],0)
        with self.assertRaises(ImportRejected):self.apply()
        self.assertEqual(before,self.state())
    def test_same_chinese_name_custom_food_not_merged(self):
        old=self.food(self.food_data['name_zh']);self.apply()
        rows=self.client.get('/api/diet/foods').json()['items'];self.assertEqual(len(rows),2)
        self.assertEqual(self.client.get('/api/diet/foods/'+str(old['id'])).json(),old)
    def test_existing_data_and_snapshots_preserved(self):
        old,_=self.recipe();before=self.state();self.apply();after=self.state()
        for table,rows in before.items():
            if table!='sqlite_sequence':self.assertTrue(all(r in after[table] for r in rows),table)
        self.assertEqual(self.client.get('/api/diet/recipes/'+str(old['id'])).json(),old)
    def test_archived_records_are_conflicts(self):
        self.apply();food=self.client.get('/api/diet/foods').json()['items'][0]
        self.client.delete('/api/diet/foods/'+str(food['id']))
        with self.assertRaises(ImportRejected):self.apply()
    def test_stale_plan_refuses_concurrent_changes(self):
        p=self.package();plan=dry_run(self.path,p);self.food('并发用户食物')
        with self.assertRaisesRegex(ImportRejected,'已改变'):
            apply_package(self.path,p,self.audit,expected_plan_sha256=plan['plan_sha256'])
    def test_no_profile_and_missing_database_no_creation(self):
        with database(self.path,write=True) as c:c.execute('DELETE FROM profiles')
        before=self.path.read_bytes()
        with self.assertRaises(Exception) as error:dry_run(self.path,self.package())
        self.assertEqual(getattr(error.exception,'status',None),409)
        self.assertEqual(getattr(error.exception,'code',None),'PROFILE_REQUIRED')
        self.assertEqual(self.path.read_bytes(),before)
        missing=self.path.parent/'absent.db'
        with self.assertRaises(FileNotFoundError):dry_run(missing,self.package())
        self.assertFalse(missing.exists())
    def test_missing_migration_never_migrated_by_import(self):
        with database(self.path,write=True) as c:c.execute("DELETE FROM diet_schema_migrations WHERE version='004_recipes'")
        before=self.state()
        with self.assertRaises(Exception):dry_run(self.path,self.package())
        self.assertEqual(before,self.state())
    def test_official_null_placeholders_are_skipped_not_foods(self):
        with zipfile.ZipFile(self.root/'source.zip','w') as z:
            z.writestr('data.json',json.dumps({'SRLegacyFoods':[None,self.raw,None]}))
        rehash(self.root)
        self.assertEqual(len(self.package()['foods']),1)
    def test_non_object_archive_rows_rejected(self):
        with zipfile.ZipFile(self.root/'source.zip','w') as z:
            z.writestr('data.json',json.dumps({'SRLegacyFoods':[7,self.raw]}))
        rehash(self.root)
        with self.assertRaises(ImportRejected):self.package()
    def test_preview_requires_explicit_nonproduction_loader(self):
        m=json.loads((self.root/'manifest.json').read_text(encoding='utf-8'))
        m['purpose']='temporary_review';write_json(self.root/'manifest.json',m)
        with self.assertRaises(ImportRejected):load_package(self.root)
        p=load_package(self.root,allow_temporary_review=True)
        self.assertEqual(self.apply(p)['status'],'committed')
    def pending_package_files(self):
        m=json.loads((self.root/'manifest.json').read_text(encoding='utf-8'))
        m.update(purpose='temporary_review',review_status='pending_final_confirmation')
        write_json(self.root/'manifest.json',m)
        self.food_data['review_status']='pending_final_confirmation'
        self.recipe_data['review_status']='pending_final_confirmation'
        write_json(self.root/'foods.json',[self.food_data])
        write_json(self.root/'recipes.json',[self.recipe_data]);rehash(self.root)
    def test_pending_candidates_require_explicit_preview_loader(self):
        self.pending_package_files()
        with self.assertRaises(ImportRejected):load_package(self.root)
        p=load_package(self.root,allow_temporary_review=True)
        self.assertEqual(p['foods'][0].review_status,'pending_final_confirmation')
        self.assertEqual(self.apply(p)['status'],'committed')
        self.assertEqual(dry_run(self.path,p)['counts'],{'add':0,'skip':2,'conflict':0})
        self.assertEqual(json.loads((self.root/'manifest.json').read_text(encoding='utf-8'))['review_status'],
                         'pending_final_confirmation')
    def test_pending_manifest_cannot_be_formal(self):
        self.pending_package_files()
        m=json.loads((self.root/'manifest.json').read_text(encoding='utf-8'))
        m['purpose']='reviewed_data';write_json(self.root/'manifest.json',m)
        with self.assertRaisesRegex(ImportRejected,'不能用于正式导入'):
            load_package(self.root)
    def test_approved_manifest_cannot_hide_pending_food_or_recipe(self):
        for kind in ('foods','recipes'):
            with self.subTest(kind=kind):
                fixture(self.root)
                m=json.loads((self.root/'manifest.json').read_text(encoding='utf-8'))
                m['purpose']='reviewed_data';write_json(self.root/'manifest.json',m)
                rows=json.loads((self.root/(kind+'.json')).read_text(encoding='utf-8'))
                rows[0]['review_status']='pending_final_confirmation'
                write_json(self.root/(kind+'.json'),rows);rehash(self.root)
                with self.assertRaisesRegex(ImportRejected,'不能用于正式导入'):load_package(self.root)
    def test_preview_mixed_approval_states_are_rejected(self):
        self.pending_package_files()
        self.food_data['review_status']='approved'
        write_json(self.root/'foods.json',[self.food_data]);rehash(self.root)
        with self.assertRaisesRegex(ImportRejected,'不得混合批准状态'):
            load_package(self.root,allow_temporary_review=True)
    def test_apply_rechecks_pending_status_after_purpose_change(self):
        self.pending_package_files();p=load_package(self.root,allow_temporary_review=True)
        p['manifest']=p['manifest'].model_copy(update={'purpose':'reviewed_data'})
        before=self.state()
        with self.assertRaisesRegex(ImportRejected,'不能用于正式导入'):self.apply(p)
        self.assertEqual(before,self.state())
        self.assertFalse(self.audit.exists())
    def test_pending_candidates_cannot_target_formal_filename(self):
        self.pending_package_files();p=load_package(self.root,allow_temporary_review=True)
        target=self.path.parent/'health.db'
        with self.assertRaisesRegex(ImportRejected,'临时目录'):
            apply_package(target,p,self.audit,expected_plan_sha256='0'*64)
        self.assertFalse(target.exists())
    def test_nonproduction_cannot_target_health_db(self):
        p=self.package();target=self.path.parent/'health.db'
        with self.assertRaisesRegex(ImportRejected,'临时目录'):
            apply_package(target,p,self.audit,expected_plan_sha256='0'*64)
        self.assertFalse(target.exists())
    def test_documentation_hash_checked(self):
        (self.root/'doc.pdf').write_bytes(b'%PDF-test-only')
        m=json.loads((self.root/'manifest.json').read_text(encoding='utf-8'))
        m['documentation']=[{'path':'doc.pdf','sha256':sha((self.root/'doc.pdf').read_bytes())}]
        write_json(self.root/'manifest.json',m);self.package()
        (self.root/'doc.pdf').write_bytes(b'tampered')
        with self.assertRaises(ImportRejected):self.package()
    def test_recipe_time_needs_evidence_and_unknown_fields_rejected(self):
        self.recipe_data['preparation_minutes']=10
        write_json(self.root/'recipes.json',[self.recipe_data]);rehash(self.root)
        with self.assertRaises(ValidationError):self.package()
    def test_audit_detects_deleted_source_marker_and_url(self):
        self.apply();food=self.client.get('/api/diet/foods').json()['items'][0]
        self.client.put('/api/diet/foods/'+str(food['id']),json={'name':'用户新名称'})
        before=self.state()
        with self.assertRaisesRegex(ImportRejected,'身份已删除或被改写'):
            dry_run(self.path,self.package(),self.audit)
        with self.assertRaises(ImportRejected):self.apply()
        self.assertEqual(before,self.state())
    def test_unresolved_pending_audit_stops_retry(self):
        from app.modules.diet.import_service import write_audit
        def fail(path,payload):
            if payload['status']=='committed':raise OSError('test')
            return write_audit(path,payload)
        with patch('app.modules.diet.import_service.write_audit',side_effect=fail):
            with self.assertRaises(ImportRejected):self.apply()
        with self.assertRaisesRegex(ImportRejected,'pending审计'):self.apply()
