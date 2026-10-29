"""Reproducible public artifact builder. Never opens a health database."""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sqlite3

from app.modules.diet.import_service import load_package
from app.modules.diet.source_mapping import canonical, digest, json_read

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / 'seed_data/usda_v3_course_demo'
MANIFEST_SHA = 'e2d45d1e5e2652ad86769281c330380779ce2738e207c520c68db73e87d11b2b'
SCHEMA_VERSION = 1
RELEASE = 'usda-course-v3-catalog-1'
NOTICE = '课程演示数据已获团队批准；来源已技术核验；菜谱为团队自编、AI辅助、未经实际试做；营养为投料估算；成分及过敏原未全面核验，不代表生产或医学用途批准。'
DDL = (
 'CREATE TABLE catalog_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)',
 'CREATE TABLE catalog_food_categories (category_key TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE)',
 'CREATE TABLE catalog_recipe_categories (category_key TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE)',
 'CREATE TABLE catalog_sources (source_key TEXT PRIMARY KEY, payload_json TEXT NOT NULL)',
 'CREATE TABLE catalog_foods (food_key TEXT PRIMARY KEY, fdc_id INTEGER NOT NULL UNIQUE, category_key TEXT NOT NULL REFERENCES catalog_food_categories(category_key), payload_json TEXT NOT NULL, record_sha256 TEXT NOT NULL)',
 'CREATE TABLE catalog_food_evidence (food_key TEXT PRIMARY KEY REFERENCES catalog_foods(food_key), payload_json TEXT NOT NULL)',
 'CREATE TABLE catalog_recipes (recipe_key TEXT PRIMARY KEY, recipe_version INTEGER NOT NULL, category_key TEXT NOT NULL REFERENCES catalog_recipe_categories(category_key), payload_json TEXT NOT NULL, record_sha256 TEXT NOT NULL)',
 'CREATE TABLE catalog_recipe_ingredients (recipe_key TEXT NOT NULL REFERENCES catalog_recipes(recipe_key), position INTEGER NOT NULL CHECK(position>0), food_key TEXT NOT NULL REFERENCES catalog_foods(food_key), amount_g REAL NOT NULL CHECK(amount_g>0), PRIMARY KEY(recipe_key,position), UNIQUE(recipe_key,food_key))',
 'CREATE TABLE catalog_recipe_steps (recipe_key TEXT NOT NULL REFERENCES catalog_recipes(recipe_key), position INTEGER NOT NULL CHECK(position>0), instruction TEXT NOT NULL, PRIMARY KEY(recipe_key,position))',
 'CREATE TABLE catalog_approvals (approval_key TEXT PRIMARY KEY, payload_json TEXT NOT NULL)',
 'CREATE TABLE catalog_package_files (path TEXT PRIMARY KEY, sha256 TEXT NOT NULL)',
)

def category_key(kind, name):
    return kind + ':' + hashlib.sha256(name.encode('utf-8')).hexdigest()[:24]

def verified_input():
    checks = {}
    for line in (PACKAGE / 'SHA256SUMS.txt').read_text(encoding='utf-8-sig').splitlines():
        expected, name = line.split(None, 1)
        path = (PACKAGE / name).resolve()
        if not path.is_relative_to(PACKAGE.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('v3 file checksum mismatch: ' + name)
        checks[name] = expected
    package = load_package(PACKAGE, expected_manifest_sha256=MANIFEST_SHA, allow_course_demo=True)
    foods = [f.model_dump() for f in package['foods']]
    recipes = [r.model_dump() for r in package['recipes']]
    approval = json_read((PACKAGE / 'approval-record.json').read_bytes())
    preview = (PACKAGE / 'provenance/approval-record.preview.json').read_bytes()
    if hashlib.sha256(preview).hexdigest() != approval['approval_preview_sha256']:
        raise ValueError('Approval preview mismatch')
    original = json_read(preview)
    for key in ('foods', 'recipes', 'dependencies', 'approved_counts'):
        if approval[key] != original[key]: raise ValueError('Approval scope mismatch')
    if approval['approval_scope'] != 'team_course_demonstration_only' or approval['formal_production_use_approved'] is not False:
        raise ValueError('Invalid approval scope')
    deps = sorted((r['recipe_key'], i['food_source_key'], i['amount_g']) for r in recipes for i in r['ingredients'])
    approved = sorted((r['recipe_key'], r['food_source_key'], r['amount_g']) for r in approval['dependencies'])
    if (len(foods), len(recipes), len(deps)) != (134, 12, 48) or deps != approved:
        raise ValueError('Counts/dependencies mismatch')
    if {f['source_key'] for f in foods} != {f['source_key'] for f in approval['foods']} or {r['recipe_key'] for r in recipes} != {r['recipe_key'] for r in approval['recipes']}:
        raise ValueError('Unapproved resource')
    evidence_hashes = json_read((PACKAGE / 'provenance/source-record-sha256.json').read_bytes())
    if {k:v['record_sha256'] for k,v in package['evidence'].items()} != evidence_hashes:
        raise ValueError('USDA source evidence mismatch')
    return package, foods, recipes, approval, checks

def content_hash(connection):
    content = {}
    for (table,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        rows = connection.execute('SELECT * FROM "' + table + '"').fetchall()
        if table == 'catalog_metadata': rows = [r for r in rows if r[0] != 'logical_content_sha256']
        content[table] = sorted([list(r) for r in rows], key=canonical)
    return digest(content)

def public_approval(approval):
    """Preserve the decision and evidence hashes, not a developer's local path.

    The original signed-scope record remains untouched in the v3 package.
    This public projection explicitly retains its original byte checksum.
    """
    result=json.loads(canonical(approval))
    result['historical_workbook']['path']=PureWindowsPath(result['historical_workbook']['path']).name
    result['source_approval_file_sha256']=hashlib.sha256((PACKAGE/'approval-record.json').read_bytes()).hexdigest()
    result['public_projection']='Local workbook path reduced to basename; approval scope and evidence unchanged.'
    return result

def build(output):
    output = Path(output)
    if output.exists(): raise ValueError('Refusing to overwrite an existing file')
    if any(output.with_name(name).exists() for name in ('catalog-release.json','SHA256SUMS.txt')):
        raise ValueError('Use an empty output directory; refusing to overwrite release metadata')
    package, foods, recipes, approval, checks = verified_input()
    output.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(output)
    try:
        c.execute('PRAGMA page_size=4096')
        c.execute('PRAGMA journal_mode=DELETE')
        c.execute('PRAGMA foreign_keys=ON')
        c.execute('BEGIN IMMEDIATE')
        for statement in DDL: c.execute(statement)
        metadata = {'schema_version':str(SCHEMA_VERSION), 'release_id':RELEASE, 'catalog_id':'health-assistant-usda', 'source_manifest_sha256':MANIFEST_SHA, 'generator_version':'1', 'notice':NOTICE}
        c.executemany('INSERT INTO catalog_metadata VALUES (?,?)', sorted(metadata.items()))
        for kind, rows in [('food', foods), ('recipe', recipes)]:
            c.executemany(f'INSERT INTO catalog_{kind}_categories VALUES (?,?)', [(category_key(kind,n),n) for n in sorted({r['category'] for r in rows})])
        for source in sorted(package['manifest'].sources, key=lambda s:s.path):
            c.execute('INSERT INTO catalog_sources VALUES (?,?)', (source.path,canonical(source.model_dump())))
        for f in sorted(foods, key=lambda f:f['source_key']):
            c.execute('INSERT INTO catalog_foods VALUES (?,?,?,?,?)', (f['source_key'],f['fdc_id'],category_key('food',f['category']),canonical(f),digest(f)))
            c.execute('INSERT INTO catalog_food_evidence VALUES (?,?)',(f['source_key'],canonical(package['evidence'][f['source_key']])))
        for r in sorted(recipes, key=lambda r:r['recipe_key']):
            c.execute('INSERT INTO catalog_recipes VALUES (?,?,?,?,?)',(r['recipe_key'],r['recipe_version'],category_key('recipe',r['category']),canonical(r),digest(r)))
            c.executemany('INSERT INTO catalog_recipe_ingredients VALUES (?,?,?,?)',[(r['recipe_key'],n,i['food_source_key'],i['amount_g']) for n,i in enumerate(r['ingredients'],1)])
            c.executemany('INSERT INTO catalog_recipe_steps VALUES (?,?,?)',[(r['recipe_key'],n,s) for n,s in enumerate(r['steps'],1)])
        c.execute('INSERT INTO catalog_approvals VALUES (?,?)',('course-v3',canonical(public_approval(approval))))
        c.executemany('INSERT INTO catalog_package_files VALUES (?,?)',sorted(checks.items()))
        logical = content_hash(c)
        c.execute('INSERT INTO catalog_metadata VALUES (?,?)',('logical_content_sha256',logical))
        if c.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('Foreign key failure')
        if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('Integrity failure')
        c.commit()
    finally:
        c.close()
    release = {'schema_version':SCHEMA_VERSION, 'release_id':RELEASE, 'source_manifest_sha256':MANIFEST_SHA, 'logical_content_sha256':logical, 'database_sha256':hashlib.sha256(output.read_bytes()).hexdigest(), 'sqlite_version':sqlite3.sqlite_version, 'counts':{'foods':134,'recipes':12,'ingredients':48,'food_categories':9,'recipe_categories':4}}
    output.with_name('catalog-release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    output.with_name('SHA256SUMS.txt').write_text(release['database_sha256']+'  '+output.name+'\n',encoding='utf-8',newline='\n')
    return release

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(build(parser.parse_args().output)))
