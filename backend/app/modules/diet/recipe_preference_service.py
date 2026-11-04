import sqlite3
from contextlib import contextmanager
from app.database import connect
from app.modules.diet.recipe_service import require_recipes,one,key,conflict
from app.modules.diet.library_service import food_row,LibraryError
from app.modules.diet.settings import utc_now

@contextmanager
def transaction(path):
    try:
        with connect(path) as c:
            c.execute('BEGIN IMMEDIATE');require_recipes(c);yield c
    except sqlite3.IntegrityError as e:
        raise LibraryError(409,'RECIPE_RESOURCE_CONFLICT','名称、别名或规则已存在，或资源仍被引用') from e

def inventory(path,id=None):
    with connect(path) as c:
        require_recipes(c)
        if id is not None:return one(c,'diet_inventory_items',id)
        return {'items':[dict(r) for r in c.execute('SELECT i.*,f.name AS food_name,f.deleted_at AS food_archived_at FROM diet_inventory_items i JOIN food_items f ON i.food_id=f.id AND i.profile_id=f.profile_id WHERE i.profile_id=1 ORDER BY i.updated_at DESC,i.id DESC')]}
def save_inventory(path,data,id=None):
    with transaction(path) as c:
        old=one(c,'diet_inventory_items',id) if id is not None else None
        if old and old['revision']!=data.revision:conflict()
        food_row(c,data.food_id);now=utc_now();v=data.model_dump(exclude={'revision'})|{'updated_at':now}
        if old:
            c.execute('UPDATE diet_inventory_items SET food_id=:food_id,quantity_g=:quantity_g,notes=:notes,updated_at=:updated_at,revision=revision+1 WHERE id=:id AND profile_id=1',v|{'id':id})
        else:
            id=c.execute('INSERT INTO diet_inventory_items(profile_id,food_id,quantity_g,notes,updated_at,created_at) VALUES(1,:food_id,:quantity_g,:notes,:updated_at,:updated_at)',v).lastrowid
        return one(c,'diet_inventory_items',id)
def delete_inventory(path,id):
    with transaction(path) as c:
        one(c,'diet_inventory_items',id);c.execute('DELETE FROM diet_inventory_items WHERE id=? AND profile_id=1',(id,))
def term_row(c,id):
    r=one(c,'diet_ingredient_terms',id,True)
    r['aliases']=[a[0] for a in c.execute('SELECT alias FROM diet_ingredient_aliases WHERE profile_id=1 AND term_id=? AND alias_key<>? ORDER BY alias_key',(id,r['name_key']))]
    return r
def terms(path,q='',id=None):
    with connect(path) as c:
        require_recipes(c)
        if id is not None:return term_row(c,id)
        sql='SELECT DISTINCT t.id FROM diet_ingredient_terms t JOIN diet_ingredient_aliases a ON a.term_id=t.id AND a.profile_id=t.profile_id WHERE t.profile_id=1 AND t.archived_at IS NULL'
        args=[]
        if q:sql+=' AND instr(a.alias_key,?)>0';args.append(key(q))
        return {'items':[term_row(c,r[0]) for r in c.execute(sql+' ORDER BY t.name_key,t.id',args).fetchall()]}
def resolve(path,name):
    with connect(path) as c:
        require_recipes(c)
        row=c.execute('SELECT term_id FROM diet_ingredient_aliases WHERE profile_id=1 AND alias_key=?',(key(name),)).fetchone()
        if not row:raise LibraryError(404,'TERM_NOT_FOUND','未找到规范名称或别名，请人工建立映射')
        return term_row(c,row[0])
def save_term(path,data,id=None):
    with transaction(path) as c:
        old=term_row(c,id) if id is not None else None
        if old and (old['name']!=data.name or old['kind']!=data.kind):
            used=c.execute('SELECT 1 FROM diet_food_composition_terms WHERE profile_id=1 AND term_id=? UNION ALL SELECT 1 FROM diet_food_preferences WHERE profile_id=1 AND term_id=?',(id,id)).fetchone()
            if used:raise LibraryError(409,'TERM_IN_USE','术语已被成分或规则引用，不能改变规范名称和类型；仍可维护别名')
        now=utc_now()
        if id is None:id=c.execute('INSERT INTO diet_ingredient_terms(profile_id,name,name_key,kind,created_at,updated_at) VALUES(1,?,?,?,?,?)',(data.name,key(data.name),data.kind,now,now)).lastrowid
        else:c.execute('UPDATE diet_ingredient_terms SET name=?,name_key=?,kind=?,updated_at=? WHERE id=? AND profile_id=1',(data.name,key(data.name),data.kind,now,id))
        c.execute('DELETE FROM diet_ingredient_aliases WHERE profile_id=1 AND term_id=?',(id,))
        aliases={key(a):a for a in data.aliases};aliases[key(data.name)]=data.name
        c.executemany('INSERT INTO diet_ingredient_aliases(profile_id,term_id,alias,alias_key) VALUES(1,?,?,?)',[(id,a,k) for k,a in aliases.items()])
        return term_row(c,id)
def delete_term(path,id):
    with transaction(path) as c:
        term_row(c,id);c.execute('DELETE FROM diet_ingredient_terms WHERE profile_id=1 AND id=?',(id,))
def composition_row(c,food_id):
    food=food_row(c,food_id)
    row=c.execute('SELECT * FROM diet_food_composition WHERE profile_id=1 AND food_id=?',(food_id,)).fetchone()
    r=dict(row) if row else {'profile_id':1,'food_id':food_id,'ingredient_status':'unknown','allergen_status':'unknown','assessed_food_updated_at':None,'source_note':'','updated_at':None}
    r['current_food_updated_at']=food['updated_at'];r['outdated']=r['assessed_food_updated_at']!=food['updated_at']
    r['terms']=[dict(x) for x in c.execute('SELECT x.term_id,x.relation,t.name,t.kind FROM diet_food_composition_terms x JOIN diet_ingredient_terms t ON t.id=x.term_id AND t.profile_id=x.profile_id WHERE x.profile_id=1 AND x.food_id=? ORDER BY x.term_id,x.relation',(food_id,))]
    return r
def composition(path,food_id):
    with connect(path) as c:require_recipes(c);return composition_row(c,food_id)
def save_composition(path,food_id,data):
    with transaction(path) as c:
        food=food_row(c,food_id)
        if food['updated_at']!=data.assessed_food_updated_at:conflict()
        resolved=[(t,term_row(c,t.term_id)) for t in data.terms]
        if data.ingredient_status=='declared_complete' and not any(t.relation=='contains' and r['kind']=='ingredient' for t,r in resolved):
            raise LibraryError(422,'COMPOSITION_INCOMPLETE','完整食材说明必须包含至少一个实际成分术语；单一食材也需登记自身')
        v=data.model_dump(exclude={'terms'})|{'profile_id':1,'food_id':food_id,'updated_at':utc_now()}
        c.execute('INSERT INTO diet_food_composition('+','.join(v)+') VALUES('+','.join(':'+k for k in v)+') ON CONFLICT(profile_id,food_id) DO UPDATE SET '+','.join(k+'=excluded.'+k for k in v if k not in ('profile_id','food_id')),v)
        c.execute('DELETE FROM diet_food_composition_terms WHERE profile_id=1 AND food_id=?',(food_id,))
        c.executemany('INSERT INTO diet_food_composition_terms(profile_id,food_id,term_id,relation) VALUES(1,?,?,?)',[(food_id,t.term_id,t.relation) for t in data.terms])
        return composition_row(c,food_id)
def preferences(path,id=None):
    with connect(path) as c:
        require_recipes(c)
        if id is not None:return one(c,'diet_food_preferences',id)
        return {'items':[dict(r) for r in c.execute('SELECT p.*,coalesce(f.name,t.name) AS target_name FROM diet_food_preferences p LEFT JOIN food_items f ON f.id=p.food_id LEFT JOIN diet_ingredient_terms t ON t.id=p.term_id WHERE p.profile_id=1 ORDER BY p.id DESC')]}
def save_preference(path,data,id=None):
    with transaction(path) as c:
        if id is not None:one(c,'diet_food_preferences',id)
        if data.food_id:food_row(c,data.food_id)
        else:term_row(c,data.term_id)
        v=data.model_dump()|{'updated_at':utc_now()}
        if id is None:id=c.execute('INSERT INTO diet_food_preferences(profile_id,food_id,term_id,rule_type,notes,updated_at,created_at) VALUES(1,:food_id,:term_id,:rule_type,:notes,:updated_at,:updated_at)',v).lastrowid
        else:c.execute('UPDATE diet_food_preferences SET '+','.join(k+'=:'+k for k in v)+' WHERE id=:id AND profile_id=1',v|{'id':id})
        return one(c,'diet_food_preferences',id)
def delete_preference(path,id):
    with transaction(path) as c:
        one(c,'diet_food_preferences',id);c.execute('DELETE FROM diet_food_preferences WHERE profile_id=1 AND id=?',(id,))
