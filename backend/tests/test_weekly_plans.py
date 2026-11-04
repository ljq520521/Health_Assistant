"""Weekly-plan acceptance through the real team app and real account APIs.

All profiles, accounts and health records here are synthetic temporary fixtures.
No test bypasses authentication/consent or mutates a released migration.
"""
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.config import Settings
from app.database import connect, init_database
from app.modules.diet import migrations as m1, migration_002 as m2, migration_003 as m3, migration_004 as m4, migration_006 as m6
from app.modules.diet import migration_005 as m5
from app.modules.diet import catalog_repository as catalog
from diet_catalog_app import authenticate

START='2026-11-02'
TODAY=date(2026,11,2)
BASE_PROFILE={'display_name':'合成周计划测试，非真实用户','allergies':'','preferences':''}


def initialize(path,weekly=True):
    init_database(path)
    for migrate in (m1.migrate_diet,m2.migrate_goals,m3.migrate_water,m4.migrate_recipes,m6.migrate_catalog):migrate(path)
    if weekly:m5.migrate_weekly(path)


class WeeklyPlanTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='diet-weekly-tests-')
        self.addCleanup(temporary.cleanup);self.path=Path(temporary.name).resolve()/'private-test.db'
        env=patch.dict(os.environ,{'HEALTH_DB_PATH':str(self.path),'DIET_APPLY_MIGRATIONS':'0'})
        env.start();self.addCleanup(env.stop)
        initialize(self.path)
        clock=patch('app.modules.diet.weekly_service.business_today',return_value=TODAY)
        clock.start();self.addCleanup(clock.stop)
        from app.main import create_app
        self.app=create_app(Settings('Weekly synthetic acceptance',self.path,()))
        self.client=TestClient(self.app);self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None)
        self.admin_token=authenticate(self.client)
        self.profile()

    def checked(self,response,status=200):
        self.assertEqual(response.status_code,status,response.text)
        return response.json() if response.content else None

    def profile(self,**changes):
        return self.checked(self.client.put('/api/profile',json=BASE_PROFILE|changes))

    def context(self,**query):
        return self.checked(self.client.get('/api/diet/weekly-plan-context',params={'start_date':START,**query}))

    def payload(self,**changes):
        selected=changes.get('selected_goal_ids',[])
        context=self.context(selected_goal_ids=','.join(map(str,selected)))
        return {'start_date':START,'portions':1,'meal_ratios':{'breakfast':None,'lunch':None,'dinner':None},'selected_goal_ids':selected,'expected_context_hash':context['context_hash'],**changes}

    def preview(self,**changes):
        return self.checked(self.client.post('/api/diet/weekly-plans/preview',json=self.payload(**changes)))

    def save(self,**changes):
        response=self.client.post('/api/diet/weekly-plans',json=self.payload(**changes))
        return self.checked(response,201)

    def detail(self,id):
        return self.checked(self.client.get(f'/api/diet/weekly-plans/{id}'))

    def feedback(self,item,status,**fields):
        return self.checked(self.client.put(f"/api/diet/weekly-plan-items/{item['id']}/feedback",json={'expected_revision':item['feedback']['revision'],'status':status,'note':'合成测试备注','reason':'合成测试原因',**fields}))

    def rule(self,**fields):
        return self.checked(self.client.post('/api/diet/food-preferences',json=fields),201)

    def forbid_all_public_recipes(self):
        # No-candidate fixtures explicitly ban a real ingredient in each recipe.
        # Missing composition alone no longer excludes candidates.
        keys={r['ingredients'][0]['food_source_key'] for r in catalog.recipes()['items']}
        for key in sorted(keys):
            food=self.checked(self.client.post('/api/diet/catalog/food-references',json={'food_key':key}),200)
            self.rule(food_id=food['id'],rule_type='forbidden')

    def term(self,name='合成测试食材',kind='ingredient'):
        return self.checked(self.client.post('/api/diet/ingredient-terms',json={'name':name,'kind':kind}),201)

    def confirm(self,context=None,allergy=(),preference=()):
        context=context or self.context()
        return self.checked(self.client.post('/api/diet/weekly-plan-context/confirm',json={'profile_fingerprint':context['profile_fingerprint'],'rules_fingerprint':context['rules_fingerprint'],'allergy_rule_ids':list(allergy),'preference_rule_ids':list(preference)}),201)

    def refresh_payload(self,plan):
        context=self.context(selected_goal_ids=','.join(map(str,plan['selected_goal_ids'])))
        return {'expected_context_hash':context['context_hash'],'expected_plan_revision':plan['revision']}

    def snapshot(self):
        with connect(self.path) as c:
            names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {name:[tuple(row) for row in c.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in names}

    def test_preview_readonly_and_persists_21_slots_without_intake_records(self):
        before=self.snapshot();preview=self.preview()
        self.assertTrue(preview['can_save']);self.assertEqual(self.snapshot(),before)
        self.assertEqual(len(preview['items']),21)
        slots={(item['date'],item['meal_type']) for item in preview['items']}
        self.assertEqual(len(slots),21)
        self.assertEqual({meal for _,meal in slots},{'breakfast','lunch','dinner'})
        plan=self.save();again=self.detail(plan['id'])
        self.assertEqual(again['items'],plan['items'])
        self.assertEqual(again['context_hash'],preview['context_hash'])
        listing=self.checked(self.client.get('/api/diet/weekly-plans'))
        self.assertIn(plan['id'],[p['id'] for p in listing['items']])
        with connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM diet_records').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT count(*) FROM food_items').fetchone()[0],0)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_integer_id_and_offset_bounds_reject_overflow_without_database_changes(self):
        before=self.snapshot()
        refresh={'expected_context_hash':self.context()['context_hash'],'expected_plan_revision':1}
        routes=(
            ('GET','/api/diet/weekly-plans/{id}',None),
            ('GET','/api/diet/weekly-plans/{id}/versions',None),
            ('POST','/api/diet/weekly-plans/{id}/refresh-preview',refresh),
            ('POST','/api/diet/weekly-plans/{id}/refresh',refresh),
            ('PUT','/api/diet/weekly-plan-items/{id}/feedback',{'expected_revision':0,'status':'pending'}),
            ('GET','/api/diet/weekly-plan-items/{id}/feedback-history',None),
        )
        for value in (-1,0,9223372036854775808):
            for method,url,payload in routes:
                with self.subTest(id=value,method=method,path=url):
                    response=self.client.request(method,url.format(id=value),json=payload)
                    self.assertEqual(response.status_code,422,response.text)
        for method,url,payload in routes:
            with self.subTest(valid_unknown_id=True,method=method,path=url):
                response=self.client.request(method,url.format(id=9223372036854775807),json=payload)
                self.assertEqual(response.status_code,404,response.text)
        for value in (-1,9223372036854775808):
            response=self.client.get('/api/diet/weekly-plans',params={'offset':value})
            self.assertEqual(response.status_code,422,response.text)
        listing=self.checked(self.client.get('/api/diet/weekly-plans',params={'offset':9223372036854775807}))
        self.assertEqual(listing['items'],[])
        self.assertEqual(self.snapshot(),before)

    def test_five_feedback_states_have_explicit_statistics_and_no_intake_side_effects(self):
        plan=self.save();items=plan['items'];initial=plan['stats']
        self.assertEqual(initial['counts']['pending'],21)
        self.assertIsNone(initial['completion_rate_percent'])
        self.assertEqual(initial['answered_count'],0)
        for item,status in zip(items,('completed','not_completed','partial','not_applicable')):
            response=self.feedback(item,status)
            self.assertEqual(response['stats'],self.detail(plan['id'])['stats'])
        current=self.detail(plan['id']);stats=current['stats']
        self.assertEqual(stats['counts'],{'pending':17,'completed':1,'not_completed':1,'partial':1,'not_applicable':1})
        self.assertEqual(stats['answered_count'],4)
        self.assertEqual(stats['completion_denominator'],3)
        self.assertEqual(stats['completion_rate_percent'],round(100/3,2))
        self.assertEqual(stats['feedback_progress_percent'],round(400/21,2))
        pending_dates={i['date'] for i in current['items'] if i['feedback']['status']=='pending'}
        answered_dates={i['date'] for i in current['items'] if i['feedback']['status']!='pending'}
        self.assertEqual(stats['pending_days'],len(pending_dates))
        self.assertEqual(stats['days_without_any_feedback'],7-len(answered_dates))
        with connect(self.path) as c:self.assertEqual(c.execute('SELECT count(*) FROM diet_records').fetchone()[0],0)

    def test_feedback_corrections_persist_history_and_reject_stale_revision(self):
        plan=self.save();original=plan['items'][0]
        self.feedback(original,'completed')
        stale=self.client.put(f"/api/diet/weekly-plan-items/{original['id']}/feedback",json={'expected_revision':original['feedback']['revision'],'status':'not_completed'})
        self.assertEqual(stale.status_code,409,stale.text)
        updated=self.detail(plan['id'])['items'][0];self.feedback(updated,'partial')
        updated=self.detail(plan['id'])['items'][0];self.feedback(updated,'pending')
        current=self.detail(plan['id'])
        self.assertEqual(current['items'][0]['feedback']['status'],'pending')
        self.assertIsNone(current['stats']['completion_rate_percent'])
        with TestClient(self.app) as reopened:
            reopened.headers['Authorization']=self.admin_token
            persisted=self.checked(reopened.get(f"/api/diet/weekly-plans/{plan['id']}"))
            self.assertEqual(persisted['items'][0]['feedback'],current['items'][0]['feedback'])
        history=self.checked(self.client.get(f"/api/diet/weekly-plan-items/{original['id']}/feedback-history"))['items']
        self.assertGreaterEqual(len(history),3)
        self.assertEqual({row['status'] for row in history},{'completed','partial','pending'})

    def test_missing_goals_never_invents_nutritional_targets(self):
        context=self.context();self.assertTrue(context['warnings'])
        preview=self.preview();self.assertTrue(preview['can_save'])
        for item in preview['items']:
            self.assertIsNotNone(item['recipe'])
            self.assertTrue(item['reasons'])
        with connect(self.path) as c:self.assertEqual(c.execute('SELECT count(*) FROM diet_daily_goals').fetchone()[0],0)

    def test_no_candidates_saved_as_explicit_empty_slots_not_failed_execution(self):
        self.forbid_all_public_recipes()
        plan=self.save();self.assertEqual(len(plan['items']),21)
        self.assertTrue(all(item['recipe'] is None and item['reasons'] for item in plan['items']))
        self.assertEqual(plan['stats']['actionable_slots'],0)
        self.assertEqual(plan['stats']['counts']['not_completed'],0)
        self.assertIsNone(plan['stats']['completion_rate_percent'])
        self.assertEqual(plan['stats']['completion_denominator'],0)
        self.assertTrue(all(not item['usable'] for item in plan['items']))

    def test_repetition_explicit_when_only_one_candidate_is_safe(self):
        food=self.checked(self.client.post('/api/diet/foods',json={'name':'合成安全边界测试食材','calories_per_100g':100}),201)
        ingredient=self.term();avoid=self.term('合成排除术语','allergen')
        composition={'ingredient_status':'declared_complete','allergen_status':'declared_complete','assessed_food_updated_at':food['updated_at'],'source_note':'合成测试声明，不代表真实过敏核验','terms':[{'term_id':ingredient['id'],'relation':'contains'}]}
        self.checked(self.client.put(f"/api/diet/foods/{food['id']}/composition",json=composition))
        self.rule(term_id=avoid['id'],rule_type='forbidden');self.forbid_all_public_recipes()
        recipe=self.checked(self.client.post('/api/diet/recipes',json={'name':'唯一合成候选','servings':1,'ingredients':[{'food_id':food['id'],'amount_g':100}],'steps':['合成测试步骤']}),201)
        plan=self.save();assigned=[item for item in plan['items'] if item['recipe']]
        self.assertEqual(len(assigned),21)
        self.assertTrue(all(item['recipe']['id']==recipe['id'] for item in assigned))
        self.assertTrue(any(item['repeated'] for item in assigned))
        self.assertTrue(any('重复' in ''.join(item['reasons']) for item in assigned))

    def test_display_name_and_height_are_ignored_but_relevant_preferences_invalidate(self):
        before=self.context();plan=self.save()
        self.profile(display_name='仅改名称',height_cm=170,weight_kg=60)
        irrelevant=self.context()
        self.assertEqual(irrelevant['profile_fingerprint'],before['profile_fingerprint'])
        self.assertEqual(irrelevant['context_hash'],before['context_hash'])
        self.assertFalse(self.detail(plan['id'])['context_changed'])
        self.profile(preferences='合成偏好：喜欢低油菜式')
        changed=self.context()
        self.assertNotEqual(changed['profile_fingerprint'],before['profile_fingerprint'])
        self.assertTrue(changed['confirmation_required'])
        self.assertTrue(changed['blockers'])
        self.assertTrue(self.detail(plan['id'])['context_changed'])

    def test_free_text_allergy_requires_manual_mapping_not_empty_confirmation(self):
        self.profile(allergies='合成测试：对鸡蛋过敏')
        context=self.context()
        self.assertTrue(context['confirmation_required']);self.assertFalse(context['confirmation_valid'])
        payload={'profile_fingerprint':context['profile_fingerprint'],'rules_fingerprint':context['rules_fingerprint'],'allergy_rule_ids':[],'preference_rule_ids':[]}
        self.assertEqual(self.client.post('/api/diet/weekly-plan-context/confirm',json=payload).status_code,422)
        term=self.term('合成测试鸡蛋过敏原','allergen');rule=self.rule(term_id=term['id'],rule_type='allergy')
        self.confirm(allergy=[rule['id']])
        context=self.context();self.assertTrue(context['confirmation_valid'])
        self.assertTrue(self.preview()['can_save'])

    def test_confirmation_rejects_wrong_rule_kind_and_stale_rule_fingerprint(self):
        self.profile(allergies='合成过敏描述')
        food=self.checked(self.client.post('/api/diet/foods',json={'name':'合成测试食品'}),201)
        like=self.rule(food_id=food['id'],rule_type='like');old=self.context()
        payload={'profile_fingerprint':old['profile_fingerprint'],'rules_fingerprint':old['rules_fingerprint'],'allergy_rule_ids':[like['id']],'preference_rule_ids':[]}
        self.assertEqual(self.client.post('/api/diet/weekly-plan-context/confirm',json=payload).status_code,422)
        allergy=self.rule(food_id=food['id'],rule_type='allergy')
        payload['allergy_rule_ids']=[allergy['id']]
        self.assertEqual(self.client.post('/api/diet/weekly-plan-context/confirm',json=payload).status_code,409)

    def test_save_and_refresh_require_current_context_and_plan_revision(self):
        payload=self.payload()
        self.checked(self.client.put('/api/diet/goals',json={'effective_from':START,'calories_kcal':2100}))
        self.assertEqual(self.client.post('/api/diet/weekly-plans',json=payload).status_code,409)
        plan=self.save();refresh=self.refresh_payload(plan)
        self.feedback(plan['items'][0],'completed')
        self.assertEqual(self.client.post(f"/api/diet/weekly-plans/{plan['id']}/refresh",json=refresh).status_code,409)

    def test_selected_shared_goal_changes_context_but_unselected_goal_does_not(self):
        a=self.checked(self.client.post('/api/profile/goals',json={'title':'合成目标A','target_value':1,'unit':'test'}),201)
        b=self.checked(self.client.post('/api/profile/goals',json={'title':'合成目标B','target_value':2,'unit':'test'}),201)
        before=self.context(selected_goal_ids=str(a['id']))
        self.checked(self.client.put(f"/api/profile/goals/{b['id']}",json={'title':'仅未选目标改名','target_value':3,'unit':'test'}))
        self.assertEqual(self.context(selected_goal_ids=str(a['id']))['context_hash'],before['context_hash'])
        self.checked(self.client.put(f"/api/profile/goals/{a['id']}",json={'title':'所选目标更新','target_value':4,'unit':'test'}))
        self.assertNotEqual(self.context(selected_goal_ids=str(a['id']))['context_hash'],before['context_hash'])

    def test_explicit_nutritional_goal_changes_ranking_targets_without_inventing_values(self):
        ratios={'breakfast':.3,'lunch':.4,'dinner':.3}
        before=self.preview(meal_ratios=ratios)
        self.assertTrue(all(item['metrics']['calories_kcal']['target'] is None for item in before['items']))
        self.checked(self.client.put('/api/diet/goals',json={'effective_from':START,'calories_kcal':2000,'protein_g':80}))
        after=self.preview(meal_ratios=ratios)
        self.assertNotEqual(before['context_hash'],after['context_hash'])
        for item in after['items']:
            self.assertEqual(item['metrics']['calories_kcal']['target'],2000*ratios[item['meal_type']])
            self.assertEqual(item['metrics']['protein_g']['target'],80*ratios[item['meal_type']])
            self.assertIsNotNone(item['scores']['nutrition'])

    def test_preference_mapping_becomes_invalid_when_the_confirmed_rule_is_deleted(self):
        self.profile(preferences='合成偏好：偏爱测试食材')
        food=self.checked(self.client.post('/api/diet/foods',json={'name':'合成偏好测试食品'}),201)
        like=self.rule(food_id=food['id'],rule_type='like')
        self.confirm(preference=[like['id']])
        self.assertTrue(self.context()['confirmation_valid'])
        self.checked(self.client.delete(f"/api/diet/food-preferences/{like['id']}"),204)
        current=self.context()
        self.assertFalse(current['confirmation_valid']);self.assertTrue(current['blockers'])
        self.assertFalse(self.preview()['can_save'])

    def test_deleted_selected_goal_blocks_refresh_and_preserves_saved_history(self):
        goal=self.checked(self.client.post('/api/profile/goals',json={'title':'合成选定目标','target_value':1,'unit':'test'}),201)
        plan=self.save(selected_goal_ids=[goal['id']]);before=plan['items']
        self.checked(self.client.delete(f"/api/profile/goals/{goal['id']}"),204)
        current=self.detail(plan['id'])
        self.assertTrue(current['context_changed']);self.assertTrue(current['blockers'])
        response=self.client.post(f"/api/diet/weekly-plans/{plan['id']}/refresh",json=self.refresh_payload(current))
        self.assertEqual(response.status_code,409,response.text)
        self.assertEqual([i['recipe'] for i in self.detail(plan['id'])['items']],[i['recipe'] for i in before])

    def test_feedback_for_no_candidate_cannot_mark_failed_or_completed(self):
        self.forbid_all_public_recipes()
        plan=self.save();item=plan['items'][0]
        for status in ('completed','not_completed','partial'):
            response=self.client.put(f"/api/diet/weekly-plan-items/{item['id']}/feedback",json={'expected_revision':item['feedback']['revision'],'status':status})
            self.assertEqual(response.status_code,422,response.text)
        self.feedback(item,'not_applicable')
        current=self.detail(plan['id']);self.assertEqual(current['stats']['actionable_slots'],0)
        self.assertIsNone(current['stats']['feedback_progress_percent'])
        self.assertIsNone(current['stats']['completion_rate_percent'])

    def test_audit_versions_and_feedback_history_are_immutable(self):
        plan=self.save();self.feedback(plan['items'][0],'completed')
        with connect(self.path) as c:
            history_before=[tuple(row) for row in c.execute('SELECT * FROM diet_plan_feedback_history')]
            versions_before=[tuple(row) for row in c.execute('SELECT * FROM diet_plan_versions')]
            for sql in ('DELETE FROM diet_plan_feedback_history',"UPDATE diet_plan_feedback_history SET status='pending'",'DELETE FROM diet_plan_versions',"UPDATE diet_plan_versions SET context_hash='bad'"):
                with self.assertRaises(sqlite3.IntegrityError):c.execute(sql)
            self.assertEqual([tuple(row) for row in c.execute('SELECT * FROM diet_plan_feedback_history')],history_before)
            self.assertEqual([tuple(row) for row in c.execute('SELECT * FROM diet_plan_versions')],versions_before)

    def test_completed_week_has_100_percent_progress_and_cannot_be_regenerated(self):
        plan=self.save()
        for item in plan['items']:self.feedback(item,'completed')
        current=self.detail(plan['id']);stats=current['stats']
        self.assertEqual(stats['counts']['completed'],21)
        self.assertEqual(stats['completion_rate_percent'],100)
        self.assertEqual(stats['feedback_progress_percent'],100)
        self.assertEqual(stats['pending_days'],0)
        self.assertEqual(stats['days_without_any_feedback'],0)
        response=self.client.post(f"/api/diet/weekly-plans/{plan['id']}/refresh",json=self.refresh_payload(current))
        self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(response.json()['code'],'WEEKLY_PLAN_NOT_REFRESHABLE')
        self.assertEqual(self.detail(plan['id'])['items'],current['items'])
        with connect(self.path) as c:self.assertEqual(c.execute('SELECT count(*) FROM diet_records').fetchone()[0],0)

    def test_hard_change_marks_old_candidates_unusable_until_explicit_refresh(self):
        plan=self.save();self.forbid_all_public_recipes()
        changed=self.detail(plan['id'])
        self.assertTrue(changed['hard_changed']);self.assertTrue(changed['context_changed'])
        self.assertTrue(all(not item['usable'] for item in changed['items']))
        payload=self.refresh_payload(changed)
        preview=self.checked(self.client.post(f"/api/diet/weekly-plans/{plan['id']}/refresh-preview",json=payload))
        self.assertTrue(all(item['recipe'] is None for item in preview['items']))
        self.assertTrue(all(item['recipe'] for item in self.detail(plan['id'])['items']))
        self.checked(self.client.post(f"/api/diet/weekly-plans/{plan['id']}/refresh",json=payload))
        refreshed=self.detail(plan['id'])
        self.assertFalse(refreshed['context_changed'])
        self.assertTrue(all(item['recipe'] is None for item in refreshed['items']))

    def test_unfilled_composition_allows_week_but_keeps_explicit_egg_exclusion(self):
        pollen=self.term('花粉','allergen');pollen_rule=self.rule(term_id=pollen['id'],rule_type='allergy')
        egg=self.term('鸡蛋');egg_rule=self.rule(term_id=egg['id'],rule_type='forbidden')
        self.profile(allergies='花粉过敏')
        self.confirm(allergy=[pollen_rule['id'],egg_rule['id']])
        plan=self.save()
        self.assertEqual(len(plan['items']),21)
        breakfast=[item for item in plan['items'] if item['meal_type']=='breakfast']
        self.assertEqual(len(breakfast),7)
        self.assertTrue(all(item['recipe'] is None and '该餐次' in item['reasons'][0] for item in breakfast))
        assigned=[item for item in plan['items'] if item['recipe']]
        self.assertEqual(len(assigned),14)
        self.assertTrue(all('鸡蛋' not in item['recipe']['name'] for item in assigned))
        self.assertTrue(all(item['recipe']['meal_type']==item['meal_type'] for item in assigned))
        self.assertTrue(all(not item['composition_verified'] for item in assigned))
        self.assertTrue(all(any('不单独排除' in reason for reason in item['reasons']) for item in assigned))
        self.assertEqual(plan['stats']['actionable_slots'],14)

    def test_week_and_single_meal_use_public_meal_categories(self):
        for meal,count in [('breakfast',1),('lunch',4),('dinner',3),('snack',4)]:
            result=self.checked(self.client.post('/api/diet/recipe-recommendations/preview',json={'date':START,'meal_type':meal}))
            self.assertEqual(result['eligible_count'],count)
            self.assertTrue(all(item['recipe']['meal_type']==meal for item in result['items']))
        plan=self.preview()
        self.assertEqual(len(plan['items']),21)
        self.assertTrue(all(item['recipe']['meal_type']==item['meal_type'] for item in plan['items']))

    def test_private_category_rename_invalidates_saved_plan(self):
        category=self.checked(self.client.post('/api/diet/recipe-categories',json={'name':'早餐'}),201)
        plan=self.save()
        self.checked(self.client.put(f"/api/diet/recipe-categories/{category['id']}",json={'name':'晚餐'}))
        self.assertTrue(self.detail(plan['id'])['context_changed'])

    def test_refresh_preserves_past_and_ever_answered_items_even_reverted_pending(self):
        plan=self.save();future=next(item for item in plan['items'] if item['date']=='2026-11-06')
        self.feedback(future,'completed')
        current=self.detail(plan['id']);future=next(item for item in current['items'] if item['id']==future['id'])
        self.feedback(future,'pending')
        before=self.detail(plan['id'])
        protected={item['id']:item for item in before['items'] if item['date']<'2026-11-04' or item['id']==future['id']}
        self.checked(self.client.put('/api/diet/goals',json={'effective_from':START,'calories_kcal':2200}))
        with patch('app.modules.diet.weekly_service.business_today',return_value=date(2026,11,4)):
            changed=self.detail(plan['id'])
            self.checked(self.client.post(f"/api/diet/weekly-plans/{plan['id']}/refresh",json=self.refresh_payload(changed)))
            after=self.detail(plan['id'])
        for item in after['items']:
            if item['id'] in protected:
                self.assertEqual(item['recipe'],protected[item['id']]['recipe'])
                self.assertEqual(item['feedback'],protected[item['id']]['feedback'])
        versions=self.checked(self.client.get(f"/api/diet/weekly-plans/{plan['id']}/versions"))['items']
        self.assertGreaterEqual(len(versions),2)
        history=self.checked(self.client.get(f"/api/diet/weekly-plan-items/{future['id']}/feedback-history"))['items']
        self.assertEqual({row['status'] for row in history},{'completed','pending'})

    def test_public_recipe_identity_nutrients_and_catalog_bytes_survive_planning(self):
        before=hashlib.sha256(catalog.DEFAULT_PATH.read_bytes()).hexdigest();plan=self.save()
        self.assertTrue(all(item['recipe']['origin']=='public' for item in plan['items']))
        for item in plan['items']:
            recipe=item['recipe'];original=catalog.recipes(key=recipe['recipe_key'])
            self.assertEqual(recipe['steps'],original['steps'])
            self.assertEqual(recipe['servings'],original['servings'])
            self.assertEqual([i['amount_g'] for i in recipe['ingredients']],[i['amount_g'] for i in original['ingredients']])
            self.assertEqual([i['food_key'] for i in recipe['ingredients']],[i['food_source_key'] for i in original['ingredients']])
        self.assertEqual(hashlib.sha256(catalog.DEFAULT_PATH.read_bytes()).hexdigest(),before)

    def test_anonymous_viewer_consent_and_masked_privacy(self):
        plan=self.save()
        for result in (self.context(),plan):
            self.assertEqual(result['profile_scope'],'shared_local_profile')
            self.assertEqual(result['profile_id'],1)
            self.assertIn('不代表多用户档案隔离',result['scope_notice'])
            self.assertTrue(result['can_write'])
        self.client.headers.pop('Authorization')
        self.assertEqual(self.client.get('/api/diet/weekly-plans').status_code,401)
        self.client.headers['Authorization']=self.admin_token
        credentials={'username':'weekly_viewer','password':'WeeklyViewer2026!'}
        self.checked(self.client.post('/api/auth/register',json=credentials),201)
        token=self.checked(self.client.post('/api/auth/login',json=credentials))['access_token']
        self.client.headers['Authorization']='Bearer '+token
        self.checked(self.client.put('/api/auth/privacy',json={'consent_health_data':True,'mask_sensitive':False,'analytics_consent':False}))
        self.assertEqual(self.client.get(f"/api/diet/weekly-plans/{plan['id']}").status_code,200)
        preview=self.checked(self.client.post('/api/diet/weekly-plans/preview',json=self.payload()))
        self.assertFalse(preview['can_write'])
        self.assertEqual(preview['profile_scope'],'shared_local_profile')
        self.assertEqual(preview['profile_id'],1)
        self.assertIn('不代表多用户档案隔离',preview['scope_notice'])
        self.assertEqual(self.client.post('/api/diet/weekly-plans',json=self.payload()).status_code,403)
        item=plan['items'][0]
        self.assertEqual(self.client.put(f"/api/diet/weekly-plan-items/{item['id']}/feedback",json={'expected_revision':item['feedback']['revision'],'status':'completed'}).status_code,403)
        self.checked(self.client.put('/api/auth/privacy',json={'consent_health_data':True,'mask_sensitive':True,'analytics_consent':False}))
        self.assertEqual(self.client.get('/api/diet/weekly-plans').status_code,403)
        self.checked(self.client.put('/api/auth/privacy',json={'consent_health_data':False,'mask_sensitive':False,'analytics_consent':False}))
        self.assertEqual(self.client.get('/api/diet/weekly-plan-context',params={'start_date':START}).status_code,403)

    def test_invalid_dates_unknown_status_and_forged_profile_rejected(self):
        for change in ({'start_date':'2026-02-30'},{'portions':0},{'profile_id':2},{'meal_ratios':{'breakfast':-.1,'lunch':None,'dinner':None}},{'meal_ratios':{'breakfast':.5,'lunch':.5,'dinner':.5}}):
            with self.subTest(change=change):
                self.assertEqual(self.client.post('/api/diet/weekly-plans',json=self.payload()|change).status_code,422)
        plan=self.save();item=plan['items'][0]
        self.assertEqual(self.client.put(f"/api/diet/weekly-plan-items/{item['id']}/feedback",json={'expected_revision':item['feedback']['revision'],'status':'success'}).status_code,422)


class WeeklyMigrationTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='diet-weekly-migration-');self.addCleanup(temporary.cleanup)
        self.path=Path(temporary.name).resolve()/'private-test.db';initialize(self.path,False)

    def snapshot(self):
        with connect(self.path) as c:
            names=[row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            return {name:[tuple(row) for row in c.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in names}

    def test_005_concurrent_idempotence_preserves_other_module_rows_and_old_registry(self):
        with connect(self.path) as c:
            c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'合成测试档案')")
            c.execute("INSERT INTO cycle_records(start_date,notes) VALUES('2026-09-01','synthetic')")
            c.execute("INSERT INTO exercise_records(record_date,exercise_type,duration_minutes,intensity) VALUES('2026-09-01','synthetic',10,'low')")
            c.execute("INSERT INTO sleep_records(sleep_at,wake_at,quality) VALUES('2026-09-01T20:00:00Z','2026-09-02T04:00:00Z',3)")
            c.execute("INSERT INTO diet_records(record_date,meal_type,food_name,amount_g,calories_kcal) VALUES('2026-09-01','lunch','synthetic',100,120)")
        from app.modules.diet.catalog_links import reference
        from app.modules.diet.recipe_preference_service import save_inventory
        from app.modules.diet.recipe_preference_schemas import InventoryInput
        food=reference(self.path,catalog.foods()['items'][0]['food_key'])
        save_inventory(self.path,InventoryInput(food_id=food['id'],quantity_g=300,notes='synthetic'))
        before=self.snapshot()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:m5.migrate_weekly(self.path),range(2)))
        self.assertEqual(sorted(results),[False,True]);after=self.snapshot()
        for name,rows in before.items():
            if name!='diet_extension_schema_migrations':self.assertEqual(after[name],rows,name)
        with connect(self.path) as c:
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_005_failure_rolls_back_and_can_retry(self):
        before=self.snapshot()
        with patch.object(m5,'STATEMENTS',m5.STATEMENTS+('INVALID SQL FOR ROLLBACK',)):
            with self.assertRaises(sqlite3.Error):m5.migrate_weekly(self.path)
        self.assertEqual(self.snapshot(),before)
        self.assertTrue(m5.migrate_weekly(self.path));self.assertFalse(m5.migrate_weekly(self.path))

    def test_missing_005_requires_explicit_migration_and_no_profile_is_not_misclassified(self):
        from app.main import create_app
        with patch.dict(os.environ,{'HEALTH_DB_PATH':str(self.path),'DIET_APPLY_MIGRATIONS':'1'}):
            app=create_app(Settings('Synthetic migration boundary',self.path,()))
            with TestClient(app) as client:
                authenticate(client)
                response=client.put('/api/profile',json=BASE_PROFILE)
                self.assertEqual(response.status_code,200,response.text)
                response=client.get('/api/diet/weekly-plan-context',params={'start_date':START})
                self.assertEqual(response.status_code,503,response.text)
                self.assertEqual(response.json()['code'],'WEEKLY_PLAN_MIGRATION_REQUIRED')
                self.assertNotIn('diet_weekly_plans',self.snapshot())
                self.assertTrue(m5.migrate_weekly(self.path))
                response=client.get('/api/diet/weekly-plan-context',params={'start_date':START})
                self.assertEqual(response.status_code,200,response.text)
                with connect(self.path) as c:c.execute('DELETE FROM profiles')
                response=client.get('/api/diet/weekly-plan-context',params={'start_date':START})
                self.assertEqual(response.status_code,409,response.text)
                self.assertEqual(response.json()['code'],'PROFILE_REQUIRED')


if __name__=='__main__':unittest.main()
