"""Importer -> real API integration using explicitly SYNTHETIC temporary data."""
from unittest.mock import patch
from test_recipes import RecipeFixture
from diet_import_fixtures import fixture
from app.modules.diet.import_service import load_package,dry_run,apply_package,database,snapshot

class ImportedRecommendationTests(RecipeFixture):
    def setUp(self):
        super().setUp();root=self.path.parent/'package';fixture(root)
        p=load_package(root,allow_test_fixtures=True);preview=dry_run(self.path,p)
        self.result=apply_package(self.path,p,self.path.parent/'audit',expected_plan_sha256=preview['plan_sha256'])
        self.fid=self.result['food_ids']['usda:fdc:900000001']
    def recommend(self,**changes):
        r=self.client.post('/api/diet/recipe-recommendations/preview',json={'date':'2026-10-14',**changes})
        self.assertEqual(r.status_code,200,r.text);return r.json()
    def post(self,url,payload):
        r=self.client.post(url,json=payload);self.assertEqual(r.status_code,201,r.text);return r.json()
    def test_no_goals_or_inventory_reasons_missing_and_readonly(self):
        with database(self.path) as c:before=snapshot(c)
        r=self.recommend();item=r['items'][0]
        self.assertIsNone(item['score']);self.assertEqual(item['scores'],{'nutrition':None,'inventory':None,'preference':None})
        self.assertEqual(item['missing_ingredients'][0]['shortage_g'],100)
        self.assertEqual(item['nutrition']['calories_kcal']['total'],120)
        self.assertIsNone(item['nutrition']['carbohydrate_g']['total'])
        self.assertFalse(item['composition_verified']);self.assertTrue(item['reasons']);self.assertTrue(r['warnings'])
        with database(self.path) as c:self.assertEqual(before,snapshot(c))
    def test_effective_targets_inventory_weights_and_unknown(self):
        for date,energy in [('2026-10-01',240),('2026-11-01',480)]:
            r=self.client.put('/api/diet/goals',json={'effective_from':date,'calories_kcal':energy,'carbohydrate_g':50})
            self.assertEqual(r.status_code,200,r.text)
        self.post('/api/diet/inventory-items',{'food_id':self.fid,'quantity_g':25})
        item=self.recommend(target_ratio=.5)['items'][0]
        self.assertEqual(item['scores']['nutrition'],100);self.assertEqual(item['scores']['inventory'],25)
        self.assertAlmostEqual(sum(item['weights'].values()),1);self.assertEqual(item['weights']['preference'],0)
        self.assertEqual(item['missing_ingredients'][0]['shortage_g'],75)
        self.assertEqual(item['metrics']['carbohydrate_g']['status'],'nutrition_unknown')
        self.assertEqual(item['data_penalty'],10);self.assertAlmostEqual(item['score'],61.875)
        self.assertEqual(self.recommend(date='2026-11-01',target_ratio=.5)['items'][0]['metrics']['calories_kcal']['target'],240)
    def test_hard_food_rules_before_scoring(self):
        for kind in ('allergy','forbidden'):
            rule=self.post('/api/diet/food-preferences',{'food_id':self.fid,'rule_type':kind})
            with patch('app.modules.diet.recipe_recommendation.nutrition',side_effect=AssertionError('must filter first')):
                result=self.recommend()
            self.assertEqual(result['items'],[]);self.assertIn('命中',result['excluded'][0]['reason'])
            self.assertEqual(self.client.delete('/api/diet/food-preferences/'+str(rule['id'])).status_code,204)
    def test_unknown_composition_allowed_but_recorded_possible_allergen_excluded(self):
        term=self.post('/api/diet/ingredient-terms',{'name':'纯测试过敏原'})
        self.post('/api/diet/food-preferences',{'term_id':term['id'],'rule_type':'allergy'})
        result=self.recommend()
        self.assertEqual(len(result['items']),1)
        self.assertEqual(result['excluded'],[])
        self.assertFalse(result['items'][0]['composition_verified'])
        self.assertTrue(any('不单独排除' in warning for warning in result['warnings']))
        ingredient=self.post('/api/diet/ingredient-terms',{'name':'纯测试实际成分'})
        food=self.client.get('/api/diet/foods/'+str(self.fid)).json()
        r=self.client.put('/api/diet/foods/'+str(self.fid)+'/composition',json={
            'ingredient_status':'declared_complete','allergen_status':'declared_complete',
            'assessed_food_updated_at':food['updated_at'],'source_note':'仅临时测试的虚构成分，非真实过敏信息',
            'terms':[{'term_id':ingredient['id'],'relation':'contains'}, {'term_id':term['id'],'relation':'may_contain'}]})
        self.assertEqual(r.status_code,200,r.text)
        result=self.recommend();self.assertEqual(result['items'],[]);self.assertIn('命中',result['excluded'][0]['reason'])
    def test_import_does_not_change_goals_inventory_or_rules(self):
        self.post('/api/diet/inventory-items',{'food_id':self.fid,'quantity_g':20})
        self.post('/api/diet/food-preferences',{'food_id':self.fid,'rule_type':'dislike'})
        self.client.put('/api/diet/goals',json={'effective_from':'2026-10-01','protein_g':40})
        root=self.path.parent/'package';p=load_package(root,allow_test_fixtures=True)
        with database(self.path) as c:before=snapshot(c)
        plan=dry_run(self.path,p)
        apply_package(self.path,p,self.path.parent/'audit',expected_plan_sha256=plan['plan_sha256'])
        with database(self.path) as c:self.assertEqual(before,snapshot(c))
