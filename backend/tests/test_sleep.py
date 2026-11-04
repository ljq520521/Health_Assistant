import io
import sqlite3
import tempfile
import unittest
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.database import SCHEMA_PATH, connect, init_database
from app.main import create_app


class SleepModuleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'health.db'
        self.client = TestClient(create_app(Settings('Sleep test', self.path, ())))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def profile(self):
        self.assertEqual(self.client.post('/api/sleep/profile', json={'display_name': '测试档案'}).status_code, 200)

    def payload(self, **overrides):
        return {'sleep_at': '2026-09-20T23:00:00+08:00', 'wake_at': '2026-09-21T07:00:00+08:00',
                'deep_minutes': 120, 'light_minutes': 300, 'awakenings': 1, 'quality': 4, 'notes': '', **overrides}

    def create(self, **overrides):
        response = self.client.post('/api/sleep-records', json=self.payload(**overrides))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_profile_bootstrap_never_overwrites_existing_profile(self):
        self.assertIsNone(self.client.get('/api/sleep/profile').json()['profile'])
        self.assertEqual(self.client.post('/api/sleep-records', json=self.payload()).status_code, 409)
        self.profile()
        self.client.post('/api/sleep/profile', json={'display_name': '不应覆盖'})
        self.assertEqual(self.client.get('/api/sleep/profile').json()['profile']['display_name'], '测试档案')

    def test_crud_normalizes_utc_and_persists(self):
        self.profile()
        row = self.create()
        self.assertEqual(row['sleep_at'], '2026-09-20T15:00:00Z')
        self.assertEqual(row['duration_minutes'], 480)
        self.assertEqual(row['stage_unrecorded_minutes'], 60)
        self.assertEqual(row['score'], 91)
        self.assertEqual(len(row['dimensions']), 4)
        url = f'/api/sleep-records/{row["id"]}'
        updated = self.client.put(url, json=self.payload(notes='更新成功'))
        self.assertEqual(updated.status_code, 200, updated.text)
        with connect(self.path) as connection:
            self.assertEqual(connection.execute('SELECT notes FROM sleep_records').fetchone()[0], '更新成功')
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)

    def test_overlap_detected_on_create_and_update_but_touching_allowed(self):
        self.profile(); first = self.create()
        self.assertEqual(self.client.post('/api/sleep-records', json=self.payload()).status_code, 409)
        second = self.create(sleep_at='2026-09-21T07:00:00+08:00', wake_at='2026-09-21T08:00:00+08:00', deep_minutes=None, light_minutes=None)
        response = self.client.put(f'/api/sleep-records/{second["id"]}', json=self.payload())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get(f'/api/sleep-records/{first["id"]}').status_code, 200)

    def test_invalid_times_stages_values_and_future_rejected(self):
        self.profile()
        future = datetime.now(timezone.utc) + timedelta(days=1)
        for change in [
            {'sleep_at': '2026-09-20T23:00:00'}, {'wake_at': '2026-09-20T22:00:00+08:00'},
            {'deep_minutes': 400, 'light_minutes': 300}, {'awakenings': -1}, {'quality': 6},
            {'deep_minutes': 1.5}, {'notes': 'x' * 2001}, {'profile_id': 99},
            {'sleep_at': '0001-01-01T00:00:00+08:00', 'wake_at': '0001-01-01T08:00:00+08:00'},
            {'sleep_at': future.isoformat(), 'wake_at': (future + timedelta(hours=8)).isoformat()},
        ]:
            with self.subTest(change=change):
                self.assertEqual(self.client.post('/api/sleep-records', json=self.payload(**change)).status_code, 422)
        self.assertEqual(self.client.get('/api/sleep-records').json()['items'], [])

    def test_shanghai_day_filter_includes_midnight_boundary(self):
        self.profile()
        self.create(sleep_at='2026-09-20T15:00:00+08:00', wake_at='2026-09-20T16:00:00Z', deep_minutes=30, light_minutes=30)
        result = self.client.get('/api/sleep-records?date_from=2026-09-21&date_to=2026-09-21').json()
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(self.client.get('/api/sleep-records?date_from=2026-09-20&date_to=2026-09-20').json()['items'], [])
        self.assertEqual(self.client.get('/api/sleep-records?date_from=2026-09-22&date_to=2026-09-20').status_code, 422)
        self.assertEqual(self.client.get('/api/sleep-records?date_to=9999-12-31').status_code, 422)
        self.assertEqual(self.client.get('/api/sleep/analysis?end_date=0001-01-01').status_code, 422)
        self.assertEqual(self.client.get('/api/sleep/analysis?end_date=9999-12-31').status_code, 422)

    def test_trends_missing_days_comparison_and_multiple_records(self):
        self.profile(); self.create()
        self.create(sleep_at='2026-09-13T23:00:00+08:00', wake_at='2026-09-14T06:00:00+08:00')
        self.create(sleep_at='2026-09-21T12:00:00+08:00', wake_at='2026-09-21T13:00:00+08:00', deep_minutes=None, light_minutes=None)
        data = self.client.get('/api/sleep/analysis?period=week&end_date=2026-09-21').json()
        self.assertEqual(data['summary']['recorded_days'], 1)
        self.assertEqual(data['summary']['average_minutes'], 540)
        self.assertEqual(data['summary']['change_minutes'], 120)
        self.assertEqual(len(data['daily']), 7)
        self.assertEqual(sum(day['duration_minutes'] is None for day in data['daily']), 6)
        self.assertEqual(data['summary']['alert_count'], 1)
        self.assertEqual(len(self.client.get('/api/sleep/analysis?period=month&end_date=2026-09-21').json()['daily']), 30)

    def test_empty_report_and_missing_quality_do_not_fabricate_data(self):
        data = self.client.get('/api/sleep/report?end_date=2026-09-21').json()
        self.assertIsNone(data['summary']['average_score'])
        self.assertIsNone(data['summary']['average_minutes'])
        self.profile(); row = self.create(quality=None, deep_minutes=None, light_minutes=None, awakenings=0)
        self.assertEqual(row['score'], 100)
        self.assertFalse(row['assessment_complete'])
        self.assertEqual(len(row['dimensions']), 3)
        self.assertIsNone(row['deep_minutes'])

    def test_settings_validation_persistence_and_alarm_midnight(self):
        self.assertEqual(self.client.put('/api/sleep/settings', json={}).status_code, 409)
        self.profile()
        response = self.client.put('/api/sleep/settings', json={'bedtime': '23:00', 'alarm_time': '07:00', 'smart_alarm': True, 'weekdays': [0, 6]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['effective_alarm_time'], '06:30')
        self.assertEqual(self.client.get('/api/sleep/settings').json()['weekdays'], [0, 6])
        for change in [{'bedtime': '24:30'}, {'weekdays': []}, {'weekdays': [0, 0]}, {'target_minutes': 0}]:
            self.assertEqual(self.client.put('/api/sleep/settings', json=change).status_code, 422)
        value = self.client.put('/api/sleep/settings', json={'bedtime': '00:10', 'reminder_minutes': 30}).json()
        self.assertEqual(value['reminder_time'], '23:40')

    def test_content_crud_upload_playback_delete_and_validation(self):
        self.assertEqual(len(self.client.get('/api/sleep/content').json()['items']), 3)
        self.assertEqual(self.client.post('/api/sleep/content', json={'title': 'bad', 'category': 'noise', 'url': 'javascript:alert(1)'}).status_code, 422)
        row = self.client.post('/api/sleep/content', json={'title': '我的冥想', 'category': 'meditation', 'url': 'https://example.com/test.mp3'}).json()
        self.assertEqual(self.client.put(f'/api/sleep/content/{row["id"]}', json={'title': '已收藏', 'category': 'meditation', 'favorite': True}).status_code, 200)
        self.assertTrue(self.client.get('/api/sleep/content').json()['items'][0]['favorite'])
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000); audio.writeframes(b'\x00\x00' * 800)
        upload = self.client.post('/api/sleep/content/upload?title=测试音频', content=buffer.getvalue(), headers={'Content-Type': 'audio/wav'})
        self.assertEqual(upload.status_code, 201, upload.text)
        resource = upload.json()
        self.assertEqual(self.client.get(resource['source']).content, buffer.getvalue())
        self.assertEqual(len(list((self.path.parent / 'sleep-audio').iterdir())), 1)
        self.assertEqual(self.client.delete(f'/api/sleep/content/{resource["id"]}').status_code, 204)
        self.assertEqual(list((self.path.parent / 'sleep-audio').iterdir()), [])
        self.assertEqual(self.client.get(resource['source']).status_code, 404)
        for body, media, expected in [(b'', 'audio/wav', 422), (b'not audio', 'audio/wav', 422), (b'text', 'text/html', 415), (b'x' * (20 * 1024 * 1024 + 1), 'audio/mpeg', 413)]:
            self.assertEqual(self.client.post('/api/sleep/content/upload?title=test', content=body, headers={'Content-Type': media}).status_code, expected)
        self.assertEqual(list((self.path.parent / 'sleep-audio').iterdir()), [])

    def test_report_csv_handles_unicode_quotes_and_formula_injection(self):
        self.profile(); self.create(notes='=HYPERLINK("bad")\n中文,备注')
        response = self.client.get('/api/sleep/report?period=week&end_date=2026-09-21&format=csv')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'\xef\xbb\xbf'))
        self.assertIn("'=HYPERLINK", response.text)
        self.assertIn('attachment;', response.headers['content-disposition'])

    def test_migration_preserves_legacy_records_and_is_idempotent(self):
        legacy = self.path.parent / 'legacy.db'
        with sqlite3.connect(legacy) as connection:
            connection.executescript(SCHEMA_PATH.read_text())
            connection.execute("INSERT INTO profiles(id,display_name) VALUES(1,'旧档案')")
            connection.execute("INSERT INTO sleep_records(sleep_at,wake_at,notes) VALUES('2026-09-20T23:00:00+08:00','2026-09-21T07:00:00+08:00','保留我')")
        init_database(legacy); init_database(legacy)
        with connect(legacy) as connection:
            row = connection.execute('SELECT * FROM sleep_records').fetchone()
            self.assertEqual(row['notes'], '保留我')
            self.assertIsNone(row['deep_minutes'])
            self.assertEqual(row['awakenings'], 0)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM sleep_content').fetchone()[0], 3)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0], 1)
