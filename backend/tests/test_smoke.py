import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.database import connect, init_database
from app.main import create_app


class ScaffoldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "health.db"
        self.app = create_app(Settings("Test", self.path, ("http://localhost:5173",)))

    def test_startup_health_catalog_and_cors(self):
        with TestClient(self.app) as client:
            response = client.get("/health", headers={"Origin": "http://localhost:5173"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok", "database": "ok", "version": "0.1.0"})
            self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")
            self.assertEqual(len(client.get("/api/modules").json()), 5)
            # Planned endpoints must not pretend to be implemented.
            self.assertEqual(client.get("/api/diet-records").status_code, 404)

    def test_initialization_preserves_existing_data(self):
        init_database(self.path)
        with connect(self.path) as connection:
            connection.execute("INSERT INTO profiles (id, display_name) VALUES (1, '测试档案')")
        init_database(self.path)
        with connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM profiles").fetchone()[0], 1)
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({"profiles", "health_goals", "diet_records", "exercise_records", "sleep_records", "cycle_records"} <= tables)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO profiles (id, display_name) VALUES (2, '第二份档案')")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO diet_records (profile_id, record_date, meal_type, food_name, amount_g) VALUES (99, '2026-09-23', 'lunch', '米饭', 100)")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO sleep_records (sleep_at, wake_at) VALUES ('2026-09-23T23:00:00+08:00', '2026-09-23T22:00:00+08:00')")

    def test_unavailable_database_returns_503_without_recreating_it(self):
        with TestClient(self.app) as client:
            self.path.unlink()
            self.assertEqual(client.get("/health").status_code, 503)
            self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
