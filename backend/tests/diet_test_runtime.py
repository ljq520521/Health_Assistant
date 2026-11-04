"""Explicit opt-in isolation for legacy diet regression tests, never an auth stub.

Without DIET_ISOLATED_TESTS=1 these tests still use the actual full app factory.
The client obtains a real temporary admin token and consent before diet requests.
"""
import os
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager
from unittest.mock import patch
from fastapi.testclient import TestClient as BaseClient
from app.database import init_database
from diet_catalog_app import authenticate

if os.environ.get('DIET_ISOLATED_TESTS') == '1':
    from diet_catalog_app import create_app as isolated_app
    def create_app(settings):
        app=isolated_app(settings)
        @asynccontextmanager
        async def lifespan(app):
            init_database(settings.database_path)
            yield
        app.router.lifespan_context=lifespan
        return app
else:
    from app.main import create_app

class TestClient(BaseClient):
    def __enter__(self):
        path=Path(self.app.state.settings.database_path).resolve()
        if not path.is_relative_to(Path(tempfile.gettempdir()).resolve()):
            raise ValueError('Diet regression harness requires a temporary database')
        self._environment=patch.dict(os.environ,{'HEALTH_DB_PATH':str(path)})
        self._environment.start()
        try:
            super().__enter__()
            authenticate(self)
            return self
        except BaseException:
            super().__exit__(None,None,None)
            self._environment.stop()
            raise
    def __exit__(self,*args):
        try:return super().__exit__(*args)
        finally:self._environment.stop()
