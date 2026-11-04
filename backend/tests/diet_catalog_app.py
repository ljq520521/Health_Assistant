"""Isolated diet API harness: real member-A auth, no app.main or exercise imports.

Only callers providing an explicit temporary database may use this helper.
It intentionally does not pretend to test the five-module application's startup.
"""
from fastapi import FastAPI
from app.config import Settings
from app.modules.profile.router import router as profile_router
from app.modules.diet.router import router as diet_router

def create_app(settings: Settings):
    app = FastAPI(title='Isolated diet verification')
    app.state.settings = settings
    app.include_router(profile_router, prefix='/api')
    app.include_router(diet_router, prefix='/api')
    return app

def authenticate(client, username='catalog_test_admin'):
    credentials = {'username': username, 'password': 'TemporaryTest2026!'}
    if not client.get('/api/auth/setup').json()['has_accounts']:
        r = client.post('/api/auth/register', json=credentials)
        assert r.status_code == 201, r.text
    r = client.post('/api/auth/login', json=credentials)
    assert r.status_code == 200, r.text
    client.headers['Authorization'] = 'Bearer ' + r.json()['access_token']
    r = client.put('/api/auth/privacy', json={'consent_health_data':True,'mask_sensitive':False,'analytics_consent':False})
    assert r.status_code == 200, r.text
    return client.headers['Authorization']
