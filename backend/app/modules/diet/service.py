from app.modules.diet.settings import utc_now
from fastapi import HTTPException
from app.database import connect
from app.modules.diet.library_service import LibraryError, food_row
from app.modules.diet.nutrition_math import NUTRIENTS, PER100, scale


def require_profile(connection):
    if connection.execute('SELECT id FROM profiles WHERE id=1').fetchone() is None:
        raise LibraryError(409, 'PROFILE_REQUIRED', '请先建立个人档案')


def find_record(connection, record_id):
    row = connection.execute('SELECT * FROM diet_records WHERE id=? AND profile_id=1', (record_id,)).fetchone()
    if row is None:
        raise HTTPException(404, '饮食记录不存在')
    return dict(row)


def list_records(path, date_from=None, date_to=None):
    with connect(path) as c:
        require_profile(c)
        sql = 'SELECT * FROM diet_records WHERE profile_id=1'
        params = []
        for value, operator in ((date_from, '>='), (date_to, '<=')):
            if value is not None:
                sql += f' AND record_date {operator} ?'
                params.append(value.isoformat())
        return {'items': [dict(row) for row in c.execute(sql+' ORDER BY record_date DESC,id DESC', params)]}


def get_record(path, record_id):
    with connect(path) as c:
        require_profile(c)
        return find_record(c, record_id)


def save_record(path, data, record_id=None):
    values = data.model_dump(mode='json')
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        require_profile(c)
        old = find_record(c, record_id) if record_id is not None else None
        columns = {r[1] for r in c.execute('PRAGMA table_info(diet_records)')}
        extended = 'nutrition_mode' in columns
        if data.nutrition_mode == 'catalog':
            if not extended:
                raise LibraryError(503, 'DIET_MIGRATION_REQUIRED', '请先完成食物库结构升级')
            refresh = values.pop('refresh_snapshot')
            same = old and old.get('nutrition_mode') == 'catalog' and old['food_id'] == data.food_id
            if same and not refresh:
                for key in ('food_name','food_version_at','nutrition_source_note','is_example'):
                    values[key] = old[key]
                for key in PER100:
                    values['snapshot_'+key] = old['snapshot_'+key]
            else:
                food = food_row(c, data.food_id)
                values.update(food_name=food['name'], food_version_at=food['updated_at'],
                              nutrition_source_note=' | '.join(filter(None,(food['source_type'],food['source_note'],food['source_url']))), is_example=food['is_example'])
                for key in PER100:
                    values['snapshot_'+key] = food[key]
            for key, source in zip(NUTRIENTS, PER100):
                # Metadata-only changes preserve stored totals exactly.
                values[key] = old[key] if same and not refresh and old['amount_g'] == data.amount_g else scale(values['snapshot_'+source], data.amount_g)
        elif extended:
            values.update(food_id=None,food_version_at=None,nutrition_source_note='',is_example=0)
            values.update({'snapshot_'+key:None for key in PER100})
        else:
            if any(values[k] is not None for k in NUTRIENTS[1:]):
                raise LibraryError(503, 'DIET_MIGRATION_REQUIRED', '请先完成营养字段升级')
            values = {k:v for k,v in values.items() if k in columns}
        now = utc_now()
        values['updated_at'] = now
        if old is None:
            values['created_at'] = now
            keys = ','.join(values)
            params = ','.join(':'+key for key in values)
            record_id = c.execute(f'INSERT INTO diet_records(profile_id,{keys}) VALUES(1,{params})',values).lastrowid
        else:
            assignments = ','.join(key+'=:'+key for key in values)
            values['id'] = record_id
            c.execute(f'UPDATE diet_records SET {assignments} WHERE id=:id AND profile_id=1',values)
        return find_record(c,record_id)


def delete_record(path, record_id):
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        require_profile(c)
        find_record(c,record_id)
        c.execute('DELETE FROM diet_records WHERE id=? AND profile_id=1',(record_id,))
