from unittest.mock import patch
from test_recipes import RecipeFixture
from app.database import connect

class RecommendationTests(RecipeFixture):
    def test_meal_filter_respects_categories_keeps_unclassified_and_hard_rules(self):
        food=self.food()
        breakfast=self.client.post('/api/diet/recipe-categories',json={'name':'早餐'}).json()
        lunch=self.client.post('/api/diet/recipe-categories',json={'name':'午餐'}).json()
        morning,_=self.recipe(food,name='早餐配方',category_id=breakfast['id'])
        midday,_=self.recipe(food,name='午餐配方',category_id=lunch['id'])
        unspecified,_=self.recipe(food,name='尚未分类配方')
        result=self.recommend(meal_type='breakfast')
        self.assertEqual({item['recipe']['id'] for item in result['items']},{morning['id'],unspecified['id']})
        self.assertEqual([item['recipe_id'] for item in result['excluded']],[midday['id']])
        self.assertEqual(len(self.recommend()['items']),3)
        self.assertEqual(self.client.post('/api/diet/recipe-recommendations/preview',json={'date':'2026-10-14','meal_type':'invalid'}).status_code,422)
        self.rule(food_id=food['id'],rule_type='forbidden')
        self.assertEqual(self.recommend(meal_type='breakfast')['items'],[])

    def recommend(self,**kw):
        r=self.client.post('/api/diet/recipe-recommendations/preview',json={'date':'2026-10-14',**kw})
        self.assertEqual(r.status_code,200,r.text);return r.json()
    def rule(self,**kw):
        r=self.client.post('/api/diet/food-preferences',json=kw);self.assertEqual(r.status_code,201,r.text);return r.json()
    def term(self,name='测试规范食材'):
        r=self.client.post('/api/diet/ingredient-terms',json={'name':name});self.assertEqual(r.status_code,201,r.text);return r.json()
    def composition(self,food,term,**kw):
        p={'ingredient_status':'declared_complete','allergen_status':'declared_complete','assessed_food_updated_at':food['updated_at'],'source_note':'临时测试声明，非真实过敏信息','terms':[{'term_id':term['id'],'relation':'contains'}],**kw}
        r=self.client.put(f"/api/diet/foods/{food['id']}/composition",json=p);self.assertEqual(r.status_code,200,r.text)
    def goal(self,**kw):
        r=self.client.put('/api/diet/goals',json={'effective_from':'2026-10-01',**kw});self.assertEqual(r.status_code,200,r.text)
    def test_food_hard_filters_before_scoring(self):
        f=self.food();self.recipe(f)
        for kind in ('allergy','forbidden'):
            rule=self.rule(food_id=f['id'],rule_type=kind)
            with patch('app.modules.diet.recipe_recommendation.nutrition',side_effect=AssertionError('filtered recipe must not be scored')):
                r=self.recommend()
            self.assertEqual(r['items'],[]);self.assertIn('命中',r['excluded'][0]['reason'])
            self.client.delete('/api/diet/food-preferences/'+str(rule['id']))
    def test_term_contains_and_may_contain(self):
        f=self.food();self.recipe(f);t=self.term();allergen=self.term('测试过敏原')
        self.rule(term_id=allergen['id'],rule_type='allergy')
        for relation in ('contains','may_contain'):
            self.composition(f,t,terms=[{'term_id':t['id'],'relation':'contains'},{'term_id':allergen['id'],'relation':relation}])
            r=self.recommend();self.assertEqual(r['items'],[]);self.assertIn('命中',r['excluded'][0]['reason'])
    def test_unknown_partial_and_stale_remain_candidates_without_safety_approval(self):
        f=self.food();self.recipe(f);t=self.term();avoid=self.term('另一个禁忌');self.rule(term_id=avoid['id'],rule_type='forbidden')
        result=self.recommend();self.assertEqual(len(result['items']),1)
        self.assertFalse(result['items'][0]['composition_verified'])
        self.assertTrue(any('不单独排除' in w for w in result['warnings']))
        self.composition(f,t,allergen_status='partial')
        self.assertFalse(self.recommend()['items'][0]['composition_verified'])
        self.composition(f,t);self.assertTrue(self.recommend()['items'][0]['composition_verified'])
        self.client.put('/api/diet/foods/'+str(f['id']),json={'name':f['name'],'calories_per_100g':99})
        self.assertFalse(self.recommend()['items'][0]['composition_verified'])
        self.rule(term_id=t['id'],rule_type='forbidden')
        self.assertEqual(self.recommend()['items'],[])  # Known matches survive stale metadata.

    def test_declared_ingredient_name_matches_without_guessing_substrings(self):
        egg=self.food('鸡蛋（全蛋，去壳，生）');egg_recipe,_=self.recipe(egg)
        other=self.food('无鸡蛋测试食品');other_recipe,_=self.recipe(other,name='非名称相等的配方')
        rule=self.term('鸡蛋');self.rule(term_id=rule['id'],rule_type='forbidden')
        result=self.recommend()
        self.assertEqual([r['recipe_id'] for r in result['excluded']],[egg_recipe['id']])
        self.assertEqual([r['recipe']['id'] for r in result['items']],[other_recipe['id']])
        self.assertFalse(result['items'][0]['composition_verified'])
        alias=self.client.post('/api/diet/ingredient-terms',json={'name':'明确另一个名称','aliases':['无鸡蛋测试食品']}).json()
        self.rule(term_id=alias['id'],rule_type='forbidden')
        self.assertEqual(self.recommend()['items'],[])
    def test_no_rules_inventory_or_targets_all_dimensions_null(self):
        self.recipe();r=self.recommend();item=r['items'][0]
        self.assertEqual(item['scores'],{'nutrition':None,'inventory':None,'preference':None})
        self.assertEqual(item['weights'],{'nutrition':0,'inventory':0,'preference':0});self.assertIsNone(item['score'])
        self.assertFalse(r['inventory_registered']);self.assertTrue(any('尚未设置饮食禁忌' in w for w in r['warnings']))
        self.assertFalse(item['composition_verified']);self.assertEqual(item['missing_ingredients'][0]['shortage_g'],100)
    def test_partial_inventory_and_portion_conversion(self):
        a=self.food();b=self.food('第二种食材');self.recipe(a,ingredients=[{'food_id':a['id'],'amount_g':200},{'food_id':b['id'],'amount_g':100}])
        self.client.post('/api/diet/inventory-items',json={'food_id':a['id'],'quantity_g':100})
        item=self.recommend(portions=2)['items'][0]
        self.assertEqual(item['scores']['inventory'],25);self.assertEqual(item['weights']['inventory'],1)
        self.assertEqual([i['required_g'] for i in item['ingredients']],[200,100]);self.assertEqual([i['shortage_g'] for i in item['missing_ingredients']],[100,100])
        self.assertFalse(item['ingredients'][1]['registered']);self.assertEqual(item['nutrition']['calories_kcal']['total'],300)
    def test_complete_nutrition_and_effective_weights(self):
        f=self.food(carbohydrate_g_per_100g=20);self.recipe(f);self.goal(calories_kcal=200,protein_g=20,carbohydrate_g=40)
        self.client.post('/api/diet/inventory-items',json={'food_id':f['id'],'quantity_g':100})
        i=self.recommend(target_ratio=.5)['items'][0]
        self.assertEqual(i['nutrition_completeness'],1);self.assertEqual(i['scores']['nutrition'],100)
        self.assertAlmostEqual(i['weights']['nutrition'],.625);self.assertAlmostEqual(i['weights']['inventory'],.375);self.assertIsNone(i['scores']['preference'])
        self.assertAlmostEqual(sum(i['weights'].values()),1);self.assertEqual(i['score'],100)
    def test_unknown_nutrient_not_zero_and_penalty_separate(self):
        self.recipe();self.goal(calories_kcal=200,carbohydrate_g=40)
        i=self.recommend(target_ratio=.5)['items'][0]
        self.assertIsNone(i['metrics']['carbohydrate_g']['actual']);self.assertIsNone(i['metrics']['carbohydrate_g']['score']);self.assertEqual(i['metrics']['carbohydrate_g']['status'],'nutrition_unknown')
        self.assertEqual(i['scores']['nutrition'],100);self.assertEqual(i['nutrition_completeness'],.75);self.assertEqual(i['target_nutrition_completeness'],.5)
        self.assertEqual(i['base_score'],100);self.assertEqual(i['data_penalty'],10);self.assertEqual(i['score'],90)
        self.assertEqual(i['nutrition']['fat_g']['total'],0)
    def test_entirely_unknown_nutrition_removes_dimension(self):
        self.recipe(self.food(calories_per_100g=None,protein_g_per_100g=None,fat_g_per_100g=None));self.goal(calories_kcal=200)
        i=self.recommend(target_ratio=.5)['items'][0];self.assertIsNone(i['scores']['nutrition']);self.assertEqual(i['weights']['nutrition'],0);self.assertIsNone(i['score'])
    def test_target_effective_date_and_ratio_required(self):
        self.recipe();self.goal(calories_kcal=200);self.goal(effective_from='2026-11-01',calories_kcal=400)
        self.assertIsNone(self.recommend(date='2026-09-01',target_ratio=.5)['goal'])
        self.assertEqual(self.recommend(target_ratio=.5)['items'][0]['metrics']['calories_kcal']['target'],100)
        self.assertEqual(self.recommend(date='2026-11-01',target_ratio=.5)['items'][0]['metrics']['calories_kcal']['target'],200)
        self.assertIsNone(self.recommend()['items'][0]['scores']['nutrition'])
    def test_preferences_and_stable_tie(self):
        f=self.food();a,_=self.recipe(f);b,_=self.recipe(f,name='另一个食谱');self.rule(food_id=f['id'],rule_type='like')
        r=self.recommend();self.assertEqual([i['recipe']['id'] for i in r['items']],[a['id'],b['id']]);self.assertEqual(r['items'][0]['score'],100)
        self.rule(food_id=f['id'],rule_type='dislike');self.assertEqual(self.recommend()['items'][0]['scores']['preference'],0)
    def test_term_preference_and_possible_does_not_earn_like(self):
        f=self.food();self.recipe(f);t=self.term();other=self.term('偏好术语');self.rule(term_id=other['id'],rule_type='like')
        self.composition(f,t,terms=[{'term_id':t['id'],'relation':'contains'},{'term_id':other['id'],'relation':'may_contain'}])
        self.assertEqual(self.recommend()['items'][0]['scores']['preference'],50)
        self.composition(f,other);self.assertEqual(self.recommend()['items'][0]['scores']['preference'],100)
    def test_empty_filters_explain_why(self):
        self.recipe(preparation_minutes=20)
        r=self.recommend(max_preparation_minutes=10);self.assertEqual(r['items'],[]);self.assertIn('制作时间',r['excluded'][0]['reason'])
        r=self.recommend(category_id=999);self.assertEqual(r['items'],[]);self.assertIn('分类',r['excluded'][0]['reason'])
    def test_examples_archived_and_read_only(self):
        f=self.food(source_type='example',source_note='虚构测试');self.recipe(f)
        with connect(self.path) as c:before=list(c.iterdump())
        self.assertEqual(self.recommend()['items'],[]);self.assertEqual(len(self.recommend(include_examples=True)['items']),1)
        with connect(self.path) as c:self.assertEqual(list(c.iterdump()),before)
        self.client.delete('/api/diet/foods/'+str(f['id']));self.assertEqual(self.recommend(include_examples=True)['items'],[])
    def test_invalid_input_and_no_profile(self):
        for change in ({'portions':0},{'portions':True},{'target_ratio':0},{'target_ratio':1.1},{'date':'2026-02-30'},{'limit':51}):
            self.assertEqual(self.client.post('/api/diet/recipe-recommendations/preview',json={'date':'2026-10-14',**change}).status_code,422)
        with connect(self.path) as c:c.execute('DELETE FROM profiles')
        self.assertEqual(self.client.post('/api/diet/recipe-recommendations/preview',json={'date':'2026-10-14'}).status_code,409)
