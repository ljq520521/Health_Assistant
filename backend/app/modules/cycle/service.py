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
def generate_report():
    settings = get_settings()
    with connect(settings.database_path) as conn:
        rows = conn.execute(
            """
            SELECT start_date, end_date FROM cycle_records
            WHERE profile_id = 1
            ORDER BY start_date ASC
            """
        ).fetchall()

    if len(rows) < 2:
        return {"message": "记录不足，无法生成报告"}

    from datetime import date
    dates = [date.fromisoformat(r["start_date"]) for r in rows]

    # 相邻记录间隔
    intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    # 过滤异常值（21~40 天视为合理）
    valid = [d for d in intervals if 21 <= d <= 40]

    avg = round(sum(valid) / len(valid)) if valid else 0
    shortest = min(valid) if valid else 0
    longest = max(valid) if valid else 0

    # 规律性：标准差
    if valid:
        mean = sum(valid) / len(valid)
        variance = sum((x - mean) ** 2 for x in valid) / len(valid)
        std = variance ** 0.5
        if std <= 3:
            regularity = "规律"
        elif std <= 7:
            regularity = "较规律"
        else:
            regularity = "不规律"
    else:
        std = 0
        regularity = "数据不足"

    # 平均经期长度
    lengths = []
    for r in rows:
        if r["end_date"]:
            d1 = date.fromisoformat(r["start_date"])
            d2 = date.fromisoformat(r["end_date"])
            lengths.append((d2 - d1).days + 1)
    avg_length = round(sum(lengths) / len(lengths)) if lengths else 0

    return {
        "total_records": len(rows),
        "avg_cycle_days": avg,
        "shortest_cycle": shortest,
        "longest_cycle": longest,
        "std_days": round(std, 1),
        "regularity": regularity,
        "avg_period_length": avg_length,
    }
