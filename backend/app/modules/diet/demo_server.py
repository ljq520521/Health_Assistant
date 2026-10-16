"""uvicorn app.modules.diet.demo_server:create_demo_app --factory

Requires HEALTH_DIET_DEMO_DB, never falls back to HEALTH_DB_PATH or .env.
"""
import os
from pathlib import Path
from app.config import Settings
from app.modules.diet.demo_environment import read_context, NOTICE


def create_demo_app():
    value = os.environ.get('HEALTH_DIET_DEMO_DB')
    if not value: raise ValueError('必须显式设置HEALTH_DIET_DEMO_DB，禁止回退到正式库')
    path = Path(value)
    if not path.is_absolute(): raise ValueError('演示数据库必须是绝对路径')
    context = read_context(path)
    from app.main import create_app
    application = create_app(Settings('饮食模块开发演示（非真实用户）',path.resolve(),
                                     ('http://127.0.0.1:5174','http://localhost:5174')))
    application.state.diet_demo = {'notice':NOTICE, 'database_path':str(path.resolve()),
                                   'review_status':context['package_review_status'],
                                   'recipe_trial_status':'未经实际试做', 'approved':False}
    return application
