"""Read authorized diet-relevant context; free text is never an automatic allergy rule."""
from datetime import date, timedelta
import hashlib
import json
import unicodedata
from app.database import connect
from app.modules.diet.library_service import LibraryError
from app.modules.diet.migration_005 import ready
from app.modules.diet.recipe_service import require_recipes
from app.modules.diet.service import require_profile
from app.modules.diet.nutrition_service import effective
from app.modules.diet.nutrition_math import NUTRIENTS
from app.modules.diet.catalog_links import source_identity
from app.modules.diet import catalog_repository
from app.modules.diet.settings import utc_now
from app.modules.diet.recipe_recommendation import ALGORITHM_VERSION


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def normalized_text(value):
    return unicodedata.normalize('NFC', value or '').strip()


def require_weekly(c):
    require_profile(c)
    try:
        installed = ready(c)
    except RuntimeError as exc:
        raise LibraryError(503, 'WEEKLY_PLAN_SCHEMA_INVALID', '005周计划结构或登记校验异常，请停止写入并检查') from exc
    if not installed:
        raise LibraryError(503, 'WEEKLY_PLAN_MIGRATION_REQUIRED', '请先显式完成001～004、006及005周计划扩展迁移')
    require_recipes(c)


def profile_and_rules(c):
    row = c.execute('SELECT id,allergies,preferences,updated_at FROM profiles WHERE id=1').fetchone()
    if row is None:
        raise LibraryError(409, 'PROFILE_REQUIRED', '请先建立个人档案')
    profile = {'allergies': normalized_text(row['allergies']), 'preferences': normalized_text(row['preferences'])}
    profile_hash = fingerprint({'profile_id': 1, **profile})
    rules = []
    comparable = []
    for item in c.execute('''SELECT p.id,p.food_id,p.term_id,p.rule_type,
        coalesce(f.name,t.name) AS target_name,f.deleted_at,t.archived_at,
        f.id AS present_food,t.id AS present_term
        FROM diet_food_preferences p LEFT JOIN food_items f ON f.id=p.food_id AND f.profile_id=p.profile_id
        LEFT JOIN diet_ingredient_terms t ON t.id=p.term_id AND t.profile_id=p.profile_id
        WHERE p.profile_id=1 ORDER BY p.id'''):
        value = {key: item[key] for key in ('id', 'food_id', 'term_id', 'rule_type', 'target_name')}
        value['valid'] = bool((item['present_food'] is not None and item['deleted_at'] is None)
                              or (item['present_term'] is not None and item['archived_at'] is None))
        rules.append(value)
        comparable.append({key: value[key] for key in ('id','food_id','term_id','rule_type','valid')}
                          | {'source_identity': source_identity(c, item['food_id']) if item['food_id'] else None})
    return profile, row['updated_at'], profile_hash, rules, comparable


def selected_rules_valid(profile, rules, allergy_ids, preference_ids):
    by_id = {r['id']: r for r in rules}
    if profile['allergies'] and not allergy_ids:
        return False
    if profile['preferences'] and not preference_ids:
        return False
    for ids, types in ((allergy_ids, {'allergy','forbidden'}), (preference_ids, {'like','dislike'})):
        for key in ids:
            rule = by_id.get(key)
            if not rule or not rule['valid'] or rule['rule_type'] not in types:
                return False
    return True


def context(c, start_date, selected_goal_ids=()):
    """All private inputs are read through the caller's single SQLite snapshot."""
    require_weekly(c)
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if start_date > date.max - timedelta(days=6):
        raise LibraryError(422, 'INVALID_WEEK', '计划开始日期不能超过9999-12-25')
    profile, updated_at, profile_hash, rules, comparable_rules = profile_and_rules(c)
    rules_hash = fingerprint(comparable_rules)
    review_needed = bool(profile['allergies'] or profile['preferences'])
    confirmation = c.execute('''SELECT * FROM diet_plan_context_confirmations
        WHERE profile_id=1 AND profile_fingerprint=? AND rules_fingerprint=? ORDER BY id DESC LIMIT 1''',
        (profile_hash, rules_hash)).fetchone()
    confirmation_valid = not review_needed
    if confirmation is not None:
        confirmation_valid = selected_rules_valid(profile, rules, json.loads(confirmation['allergy_rule_ids_json']),
                                                  json.loads(confirmation['preference_rule_ids_json']))
    blockers = []
    if not confirmation_valid:
        blockers.append('个人档案中的过敏/偏好文字尚未确认映射到当前有效饮食规则，请先完成核对。')
    goals = [{key: r[key] for key in ('id','title','target_value','current_value','unit','due_date')}
             for r in c.execute('SELECT * FROM health_goals WHERE profile_id=1 ORDER BY id')]
    selected_ids = sorted(selected_goal_ids)
    by_id = {goal['id']: goal for goal in goals}
    missing_ids = [key for key in selected_ids if key not in by_id]
    if missing_ids:
        blockers.append('选定的健康目标已删除或不属于当前档案。旧计划保留历史；请新建计划并重新选择目标，不能刷新旧计划的固定目标集合。')
    selected_goals = [{key: by_id[id][key] for key in ('id','title','target_value','unit','due_date')}
                      for id in selected_ids if id in by_id]
    effective_goals = []
    for offset in range(7):
        day = start_date + timedelta(days=offset)
        goal = effective(c, day)
        effective_goals.append({'date': day.isoformat(), **{key: goal[key] if goal else None for key in NUTRIENTS}})
    # SQL projections intentionally omit display names, note-only edits, timestamps
    # and water goals unless the existing ranker uses them for validity checks.
    foods = [dict(r) for r in c.execute('''SELECT id,deleted_at,updated_at,source_url,source_note,
        calories_per_100g,protein_g_per_100g,fat_g_per_100g,carbohydrate_g_per_100g
        FROM food_items WHERE profile_id=1 ORDER BY id''')]
    # Keep only source identity, not arbitrary source prose, in the fingerprint.
    for food in foods:
        food['source_identity'] = source_identity(c, food['id'])
        food.pop('source_url'); food.pop('source_note')
    compositions = [dict(r) for r in c.execute('''SELECT food_id,ingredient_status,allergen_status,assessed_food_updated_at
        FROM diet_food_composition WHERE profile_id=1 ORDER BY food_id''')]
    terms = [dict(r) for r in c.execute('''SELECT food_id,term_id,relation FROM diet_food_composition_terms
        WHERE profile_id=1 ORDER BY food_id,term_id,relation''')]
    aliases = [dict(r) for r in c.execute('''SELECT a.term_id,a.alias_key FROM diet_ingredient_aliases a
        JOIN diet_ingredient_terms t ON t.id=a.term_id AND t.profile_id=a.profile_id
        WHERE a.profile_id=1 AND t.archived_at IS NULL ORDER BY a.term_id,a.alias_key''')]
    stock = [dict(r) for r in c.execute('SELECT food_id,quantity_g FROM diet_inventory_items WHERE profile_id=1 ORDER BY food_id')]
    recipe_versions = [dict(r) for r in c.execute('''SELECT id,revision,archived_at FROM diet_recipes
        WHERE profile_id=1 ORDER BY id''')]
    recipe_categories = [dict(r) for r in c.execute('SELECT id,name FROM diet_recipe_categories WHERE profile_id=1 ORDER BY id')]
    catalog_data = None
    try:
        metadata = catalog_repository.metadata()
        catalog_data = {key: metadata[key] for key in ('release_id','logical_content_sha256','schema_version')}
    except LibraryError as exc:
        catalog_data = {'error': exc.code}
        blockers.append(exc.detail)
    hard_input = {'algorithm_version': ALGORITHM_VERSION, 'allergies': profile['allergies'],
                  'rules': [r for r in comparable_rules if r['rule_type'] in ('allergy','forbidden')],
                  'foods': foods, 'compositions': compositions, 'composition_terms': terms, 'term_aliases': aliases, 'catalog': catalog_data}
    hard_hash = fingerprint(hard_input)
    inputs = {'profile_fingerprint': profile_hash, 'rules': comparable_rules, 'hard_fingerprint': hard_hash,
              'start_date': start_date.isoformat(), 'selected_goals': selected_goals, 'missing_goal_ids': missing_ids,
              'effective_goals': effective_goals, 'inventory': stock, 'recipes': recipe_versions, 'recipe_categories': recipe_categories,
              'catalog': catalog_data, 'confirmation_valid': confirmation_valid}
    warnings = ['自由文本由用户明确核对后映射，不自动推断过敏关系；课程批准不代表过敏安全认证。',
                '选定健康目标仅作为计划背景，不自动换算热量；营养目标沿用饮食模块已保存的明确数值。']
    if any(all(day[nutrient] is None for nutrient in NUTRIENTS) for day in effective_goals):
        warnings.append('部分日期尚无营养目标，相应营养评分不参与，不生成默认热量建议。')
    if not any(r['rule_type'] in ('allergy','forbidden') for r in rules):
        warnings.append('尚未设置饮食硬禁忌，候选不能被解释为已核验过敏安全。')
    return {'profile_id': 1, 'profile': profile, 'profile_updated_at': updated_at,
            'profile_fingerprint': profile_hash, 'rules_fingerprint': rules_hash, 'hard_fingerprint': hard_hash,
            'context_hash': fingerprint(inputs), 'confirmation_required': review_needed,
            'confirmation_valid': confirmation_valid, 'confirmation_id': confirmation['id'] if confirmation else None,
            'rules': rules, 'shared_goals': goals, 'selected_goals': selected_goals,
            'effective_goals': effective_goals, 'blockers': blockers, 'warnings': warnings,
            'inputs': inputs}


def context_summary(value):
    """Audit hashes and used goals, without copying profile free text or medical fields."""
    return {key: value[key] for key in ('profile_id','profile_updated_at','profile_fingerprint',
            'rules_fingerprint','hard_fingerprint','context_hash','confirmation_id','confirmation_valid',
            'selected_goals','effective_goals','warnings')}


def get_context(path, start_date, selected_goal_ids=()):
    with connect(path) as c:
        c.execute('BEGIN')
        value = context(c, start_date, selected_goal_ids)
        value.pop('inputs')
        return value


def confirm_context(path, data, actor_id):
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE'); require_weekly(c)
        profile, _, profile_hash, rules, comparable = profile_and_rules(c)
        rules_hash = fingerprint(comparable)
        if profile_hash != data.profile_fingerprint or rules_hash != data.rules_fingerprint:
            raise LibraryError(409, 'DIET_CONTEXT_CHANGED', '档案或规则已更新，请重新读取后核对')
        if not selected_rules_valid(profile, rules, data.allergy_rule_ids, data.preference_rule_ids):
            raise LibraryError(422, 'DIET_PROFILE_MAPPING_REQUIRED', '非空过敏文字必须选择有效过敏/禁用规则，非空偏好必须选择有效喜欢/不喜欢规则')
        stamp = utc_now()
        id = c.execute('''INSERT INTO diet_plan_context_confirmations
            (profile_id,profile_fingerprint,rules_fingerprint,allergy_rule_ids_json,preference_rule_ids_json,actor_user_id,confirmed_at)
            VALUES(1,?,?,?,?,?,?)''', (profile_hash, rules_hash, canonical(sorted(data.allergy_rule_ids)),
                canonical(sorted(data.preference_rule_ids)), actor_id, stamp)).lastrowid
        return {'id': id, 'profile_fingerprint': profile_hash, 'rules_fingerprint': rules_hash,
                'allergy_rule_ids': sorted(data.allergy_rule_ids), 'preference_rule_ids': sorted(data.preference_rule_ids),
                'actor_user_id': actor_id, 'confirmed_at': stamp,
                'notice': '此记录只确认文字与规则的映射，不代表成分、交叉接触或过敏安全核验。'}
