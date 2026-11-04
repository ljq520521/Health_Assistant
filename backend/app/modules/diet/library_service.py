from fastapi import HTTPException
from app.database import connect
from app.modules.diet.migrations import migration_ready
from app.modules.diet.settings import utc_now


class LibraryError(Exception):
    def __init__(self, status, code, detail):
        self.status, self.code, self.detail = status, code, detail


def ready(connection):
    if connection.execute('SELECT id FROM profiles WHERE id=1').fetchone() is None:
        raise LibraryError(409, 'PROFILE_REQUIRED', '请先建立个人档案')
    if not migration_ready(connection):
        raise LibraryError(503, 'DIET_MIGRATION_REQUIRED', '食物库尚未启用：请先备份并确认执行饮食迁移；原饮食记录功能仍可使用')


def category_row(connection, category_id):
    row = connection.execute('SELECT id,profile_id,name,created_at,updated_at FROM food_categories WHERE id=? AND profile_id=1', (category_id,)).fetchone()
    if row is None:
        raise LibraryError(404, 'CATEGORY_NOT_FOUND', '食物分类不存在')
    return dict(row)


def categories(path):
    with connect(path) as connection:
        ready(connection)
        return {'items': [dict(row) for row in connection.execute('SELECT id,profile_id,name,created_at,updated_at FROM food_categories WHERE profile_id=1 ORDER BY name_key,id')]}


def get_category(path, category_id):
    with connect(path) as connection:
        ready(connection)
        return category_row(connection, category_id)


def save_category(path, data, category_id=None):
    with connect(path) as connection:
        connection.execute('BEGIN IMMEDIATE')
        ready(connection)
        if category_id is not None:
            category_row(connection, category_id)
        key = data.name.casefold()
        existing = connection.execute('SELECT id FROM food_categories WHERE profile_id=1 AND name_key=?', (key,)).fetchone()
        if existing and existing['id'] != category_id:
            raise LibraryError(409, 'CATEGORY_NAME_EXISTS', '此分类名称已存在')
        now = utc_now()
        if category_id is None:
            category_id = connection.execute('INSERT INTO food_categories(profile_id,name,name_key,created_at,updated_at) VALUES(1,?,?,?,?)', (data.name,key,now,now)).lastrowid
        else:
            connection.execute('UPDATE food_categories SET name=?,name_key=?,updated_at=? WHERE id=? AND profile_id=1', (data.name,key,now,category_id))
        return category_row(connection, category_id)


def delete_category(path, category_id):
    with connect(path) as connection:
        connection.execute('BEGIN IMMEDIATE')
        ready(connection)
        category_row(connection, category_id)
        if connection.execute('SELECT id FROM food_items WHERE profile_id=1 AND category_id=? AND deleted_at IS NULL LIMIT 1', (category_id,)).fetchone():
            raise LibraryError(409, 'CATEGORY_IN_USE', '分类仍被有效食物使用，请先调整食物分类或归档食物')
        # Archived foods become uncategorized through the FK; their nutrition is preserved.
        connection.execute('DELETE FROM food_categories WHERE id=? AND profile_id=1', (category_id,))


def food_row(connection, food_id):
    row = connection.execute('SELECT * FROM food_items WHERE id=? AND profile_id=1 AND deleted_at IS NULL', (food_id,)).fetchone()
    if row is None:
        raise LibraryError(404, 'FOOD_NOT_FOUND', '食物不存在或已归档')
    from app.modules.diet.catalog_links import annotate
    return annotate(connection,dict(row))


def foods(path, q='', category_id=None, uncategorized=False):
    with connect(path) as connection:
        ready(connection)
        sql = 'SELECT * FROM food_items WHERE profile_id=1 AND deleted_at IS NULL'
        params = []
        if q:
            # instr treats %, _ and backslashes literally, unlike unescaped LIKE.
            sql += ' AND instr(lower(name),lower(?)) > 0'
            params.append(q)
        if category_id is not None:
            sql += ' AND category_id=?'
            params.append(category_id)
        if uncategorized:
            sql += ' AND category_id IS NULL'
        from app.modules.diet.catalog_links import annotate
        return {'items': [annotate(connection,dict(row)) for row in connection.execute(sql + ' ORDER BY updated_at DESC,id DESC', params)]}


def get_food(path, food_id):
    with connect(path) as connection:
        ready(connection)
        return food_row(connection, food_id)


def save_food(path, data, food_id=None):
    with connect(path) as connection:
        connection.execute('BEGIN IMMEDIATE')
        return save_food_in_connection(connection, data, food_id)


def save_food_in_connection(connection, data, food_id=None):
    """Caller owns the transaction; shared by API and atomic offline importer."""
    values = data.model_dump()
    values.update(is_example=int(data.source_type == 'example'), updated_at=utc_now())
    ready(connection)
    if food_id is not None:
        from app.modules.diet.catalog_links import assert_editable
        assert_editable(connection,food_id)
        food_row(connection, food_id)
    if data.category_id is not None:
        category_row(connection, data.category_id)
    if food_id is None:
        values['created_at'] = values['updated_at']
        columns = ','.join(values)
        placeholders = ','.join(':'+key for key in values)
        food_id = connection.execute(f'INSERT INTO food_items(profile_id,{columns}) VALUES(1,{placeholders})', values).lastrowid
    else:
        assignments = ','.join(key+'=:'+key for key in values)
        values['id'] = food_id
        connection.execute(f'UPDATE food_items SET {assignments} WHERE id=:id AND profile_id=1', values)
    return food_row(connection, food_id)


def archive_food(path, food_id):
    with connect(path) as connection:
        connection.execute('BEGIN IMMEDIATE')
        ready(connection)
        from app.modules.diet.catalog_links import assert_editable
        assert_editable(connection,food_id)
        food_row(connection, food_id)
        now = utc_now()
        connection.execute('UPDATE food_items SET deleted_at=?,updated_at=? WHERE id=? AND profile_id=1', (now,now,food_id))
