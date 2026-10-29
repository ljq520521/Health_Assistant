r"""Full-team acceptance entry point; never falls back to the isolated app.

Run after member C restores exercise/recommendation.py:
  ..\.venv\Scripts\python.exe -B tests/run_diet_full.py

Historical v2/v3 packages remain byte-identical. Only their HTTP client fixture
is adapted to obtain a real temporary admin token and health-data consent.
All original test bodies and assertions, including cycle integration, run intact.
"""
import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

def main():
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    os.environ.pop('DIET_ISOLATED_TESTS',None)
    with tempfile.TemporaryDirectory(prefix='diet-full-acceptance-') as folder:
        os.environ['HEALTH_DB_PATH']=str(Path(folder).resolve()/'unused-fallback.db')
        os.environ['DIET_APPLY_MIGRATIONS']='0'
        try:
            importlib.import_module('app.main')
        except ImportError as exc:
            print(f'BLOCKED: real team application import failed: {exc}. No test application substituted.')
            return 2
        from diet_test_runtime import TestClient as AuthenticatedClient
        suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent),pattern='test_*.py')
        for name in ('app.modules.diet.seed_data.usda_v2.test_seed',
                     'app.modules.diet.seed_data.usda_v3_course_demo.test_seed'):
            module=importlib.import_module(name)
            # This client runs the real register/login/privacy APIs. It does not
            # replace app factories, auth dependencies, responses, or assertions.
            module.TestClient=AuthenticatedClient
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
