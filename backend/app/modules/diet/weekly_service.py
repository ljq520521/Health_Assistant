"""Persisted seven-day recipe snapshots and explicit feedback, never intake records."""
from collections import Counter
from datetime import date, datetime, timedelta
import json
from zoneinfo import ZoneInfo
from app.database import connect
from app.modules.diet.library_service import LibraryError
from app.modules.diet.recipe_recommendation import RecommendationInput, recommend_in_connection
from app.modules.diet.settings import BUSINESS_TIME_ZONE, utc_now
from app.modules.diet.weekly_context import context, context_summary, canonical, require_weekly
from app.modules.diet.weekly_schemas import MEALS, STATUS_VALUES, PlanInput


def business_today():
    return datetime.now(ZoneInfo(BUSINESS_TIME_ZONE)).date()


def conflict(code='DIET_CONTEXT_CHANGED', message='个人资料或推荐条件已更新，请重新预览'):
    raise LibraryError(409, code, message)


def check_context(value, expected_hash, require_confirmed=True):
    if value['context_hash'] != expected_hash:
        conflict()
    if require_confirmed and value['blockers']:
        conflict('DIET_PROFILE_REVIEW_REQUIRED', '；'.join(value['blockers']))


def parameters(data):
    return {'start_date': data.start_date.isoformat(), 'portions': data.portions,
            'meal_ratios': data.meal_ratios.model_dump(), 'selected_goal_ids': sorted(data.selected_goal_ids)}


def pending_feedback(stamp=None):
    return {'status':'pending', 'revision':0, 'note':'', 'reason':'', 'updated_at':stamp, 'actor_user_id':None}


def statistics(items):
    actionable = [item for item in items if item['recipe'] is not None]
    counts = {status: 0 for status in STATUS_VALUES}
    by_date = {}
    for item in actionable:
        status = item['feedback']['status']
        counts[status] += 1
        by_date.setdefault(item['date'], []).append(status)
    answered = len(actionable) - counts['pending']
    denominator = counts['completed'] + counts['not_completed'] + counts['partial']
    return {'total_slots':len(items), 'actionable_slots':len(actionable), 'counts':counts,
            'answered_count':answered,
            'feedback_progress_percent':round(100 * answered / len(actionable), 2) if actionable else None,
            'completion_denominator':denominator,
            'completion_rate_percent':round(100 * counts['completed'] / denominator, 2) if denominator else None,
            'pending_days':sum('pending' in values for values in by_date.values()),
            'days_without_any_feedback':sum(all(v == 'pending' for v in values) for values in by_date.values())}


def empty_item(day, meal, reason, excluded=None):
    return {'date':day, 'meal_type':meal, 'recipe':None, 'nutrition':None,
            'ingredients':[], 'missing_ingredients':[], 'reasons':[reason], 'repeated':False,
            'usable':False, 'excluded':excluded or []}


def generate(c, data, value, preserved=None):
    """Rotate eligible candidates; original safety filters and nutrient math are unchanged."""
    preserved = preserved or {}
    used = Counter()
    previous = None
    items = []
    warnings = list(value['warnings'])
    day_results = {}
    for offset in range(7):
        day = data.start_date + timedelta(days=offset)
        for meal in MEALS:
            key = (day.isoformat(), meal)
            if key in preserved:
                item = json.loads(canonical(preserved[key]))
                item['preserved'] = True
            elif value['blockers']:
                item = empty_item(key[0], meal, '档案与规则尚未完成核对，不能生成个性化候选。')
            else:
                ratio = getattr(data.meal_ratios, meal)
                cache_key = (day.isoformat(), meal, ratio)
                if cache_key not in day_results:
                    # Validated input caps display at 50; the whole ranked set is reused
                    # for week rotation so a large private library is not truncated.
                    query = RecommendationInput(date=day.isoformat(), portions=data.portions,
                                                target_ratio=ratio, meal_type=meal, limit=50)
                    day_results[cache_key] = recommend_in_connection(c, query, all_candidates=True)
                result = day_results[cache_key]
                for warning in result['warnings']:
                    if warning not in warnings:
                        warnings.append(warning)
                candidates = result['items']
                if not candidates:
                    item = empty_item(key[0], meal, '该餐次无符合当前条件和禁忌规则的候选；请补充适合该餐次的食谱，不以其他餐次替代。', result['excluded'])
                else:
                    ranked = list(enumerate(candidates))
                    _, selected = min(ranked, key=lambda pair:(pair[1]['recipe']['id'] == previous,
                                                               used[pair[1]['recipe']['id']], pair[0]))
                    selected = json.loads(canonical(selected))
                    identity = selected['recipe']['id']
                    repeated = used[identity] > 0
                    reasons = list(selected['reasons'])
                    if repeated:
                        reasons.append('合格食谱数量不足以覆盖全部餐次，本项明确重复使用；未跳过禁忌过滤。')
                    else:
                        reasons.append('在已通过硬过滤的候选中，优先避免相邻重复并减少本周重复，沿用原候选排序。')
                    item = selected | {'date':key[0], 'meal_type':meal, 'reasons':reasons,
                                       'repeated':repeated, 'usable':True, 'preserved':False}
            if item['recipe'] is not None:
                previous = item['recipe']['id']
                used[previous] += 1
            item.setdefault('feedback', pending_feedback())
            items.append(item)
    return items, warnings


def preview(path, data):
    with connect(path) as c:
        c.execute('BEGIN')
        value = context(c, data.start_date, data.selected_goal_ids)
        check_context(value, data.expected_context_hash, False)
        items, warnings = generate(c, data, value)
        # A public catalog release may be replaced outside the private SQLite
        # transaction; detect that race before publishing this preview.
        check_context(context(c, data.start_date, data.selected_goal_ids), value['context_hash'], False)
        return parameters(data) | context_summary(value) | {'can_save':not value['blockers'],
                    'blockers':value['blockers'], 'warnings':warnings, 'items':items, 'stats':statistics(items)}


def find_plan(c, id):
    require_weekly(c)
    row = c.execute('SELECT * FROM diet_weekly_plans WHERE id=? AND profile_id=1', (id,)).fetchone()
    if not row:
        raise LibraryError(404, 'WEEKLY_PLAN_NOT_FOUND', '周计划不存在或不属于当前档案')
    return dict(row)


def stored_items(c, id):
    result = []
    for row in c.execute('''SELECT i.*,f.status,f.revision AS feedback_revision,f.note,f.reason,
        f.actor_user_id AS feedback_actor,f.updated_at AS feedback_updated_at,
        EXISTS(SELECT 1 FROM diet_plan_feedback_history h WHERE h.item_id=i.id) AS ever_feedback
        FROM diet_plan_items i JOIN diet_plan_feedback f ON f.item_id=i.id AND f.profile_id=i.profile_id
        WHERE i.plan_id=? AND i.profile_id=1 ORDER BY i.position''', (id,)):
        snapshot = json.loads(row['snapshot_json'])
        result.append(snapshot | {'id':row['id'], 'date':row['plan_date'], 'meal_type':row['meal_type'],
            'generation_revision':row['generation_revision'],
            'generation_context_hash':row['generation_context_hash'],
            'generation_hard_fingerprint':row['generation_hard_fingerprint'],
            'ever_feedback':bool(row['ever_feedback']),
            'feedback':{'status':row['status'], 'revision':row['feedback_revision'], 'note':row['note'],
                        'reason':row['reason'], 'actor_user_id':row['feedback_actor'], 'updated_at':row['feedback_updated_at']}})
    return result


def shape_plan(c, row, current=None):
    current = current or context(c, row['start_date'], json.loads(row['selected_goal_ids_json']))
    items = stored_items(c, row['id'])
    changed = row['context_hash'] != current['context_hash']
    hard_changed = row['hard_fingerprint'] != current['hard_fingerprint'] or not current['confirmation_valid']
    today = business_today().isoformat()
    for item in items:
        item['historical'] = item['date'] < today
        item['context_changed'] = item['generation_context_hash'] != current['context_hash']
        item['hard_changed'] = item['generation_hard_fingerprint'] != current['hard_fingerprint'] or not current['confirmation_valid']
        item['usable'] = item['recipe'] is not None and (item['historical'] or
                         (not item['context_changed'] and not current['blockers']))
        item['refreshable'] = not item['historical'] and not item['ever_feedback']
    result = {key: row[key] for key in ('id','start_date','portions','revision','context_hash','hard_fingerprint',
               'profile_fingerprint','profile_updated_at','created_at','updated_at')}
    result.update(meal_ratios=json.loads(row['meal_ratios_json']), selected_goal_ids=json.loads(row['selected_goal_ids_json']),
                  current_context_hash=current['context_hash'], current_hard_fingerprint=current['hard_fingerprint'],
                  context_changed=changed, hard_changed=hard_changed, blockers=current['blockers'],
                  warnings=current['warnings'], items=items, stats=statistics(items),
                  notice='个人资料或推荐条件已更新，建议刷新未来食谱。已反馈及历史项目保留。' if changed else '')
    return result


def write_version(c, row, actor_id, stamp):
    payload = {key: row[key] for key in ('id','start_date','portions','revision','context_hash','hard_fingerprint',
                                      'profile_fingerprint','profile_updated_at')}
    payload.update(meal_ratios=json.loads(row['meal_ratios_json']), selected_goal_ids=json.loads(row['selected_goal_ids_json']),
                   items=stored_items(c, row['id']))
    c.execute('''INSERT INTO diet_plan_versions
        (plan_id,profile_id,revision,context_hash,hard_fingerprint,context_json,snapshot_json,actor_user_id,created_at)
        VALUES(?,1,?,?,?,?,?,?,?)''', (row['id'], row['revision'], row['context_hash'], row['hard_fingerprint'],
              row['context_json'], canonical(payload), actor_id, stamp))


def save(path, data, actor_id):
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        value = context(c, data.start_date, data.selected_goal_ids)
        check_context(value, data.expected_context_hash)
        items, warnings = generate(c, data, value)
        check_context(context(c, data.start_date, data.selected_goal_ids), value['context_hash'])
        stamp = utc_now()
        id = c.execute('''INSERT INTO diet_weekly_plans
            (profile_id,start_date,portions,meal_ratios_json,selected_goal_ids_json,revision,context_hash,
             hard_fingerprint,profile_fingerprint,profile_updated_at,context_json,created_by,updated_by,created_at,updated_at)
            VALUES(1,?,?,?,?,1,?,?,?,?,?,?,?,?,?)''',
            (data.start_date.isoformat(),data.portions,canonical(data.meal_ratios.model_dump()),canonical(sorted(data.selected_goal_ids)),
             value['context_hash'],value['hard_fingerprint'],value['profile_fingerprint'],value['profile_updated_at'],
             canonical(context_summary(value)),actor_id,actor_id,stamp,stamp)).lastrowid
        for position, item in enumerate(items):
            snapshot = {key: value for key, value in item.items() if key != 'feedback'}
            item_id = c.execute('''INSERT INTO diet_plan_items
                (profile_id,plan_id,position,plan_date,meal_type,snapshot_json,generation_context_hash,generation_hard_fingerprint,
                 generation_revision,created_at,updated_at) VALUES(1,?,?,?,?,?,?,?,1,?,?)''',
                (id,position,item['date'],item['meal_type'],canonical(snapshot),value['context_hash'],value['hard_fingerprint'],stamp,stamp)).lastrowid
            c.execute("INSERT INTO diet_plan_feedback(item_id,profile_id,status,updated_at) VALUES(?,1,'pending',?)", (item_id,stamp))
        row = find_plan(c, id)
        write_version(c, row, actor_id, stamp)
        result = shape_plan(c, row, value)
        result['warnings'] = warnings
        return result


def get(path, id):
    with connect(path) as c:
        c.execute('BEGIN')
        return shape_plan(c, find_plan(c, id))


def list_plans(path, limit=30, offset=0):
    with connect(path) as c:
        c.execute('BEGIN'); require_weekly(c)
        rows = c.execute('SELECT * FROM diet_weekly_plans WHERE profile_id=1 ORDER BY start_date DESC,id DESC LIMIT ? OFFSET ?', (limit,offset)).fetchall()
        items = []
        for row in rows:
            summary = shape_plan(c, dict(row))
            summary.pop('items')
            items.append(summary)
        return {'items':items, 'limit':limit, 'offset':offset,
                'total':c.execute('SELECT count(*) FROM diet_weekly_plans WHERE profile_id=1').fetchone()[0]}


def parameters_from_row(row, expected_hash):
    return PlanInput(start_date=row['start_date'], portions=row['portions'],
                     meal_ratios=json.loads(row['meal_ratios_json']),
                     selected_goal_ids=json.loads(row['selected_goal_ids_json']), expected_context_hash=expected_hash)


def prepare_refresh(c, id, data):
    row = find_plan(c, id)
    if row['revision'] != data.expected_plan_revision:
        conflict('WEEKLY_PLAN_REVISION_CONFLICT', '计划已被更新，请重新读取计划后刷新')
    request = parameters_from_row(row, data.expected_context_hash)
    value = context(c, request.start_date, request.selected_goal_ids)
    check_context(value, data.expected_context_hash)
    old = stored_items(c, id)
    today = business_today().isoformat()
    preserved = {(i['date'],i['meal_type']):i for i in old if i['date'] < today or i['ever_feedback']}
    if len(preserved) == 21:
        conflict('WEEKLY_PLAN_NOT_REFRESHABLE', '没有可刷新的未来未反馈项目；历史和所有已反馈项目保持不变')
    generated, warnings = generate(c, request, value, preserved)
    by_slot = {(i['date'],i['meal_type']):i for i in old}
    for item in generated:
        previous = by_slot[(item['date'],item['meal_type'])]
        item['id'] = previous['id']
        item['feedback'] = previous['feedback']
        item['ever_feedback'] = previous['ever_feedback']
        if item.get('preserved'):
            item['usable'] = item['recipe'] is not None and (item['date'] < today or
                             item['generation_context_hash'] == value['context_hash'])
    check_context(context(c, request.start_date, request.selected_goal_ids), value['context_hash'])
    return row, value, generated, warnings, preserved


def refresh_preview(path, id, data):
    with connect(path) as c:
        c.execute('BEGIN')
        row,value,items,warnings,preserved = prepare_refresh(c,id,data)
        return {'id':id, 'start_date':row['start_date'], 'revision':row['revision'], 'next_revision':row['revision']+1,
                'context_hash':value['context_hash'], 'hard_fingerprint':value['hard_fingerprint'],
                'profile_fingerprint':value['profile_fingerprint'], 'profile_updated_at':value['profile_updated_at'],
                'can_save':True, 'blockers':[], 'warnings':warnings, 'preserved_count':len(preserved),
                'refreshed_count':21-len(preserved), 'items':items, 'stats':statistics(items)}


def refresh(path, id, data, actor_id):
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        row,value,items,warnings,preserved = prepare_refresh(c,id,data)
        revision = row['revision'] + 1
        stamp = utc_now()
        c.execute('''UPDATE diet_weekly_plans SET revision=?,context_hash=?,hard_fingerprint=?,profile_fingerprint=?,
            profile_updated_at=?,context_json=?,updated_by=?,updated_at=? WHERE id=? AND profile_id=1''',
            (revision,value['context_hash'],value['hard_fingerprint'],value['profile_fingerprint'],value['profile_updated_at'],
             canonical(context_summary(value)),actor_id,stamp,id))
        for item in items:
            if (item['date'],item['meal_type']) in preserved:
                continue
            snapshot = {key: val for key,val in item.items() if key not in ('id','feedback','ever_feedback')}
            c.execute('''UPDATE diet_plan_items SET snapshot_json=?,generation_context_hash=?,generation_hard_fingerprint=?,
                generation_revision=?,updated_at=? WHERE id=? AND profile_id=1''',
                (canonical(snapshot),value['context_hash'],value['hard_fingerprint'],revision,stamp,item['id']))
        row = find_plan(c, id)
        write_version(c, row, actor_id, stamp)
        result = shape_plan(c, row, value)
        result.update(warnings=warnings, preserved_count=len(preserved), refreshed_count=21-len(preserved))
        return result


def find_item(c, id):
    require_weekly(c)
    row = c.execute('SELECT * FROM diet_plan_items WHERE id=? AND profile_id=1', (id,)).fetchone()
    if not row:
        raise LibraryError(404, 'WEEKLY_PLAN_ITEM_NOT_FOUND', '计划事项不存在或不属于当前档案')
    return dict(row)


def save_feedback(path, id, data, actor_id):
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        item = find_item(c,id)
        current = c.execute('SELECT * FROM diet_plan_feedback WHERE item_id=? AND profile_id=1', (id,)).fetchone()
        if current['revision'] != data.expected_revision:
            conflict('WEEKLY_FEEDBACK_REVISION_CONFLICT', '反馈已被更新，请重新读取后保存')
        snapshot = json.loads(item['snapshot_json'])
        if snapshot['recipe'] is None and data.status not in ('pending','not_applicable'):
            raise LibraryError(422, 'WEEKLY_PLAN_NO_CANDIDATE', '本项没有食谱候选，仅可标记未反馈或不适用')
        plan = find_plan(c, item['plan_id'])
        revision = current['revision'] + 1
        stamp = utc_now()
        c.execute('''INSERT INTO diet_plan_feedback_history
            (item_id,profile_id,revision,plan_revision_at_submission,item_generation_revision,status,note,reason,actor_user_id,created_at)
            VALUES(?,1,?,?,?,?,?,?,?,?)''', (id,revision,plan['revision'],item['generation_revision'],data.status,data.note,data.reason,actor_id,stamp))
        c.execute('''UPDATE diet_plan_feedback SET revision=?,status=?,note=?,reason=?,actor_user_id=?,updated_at=?
            WHERE item_id=? AND profile_id=1''', (revision,data.status,data.note,data.reason,actor_id,stamp,id))
        # A refresh preview also depends on which items have ever received
        # feedback. Advance the whole-plan CAS token so concurrent feedback
        # cannot silently change the scope of an already reviewed refresh.
        c.execute('''UPDATE diet_weekly_plans SET revision=revision+1,updated_by=?,updated_at=?
            WHERE id=? AND profile_id=1''', (actor_id,stamp,item['plan_id']))
        updated_plan = find_plan(c,item['plan_id'])
        write_version(c,updated_plan,actor_id,stamp)
        feedback = {key: val for key,val in dict(c.execute('SELECT * FROM diet_plan_feedback WHERE item_id=?',(id,)).fetchone()).items()
                    if key not in ('profile_id','item_id')}
        return {'feedback':feedback, 'stats':statistics(stored_items(c,item['plan_id'])),
                'plan_id':item['plan_id'], 'plan_revision':updated_plan['revision'],
                'notice':'反馈只记录计划执行情况，未创建或修改实际饮食摄入记录。'}


def feedback_history(path, id):
    with connect(path) as c:
        c.execute('BEGIN'); find_item(c,id)
        return {'items':[dict(row) for row in c.execute('''SELECT id,item_id,revision,plan_revision_at_submission,
            item_generation_revision,status,note,reason,actor_user_id,created_at FROM diet_plan_feedback_history
            WHERE item_id=? AND profile_id=1 ORDER BY revision DESC''',(id,))]}


def versions(path, id):
    with connect(path) as c:
        c.execute('BEGIN'); find_plan(c,id)
        return {'items':[{'revision':row['revision'], 'context_hash':row['context_hash'],
                         'hard_fingerprint':row['hard_fingerprint'], 'created_at':row['created_at'],
                         'actor_user_id':row['actor_user_id'], 'snapshot':json.loads(row['snapshot_json'])}
                        for row in c.execute('SELECT * FROM diet_plan_versions WHERE plan_id=? AND profile_id=1 ORDER BY revision DESC',(id,))]}
