"""Explicit test-only workflow for a pending package; never targets health.db.

The normal import CLI remains unchanged. Metadata is added only to demo source
notes; package identity, nutrients, recipe ingredients and steps stay untouched.
"""
import argparse
import json
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from app.database import connect, init_database
from app.modules.diet import import_service as importer
from app.modules.diet.migrations import migrate_diet, migration_ready
from app.modules.diet.migration_002 import migrate_goals
from app.modules.diet.migration_003 import migrate_water
from app.modules.diet.migration_004 import migrate_recipes

NOTICE = '来源数据已技术核验，尚未获得团队正式批准'
PROFILE_NAME = '开发演示档案（非真实用户）'
MARKER_FILE = 'DEVELOPMENT_DEMO_ONLY.json'
V2_SHA256 = 'bdc647117fe396ee04d7bac93bd0ef5b1d1cf22e7b8fd02047565470bb2321a6'


def safe_path(path):
    raw = Path(path).absolute()
    target = raw.resolve()
    if target != raw or target.name != 'demo.db' or not target.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise ValueError('演示库必须是独立系统临时目录内的demo.db，不接受链接或health.db')
    return target


def read_context(path):
    path = safe_path(path)
    if not path.is_file():
        raise ValueError('演示库不存在；拒绝自动创建或回退到正式库')
    context = json.loads((path.parent / MARKER_FILE).read_text(encoding='utf-8'))
    if (context.get('database_path') != str(path) or context.get('purpose') != 'pending-validation'
            or context.get('status') != 'ready' or context.get('approved') is not False
            or context.get('manifest_sha256') != V2_SHA256):
        raise ValueError('演示库标识不正确或初始化未完成')
    with importer.database(path) as c:
        profile = c.execute('SELECT * FROM profiles WHERE id=1').fetchone()
        if profile is None or profile['display_name'] != PROFILE_NAME:
            raise ValueError('缺少明确标记的演示档案')
        if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or c.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('演示数据库完整性失败')
        if not migration_ready(c): raise ValueError('缺少饮食迁移版本')
        if c.execute('SELECT COUNT(*) FROM diet_schema_migrations').fetchone()[0] != 4:
            raise ValueError('需要完整001—004结构')
    return context


@contextmanager
def labelled_payloads():
    """Offline, single-process test import context. Do not use in serving requests."""
    food_factory, recipe_factory = importer.food_payload, importer.recipe_payload

    def food(*args, **kwargs):
        payload = food_factory(*args, **kwargs)
        return type(payload).model_validate(payload.model_dump() | {'source_note': NOTICE + '；仅限开发演示。\n' + payload.source_note})

    def recipe(*args, **kwargs):
        payload = recipe_factory(*args, **kwargs)
        return type(payload).model_validate(payload.model_dump() | {'source_note': NOTICE + '；未经实际试做；仅限开发演示。\n' + payload.source_note})

    with patch.object(importer, 'food_payload', food), patch.object(importer, 'recipe_payload', recipe):
        yield


def initialize_empty(path):
    path = safe_path(path)
    # Exclusive creation: never initialize or replace an existing database.
    with path.open('xb'):
        pass
    init_database(path)
    migrate_diet(path); migrate_goals(path); migrate_water(path); migrate_recipes(path)
    with connect(path) as c:
        c.execute('INSERT INTO profiles(id,display_name) VALUES(1,?)', (PROFILE_NAME,))


def create_demo(package_root):
    package = importer.load_package(package_root, expected_manifest_sha256=V2_SHA256, allow_temporary_review=True)
    m = package['manifest']
    if (m.purpose != 'temporary_review' or m.review_status != 'pending_final_confirmation'
            or len(package['foods']) != 134 or len(package['recipes']) != 12):
        raise ValueError('本入口仅接受原始v2的134种食物及12道待确认菜谱')
    folder = Path(tempfile.mkdtemp(prefix='health-assistant-demo-')).resolve()
    path = folder / 'demo.db'
    metadata = {'purpose': 'pending-validation', 'approved': False, 'status': 'initializing',
                'database_path': str(path), 'notice': NOTICE, 'profile_name': PROFILE_NAME,
                'manifest_sha256': V2_SHA256, 'package_path': str(Path(package_root).resolve()),
                'package_review_status': m.review_status, 'recipe_trial_status': '未经实际试做',
                'created_at': datetime.now(timezone.utc).isoformat()}
    importer.write_audit(folder / MARKER_FILE, metadata)
    try:
        initialize_empty(path)
        with labelled_payloads():
            preview = importer.dry_run(path, package, folder / 'audit')
            if preview['counts'] != {'add':146, 'skip':0, 'conflict':0}:
                raise ValueError('初始化导入预览数量异常')
            result = importer.apply_package(path, package, folder / 'audit', expected_plan_sha256=preview['plan_sha256'])
            with importer.database(path) as c: before = importer.snapshot(c)
            repeat = importer.dry_run(path, package, folder / 'audit')
            if repeat['counts'] != {'add':0, 'skip':146, 'conflict':0}:
                raise ValueError('重复导入检查失败')
            importer.apply_package(path, package, folder / 'audit', expected_plan_sha256=repeat['plan_sha256'])
            with importer.database(path) as c:
                if before != importer.snapshot(c): raise ValueError('重复导入改变了业务数据')
        metadata.update(status='ready', food_count=134, recipe_count=12,
                        initial_counts=preview['counts'], repeat_counts=repeat['counts'],
                        initial_run_id=result['run_id'])
        (folder / MARKER_FILE).write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
        return read_context(path)
    except Exception as exc:
        importer.write_audit(folder / 'INITIALIZATION_FAILED.json', {'database_path':str(path),'error':str(exc)})
        raise RuntimeError(f'演示初始化失败，停止并保留证据：{folder}；{exc}') from exc


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--result', type=Path, required=True, help='必须是尚不存在的输出文件')
    args=p.parse_args()
    if args.result.exists(): raise ValueError('结果文件已存在，不覆盖')
    result=create_demo(args.package)
    importer.write_audit(args.result,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
