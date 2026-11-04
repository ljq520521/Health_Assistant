import tempfile
import unittest
from pathlib import Path
from diet_test_runtime import TestClient
from app.config import Settings
from app.database import connect
from diet_test_runtime import create_app


class DietTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'diet.db'
        self.client = TestClient(create_app(Settings('Diet test', self.path, ())))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        with connect(self.path) as connection:
            connection.execute("INSERT INTO profiles(id, display_name) VALUES (1, '测试档案')")
        self.payload = dict(record_date='2026-10-14', meal_type='lunch', food_name='米饭', amount_g=100, calories_kcal=120, notes='备注')

    def create(self, **changes):
        return self.client.post('/api/diet-records', json=self.payload | changes)

    def test_crud_and_persistence(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        original = response.json()
        record_id = original['id']
        self.assertEqual(original['profile_id'], 1)
        self.assertEqual(self.client.get(f'/api/diet-records/{record_id}').json(), original)
        self.assertEqual(self.client.get('/api/diet-records').json()['items'], [original])
        changed = self.client.put(f'/api/diet-records/{record_id}', json=self.payload | dict(food_name='面条', amount_g=150)).json()
        self.assertEqual(changed['food_name'], '面条')
        self.assertEqual(changed['created_at'], original['created_at'])
        self.assertNotEqual(changed['updated_at'], original['updated_at'])
        with connect(self.path) as connection:
            self.assertEqual(connection.execute('SELECT food_name FROM diet_records WHERE id=?', (record_id,)).fetchone()[0], '面条')
        response = self.client.delete(f'/api/diet-records/{record_id}')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertEqual(self.client.get('/api/diet-records').json(), {'items': []})

    def test_filter_inclusive_and_order(self):
        first = self.create(record_date='2026-10-13').json()
        second = self.create().json()
        third = self.create().json()
        self.create(record_date='2026-10-15')
        items = self.client.get('/api/diet-records?date_from=2026-10-13&date_to=2026-10-14').json()['items']
        self.assertEqual([item['id'] for item in items], [third['id'], second['id'], first['id']])
        self.assertEqual(len(self.client.get('/api/diet-records?date_from=2026-10-14').json()['items']), 3)
        self.assertEqual(len(self.client.get('/api/diet-records?date_to=2026-10-13').json()['items']), 1)
        for query in ('date_from=2026-10-15&date_to=2026-10-13', 'date_from=2026-02-30', 'date_to=123', 'date_from=20261014'):
            with self.subTest(query=query):
                self.assertEqual(self.client.get('/api/diet-records?' + query).status_code, 422)

    def test_invalid_inputs_do_not_write(self):
        record_id = self.create().json()['id']
        invalid = [('meal_type', 'brunch'), ('record_date', '2026-02-30'), ('record_date', '20261014'), ('record_date', 0), ('amount_g', -1), ('amount_g', 0), ('amount_g', True), ('calories_kcal', -1), ('calories_kcal', 'NaN'), ('food_name', '   '), ('food_name', '米' * 101), ('notes', None), ('profile_id', 2)]
        for field, value in invalid:
            with self.subTest(field=field, value=value):
                self.assertEqual(self.create(**{field: value}).status_code, 422)
                self.assertEqual(self.client.put(f'/api/diet-records/{record_id}', json=self.payload | {field: value}).status_code, 422)
        for field in ('record_date', 'meal_type', 'food_name', 'amount_g'):
            payload = self.payload.copy()
            del payload[field]
            self.assertEqual(self.client.post('/api/diet-records', json=payload).status_code, 422)
            self.assertEqual(self.client.put(f'/api/diet-records/{record_id}', json=payload).status_code, 422)
        self.assertEqual(len(self.client.get('/api/diet-records').json()['items']), 1)

    def test_null_zero_and_put_defaults(self):
        result = self.create(calories_kcal=None, food_name='  米饭  ').json()
        self.assertIsNone(result['calories_kcal'])
        self.assertEqual(result['food_name'], '米饭')
        self.assertEqual(self.create(calories_kcal=0).json()['calories_kcal'], 0)
        payload = {key: self.payload[key] for key in ('record_date', 'meal_type', 'food_name', 'amount_g')}
        result = self.client.put(f"/api/diet-records/{result['id']}", json=payload).json()
        self.assertIsNone(result['calories_kcal'])
        self.assertEqual(result['notes'], '')
        with connect(self.path) as connection:
            self.assertIsNone(connection.execute('SELECT calories_kcal FROM diet_records WHERE id=?', (result['id'],)).fetchone()[0])

    def test_missing_profile_all_endpoints(self):
        with connect(self.path) as connection:
            connection.execute('DELETE FROM profiles')
        for method, url, kwargs in [('get', '', {}), ('post', '', {'json': self.payload}), ('get', '/1', {}), ('put', '/1', {'json': self.payload}), ('delete', '/1', {})]:
            with self.subTest(method=method, url=url):
                self.assertEqual(getattr(self.client, method)('/api/diet-records' + url, **kwargs).status_code, 409)

    def test_nonexistent_and_invalid_id(self):
        for method, kwargs in [('get', {}), ('put', {'json': self.payload}), ('delete', {})]:
            self.assertEqual(getattr(self.client, method)('/api/diet-records/999', **kwargs).status_code, 404)
            self.assertEqual(getattr(self.client, method)('/api/diet-records/abc', **kwargs).status_code, 422)


if __name__ == '__main__':
    unittest.main()
