import json
import unicodedata
from app.database import connect
from app.modules.diet.library_service import LibraryError, food_row
from app.modules.diet.service import require_profile
from app.modules.diet.migration_004 import ready
from app.modules.diet.settings import utc_now
from app.modules.diet.nutrition_math import NUTRIENTS, PER100, scale, total

def key(value): return unicodedata.normalize('NFKC',value).strip().casefold()
def require_recipes(c):
    require_profile(c)
    if not ready(c): raise LibraryError(503,'RECIPES_MIGRATION_REQUIRED','食谱模块尚未启用，请备份并经授权完成004迁移；原饮食功能不受影响')
def conflict(): raise LibraryError(409,'REVISION_CONFLICT','数据已变更，请重新读取后再保存')
def one(c,table,id,active=False):
    # table names are internal constants only, never request inputs.
    r=c.execute('SELECT * FROM '+table+' WHERE id=? AND profile_id=1'+(' AND archived_at IS NULL' if active else ''),(id,)).fetchone()
    if not r: raise LibraryError(404,'RECIPE_RESOURCE_NOT_FOUND','食谱资源不存在或已归档')
    return dict(r)
def categories(path):
    with connect(path) as c:
        require_recipes(c);return {'items':[dict(r) for r in c.execute('SELECT * FROM diet_recipe_categories WHERE profile_id=1 ORDER BY name_key,id')]}
def category(path,id):
    with connect(path) as c: require_recipes(c);return one(c,'diet_recipe_categories',id)
def save_category(path,data,id=None):
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE');require_recipes(c)
        if id is not None: one(c,'diet_recipe_categories',id)
        exists=c.execute('SELECT id FROM diet_recipe_categories WHERE profile_id=1 AND name_key=?',(key(data.name),)).fetchone()
        if exists and exists[0]!=id: raise LibraryError(409,'CATEGORY_EXISTS','食谱分类名称已存在')
        now=utc_now()
        if id is None: id=c.execute('INSERT INTO diet_recipe_categories(profile_id,name,name_key,created_at,updated_at) VALUES(1,?,?,?,?)',(data.name,key(data.name),now,now)).lastrowid
        else: c.execute('UPDATE diet_recipe_categories SET name=?,name_key=?,updated_at=? WHERE id=?',(data.name,key(data.name),now,id))
        return one(c,'diet_recipe_categories',id)
def delete_category(path,id):
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE');require_recipes(c);one(c,'diet_recipe_categories',id)
        if c.execute('SELECT 1 FROM diet_recipes WHERE profile_id=1 AND category_id=? AND archived_at IS NULL',(id,)).fetchone():
            raise LibraryError(409,'CATEGORY_IN_USE','分类仍被有效食谱使用')
        c.execute('UPDATE diet_recipes SET category_id=NULL WHERE profile_id=1 AND category_id=?',(id,))
        c.execute('DELETE FROM diet_recipe_categories WHERE id=? AND profile_id=1',(id,))
def nutrition(recipe,portions=None):
    factor=(portions if portions is not None else recipe['servings'])/recipe['servings']
    result={}
    for nutrient,per100 in zip(NUTRIENTS,PER100):
        if recipe['nutrition_mode']=='manual':
            value=recipe['manual_'+nutrient]
            result[nutrient]={'total':None if value is None else scale(value,factor*100),'known_sum':None if value is None else scale(value,factor*100),'unknown_count':int(value is None),'complete':value is not None}
        else:
            values=[scale(i[per100+'_snapshot'],i['amount_g']*factor) for i in recipe['ingredients']]
            known=[v for v in values if v is not None];missing=len(values)-len(known)
            result[nutrient]={'total':total(known) if not missing else None,'known_sum':total(known) if known else None,'unknown_count':missing,'complete':missing==0}
    return result
def detail(c,id):
    r=one(c,'diet_recipes',id,True)
    r['ingredients']=[dict(x) for x in c.execute('SELECT i.*,f.deleted_at AS food_archived_at,f.updated_at AS current_food_updated_at FROM diet_recipe_ingredients i JOIN food_items f ON f.id=i.food_id AND f.profile_id=i.profile_id WHERE i.recipe_id=? AND i.profile_id=1 ORDER BY position',(id,))]
    r['steps']=[x[0] for x in c.execute('SELECT instruction FROM diet_recipe_steps WHERE recipe_id=? AND profile_id=1 ORDER BY position',(id,))]
    r['is_example']=r['source_type']=='example' or any(i['is_example'] for i in r['ingredients'])
    r['nutrition']=nutrition(r);r['per_serving']=nutrition(r,1)
    r['snapshot_outdated']=any(i['food_updated_at_snapshot']!=i['current_food_updated_at'] for i in r['ingredients'])
    return r
def get(path,id):
    with connect(path) as c: require_recipes(c);return detail(c,id)
def recipes(path,q='',category_id=None):
    with connect(path) as c:
        c.execute('BEGIN');require_recipes(c)
        sql='SELECT id FROM diet_recipes WHERE profile_id=1 AND archived_at IS NULL';args=[]
        if q: sql+=' AND instr(lower(name),lower(?))>0';args.append(q)
        if category_id is not None: sql+=' AND category_id=?';args.append(category_id)
        return {'items':[detail(c,r[0]) for r in c.execute(sql+' ORDER BY updated_at DESC,id DESC',args).fetchall()]}
def save(path,data,id=None,refresh=False):
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        return save_in_connection(c,data,id,refresh)

def save_in_connection(c,data,id=None,refresh=False):
    """Caller owns commit/rollback, including imported ingredient snapshots."""
    require_recipes(c)
    old=detail(c,id) if id is not None else None
    if old and data.revision!=old['revision']: conflict()
    if data.category_id: one(c,'diet_recipe_categories',data.category_id)
    now=utc_now();values=data.model_dump(exclude={'ingredients','steps','revision'})
    if id is None:
        values.update(profile_id=1,created_at=now,updated_at=now)
        id=c.execute('INSERT INTO diet_recipes('+','.join(values)+') VALUES('+','.join(':'+k for k in values)+')',values).lastrowid
    else:
        values.update(updated_at=now,revision=old['revision']+1)
        c.execute('UPDATE diet_recipes SET '+','.join(k+'=:'+k for k in values)+' WHERE id=:id AND profile_id=1',values|{'id':id})
    previous={i['food_id']:i for i in old['ingredients']} if old else {}
    new=[]
    for pos,item in enumerate(data.ingredients,1):
        prior=previous.get(item.food_id)
        if prior and not refresh:
            snapshot={k:v for k,v in prior.items() if k.endswith('_snapshot') or k=='is_example'}
        else:
            food=food_row(c,item.food_id)
            snapshot={k+'_snapshot':food[k] for k in PER100}
            snapshot.update(food_name_snapshot=food['name'],food_updated_at_snapshot=food['updated_at'],source_snapshot=json.dumps({k:food[k] for k in ('source_type','source_note','source_url')},ensure_ascii=False),is_example=food['is_example'])
        new.append(snapshot|{'profile_id':1,'recipe_id':id,'food_id':item.food_id,'amount_g':item.amount_g,'position':pos})
    c.execute('DELETE FROM diet_recipe_ingredients WHERE recipe_id=? AND profile_id=1',(id,))
    c.execute('DELETE FROM diet_recipe_steps WHERE recipe_id=? AND profile_id=1',(id,))
    for v in new: c.execute('INSERT INTO diet_recipe_ingredients('+','.join(v)+') VALUES('+','.join(':'+k for k in v)+')',v)
    c.executemany('INSERT INTO diet_recipe_steps(profile_id,recipe_id,position,instruction) VALUES(1,?,?,?)',[(id,pos,s) for pos,s in enumerate(data.steps,1)])
    return detail(c,id)

def refresh(path,id,data):
    from app.modules.diet.recipe_schemas import RecipeInput
    r=get(path,id)
    payload={k:r[k] for k in RecipeInput.model_fields if k in r}
    payload['ingredients']=[{k:i[k] for k in ('food_id','amount_g')} for i in r['ingredients']]
    payload['revision']=data.revision
    return save(path,RecipeInput(**payload),id,True)
def archive(path,id):
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE');require_recipes(c);one(c,'diet_recipes',id,True)
        now=utc_now();c.execute('UPDATE diet_recipes SET archived_at=?,updated_at=?,revision=revision+1 WHERE id=? AND profile_id=1',(now,now,id))
