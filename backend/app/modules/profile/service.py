"""Health profile and cumulative health goals (single local profile id=1)."""

from fastapi import HTTPException

from app.database import connect
from app.modules.profile.schemas import GoalInput, ProfileInput
from app.modules.profile.settings import utc_now

SENSITIVE_FIELDS = ("medical_history", "allergies", "medications")


def _shape_profile(row, user) -> dict:
    profile = dict(row)
    profile["sensitive_masked"] = False
    # Masking is a display preference for viewer accounts. The admin always
    # reads the real values, otherwise a masked GET followed by PUT would erase
    # the very fields it hid.
    if user["role"] != "admin" and user["mask_sensitive"]:
        for field in SENSITIVE_FIELDS:
            profile[field] = ""
        profile["sensitive_masked"] = True
    return profile


def get_profile(path, user) -> dict:
    with connect(path) as connection:
        row = connection.execute("SELECT * FROM profiles WHERE id = 1").fetchone()
    if row is None:
        raise HTTPException(404, "尚未建立个人档案")
    return _shape_profile(row, user)


def save_profile(path, data: ProfileInput, user) -> dict:
    values = data.model_dump()
    now = utc_now()
    with connect(path) as connection:
        exists = (
            connection.execute("SELECT id FROM profiles WHERE id = 1").fetchone()
            is not None
        )
        if exists:
            connection.execute(
                """UPDATE profiles
                   SET display_name = ?, height_cm = ?, weight_kg = ?,
                       medical_history = ?, allergies = ?, medications = ?,
                       preferences = ?, updated_at = ?
                   WHERE id = 1""",
                (
                    values["display_name"],
                    values["height_cm"],
                    values["weight_kg"],
                    values["medical_history"],
                    values["allergies"],
                    values["medications"],
                    values["preferences"],
                    now,
                ),
            )
        else:
            connection.execute(
                """INSERT INTO profiles
                       (id, display_name, height_cm, weight_kg,
                        medical_history, allergies, medications, preferences,
                        created_at, updated_at)
                   VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    values["display_name"],
                    values["height_cm"],
                    values["weight_kg"],
                    values["medical_history"],
                    values["allergies"],
                    values["medications"],
                    values["preferences"],
                    now,
                    now,
                ),
            )
        row = connection.execute("SELECT * FROM profiles WHERE id = 1").fetchone()
    return _shape_profile(row, user)


def _require_profile(connection) -> None:
    if connection.execute("SELECT id FROM profiles WHERE id = 1").fetchone() is None:
        raise HTTPException(409, "请先建立个人档案")


def _shape_goal(row) -> dict:
    goal = dict(row)
    goal["progress_percent"] = round(
        min(goal["current_value"] / goal["target_value"], 1.0) * 100, 1
    )
    return goal


def _find_goal(connection, goal_id: int):
    row = connection.execute(
        "SELECT * FROM health_goals WHERE id = ? AND profile_id = 1", (goal_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "健康目标不存在")
    return row


def list_goals(path) -> dict:
    with connect(path) as connection:
        _require_profile(connection)
        rows = connection.execute(
            """SELECT * FROM health_goals
               WHERE profile_id = 1
               ORDER BY created_at DESC, id DESC"""
        ).fetchall()
    return {"items": [_shape_goal(row) for row in rows]}


def get_goal(path, goal_id: int) -> dict:
    with connect(path) as connection:
        _require_profile(connection)
        return _shape_goal(_find_goal(connection, goal_id))


def create_goal(path, data: GoalInput) -> dict:
    values = data.model_dump()
    now = utc_now()
    due_date = values["due_date"].isoformat() if values["due_date"] else None
    with connect(path) as connection:
        _require_profile(connection)
        cursor = connection.execute(
            """INSERT INTO health_goals
                   (profile_id, title, target_value, current_value, unit, due_date,
                    created_at, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
            (
                values["title"],
                values["target_value"],
                values["current_value"],
                values["unit"],
                due_date,
                now,
                now,
            ),
        )
        row = connection.execute(
            "SELECT * FROM health_goals WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return _shape_goal(row)


def update_goal(path, goal_id: int, data: GoalInput) -> dict:
    values = data.model_dump()
    now = utc_now()
    due_date = values["due_date"].isoformat() if values["due_date"] else None
    with connect(path) as connection:
        _require_profile(connection)
        _find_goal(connection, goal_id)
        connection.execute(
            """UPDATE health_goals
               SET title = ?, target_value = ?, current_value = ?, unit = ?,
                   due_date = ?, updated_at = ?
               WHERE id = ? AND profile_id = 1""",
            (
                values["title"],
                values["target_value"],
                values["current_value"],
                values["unit"],
                due_date,
                now,
                goal_id,
            ),
        )
        row = connection.execute(
            "SELECT * FROM health_goals WHERE id = ?", (goal_id,)
        ).fetchone()
    return _shape_goal(row)


def delete_goal(path, goal_id: int) -> None:
    with connect(path) as connection:
        _require_profile(connection)
        cursor = connection.execute(
            "DELETE FROM health_goals WHERE id = ? AND profile_id = 1", (goal_id,)
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, "健康目标不存在")
