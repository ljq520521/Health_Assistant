from app.config import get_settings
from app.database import connect
from . import schemas


def list_records():
    settings = get_settings()
    with connect(settings.database_path) as conn:
        rows = conn.execute(
            """
            SELECT id, profile_id, start_date, end_date, flow_level,
                   symptoms, mood, notes, created_at, updated_at
            FROM cycle_records
            WHERE profile_id = 1
            ORDER BY start_date DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def create_record(data: schemas.CycleRecordCreate):
    settings = get_settings()
    with connect(settings.database_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO cycle_records
                (profile_id, start_date, end_date, flow_level, symptoms, mood, notes)
            VALUES
                (1, :start_date, :end_date, :flow_level, :symptoms, :mood, :notes)
            """,
            data.model_dump(),
        )
        record_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM cycle_records WHERE id = ?", (record_id,)
        ).fetchone()
        return dict(row)


def delete_record(record_id: int):
    settings = get_settings()
    with connect(settings.database_path) as conn:
        cursor = conn.execute(
            "DELETE FROM cycle_records WHERE id = ? AND profile_id = 1",
            (record_id,),
        )
        if cursor.rowcount == 0:
            return {"message": "记录不存在"}
        return {"message": "删除成功"}


def predict_next_cycle():
    settings = get_settings()
    with connect(settings.database_path) as conn:
        rows = conn.execute(
            """
            SELECT start_date FROM cycle_records
            WHERE profile_id = 1
            ORDER BY start_date DESC LIMIT 2
            """
        ).fetchall()

    if len(rows) < 2:
        return {"message": "记录不足，无法预测"}

    from datetime import date, timedelta
    d1 = date.fromisoformat(rows[0]["start_date"])
    d2 = date.fromisoformat(rows[1]["start_date"])
    interval = (d1 - d2).days
    next_date = d1 + timedelta(days=interval)
    return {
        "last_start": d1.isoformat(),
        "avg_cycle_days": interval,
        "predicted_next": next_date.isoformat(),
    }
