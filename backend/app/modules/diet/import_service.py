"""Atomic append-only import. Dry runs use SQLite mode=ro/query_only.

No schema creation, profile creation, archive restoration or algorithm changes.
"""
import csv
import io
import json
import os
import sqlite3
import tempfile
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from pydantic import ValidationError
from app.modules.diet import library_service as library, recipe_service as recipes
from app.modules.diet.library_schemas import FoodInput
from app.modules.diet.recipe_schemas import RecipeInput
from app.modules.diet.import_schemas import Manifest, Food, Recipe, Ingredient
from app.modules.diet.source_mapping import (ImportRejected, canonical, digest, sha, json_read,
                                            verified_bytes, verify_foods, FIELDS)

MARKER = '\nHAIMPORT1:'

def verify_review_state(manifest, foods, recipe_items):
    """Pending candidates are never an approval; old approved previews stay readable."""
    states = [manifest.review_status, *(f.review_status for f in foods),
              *(r.review_status for r in recipe_items)]
    if manifest.purpose != 'temporary_review' and any(s != 'approved' for s in states):
        raise ImportRejected('待最终确认记录仅可用于temporary_review，不能用于正式导入')
    if manifest.purpose == 'temporary_review' and len(set(states)) != 1:
        raise ImportRejected('临时审核包清单与记录的审核状态必须一致，不得混合批准状态')

def _no_bools(value):
    if isinstance(value, bool):
        raise ImportRejected('不接受布尔值替代数字')
    if isinstance(value, dict):
        for v in value.values(): _no_bools(v)
    if isinstance(value, list):
        for v in value: _no_bools(v)

def _csv(data, fields, numbers=(), integers=(), nullable=()):
    reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline=''))
    if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames) or set(reader.fieldnames) != set(fields):
        raise ImportRejected('CSV列缺失、重复或含未知列')
    rows = []
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ImportRejected('CSV列数不一致')
        for k, value in list(row.items()):
            if value == '' and k in nullable: row[k] = None
            elif k in integers:
                if not value.isascii() or not value.isdecimal(): raise ImportRejected('CSV整数非法：' + k)
                row[k] = int(value)
            elif k in numbers:
                try: row[k] = float(value)
                except ValueError as e: raise ImportRejected('CSV数值非法：' + k) from e
        rows.append(row)
    return rows

def load_package(root, *, expected_manifest_sha256=None, allow_test_fixtures=False, allow_temporary_review=False, allow_course_demo=False):
    root = Path(root).resolve()
    raw = (root / 'manifest.json').read_bytes()
    manifest_sha = sha(raw)
    if expected_manifest_sha256 is not None and expected_manifest_sha256 != manifest_sha:
        raise ImportRejected('审核manifest SHA256不符')
    obj = json_read(raw); _no_bools(obj)
    manifest = Manifest.model_validate(obj)
    if manifest.purpose == 'course_demo' and not allow_course_demo:
        raise ImportRejected('课程演示批准不代表正式用途批准；仅允许专用演示入口')
    if manifest.purpose == 'test_fixture' and not allow_test_fixtures:
        raise ImportRejected('测试夹具不能作为真实数据包导入')
    if manifest.purpose == 'temporary_review' and not allow_temporary_review:
        raise ImportRejected('临时审核包尚未经用户确认，不能作为正式导入包')
    for document in manifest.documentation:
        verified_bytes(root, document)
    for stamp in [manifest.reviewed_at, *(s.retrieved_at for s in manifest.sources)]:
        try: dt = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        except ValueError as e: raise ImportRejected('审核/获取时间必须为ISO8601') from e
        if dt.tzinfo is None: raise ImportRejected('审核/获取时间必须包含时区')
    expected = {'foods', 'recipes'} if manifest.format == 'json' else {'foods', 'recipes', 'ingredients', 'steps'}
    if set(manifest.files) != expected:
        raise ImportRejected('数据包文件清单不完整或存在未知文件')
    blobs = {k: verified_bytes(root, ref) for k, ref in manifest.files.items()}
    if manifest.format == 'json':
        food_rows, recipe_rows = json_read(blobs['foods']), json_read(blobs['recipes'])
        if not isinstance(food_rows, list) or not isinstance(recipe_rows, list):
            raise ImportRejected('foods/recipes必须为数组')
    else:
        food_rows = _csv(blobs['foods'], Food.model_fields, FIELDS, ('fdc_id', 'basis_g'), FIELDS)
        recipe_rows = _csv(blobs['recipes'], set(Recipe.model_fields)-{'ingredients', 'steps'},
                           ('servings',), ('recipe_version', 'preparation_minutes'), ('preparation_minutes', 'time_evidence'))
        ingredients = _csv(blobs['ingredients'], ('recipe_key','position','food_source_key','amount_g'), ('amount_g',), ('position',))
        steps = _csv(blobs['steps'], ('recipe_key','position','instruction'), (), ('position',))
        keys = {r['recipe_key'] for r in recipe_rows}
        if any(r['recipe_key'] not in keys for r in ingredients + steps):
            raise ImportRejected('CSV存在孤立配料或步骤')
        for recipe in recipe_rows:
            for rows, dest in ((ingredients, 'ingredients'), (steps, 'steps')):
                selected = sorted((r for r in rows if r['recipe_key']==recipe['recipe_key']), key=lambda r:r['position'])
                if [r['position'] for r in selected] != list(range(1, len(selected)+1)):
                    raise ImportRejected('CSV顺序必须唯一且连续')
                recipe[dest] = ([{'food_source_key':r['food_source_key'],'amount_g':r['amount_g']} for r in selected]
                                if dest=='ingredients' else [r['instruction'] for r in selected])
    _no_bools(food_rows); _no_bools(recipe_rows)
    foods = [Food.model_validate(r) for r in food_rows]
    recipe_items = [Recipe.model_validate(r) for r in recipe_rows]
    verify_review_state(manifest, foods, recipe_items)
    keys = {f.source_key for f in foods}
    if len(keys) != len(foods) or len({r.recipe_key for r in recipe_items}) != len(recipe_items):
        raise ImportRejected('数据包来源身份重复')
    if any(i.food_source_key not in keys for r in recipe_items for i in r.ingredients):
        raise ImportRejected('菜谱引用未审核或未包含的食物')
    evidence = verify_foods(root, manifest, foods)
    return {'manifest': manifest, 'manifest_sha256': manifest_sha, 'foods': foods,
            'recipes': recipe_items, 'evidence': evidence}

@contextmanager
def database(path, *, write=False):
    path = Path(path).resolve(strict=True)
    c = sqlite3.connect(path.as_uri() + ('?mode=rw' if write else '?mode=ro'), uri=True, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        c.execute('PRAGMA foreign_keys=ON')
        if not write: c.execute('PRAGMA query_only=ON')
        with c:
            c.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield c
    finally:
        c.close()

def snapshot(c):
    result = {}
    for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        name = r[0]
        quoted = '"' + name.replace('"', '""') + '"'
        result[name] = sorted(canonical(dict(row)) for row in c.execute('SELECT * FROM ' + quoted))
    return result

def marker(row):
    note = row['source_note']
    if MARKER not in note: return None
    try:
        m = json_read(note.split(MARKER)[-1])
        if set(m) != {'key','content_sha256','run_id'}: raise ValueError()
        if any(not isinstance(m[k], str) or not m[k] for k in m): raise ValueError()
        return m
    except (ValueError, TypeError) as e:
        raise ImportRejected('已有记录来源标记损坏，停止导入') from e

def note(prefix, key, content, run_id):
    return prefix + MARKER + canonical({'key':key, 'content_sha256':digest(content), 'run_id':run_id})

def food_payload(f, run_id, category_id=None):
    prefix = f'USDA FoodData Central | FDC {f.fdc_id} | {f.original_english_name}'
    return FoodInput(name=f.name_zh, category_id=category_id, source_type='referenced', source_url=f.source_url,
                     source_note=note(prefix, f.source_key, f.model_dump(), run_id), **{k:getattr(f,k) for k in FIELDS})

def recipe_payload(r, run_id, food_ids, category_id=None):
    return RecipeInput(name=r.name, category_id=category_id, description=r.description,
                       servings=r.servings, preparation_minutes=r.preparation_minutes, nutrition_mode='calculated',
                       source_type='user_entered', source_note=note(r.source_note, r.recipe_key, r.model_dump(), run_id),
                       ingredients=[{'food_id':food_ids[i.food_source_key], 'amount_g':i.amount_g} for i in r.ingredients], steps=r.steps)

def _category(c, table, name, create=False):
    normalized = recipes.key(name) if table == 'diet_recipe_categories' else name.casefold()
    found = c.execute('SELECT id FROM '+table+' WHERE profile_id=1 AND name_key=?',(normalized,)).fetchone()
    if found: return found[0]
    if not create: return None
    now = datetime.now(timezone.utc).isoformat()
    return c.execute('INSERT INTO '+table+'(profile_id,name,name_key,created_at,updated_at) VALUES(1,?,?,?,?)',
                     (name,normalized,now,now)).lastrowid

def _same_food(c, row, food, meta):
    if row['deleted_at'] is not None: return False
    payload = food_payload(food, meta['run_id'], _category(c,'food_categories',food.category)).model_dump()
    return payload['category_id'] is not None and row['is_example']==0 and all(row[k]==v for k,v in payload.items())

def _same_recipe(c, row, recipe, meta, ids):
    if row['archived_at'] is not None: return False
    if any(i.food_source_key not in ids for i in recipe.ingredients): return False
    payload = recipe_payload(recipe, meta['run_id'], ids, _category(c,'diet_recipe_categories',recipe.category)).model_dump()
    detail = recipes.detail(c,row['id'])
    if detail['snapshot_outdated'] or payload['category_id'] is None: return False
    if any(detail[k]!=v for k,v in payload.items() if k not in ('ingredients','steps','revision')): return False
    if detail['steps'] != payload['steps']: return False
    expected = payload['ingredients']
    if [{k:i[k] for k in ('food_id','amount_g')} for i in detail['ingredients']] != expected: return False
    for ingredient in detail['ingredients']:
        f = library.food_row(c,ingredient['food_id'])
        if any(ingredient[k+'_snapshot']!=f[k] for k in FIELDS): return False
        if ingredient['food_name_snapshot']!=f['name'] or ingredient['is_example']!=f['is_example']: return False
        if json_read(ingredient['source_snapshot']) != {k:f[k] for k in ('source_type','source_note','source_url')}: return False
    return True

def plan(c, package, path):
    recipes.require_recipes(c)
    if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchone():
        raise ImportRejected('目标数据库完整性/外键检查失败')
    before = snapshot(c)
    result = {'database':str(Path(path).resolve()), 'manifest_sha256':package['manifest_sha256'],
              'database_sha256':digest(before), 'items':[], 'counts':{'add':0,'skip':0,'conflict':0}, 'food_ids':{}}
    for kind, table, data in (('food','food_items',package['foods']), ('recipe','diet_recipes',package['recipes'])):
        rows = [dict(r) for r in c.execute('SELECT * FROM '+table+' WHERE profile_id=1')]
        identities = {}
        for row in rows:
            m = marker(row)
            if m: identities.setdefault(m['key'], []).append((row,m))
        for item in data:
            key = item.source_key if kind=='food' else item.recipe_key
            # Validate note length and API constraints even in a dry run.
            if kind=='food': food_payload(item, 'preview')
            else: recipe_payload(item, 'preview', {i.food_source_key:n+1 for n,i in enumerate(item.ingredients)})
            matches = identities.get(key, [])
            action, reason, row_id = 'add', '新增来源身份', None
            if kind=='food' and any(not marker(r) and r['source_url']==item.source_url for r in rows):
                action,reason='conflict','已有用户来源记录，不能自动接管'
            elif len(matches)>1: action,reason='conflict','数据库存在重复来源身份'
            elif matches:
                row,m = matches[0];row_id=row['id']
                same = m['content_sha256']==digest(item.model_dump())
                same = same and (_same_food(c,row,item,m) if kind=='food' else _same_recipe(c,row,item,m,result['food_ids']))
                action,reason=('skip','来源及当前内容一致') if same else ('conflict','已归档或内容/快照发生变化，禁止覆盖')
            if kind=='food' and action=='skip': result['food_ids'][key]=row_id
            result['items'].append({'kind':kind,'key':key,'name':item.name_zh if kind=='food' else item.name,
                                    'action':action,'reason':reason,'id':row_id,'content_sha256':digest(item.model_dump())})
            result['counts'][action]+=1
    result['plan_sha256']=digest(result)
    return result

def verify_audit_history(c, audit_dir, path, package):
    """Keep the external ledger across runs; a removed source marker is a conflict."""
    if audit_dir is None or not Path(audit_dir).exists(): return
    target=str(Path(path).resolve())
    keys={f.source_key for f in package['foods']} | {r.recipe_key for r in package['recipes']}
    for pending in Path(audit_dir).glob('*.pending.json'):
        previous=json_read(pending.read_bytes())
        if previous['preview']['database']!=target: continue
        stem=str(pending)[:-len('.pending.json')]
        committed=Path(stem+'.committed.json');failed=Path(stem+'.failed.json')
        if not committed.exists():
            if failed.exists(): continue
            raise ImportRejected('存在结果未确认的pending审计，须先只读核对：'+pending.name)
        report=json_read(committed.read_bytes())
        for saved in report['added']:
            if saved['key'] not in keys: continue
            table=saved['table']
            if table not in ('food_items','diet_recipes'):raise ImportRejected('历史审计表名非法')
            row=c.execute('SELECT * FROM '+table+' WHERE id=? AND profile_id=1',(saved['id'],)).fetchone()
            m=marker(row) if row else None
            if not row or row['created_at']!=saved['created_at'] or not m or m['key']!=saved['key'] or m['run_id']!=report['run_id']:
                raise ImportRejected('历史导入身份已删除或被改写，不能重新新增：'+saved['key'])

def dry_run(path, package, audit_dir=None):
    with database(path) as c:
        verify_audit_history(c,audit_dir,path,package)
        return plan(c,package,path)

def write_audit(path, payload):
    # Exclusive creation; flushed before any database write. Audit stages are separate immutable files.
    with Path(path).open('x', encoding='utf-8') as out:
        out.write(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False))
        out.flush();os.fsync(out.fileno())

def apply_package(path, package, audit_dir, *, expected_plan_sha256, allow_course_demo=False):
    # Recheck at the write boundary, including callers holding a previously loaded package.
    verify_review_state(package['manifest'], package['foods'], package['recipes'])
    if package['manifest'].purpose == 'course_demo' and not allow_course_demo:
        raise ImportRejected('课程演示数据不得通过普通正式导入入口写入')
    if package['manifest'].purpose != 'reviewed_data':
        target=Path(path).resolve()
        if not target.is_relative_to(Path(tempfile.gettempdir()).resolve()) or target.name=='health.db':
            raise ImportRejected('非正式数据包仅允许独立系统临时目录数据库')
    audit_dir=Path(audit_dir).resolve();audit_dir.mkdir(parents=True,exist_ok=True)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex
    prefix=audit_dir/run_id
    with database(path,write=True) as c:
        verify_audit_history(c,audit_dir,path,package)
        preview=plan(c,package,path)
        if preview['plan_sha256']!=expected_plan_sha256:
            raise ImportRejected('数据库或数据包已改变，请重新dry-run审核')
        if preview['counts']['conflict']: raise ImportRejected('存在冲突，整批拒绝')
        before=snapshot(c)
        audit={'run_id':run_id,'started_at':datetime.now(timezone.utc).isoformat(),'preview':preview,
               'source_manifest':package['manifest'].model_dump(),'source_evidence':package['evidence']}
        write_audit(str(prefix)+'.pending.json',audit|{'status':'pending'})
        ids=dict(preview['food_ids']);recipe_ids={};added=[]
        actions={(r['kind'],r['key']):r for r in preview['items']}
        try:
            for f in package['foods']:
                if actions['food',f.source_key]['action']=='skip': continue
                cat=_category(c,'food_categories',f.category,True)
                row=library.save_food_in_connection(c,food_payload(f,run_id,cat));ids[f.source_key]=row['id']
                added.append({'table':'food_items','key':f.source_key,'id':row['id'],'created_at':row['created_at']})
            for r in package['recipes']:
                action=actions['recipe',r.recipe_key]
                if action['action']=='skip': recipe_ids[r.recipe_key]=action['id'];continue
                cat=_category(c,'diet_recipe_categories',r.category,True)
                row=recipes.save_in_connection(c,recipe_payload(r,run_id,ids,cat));recipe_ids[r.recipe_key]=row['id']
                added.append({'table':'diet_recipes','key':r.recipe_key,'id':row['id'],'created_at':row['created_at']})
            after=snapshot(c)
            if set(after)!=set(before): raise ImportRejected('导入不得修改数据库表结构')
            append_tables={'food_categories','food_items','diet_recipe_categories','diet_recipes','diet_recipe_ingredients','diet_recipe_steps'}
            for table, rows in before.items():
                if table=='sqlite_sequence': continue
                if table in append_tables:
                    if Counter(rows)-Counter(after[table]): raise ImportRejected('原有行发生变化：'+table)
                elif rows!=after[table]: raise ImportRejected('非导入业务表发生变化：'+table)
            if c.execute('PRAGMA foreign_key_check').fetchone(): raise ImportRejected('导入后外键失败')
            if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ImportRejected('导入后完整性失败')
            # Commit here so a failed commit is caught and explicitly rolled back.
            c.commit()
        except Exception as error:
            c.rollback()
            write_audit(str(prefix)+'.failed.json',audit|{'status':'rolled_back','error':str(error)})
            raise
    result=audit|{'status':'committed','finished_at':datetime.now(timezone.utc).isoformat(),
                  'added':added,'food_ids':ids,'recipe_ids':recipe_ids,'database_after_sha256':digest(after)}
    try: write_audit(str(prefix)+'.committed.json',result)
    except OSError as error:
        raise ImportRejected('数据库已提交但完成审计写入失败；保留pending，须只读核对run_id='+run_id+'，不要盲目重试或恢复') from error
    return result
