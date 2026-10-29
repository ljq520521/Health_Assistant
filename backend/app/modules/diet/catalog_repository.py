"""Read-only public resources, independent of user database and cwd."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
from app.modules.diet.build_catalog import SCHEMA_VERSION, content_hash, NOTICE
from app.modules.diet.library_service import LibraryError

DEFAULT_PATH = Path(__file__).resolve().parent / 'catalog_data/food_catalog.db'

@contextmanager
def catalog(path=None):
    path = Path(path or DEFAULT_PATH).resolve()
    if not path.is_file(): raise LibraryError(503,'CATALOG_MISSING','公共目录文件缺失，请恢复项目发布的 food_catalog.db')
    c = None
    try:
        release=json.loads(path.with_name('catalog-release.json').read_bytes())
        if not isinstance(release,dict): raise ValueError('Invalid release manifest')
        c=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
        c.execute('PRAGMA query_only=ON')
        c.execute('PRAGMA foreign_keys=ON')
        metadata=dict(c.execute('SELECT key,value FROM catalog_metadata'))
        if metadata.get('schema_version') != str(SCHEMA_VERSION) or release.get('schema_version') != SCHEMA_VERSION:
            raise LibraryError(503,'CATALOG_VERSION_UNSUPPORTED','公共目录版本与应用不兼容')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=release['database_sha256'] or content_hash(c)!=release['logical_content_sha256']:
            raise ValueError('Catalog checksum mismatch')
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('Invalid catalog')
        c.row_factory=sqlite3.Row
    except LibraryError:
        if c: c.close()
        raise
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error) as exc:
        if c: c.close()
        raise LibraryError(503,'CATALOG_CORRUPT','公共目录或发布校验文件损坏，请恢复同一版本发布文件') from exc
    try: yield c
    finally: c.close()

def metadata(path=None):
    with catalog(path) as c:
        return dict(c.execute('SELECT key,value FROM catalog_metadata'))

def categories(kind,path=None):
    assert kind in ('food','recipe')
    with catalog(path) as c:
        return {'items':[dict(r) for r in c.execute(f'SELECT * FROM catalog_{kind}_categories ORDER BY name')]}

def foods(q='',category=None,key=None,path=None):
    with catalog(path) as c:
        rows=c.execute('SELECT * FROM catalog_foods ORDER BY food_key').fetchall()
        items=[]
        for row in rows:
            f=json.loads(row['payload_json'])
            if key is not None and row['food_key']!=key: continue
            if category and row['category_key']!=category: continue
            if q.casefold() not in (f['name_zh']+' '+f['original_english_name']+' '+str(f['fdc_id'])).casefold(): continue
            items.append(f|{'food_key':f['source_key'],'origin':'public','editable':False,'name':f['name_zh'],'category_key':row['category_key'],'record_sha256':row['record_sha256'],'notice':NOTICE})
        if key is not None:
            if not items: raise LibraryError(404,'CATALOG_FOOD_NOT_FOUND','公共食品不存在')
            return items[0]
        return {'items':items}

def recipes(q='',category=None,key=None,path=None):
    with catalog(path) as c:
        items=[]
        for row in c.execute('SELECT * FROM catalog_recipes ORDER BY recipe_key'):
            r=json.loads(row['payload_json'])
            if key is not None and row['recipe_key']!=key: continue
            if category and row['category_key']!=category: continue
            if q.casefold() not in r['name'].casefold(): continue
            items.append(r|{'origin':'public','editable':False,'category_key':row['category_key'],'record_sha256':row['record_sha256'],'notice':NOTICE})
        if key is not None:
            if not items: raise LibraryError(404,'CATALOG_RECIPE_NOT_FOUND','公共食谱不存在')
            return items[0]
        return {'items':items}
