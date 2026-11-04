"""Offline pending seed import into explicitly labelled, temporary demo databases."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

from app.modules.diet import import_service as importer
from app.modules.diet.demo_environment import (
    NOTICE, PROFILE_NAME, initialize_empty, labelled_payloads, safe_path,
)
from app.modules.diet.migration_004 import ready
from app.modules.diet.source_mapping import ImportRejected, json_read

PACKAGE = Path(__file__).resolve().parent
MANIFEST_SHA256 = '2391951c2738a0b5ca181c441a216d872731f9eed8fc8290b2e6001610f4e29b'
MARKER = 'SEED_DEMO_ONLY.json'
PREFIX = 'health-diet-seed-'


def load_seed():
    package = importer.load_package(
        PACKAGE, expected_manifest_sha256=MANIFEST_SHA256, allow_temporary_review=True,
    )
    manifest = package['manifest']
    if (manifest.purpose != 'temporary_review'
            or manifest.review_status != 'pending_final_confirmation'
            or manifest.package_version != 2
            or len(package['foods']) != 134 or len(package['recipes']) != 12):
        raise ImportRejected('只接受固定的待审核 v2：134 食物、12 菜谱')
    hashes = json_read((PACKAGE / 'provenance/source-record-sha256.json').read_bytes())
    if {key: value['record_sha256'] for key, value in package['evidence'].items()} != hashes:
        raise ImportRejected('USDA 原始条目哈希与 v2 核验记录不符')
    return package


def prepare_new(folder):
    """Explicit initialization reuses the existing demo-only profile/migrations flow."""
    folder = Path(folder).resolve()
    path = safe_path(folder / 'demo.db')
    if not folder.name.startswith(PREFIX):
        raise ImportRejected('只接受本工具新建的独立演示目录')
    if path.exists() or (folder / MARKER).exists():
        raise ImportRejected('拒绝初始化或覆盖已有演示库')
    os.environ['HEALTH_DB_PATH'] = str(path)
    os.environ['DIET_APPLY_MIGRATIONS'] = '0'
    initialize_empty(path)  # Base schema, explicit 001-004, labelled profile id=1.
    metadata = {
        'purpose': 'pending-seed-demo', 'approved': False, 'status': 'ready',
        'database_path': str(path), 'manifest_sha256': MANIFEST_SHA256,
        'package_review_status': 'pending_final_confirmation',
        'recipe_trial_status': '未经实际试做', 'profile_name': PROFILE_NAME,
        'notice': NOTICE, 'created_at': datetime.now(timezone.utc).isoformat(),
    }
    importer.write_audit(folder / MARKER, metadata)
    checked_context(path)
    return path


def checked_context(path):
    """Read-only gate; never initializes or repairs an existing database."""
    path = safe_path(path)
    if not path.parent.name.startswith(PREFIX):
        raise ImportRejected('目标不是本种子工具的独立临时演示库')
    marker = path.parent / MARKER
    if marker.is_symlink() or not marker.is_file():
        raise ImportRejected('缺少演示标识；不能将普通用户库作为目标')
    context = json_read(marker.read_bytes())
    expected = {
        'purpose': 'pending-seed-demo', 'approved': False, 'status': 'ready',
        'database_path': str(path), 'manifest_sha256': MANIFEST_SHA256,
        'package_review_status': 'pending_final_confirmation',
        'recipe_trial_status': '未经实际试做', 'profile_name': PROFILE_NAME,
    }
    if any(context.get(key) != value for key, value in expected.items()):
        raise ImportRejected('演示标识不匹配，停止')
    if (path.parent / 'audit').resolve() != path.parent / 'audit':
        raise ImportRejected('审计目录不能是链接')
    with importer.database(path) as connection:
        if not ready(connection):
            raise ImportRejected('必须先显式完成 001-004；本导入操作不会补跑迁移')
        profiles = connection.execute('SELECT id,display_name FROM profiles').fetchall()
        if len(profiles) != 1 or tuple(profiles[0]) != (1, PROFILE_NAME):
            raise ImportRejected('仅支持合法且明确标记的单演示档案 id=1')
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ImportRejected('数据库完整性检查失败')
        if connection.execute('PRAGMA foreign_key_check').fetchone():
            raise ImportRejected('数据库外键检查失败')
    return context


def import_demo(path, package, *, apply=False, expected_plan_sha256=None):
    context = checked_context(path)
    path = Path(context['database_path'])
    audit = path.parent / 'audit'
    with labelled_payloads():
        preview = importer.dry_run(path, package, audit)
        result = {'status': 'dry_run', 'database_path': str(path),
                  'manifest_sha256': package['manifest_sha256'],
                  'counts': preview['counts'], 'plan_sha256': preview['plan_sha256'],
                  'approved': False, 'notice': NOTICE}
        if apply:
            if preview['counts']['conflict']:
                raise ImportRejected('来源或用户内容冲突，整批停止，不覆盖')
            if not expected_plan_sha256:
                raise ImportRejected('写入必须提供审核过的 dry-run plan SHA256')
            committed = importer.apply_package(
                path, package, audit, expected_plan_sha256=expected_plan_sha256,
            )
            result.update(status=committed['status'], audit_dir=str(audit),
                          run_id=committed['run_id'])
    return result


def create_demo_app():
    """Serve only this seed's labelled DB; keep cycle get_settings() on the same DB."""
    value = os.environ.get('HEALTH_DIET_SEED_DB')
    if not value or not Path(value).is_absolute():
        raise ValueError('必须显式设置 HEALTH_DIET_SEED_DB 的绝对路径')
    context = checked_context(Path(value))
    path = Path(context['database_path'])
    os.environ['HEALTH_DB_PATH'] = str(path)
    os.environ['DIET_APPLY_MIGRATIONS'] = '0'
    from app.config import Settings
    from app.main import create_app
    application = create_app(Settings('饮食种子课堂演示（非真实用户）', path,
                                      ('http://127.0.0.1:5173', 'http://localhost:5173')))
    application.state.diet_demo = {
        'notice': NOTICE, 'database_path': str(path), 'approved': False,
        'review_status': context['package_review_status'],
        'recipe_trial_status': context['recipe_trial_status'],
    }
    return application


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    targets = parser.add_mutually_exclusive_group()
    targets.add_argument('--create-demo', action='store_true', help='新建独立临时演示库并保留')
    targets.add_argument('--database', type=Path, help='仅接受本工具已标记的演示库；不使用环境默认库')
    parser.add_argument('--apply', action='store_true', help='显式允许演示写入')
    parser.add_argument('--expected-plan-sha256')
    parser.add_argument('--confirm-database', type=Path)
    args = parser.parse_args(argv)
    if args.apply and not (args.create_demo or args.database):
        parser.error('--apply 需要 --create-demo 或明确指定 --database')
    if args.create_demo and (args.expected_plan_sha256 or args.confirm_database):
        parser.error('新库流程不接受旧库确认参数')
    if args.database and args.apply:
        if not args.expected_plan_sha256 or not args.confirm_database:
            parser.error('已有演示库写入需要 --expected-plan-sha256 和 --confirm-database')
        if args.database.resolve() != args.confirm_database.resolve():
            parser.error('确认路径与目标不一致')
    try:
        package = load_seed()  # Verify everything before even creating a temp directory.
        if args.create_demo:
            path = prepare_new(tempfile.mkdtemp(prefix=PREFIX))
            result = import_demo(path, package)
            if args.apply:
                # Explicit --create-demo --apply authorizes this brand-new empty target only.
                result = import_demo(path, package, apply=True, expected_plan_sha256=result['plan_sha256'])
        elif args.database:
            result = import_demo(args.database, package, apply=args.apply,
                                 expected_plan_sha256=args.expected_plan_sha256)
        else:
            with tempfile.TemporaryDirectory(prefix=PREFIX) as folder:
                path = prepare_new(folder)
                result = import_demo(path, package)
            result['temporary_directory_removed'] = not Path(folder).exists()
            result['scope'] = '默认只预览；临时结构和演示档案随预览清理；没有导入食物或菜谱'
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result['counts']['conflict'] else 0
    except Exception as error:
        print(json.dumps({'status': 'rejected', 'error': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
