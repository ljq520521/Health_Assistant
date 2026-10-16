from test_recipes import RecipeFixture

class RecipePreferencesTests(RecipeFixture):
    def term(self,name='测试食材术语',**kw):
        r=self.client.post('/api/diet/ingredient-terms',json={'name':name,**kw});self.assertEqual(r.status_code,201,r.text);return r.json()
    def test_inventory_crud_zero_revision(self):
        f=self.food();p={'food_id':f['id'],'quantity_g':100}
        r=self.client.post('/api/diet/inventory-items',json=p);self.assertEqual(r.status_code,201,r.text);id=r.json()['id']
        self.assertEqual(self.client.post('/api/diet/inventory-items',json=p).status_code,409)
        self.assertEqual(self.client.put(f'/api/diet/inventory-items/{id}',json=p|{'quantity_g':0,'revision':1}).status_code,200)
        self.assertEqual(self.client.put(f'/api/diet/inventory-items/{id}',json=p|{'revision':1}).status_code,409)
        self.assertEqual(self.client.get('/api/diet/inventory-items').json()['items'][0]['quantity_g'],0)
        for amount in (-1,True,'10'):
            self.assertEqual(self.client.put(f'/api/diet/inventory-items/{id}',json=p|{'quantity_g':amount,'revision':2}).status_code,422)
        self.assertEqual(self.client.delete(f'/api/diet/inventory-items/{id}').status_code,204)
        self.assertEqual(self.client.get(f'/api/diet/inventory-items/{id}').status_code,404)
    def test_alias_normalization_and_atomic_collision(self):
        t=self.term('测试豆',aliases=['测试豆别名','ＳＯＹ'])
        self.assertEqual(self.client.get('/api/diet/ingredient-terms/resolve',params={'name':' soy '}).json()['id'],t['id'])
        self.assertEqual(self.client.get('/api/diet/ingredient-terms',params={'q':'别名'}).json()['items'][0]['id'],t['id'])
        self.assertEqual(self.client.post('/api/diet/ingredient-terms',json={'name':'另一个','aliases':['soy']}).status_code,409)
        self.assertEqual(len(self.client.get('/api/diet/ingredient-terms').json()['items']),1)
        self.assertEqual(self.client.put('/api/diet/ingredient-terms/'+str(t['id']),json={'name':'测试豆','aliases':['新别名']}).status_code,200)
        self.assertEqual(self.client.delete('/api/diet/ingredient-terms/'+str(t['id'])).status_code,204)
    def test_composition_missing_complete_and_stale(self):
        f=self.food();t=self.term();url=f"/api/diet/foods/{f['id']}/composition"
        self.assertTrue(self.client.get(url).json()['outdated'])
        p={'assessed_food_updated_at':f['updated_at'],'ingredient_status':'declared_complete','allergen_status':'declared_complete','source_note':'独立测试资料，非权威','terms':[{'term_id':t['id'],'relation':'contains'}]}
        r=self.client.put(url,json=p);self.assertEqual(r.status_code,200,r.text);self.assertFalse(r.json()['outdated'])
        self.assertEqual(self.client.put(url,json=p|{'terms':[]}).status_code,422)
        self.assertEqual(self.client.delete('/api/diet/ingredient-terms/'+str(t['id'])).status_code,409)
        self.assertEqual(self.client.put('/api/diet/ingredient-terms/'+str(t['id']),json={'name':'误改身份'}).status_code,409)
        self.client.put('/api/diet/foods/'+str(f['id']),json={'name':'更新食物'})
        self.assertTrue(self.client.get(url).json()['outdated'])
        self.assertEqual(self.client.put(url,json=p).status_code,409)
    def test_preferences_crud_and_target_validation(self):
        f=self.food();t=self.term();p={'food_id':f['id'],'rule_type':'like'}
        r=self.client.post('/api/diet/food-preferences',json=p);self.assertEqual(r.status_code,201,r.text);url='/api/diet/food-preferences/'+str(r.json()['id'])
        self.assertEqual(self.client.put(url,json={'term_id':t['id'],'rule_type':'allergy'}).status_code,200)
        self.assertEqual(self.client.get(url).json()['term_id'],t['id'])
        self.assertEqual(self.client.get('/api/diet/food-preferences').json()['items'][0]['target_name'],t['name'])
        self.assertEqual(self.client.post('/api/diet/food-preferences',json=p|{'term_id':t['id']}).status_code,422)
        self.assertEqual(self.client.delete(url).status_code,204)
    def test_missing_resources(self):
        for url in ('inventory-items','ingredient-terms','food-preferences'):
            self.assertEqual(self.client.get('/api/diet/'+url+'/999').status_code,404)
