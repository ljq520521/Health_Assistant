from datetime import date
import sqlite3
from unittest.mock import patch
from test_recipes import RecipeFixture
from app.database import connect

class ReportTests(RecipeFixture):
    def setUp(self):
        super().setUp()
        clock=patch('app.modules.diet.report_service.today',return_value=date(2026,10,14))
        clock.start();self.addCleanup(clock.stop)
    def report(self,day='2026-10-13',period='day'):
        r=self.client.get('/api/diet/reports',params={'date':day,'period':period})
        self.assertEqual(r.status_code,200,r.text);return r.json()
    def meal(self,day='2026-10-13',**kw):
        r=self.client.post('/api/diet-records',json={'record_date':day,'meal_type':'breakfast','food_name':'临时测试食物','amount_g':100,**kw})
        self.assertEqual(r.status_code,201,r.text);return r.json()
    def water(self,day='2026-10-13',amount=250,**kw):
        r=self.client.post('/api/diet/water-records',json={'drank_at':day+'T09:00:00+08:00','amount_ml':amount,**kw})
        self.assertEqual(r.status_code,201,r.text)
    def goal(self,day,**kw):
        r=self.client.put('/api/diet/goals',json={'effective_from':day,**kw});self.assertEqual(r.status_code,200,r.text)
    def test_daily_meals_and_nutrients(self):
        for i,meal in enumerate(('breakfast','lunch','dinner','snack')):self.meal(meal_type=meal,calories_kcal=i*100,protein_g=10,fat_g=0,carbohydrate_g=20)
        r=self.report();self.assertEqual(r['overview']['record_count'],4)
        self.assertEqual([v['record_count'] for v in r['meal_distribution']],[1,1,1,1]);self.assertEqual(r['overview']['recorded_meal_slots'],4)
        self.assertEqual(r['nutrition']['total']['nutrients']['calories_kcal']['known_sum'],600)
        self.assertEqual(r['averages']['known_calories_per_recorded_day'],600)
    def test_week_cross_month_and_year(self):
        r=self.report('2025-01-01','week');self.assertEqual((r['date_from'],r['date_to']),('2024-12-30','2025-01-05'));self.assertEqual(r['period_days'],7)
        r=self.report('2026-04-01','week');self.assertEqual((r['date_from'],r['date_to']),('2026-03-30','2026-04-05'))
    def test_month_leap_year(self):
        self.assertEqual(self.report('2024-02-29','month')['period_days'],29)
        self.assertEqual(self.report('2025-02-01','month')['period_days'],28)
        self.assertEqual(self.report('2025-12-31','month')['date_to'],'2025-12-31')
    def test_partial_current_period_and_future_rejection(self):
        self.meal('2026-10-15',calories_kcal=999)
        r=self.report('2026-10-14','month');self.assertEqual(r['date_to'],'2026-10-14');self.assertEqual(r['period_to'],'2026-10-31');self.assertTrue(r['is_partial_period']);self.assertEqual(r['overview']['record_count'],0)
        self.assertTrue(self.report('2026-10-14')['is_partial_period'])
        self.assertFalse(self.report('2026-10-13')['is_partial_period'])
        self.assertEqual(self.client.get('/api/diet/reports?date=2026-10-15').status_code,422)
    def test_null_zero_and_partial(self):
        self.meal(calories_kcal=0,fat_g=0);self.meal(calories_kcal=None,meal_type='lunch')
        r=self.report();m=r['nutrition']['total']['nutrients']['calories_kcal']
        self.assertEqual(m['known_sum'],0);self.assertEqual(m['unknown_count'],1);self.assertEqual(m['data_status'],'partial')
        self.assertIsNone(r['nutrition']['total']['nutrients']['protein_g']['known_sum'])
        self.assertEqual(r['averages']['known_calories_per_period_day'],0)
    def test_empty_not_actual_zero_and_no_gap_advice(self):
        self.goal('2026-10-01',calories_kcal=1000,water_ml=2000)
        r=self.report();self.assertEqual(r['nutrition']['total']['nutrients']['calories_kcal']['data_status'],'no_records')
        self.assertIsNone(r['averages']['known_calories_per_period_day']);self.assertIsNone(r['water']['known_sum_ml']);self.assertIsNone(r['water']['achievement_percent'])
        self.assertIsNone(r['water']['daily'][0]['known_sum_ml']);self.assertIsNone(r['water']['daily'][0]['goal_met'])
        self.assertNotIn('recorded_water_below_target',[s['rule_id'] for s in r['suggestions']])
    def test_known_average_denominators(self):
        self.meal('2026-10-05',calories_kcal=100);self.meal('2026-10-06',calories_kcal=200);self.meal('2026-10-07')
        r=self.report('2026-10-05','week');a=r['averages']
        self.assertEqual(a['recorded_day_denominator'],3);self.assertEqual(a['period_day_denominator'],7)
        self.assertEqual(a['known_calories_per_recorded_day'],100);self.assertEqual(a['known_calories_per_period_day'],42.8571)
        self.assertEqual(r['overview']['missing_days'],4)
    def test_goal_versions_daily_and_total(self):
        self.goal('2026-10-05',calories_kcal=100,water_ml=200)
        self.goal('2026-10-08',calories_kcal=200,water_ml=400)
        self.meal('2026-10-05',calories_kcal=100);self.water('2026-10-05',100)
        r=self.report('2026-10-05','week');m=r['nutrition']['total']['nutrients']['calories_kcal']
        self.assertEqual(m['target'],1100);self.assertEqual(r['water']['target_ml'],2200)
        self.assertEqual(r['water']['daily'][3]['goal_effective_from'],'2026-10-08')
        self.assertAlmostEqual(m['achievement_percent'],9.0909);self.assertEqual(m['ratio_basis'],'known_only')
    def test_missing_target_day_disables_range_ratio(self):
        self.goal('2026-10-06',calories_kcal=100,water_ml=200)
        self.meal('2026-10-06',calories_kcal=100);self.water('2026-10-06')
        r=self.report('2026-10-05','week');self.assertIsNone(r['water']['target_ml']);self.assertIsNone(r['water']['achievement_percent'])
        self.assertIsNone(r['nutrition']['total']['nutrients']['calories_kcal']['target'])
    def test_water_timezone_and_below_target_evidence(self):
        self.goal('2026-10-13',water_ml=500)
        self.water(drank_at='2026-10-12T16:00:00Z',amount=100)
        self.water(drank_at='2026-10-13T15:59:59Z',amount=200)
        self.water(drank_at='2026-10-13T16:00:00Z',amount=999)
        r=self.report();self.assertEqual(r['water']['known_sum_ml'],300);self.assertEqual(r['water']['achievement_percent'],60)
        advice=next(s for s in r['suggestions'] if s['rule_id']=='recorded_water_below_target')
        self.assertEqual(advice['evidence']['days'][0]['gap_ml'],200);self.assertIn('已记录',advice['text'])
    def test_shared_summary_parity(self):
        self.meal(calories_kcal=321);self.water();self.goal('2026-10-13',calories_kcal=500,water_ml=1000)
        r=self.report();n=self.client.get('/api/diet/nutrition-summary?date_from=2026-10-13&date_to=2026-10-13').json()
        self.assertEqual(r['nutrition'],n)
        w=self.client.get('/api/diet/water-summary?date=2026-10-13').json();self.assertEqual(r['water']['daily'][0]['known_sum_ml'],w['total_ml']);self.assertEqual(r['water']['daily'][0]['achievement_percent'],w['achievement_percent'])
    def test_rules_traceable_no_diagnosis(self):
        self.meal();r=self.report();unknown=next(s for s in r['suggestions'] if s['rule_id']=='unknown_calories_kcal')
        self.assertEqual(unknown['evidence']['unknown_count'],1);self.assertIn('历史快照',unknown['text'])
        for s in r['suggestions']:self.assertIn('path',s['evidence'])
    def test_readonly_and_profile_scope(self):
        self.meal(calories_kcal=10)
        with connect(self.path) as c:
            # This application's schema enforces a single local profile, id=1.
            with self.assertRaises(sqlite3.IntegrityError):c.execute("INSERT INTO profiles(id,display_name) VALUES(2,'other isolated test')")
            before=list(c.iterdump())
        self.assertEqual(self.report()['nutrition']['total']['nutrients']['calories_kcal']['known_sum'],10)
        with connect(self.path) as c:self.assertEqual(list(c.iterdump()),before)
    def test_no_profile_and_invalid_arguments(self):
        for q in ('period=year&date=2026-10-13','date=2026-02-30','date=bad','period=week'):
            self.assertEqual(self.client.get('/api/diet/reports?'+q).status_code,422)
        with connect(self.path) as c:c.execute('DELETE FROM profiles')
        r=self.client.get('/api/diet/reports?date=2026-10-13');self.assertEqual(r.status_code,409);self.assertEqual(r.json()['code'],'PROFILE_REQUIRED')
