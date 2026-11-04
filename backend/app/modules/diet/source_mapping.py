"""Offline USDA JSON archive verification. Never invent missing nutrients."""
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path

SOURCE_URLS = {
    ('Foundation', '2026-04-30'): 'https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_json_2026-04-30.zip',
    ('SR Legacy', '2018-04'): 'https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_json_2018-04.zip',
}
FIELDS = ('calories_per_100g', 'protein_g_per_100g', 'fat_g_per_100g', 'carbohydrate_g_per_100g')
NUTRIENTS = {
    1008: ('Energy', 'KCAL'),
    2047: ('Energy (Atwater General Factors)', 'KCAL'),
    2048: ('Energy (Atwater Specific Factors)', 'KCAL'),
    1003: ('Protein', 'G'),
    1004: ('Total lipid (fat)', 'G'),
    1005: ('Carbohydrate, by difference', 'G'),
}

class ImportRejected(ValueError):
    pass

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(value):
    return sha(canonical(value).encode('utf-8'))

def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ImportRejected('JSON重复字段：' + key)
        result[key] = value
    return result

def json_read(data):
    def invalid(value):
        raise ImportRejected('JSON非法数值：' + value)
    return json.loads(data, object_pairs_hook=_pairs, parse_constant=invalid)

def local_file(root, name):
    root = Path(root).resolve()
    p = (root / name).resolve()
    if p == root or not p.is_relative_to(root) or not p.is_file():
        raise ImportRejected('数据文件不存在或越出数据包目录：' + name)
    return p

def verified_bytes(root, ref):
    data = local_file(root, ref.path).read_bytes()
    if sha(data) != ref.sha256:
        raise ImportRejected('文件SHA256不符：' + ref.path)
    return data

def archive_records(data, data_type, wanted=None):
    """Read ZIP in memory; never extract archive paths to disk."""
    key = {'Foundation': 'FoundationFoods', 'SR Legacy': 'SRLegacyFoods'}[data_type]
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        members = [i for i in z.infolist() if i.filename.lower().endswith('.json')]
        if len(members) != 1 or members[0].file_size > 400_000_000:
            raise ImportRejected('USDA压缩包必须有一个不超过400MB的JSON文件')
        content = json_read(z.read(members[0]))
    if not isinstance(content, dict) or key not in content or not isinstance(content[key], list):
        raise ImportRejected('USDA数据类型或JSON顶层结构不符')
    result = {}
    for food in content[key]:
        # The official 2026-04 Foundation archive includes null placeholders.
        if food is None:
            continue
        if not isinstance(food, dict):
            raise ImportRejected('USDA条目必须为对象或空占位')
        fid = food.get('fdcId')
        if type(fid) is not int or fid <= 0:
            raise ImportRejected('官方条目FDC ID非法')
        if wanted is not None and fid not in wanted:
            continue
        if fid in result:
            raise ImportRejected('来源包内FDC ID重复')
        if food.get('dataType') != data_type:
            raise ImportRejected('来源条目dataType不符')
        result[fid] = food
    return result

def mapped_nutrients(record):
    rows = {}
    for row in record.get('foodNutrients', []):
        n = row.get('nutrient', {})
        nid = n.get('id')
        if nid not in NUTRIENTS:
            continue
        name, unit = NUTRIENTS[nid]
        if n.get('name') != name or str(n.get('unitName', '')).upper() != unit:
            raise ImportRejected(f'营养字段{nid}名称/单位不符')
        if nid in rows:
            raise ImportRejected(f'营养字段{nid}重复，须人工核对')
        amount = row.get('amount')
        if amount is not None and (type(amount) not in (int, float) or not math.isfinite(amount) or amount < 0):
            raise ImportRejected('来源营养值非法')
        # A qualified/LOQ value is not a measured zero. Preserve raw row in provenance.
        qualified = any(row.get(k) not in (None, '', 0, 0.0) for k in ('loq', 'limitOfQuantification', 'qualifier'))
        qualified = qualified or '<' in str(row.get('footnote', ''))
        rows[nid] = {'value': None if qualified else amount, 'raw': row, 'qualified': qualified}
    if record['dataType'] == 'Foundation':
        eid = 2048 if rows.get(2048, {}).get('value') is not None else 2047
    else:
        eid = 1008
    ids = (eid, 1003, 1004, 1005)
    values = {field: rows.get(nid, {}).get('value') for field, nid in zip(FIELDS, ids)}
    for field, value in values.items():
        if value is not None and value > (1000 if field == FIELDS[0] else 100):
            raise ImportRejected('来源异常值需人工审核：' + field)
    return values, {'energy_nutrient_id': eid, 'nutrient_rows': rows}

def verify_foods(root, manifest, foods):
    sources = {s.path: s for s in manifest.sources}
    if len(sources) != len(manifest.sources):
        raise ImportRejected('来源文件重复')
    records = {}
    for path, source in sources.items():
        if SOURCE_URLS.get((source.data_type, source.release)) != source.url:
            raise ImportRejected('尚未支持或未经审核的官方来源/版本')
        wanted = {f.fdc_id for f in foods if f.source_archive == path}
        records[path] = archive_records(verified_bytes(root, source), source.data_type, wanted)
    evidence = {}
    for food in foods:
        raw = records.get(food.source_archive, {}).get(food.fdc_id)
        if raw is None or raw.get('description') != food.original_english_name:
            raise ImportRejected('FDC身份/英文原名未匹配：' + food.source_key)
        nutrients, provenance = mapped_nutrients(raw)
        if any(getattr(food, k) != v for k, v in nutrients.items()):
            raise ImportRejected('营养值与官方原始条目不一致：' + food.source_key)
        evidence[food.source_key] = {'source': sources[food.source_archive].model_dump(),
                                    'record_sha256': digest(raw), **provenance}
    return evidence
