"""User-owned references to public immutable sources. No bulk user-data import."""
import json
from app.database import connect
from app.modules.diet import catalog_repository as catalog
from app.modules.diet.library_service import LibraryError
from app.modules.diet.migration_006 import ready
from app.modules.diet.settings import utc_now
from app.modules.diet.nutrition_math import PER100

def link(c,food_id):
    if not c.execute("SELECT 1 FROM sqlite_master WHERE name='diet_catalog_food_links'").fetchone(): return None
    row=c.execute('SELECT * FROM diet_catalog_food_links WHERE food_id=? AND profile_id=1',(food_id,)).fetchone()
    return dict(row) if row else None

def assert_editable(c,food_id):
    if link(c,food_id): raise LibraryError(403,'PUBLIC_FOOD_READ_ONLY','公共参考数据不能修改或归档；请另建我的食物')

def annotate(c,row):
    origin=link(c,row['id'])
    return row|({'origin':'public','editable':False,'food_key':origin['food_key']} if origin else {'origin':'private','editable':True})

def require_links(c):
    if not ready(c): raise LibraryError(503,'CATALOG_LINK_MIGRATION_REQUIRED','请先显式完成006公共目录关联迁移')
    if not c.execute('SELECT 1 FROM profiles WHERE id=1').fetchone(): raise LibraryError(409,'PROFILE_REQUIRED','请先建立个人档案')

def ensure_food(c,key):
    require_links(c)
    f=catalog.foods(key=key)
    existing=c.execute('SELECT food_id,record_sha256 FROM diet_catalog_food_links WHERE profile_id=1 AND food_key=?',(key,)).fetchone()
    if existing:
        if existing['record_sha256']!=f['record_sha256']:
            raise LibraryError(409,'CATALOG_REFERENCE_STALE','公共食品版本变化，请经审核升级引用；旧历史快照保持不变')
        return existing['food_id']
    now=utc_now()
    values={'profile_id':1,'category_id':None,'name':f['name'],'source_type':'referenced','source_note':catalog.NOTICE+'\nFDC: '+key,'source_url':f['source_url'],'is_example':0,'created_at':now,'updated_at':now}
    values.update({k:f[k] for k in PER100})
    id=c.execute('INSERT INTO food_items('+','.join(values)+') VALUES('+','.join(':'+k for k in values)+')',values).lastrowid
    c.execute('INSERT INTO diet_catalog_food_links VALUES (?,?,?,?,?,?)',(id,1,key,catalog.metadata()['release_id'],f['record_sha256'],now))
    return id

def reference(path,key):
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        id=ensure_food(c,key)
        return annotate(c,dict(c.execute('SELECT * FROM food_items WHERE id=?',(id,)).fetchone()))

def copy_recipe(path,key):
    from app.modules.diet.recipe_service import save_in_connection
    from app.modules.diet.recipe_schemas import RecipeInput
    r=catalog.recipes(key=key)
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE'); require_links(c)
        ingredients=[{'food_id':ensure_food(c,i['food_source_key']),'amount_g':i['amount_g']} for i in r['ingredients']]
        payload=RecipeInput(name=r['name'],description=r['description'],servings=r['servings'],preparation_minutes=r['preparation_minutes'],ingredients=ingredients,steps=r['steps'],source_type='referenced',source_note=r['source_note']+'；此副本属于我的食谱，后续修改不自动获得课程审批。',source_url='')
        result=save_in_connection(c,payload)
        c.execute('INSERT INTO diet_catalog_recipe_origins VALUES (?,?,?,?,?,?)',(result['id'],1,key,catalog.metadata()['release_id'],r['record_sha256'],utc_now()))
        return result

def source_identity(c,food_id):
    """Conservative same-source hard rules, including old imported snapshots.

    Exact FDC URLs and import markers are identity claims, never approval proof.
    Matching them can only extend exclusions, never grant safety approval.
    """
    import re
    bound=link(c,food_id)
    if bound: return bound['food_key']
    row=c.execute('SELECT source_url,source_note FROM food_items WHERE id=? AND profile_id=1',(food_id,)).fetchone()
    if not row:return None
    match=re.fullmatch(r'https://fdc\.nal\.usda\.gov/food-details/([0-9]+)/nutrients/?',row['source_url'])
    if match:return 'usda:fdc:'+match[1]
    if '\nHAIMPORT1:' in row['source_note']:
        try:
            marker=json.loads(row['source_note'].split('\nHAIMPORT1:')[-1])
            if not isinstance(marker,dict): return None
            key=marker.get('key',marker.get('source_key'))
            if isinstance(key,str) and re.fullmatch(r'usda:fdc:[0-9]+',key):return key
        except (ValueError,TypeError):pass
    return None

def public_recipe(r,foods):
    """Adapt immutable payload to the existing nutrient calculator/ranker."""
    ingredients=[]
    for n,i in enumerate(r['ingredients'],1):
        f=foods[i['food_source_key']]
        ingredients.append({'food_id':f['food_key'],'food_key':f['food_key'],'food_name_snapshot':f['name'],'amount_g':i['amount_g'],'position':n,'food_archived_at':None,'is_example':False,**{k+'_snapshot':f[k] for k in PER100}})
    result=r|{'id':r['recipe_key'],'category_id':r['category_key'],'revision':r['recipe_version'],'nutrition_mode':'calculated','ingredients':ingredients,'is_example':False,'snapshot_outdated':False,'source_type':'referenced','source_url':'','origin':'public'}
    from app.modules.diet.recipe_service import nutrition
    return result|{'nutrition':nutrition(result),'per_serving':nutrition(result,1)}
