"""Course approval evidence and presentation metadata; no nutrition algorithms."""
from contextlib import contextmanager
from unittest.mock import patch

from app.modules.diet import import_service as importer
from app.modules.diet.source_mapping import ImportRejected, digest, json_read, sha

NOTICE = '课程演示数据已获团队批准；食品来源已技术核验；成分与过敏原未完整核验；仅限课程演示'


def verify_scope(root, package):
    approval = json_read((root / 'approval-record.json').read_bytes())
    preview = (root / 'provenance/approval-record.preview.json').read_bytes()
    if (sha(preview) != approval['approval_preview_sha256']
            or approval['approval_scope'] != 'team_course_demonstration_only'
            or approval['formal_production_use_approved'] is not False
            or approval['approver']['signature'] != '食物板块负责人'
            or approval['recorded_at'] != '2026-10-15T23:41:09+08:00'):
        raise ImportRejected('课程审批依据或范围不符')
    original = json_read(preview)
    for key in ('foods', 'recipes', 'dependencies', 'approved_counts'):
        if approval[key] != original[key]:
            raise ImportRejected('批准记录与已确认预览不一致')
    v2 = root.parent / 'usda_v2'
    if sha((v2 / 'manifest.json').read_bytes()) != approval['parent']['seed_manifest_sha256']:
        raise ImportRejected('v2基线清单不符')
    old_foods = json_read((v2 / 'foods.json').read_bytes())
    old_recipes = json_read((v2 / 'recipes.json').read_bytes())
    approved_foods = {r['source_key']: r for r in approval['foods']}
    approved_recipes = {r['recipe_key']: r for r in approval['recipes']}
    if ({f.source_key for f in package['foods']} != set(approved_foods)
            or {r.recipe_key for r in package['recipes']} != set(approved_recipes)):
        raise ImportRejected('记录超出批准范围')
    for old, new in zip(old_foods, package['foods']):
        if (digest(old) != approved_foods[new.source_key]['original_record_sha256']
                or new.model_dump() != old | {'review_status': 'approved'}):
            raise ImportRejected('食物身份、营养或原始说明发生变化')
    for old, new in zip(old_recipes, package['recipes']):
        original_row = old | {'source_note': old['source_note'].removesuffix(' 未经实际试做。')}
        expected = old | {
            'review_status': 'approved',
            'description': old['description'].replace('临时审核配方，待团队确认。', '课程演示配方，已获团队课程演示使用批准。'),
            'source_note': old['source_note'].replace('待审核', '已获团队课程演示使用批准'),
        }
        if (digest(original_row) != approved_recipes[new.recipe_key]['original_record_sha256']
                or new.model_dump() != expected):
            raise ImportRejected('菜谱食材、克重、步骤或试做说明发生变化')
    expected = [(d['recipe_key'], d['food_source_key'], d['amount_g']) for d in approval['dependencies']]
    actual = [(r.recipe_key, i.food_source_key, i.amount_g) for r in package['recipes'] for i in r.ingredients]
    if len(actual) != 48 or sorted(actual) != sorted(expected):
        raise ImportRejected('48条食材依赖与批准记录不一致')


@contextmanager
def labelled_payloads():
    """Offline import/verification only, never patch factories during HTTP requests."""
    food_factory, recipe_factory = importer.food_payload, importer.recipe_payload

    def food(*args, **kwargs):
        payload = food_factory(*args, **kwargs)
        return type(payload).model_validate(payload.model_dump() | {'source_note': NOTICE + '。\n' + payload.source_note})

    def recipe(*args, **kwargs):
        payload = recipe_factory(*args, **kwargs)
        return type(payload).model_validate(payload.model_dump() | {'source_note': NOTICE + '。\n' + payload.source_note})

    with patch.object(importer, 'food_payload', food), patch.object(importer, 'recipe_payload', recipe):
        yield


def record_approvals(path, package):
    """Bind display approval to unchanged imported rows, not names or note keywords.

    Generated before serving. The UI compares the full approved projection;
    user edits made after startup no longer match, and receive no approval badge.
    """
    result = {'food': {}, 'recipe': {}}
    with labelled_payloads(), importer.database(path) as connection:
        plan = importer.plan(connection, package, path)
        for item in plan['items']:
            if item['action'] != 'skip':
                continue
            if item['kind'] == 'food':
                row = dict(connection.execute('SELECT * FROM food_items WHERE id=?', (item['id'],)).fetchone())
                fields = list(importer.FoodInput.model_fields) + ['id', 'updated_at']
                projection = {k: row[k] for k in fields}
            else:
                row = importer.recipes.detail(connection, item['id'])
                fields = list(importer.RecipeInput.model_fields) + ['id', 'updated_at']
                projection = {k: row[k] for k in fields}
                projection['ingredients'] = [{k: i[k] for k in ('food_id', 'amount_g')} for i in row['ingredients']]
                projection['snapshot_outdated'] = False
            result[item['kind']][str(item['id'])] = projection
    return result
