r"""Run diet regression against a real-auth, diet-only temporary test app.

Run from backend: ..\.venv\Scripts\python.exe -B tests/run_diet_isolated.py
This is not full-site acceptance. Full-app startup and seed-server integration
tests retain their original assertions and are explicitly reported as blocked.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['DIET_ISOLATED_TESTS']='1'

MODULES=(
    'test_diet','test_food_library','test_diet_migrations','test_nutrition',
    'test_water','test_recipes','test_recipe_preferences','test_recipe_recommendation',
    'test_reports','test_diet_import','test_diet_import_recommendation','test_public_catalog','test_diet_demo',
    'app.modules.diet.seed_data.usda_v2.test_seed',
    'app.modules.diet.seed_data.usda_v3_course_demo.test_seed',
)
BLOCKED={
    'test_diet_migrations.MigrationTests.test_startup_never_migrates_and_explicit_migration_enables_library',
    'test_nutrition.GoalsMigrationTests.test_concurrent_and_startup_does_not_apply_002',
    'test_water.WaterMigrationTests.test_startup_does_not_apply_003',
    'test_recipes.RecipeMigrationTests.test_unmigrated_app_compatibility',
    'test_diet_demo.DemoTests.test_demo_config_and_normal_config_separate',
    'app.modules.diet.seed_data.usda_v2.test_seed.SeedTests.test_real_seed_api_search_nutrition_recommendation_and_cycle',
    'app.modules.diet.seed_data.usda_v3_course_demo.test_seed.CourseSeedTests.test_real_seed_api_search_nutrition_recommendation_and_cycle',
    'app.modules.diet.seed_data.usda_v3_course_demo.test_seed.CourseSeedTests.test_display_approval_is_bound_to_matching_imported_rows',
}
REASON='Full application blocked: exercise/recommendation.py is missing; no substitute health endpoint or auth bypass is used'

class BlockedIntegration(unittest.TestCase):
    def __init__(self,test_id):
        super().__init__();self.test_id=test_id
    def id(self):return self.test_id
    def shortDescription(self):return self.test_id
    def runTest(self):self.skipTest(REASON)

def flattened(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite):yield from flattened(test)
        else:yield test

def main():
    with tempfile.TemporaryDirectory(prefix='diet-isolated-run-') as folder:
        # A safe absolute fallback exists even before individual fixtures load.
        os.environ['HEALTH_DB_PATH']=str(Path(folder)/'unused-fallback.db')
        os.environ['DIET_APPLY_MIGRATIONS']='0'
        cases=list(flattened(unittest.defaultTestLoader.loadTestsFromNames(MODULES)))
        found={test.id() for test in cases}
        if not BLOCKED.issubset(found):
            raise RuntimeError('Blocked integration inventory drift: '+repr(BLOCKED-found))
        suite=unittest.TestSuite(BlockedIntegration(test.id()) if test.id() in BLOCKED else test for test in cases)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped)
        print(f'Independent results: {passed} passed; {len(result.skipped)} blocked; {len(result.failures)} failed; {len(result.errors)} errors')
        return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
