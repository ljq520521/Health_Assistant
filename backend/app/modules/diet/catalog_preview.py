"""Loopback-only isolated diet UI acceptance server, never a full-site substitute.

Creates and removes its own temporary user database. No existing database path
can be supplied. Authentication and privacy dependencies are the real profile
module's implementations; no accounts, profiles or health records are prefilled.
Run from backend: python -B -m app.modules.diet.catalog_preview
"""
import argparse
import os
from pathlib import Path
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8018)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Use an unprivileged local port')
    with tempfile.TemporaryDirectory(prefix='diet-catalog-preview-') as directory:
        path = Path(directory).resolve() / 'temporary-user.db'
        os.environ['HEALTH_DB_PATH'] = str(path)
        os.environ['DIET_APPLY_MIGRATIONS'] = '0'
        from fastapi import FastAPI
        import uvicorn
        from app.config import Settings
        from app.database import init_database
        from app.modules.profile.router import router as profile_router
        from app.modules.diet.router import router as diet_router
        from app.modules.diet import migrations, migration_002, migration_003, migration_004, migration_006
        from app.modules.diet.build_catalog import MANIFEST_SHA
        init_database(path)
        for migrate in (migrations.migrate_diet, migration_002.migrate_goals,
                        migration_003.migrate_water, migration_004.migrate_recipes,
                        migration_006.migrate_catalog):
            migrate(path)
        application = FastAPI(title='Independent diet preview — not full application')
        application.state.settings = Settings('Independent diet preview', path, ())
        application.state.diet_demo = {
            'environment': 'development_demo', 'database_path': str(path),
            'notice': '独立饮食验收环境，非真实用户、非真实健康记录；未验收完整团队应用。',
            'review_status': 'approved', 'recipe_trial_status': '未经实际试做',
            'course_approval': {'status': 'approved', 'scope': 'team_course_demonstration_only',
                                'manifest_sha256': MANIFEST_SHA},
        }
        application.include_router(profile_router, prefix='/api')
        application.include_router(diet_router, prefix='/api')
        print('INDEPENDENT DIET PREVIEW ONLY. Temporary user database:', path, flush=True)
        uvicorn.run(application, host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
