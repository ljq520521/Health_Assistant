"""Exercise record persistence (member C).

Only the ``exercise_records`` table is touched. Every query is scoped to the
single local profile (``profile_id = 1``); the module never accepts a
``profile_id`` from the client. Daily totals and trends are computed in the
frontend from the filtered list, so there is no extra statistics endpoint.
"""

from datetime import date, datetime, timezone

from fastapi import HTTPException

from app.database import connect

PROFILE_ID = 1
PROFILE_REQUIRED = "请先建立个人档案"
RECORD_NOT_FOUND = "运动记录不存在"


def utc_now() -> str:
    """Audit timestamps use the same UTC ``...Z`` shape as the SQL defaults."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def require_profile(connection) -> None:
    if connection.execute("SELECT id FROM profiles WHERE id = ?", (PROFILE_ID,)).fetchone() is None:
        raise HTTPException(status_code=409, detail=PROFILE_REQUIRED)


def find_record(connection, record_id: int) -> dict:
    row = connection.execute(
        "SELECT * FROM exercise_records WHERE id = ? AND profile_id = ?",
        (record_id, PROFILE_ID),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=RECORD_NOT_FOUND)
    return dict(row)


def list_records(path, date_from: date | None = None, date_to: date | None = None) -> dict:
    with connect(path) as connection:
        require_profile(connection)
        sql = "SELECT * FROM exercise_records WHERE profile_id = ?"
        params: list = [PROFILE_ID]
        if date_from is not None:
            sql += " AND record_date >= ?"
            params.append(date_from.isoformat())
        if date_to is not None:
            sql += " AND record_date <= ?"
            params.append(date_to.isoformat())
        rows = connection.execute(sql + " ORDER BY record_date DESC, id DESC", params).fetchall()
        return {"items": [dict(row) for row in rows]}


def get_record(path, record_id: int) -> dict:
    with connect(path) as connection:
        require_profile(connection)
        return find_record(connection, record_id)


def create_record(path, data) -> dict:
    values = data.model_dump(mode="json")
    now = utc_now()
    values["created_at"] = now
    values["updated_at"] = now
    with connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        require_profile(connection)
        columns = ", ".join(values)
        placeholders = ", ".join(f":{key}" for key in values)
        cursor = connection.execute(
            f"INSERT INTO exercise_records (profile_id, {columns}) VALUES (:profile_id, {placeholders})",
            {"profile_id": PROFILE_ID, **values},
        )
        return find_record(connection, cursor.lastrowid)


def update_record(path, record_id: int, data) -> dict:
    """PUT is a full replacement; the server refreshes ``updated_at``."""
    values = data.model_dump(mode="json")
    values["updated_at"] = utc_now()
    with connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        require_profile(connection)
        find_record(connection, record_id)
        assignments = ", ".join(f"{key} = :{key}" for key in values)
        connection.execute(
            f"UPDATE exercise_records SET {assignments} WHERE id = :record_id AND profile_id = :profile_id",
            {**values, "record_id": record_id, "profile_id": PROFILE_ID},
        )
        return find_record(connection, record_id)


def delete_record(path, record_id: int) -> None:
    with connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        require_profile(connection)
        cursor = connection.execute(
            "DELETE FROM exercise_records WHERE id = ? AND profile_id = ?",
            (record_id, PROFILE_ID),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=RECORD_NOT_FOUND)
