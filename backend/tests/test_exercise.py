"""Tests for the exercise module (member C)."""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.config import Settings
from app.database import connect, init_database
from app.main import create_app

TODAY = datetime.now(ZoneInfo("Asia/Shanghai")).date()

PAYLOAD = {
    "record_date": "2026-10-20",
    "exercise_type": "快走",
    "duration_minutes": 40,
    "intensity": "medium",
    "notes": "晚饭后",
}


class ExerciseApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "health.db"
        self.app = create_app(Settings("Test", self.path, ("http://localhost:5173",)))
        init_database(self.path)

    def client(self) -> TestClient:
        return TestClient(self.app)

    def create_profile(self):
        with connect(self.path) as connection:
            connection.execute("INSERT INTO profiles (id, display_name) VALUES (1, '测试档案')")

    def test_requires_profile_before_any_record_access(self):
        with self.client() as client:
            for method, url in (
                ("get", "/api/exercise-records"),
                ("post", "/api/exercise-records"),
                ("get", "/api/exercise-records/1"),
                ("put", "/api/exercise-records/1"),
                ("delete", "/api/exercise-records/1"),
            ):
                response = getattr(client, method)(url, json=PAYLOAD) if method in ("post", "put") else getattr(client, method)(url)
                self.assertEqual(response.status_code, 409, url)
                self.assertEqual(response.json()["detail"], "请先建立个人档案")

    def test_create_read_update_delete_round_trip(self):
        self.create_profile()
        with self.client() as client:
            created = client.post("/api/exercise-records", json=PAYLOAD)
            self.assertEqual(created.status_code, 201)
            record = created.json()
            self.assertEqual(record["profile_id"], 1)
            self.assertEqual(record["record_date"], "2026-10-20")
            self.assertEqual(record["exercise_type"], "快走")
            self.assertEqual(record["duration_minutes"], 40)
            self.assertEqual(record["intensity"], "medium")
            self.assertEqual(record["notes"], "晚饭后")
            self.assertRegex(record["created_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertEqual(record["created_at"], record["updated_at"])

            record_id = record["id"]
            fetched = client.get(f"/api/exercise-records/{record_id}")
            self.assertEqual(fetched.status_code, 200)
            self.assertEqual(fetched.json(), record)

            replacement = {
                "record_date": "2026-10-21",
                "exercise_type": "力量训练",
                "duration_minutes": 25,
                "intensity": "high",
                "notes": "",
            }
            updated = client.put(f"/api/exercise-records/{record_id}", json=replacement)
            self.assertEqual(updated.status_code, 200)
            body = updated.json()
            self.assertEqual(body["id"], record_id)
            self.assertEqual(body["exercise_type"], "力量训练")
            self.assertEqual(body["duration_minutes"], 25)
            self.assertEqual(body["intensity"], "high")
            self.assertEqual(body["notes"], "")
            self.assertEqual(body["created_at"], record["created_at"])

            deleted = client.delete(f"/api/exercise-records/{record_id}")
            self.assertEqual(deleted.status_code, 204)
            self.assertEqual(deleted.content, b"")
            self.assertEqual(client.get(f"/api/exercise-records/{record_id}").status_code, 404)
            self.assertEqual(client.delete(f"/api/exercise-records/{record_id}").status_code, 404)

    def test_list_is_filtered_by_date_range_and_newest_first(self):
        self.create_profile()
        with self.client() as client:
            for record_date, minutes in (
                ("2026-10-01", 20),
                ("2026-10-03", 30),
                ("2026-10-03", 15),
                ("2026-10-10", 45),
            ):
                response = client.post(
                    "/api/exercise-records",
                    json={**PAYLOAD, "record_date": record_date, "duration_minutes": minutes},
                )
                self.assertEqual(response.status_code, 201)

            everything = client.get("/api/exercise-records").json()["items"]
            self.assertEqual([item["record_date"] for item in everything],
                             ["2026-10-10", "2026-10-03", "2026-10-03", "2026-10-01"])
            # Same business date is ordered by descending id.
            self.assertGreater(everything[1]["id"], everything[2]["id"])

            window = client.get(
                "/api/exercise-records", params={"date_from": "2026-10-03", "date_to": "2026-10-10"}
            ).json()["items"]
            self.assertEqual([item["record_date"] for item in window],
                             ["2026-10-10", "2026-10-03", "2026-10-03"])

            single_day = client.get(
                "/api/exercise-records", params={"date_from": "2026-10-03", "date_to": "2026-10-03"}
            ).json()["items"]
            self.assertEqual(len(single_day), 2)
            self.assertEqual(sum(item["duration_minutes"] for item in single_day), 45)

            empty = client.get(
                "/api/exercise-records", params={"date_from": "2026-11-01"}
            ).json()
            self.assertEqual(empty, {"items": []})

    def test_rejects_invalid_input(self):
        self.create_profile()
        invalid_payloads = (
            {**PAYLOAD, "record_date": "2026-02-30"},
            {**PAYLOAD, "record_date": "昨天"},
            {**PAYLOAD, "exercise_type": "   "},
            {**PAYLOAD, "exercise_type": "跑" * 51},
            {**PAYLOAD, "duration_minutes": 0},
            {**PAYLOAD, "duration_minutes": -5},
            {**PAYLOAD, "duration_minutes": 1441},
            {**PAYLOAD, "duration_minutes": 12.5},
            {**PAYLOAD, "intensity": "extreme"},
            {**PAYLOAD, "notes": "备" * 501},
            {k: v for k, v in PAYLOAD.items() if k != "record_date"},
            {**PAYLOAD, "id": 99},
        )
        with self.client() as client:
            for payload in invalid_payloads:
                response = client.post("/api/exercise-records", json=payload)
                self.assertEqual(response.status_code, 422, payload)
            self.assertEqual(client.get("/api/exercise-records").json(), {"items": []})

    def test_rejects_reversed_date_range(self):
        self.create_profile()
        with self.client() as client:
            response = client.get(
                "/api/exercise-records",
                params={"date_from": "2026-10-10", "date_to": "2026-10-01"},
            )
            self.assertEqual(response.status_code, 422)
            self.assertIn("起始日期", response.json()["detail"])

    def test_unknown_id_returns_404(self):
        self.create_profile()
        with self.client() as client:
            self.assertEqual(client.get("/api/exercise-records/999").status_code, 404)
            self.assertEqual(
                client.put("/api/exercise-records/999", json=PAYLOAD).status_code, 404
            )
            self.assertEqual(client.delete("/api/exercise-records/999").status_code, 404)
            self.assertEqual(client.get("/api/exercise-records/not-an-id").status_code, 422)

    def test_recommendation_requires_profile(self):
        with self.client() as client:
            response = client.get("/api/exercise-records/recommendation")
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["detail"], "请先建立个人档案")

    def test_recommendation_uses_bmi_goals_preferences_and_last_week(self):
        with connect(self.path) as connection:
            connection.execute(
                """
                INSERT INTO profiles (id, display_name, height_cm, weight_kg, preferences)
                VALUES (1, '联调档案', 170, 82, '喜欢快走和瑜伽')
                """
            )
            connection.execute(
                """
                INSERT INTO health_goals (profile_id, title, target_value, unit)
                VALUES (1, '减脂 5 公斤', 5, '公斤')
                """
            )
        with self.client() as client:
            for days_ago, minutes, intensity in ((0, 30, "medium"), (2, 45, "high"), (10, 60, "low")):
                response = client.post(
                    "/api/exercise-records",
                    json={
                        "record_date": (TODAY - timedelta(days=days_ago)).isoformat(),
                        "exercise_type": "快走",
                        "duration_minutes": minutes,
                        "intensity": intensity,
                        "notes": "",
                    },
                )
                self.assertEqual(response.status_code, 201)

            response = client.get("/api/exercise-records/recommendation")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["bmi"], 28.4)
            self.assertEqual(data["bmi_label"], "肥胖")
            self.assertEqual(data["focus"], "fat_loss")
            self.assertEqual(data["focus_label"], "减脂优先")
            # BMI >= 28 raises the fat-loss target; the 10-day-old record is outside the week.
            self.assertEqual(data["weekly_target_minutes"], 225)
            self.assertEqual(data["weekly_done_minutes"], 75)
            self.assertEqual(data["days_active_last_week"], 2)
            self.assertEqual(data["weekly_progress_percent"], 33)
            self.assertEqual(data["preferred_types"], ["快走", "瑜伽"])
            self.assertEqual([item["tag"] for item in data["suggestions"]], ["有氧", "力量", "恢复", "今天"])
            self.assertIn("本周还差 150 分钟", data["suggestions"][0]["title"])
            self.assertIn("今天已完成 30 分钟", data["suggestions"][3]["title"])
            self.assertTrue(any("体重基数较大" in note for note in data["safety_notes"]))
            self.assertTrue(any("高强度运动占比偏高" in note for note in data["safety_notes"]))
            evidence = " ".join(data["evidence"])
            self.assertIn("BMI 28.4", evidence)
            self.assertIn("减脂 5 公斤", evidence)
            self.assertIn("喜欢快走和瑜伽", evidence)

    def test_recommendation_handles_missing_body_data_and_medical_history(self):
        with connect(self.path) as connection:
            connection.execute(
                """
                INSERT INTO profiles (id, display_name, medical_history)
                VALUES (1, '联调档案', '高血压')
                """
            )
            connection.execute(
                """
                INSERT INTO health_goals (profile_id, title, target_value, unit)
                VALUES (1, '增肌', 3, '公斤')
                """
            )
        with self.client() as client:
            response = client.get("/api/exercise-records/recommendation")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsNone(data["bmi"])
            self.assertIsNone(data["bmi_label"])
            self.assertEqual(data["focus"], "muscle_gain")
            self.assertEqual(data["weekly_target_minutes"], 150)
            self.assertEqual(data["weekly_done_minutes"], 0)
            self.assertEqual(data["weekly_progress_percent"], 0)
            self.assertEqual(data["preferred_types"], [])
            self.assertIn("还没有运动记录", data["summary"])
            self.assertTrue(any("既往病史" in note for note in data["safety_notes"]))
            self.assertTrue(any("没有完整的身高体重" in line for line in data["evidence"]))
            self.assertTrue(any("力量训练" in item["title"] for item in data["suggestions"]))


if __name__ == "__main__":
    unittest.main()
