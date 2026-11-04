"""Sleep permission regressions using real account login and live privacy settings."""

import io
import tempfile
import time
import unittest
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.database import connect
from app.main import create_app
from app.modules.profile.security import create_token, get_or_create_secret
from app.modules.profile.settings import TOKEN_TTL_SECONDS


class SleepAuthTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'health.db'
        self.client = TestClient(create_app(Settings('Sleep permissions', self.path, ())))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.password = 'SleepPermissions2026!'
        self.admin_id, self.admin = self.account('sleep_admin')
        self.viewer_id, self.viewer = self.account('sleep_viewer', self.admin)
        self.payload = {'sleep_at': '2026-09-20T23:00:00+08:00',
                        'wake_at': '2026-09-21T07:00:00+08:00', 'notes': 'private sleep note'}
        self.assertEqual(self.call('POST', '/sleep/profile', self.admin,
                                   json={'display_name': 'Private owner'}).status_code, 200)
        record = self.call('POST', '/sleep-records', self.admin, json=self.payload)
        self.assertEqual(record.status_code, 201, record.text)
        self.record_id = record.json()['id']
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b'\x00\x00' * 800)
        self.wav = buffer.getvalue()
        upload = self.call('POST', '/sleep/content/upload?title=PrivateAudio', self.admin,
                           content=self.wav, headers={'Content-Type': 'audio/wav'})
        self.assertEqual(upload.status_code, 201, upload.text)
        self.content_id = upload.json()['id']

    def call(self, method, path, token=None, **kwargs):
        headers = kwargs.pop('headers', {})
        if token:
            headers = {**headers, 'Authorization': f'Bearer {token}'}
        return self.client.request(method, '/api' + path, headers=headers, **kwargs)

    def account(self, username, actor=None):
        credentials = {'username': username, 'password': self.password}
        registered = self.call('POST', '/auth/register', actor, json=credentials)
        self.assertEqual(registered.status_code, 201, registered.text)
        logged_in = self.call('POST', '/auth/login', json=credentials)
        self.assertEqual(logged_in.status_code, 200, logged_in.text)
        return registered.json()['id'], logged_in.json()['access_token']

    def privacy(self, token, **changes):
        value = {'consent_health_data': True, 'mask_sensitive': False,
                 'analytics_consent': False, **changes}
        self.assertEqual(self.call('PUT', '/auth/privacy', token, json=value).status_code, 200)

    def reads(self):
        return ['/sleep/profile', '/sleep-records', f'/sleep-records/{self.record_id}',
                '/sleep/settings', '/sleep/analysis', '/sleep/report',
                '/sleep/report?format=csv', '/sleep/content',
                f'/sleep/content/{self.content_id}/audio']

    def writes(self):
        return [
            ('POST', '/sleep/profile', {'json': {'display_name': 'Unauthorized change'}}),
            ('POST', '/sleep-records', {'json': self.payload}),
            ('PUT', f'/sleep-records/{self.record_id}', {'json': {**self.payload, 'notes': 'changed'}}),
            ('DELETE', f'/sleep-records/{self.record_id}', {}),
            ('PUT', '/sleep/settings', {'json': {'target_minutes': 420}}),
            ('POST', '/sleep/content', {'json': {'title': 'New', 'category': 'noise',
                                                'url': 'https://example.com/sleep.mp3'}}),
            ('POST', '/sleep/content/upload?title=Forbidden',
             {'content': self.wav, 'headers': {'Content-Type': 'audio/wav'}}),
            ('PUT', f'/sleep/content/{self.content_id}',
             {'json': {'title': 'Changed', 'category': 'meditation', 'favorite': True}}),
            ('DELETE', f'/sleep/content/{self.content_id}', {}),
        ]

    def snapshot(self):
        with connect(self.path) as connection:
            tables = {table: [tuple(row) for row in connection.execute(f'SELECT * FROM {table}')]
                      for table in ('profiles', 'sleep_records', 'sleep_settings', 'sleep_content')}
        files = {p.name: p.read_bytes() for p in (self.path.parent / 'sleep-audio').iterdir()}
        return tables, files

    def assert_blocked(self, token, status):
        before = self.snapshot()
        for path in self.reads():
            with self.subTest(method='GET', path=path):
                response = self.call('GET', path, token)
                self.assertEqual(response.status_code, status, response.text)
                self.assertNotIn('private sleep note', response.text)
                self.assertNotIn('PrivateAudio', response.text)
                if status == 401:
                    self.assertEqual(response.headers['www-authenticate'], 'Bearer')
        for method, path, kwargs in self.writes():
            with self.subTest(method=method, path=path):
                response = self.call(method, path, token, **kwargs)
                self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(self.snapshot(), before, 'Rejected writes must not change rows or files')

    def test_anonymous_cannot_read_write_export_or_download(self):
        self.assert_blocked(None, 401)

    def test_invalid_and_tampered_tokens_are_rejected(self):
        self.assert_blocked('not-a-token', 401)
        self.assert_blocked(self.admin + 'tampered', 401)

    def test_expired_token_is_rejected_everywhere(self):
        with connect(self.path) as connection:
            secret = get_or_create_secret(connection)
        expired = create_token(user_id=self.admin_id, role='admin', token_version=0,
                               secret=secret, issued_at=time.time() - TOKEN_TTL_SECONDS - 10)
        self.assert_blocked(expired, 401)

    def test_authorized_viewer_can_read_export_and_download_but_not_write(self):
        for path in self.reads():
            with self.subTest(path=path):
                response = self.call('GET', path, self.viewer)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.headers['cache-control'], 'no-store')
        before = self.snapshot()
        for method, path, kwargs in self.writes():
            with self.subTest(method=method, path=path):
                self.assertEqual(self.call(method, path, self.viewer, **kwargs).status_code, 403)
        self.assertEqual(self.snapshot(), before)

    def test_consent_revocation_is_live_for_admin_and_viewer(self):
        for token in (self.admin, self.viewer):
            self.privacy(token, consent_health_data=False)
            self.assert_blocked(token, 403)
            self.privacy(token, consent_health_data=True)
            self.assertEqual(self.call('GET', '/sleep-records', token).status_code, 200)

    def test_sensitive_mask_blocks_viewer_and_preserves_owner_access(self):
        self.privacy(self.viewer, mask_sensitive=True)
        self.assert_blocked(self.viewer, 403)
        self.privacy(self.admin, mask_sensitive=True)
        self.assertEqual(self.call('GET', '/sleep-records', self.admin).status_code, 200)
        self.assertEqual(self.call('PUT', '/sleep/settings', self.admin, json={}).status_code, 200)

    def test_disabled_account_and_reenabled_account_invalidate_existing_token(self):
        url = f'/auth/users/{self.viewer_id}/status'
        self.assertEqual(self.call('PUT', url, self.admin, json={'status': 'disabled'}).status_code, 200)
        self.assert_blocked(self.viewer, 403)
        self.assertEqual(self.call('PUT', url, self.admin, json={'status': 'active'}).status_code, 200)
        self.assert_blocked(self.viewer, 401)
        logged_in = self.call('POST', '/auth/login', json={'username': 'sleep_viewer', 'password': self.password})
        self.assertEqual(self.call('GET', '/sleep-records', logged_in.json()['access_token']).status_code, 200)

    def test_password_change_revokes_old_token(self):
        changed = self.call('PUT', '/auth/password', self.admin,
                            json={'current_password': self.password, 'new_password': 'ReplacementPassword2026!'})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assert_blocked(self.admin, 401)
        self.assertEqual(self.call('GET', '/sleep-records', changed.json()['access_token']).status_code, 200)

    def test_audio_range_and_missing_resources_still_require_auth(self):
        audio = f'/sleep/content/{self.content_id}/audio'
        self.assertEqual(self.call('GET', audio, headers={'Range': 'bytes=0-15'}).status_code, 401)
        response = self.call('GET', audio, self.viewer, headers={'Range': 'bytes=0-15'})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, self.wav[:16])
        for path in ('/sleep-records/999999', '/sleep/content/999999/audio'):
            self.assertEqual(self.call('GET', path).status_code, 401)
            self.assertEqual(self.call('GET', path, self.admin).status_code, 404)

    def test_viewer_cannot_bootstrap_missing_profile(self):
        with connect(self.path) as connection:
            connection.execute('DELETE FROM profiles')
        self.assertEqual(self.call('POST', '/sleep/profile', self.viewer,
                                   json={'display_name': 'Bypass'}).status_code, 403)
        self.assertEqual(self.call('POST', '/sleep/profile', json={'display_name': 'Bypass'}).status_code, 401)
        self.assertIsNone(self.call('GET', '/sleep/profile', self.admin).json()['profile'])


if __name__ == '__main__':
    unittest.main()
