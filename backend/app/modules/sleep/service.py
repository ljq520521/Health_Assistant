"""Personal habit metrics, not clinical sleep staging or a diagnostic scale."""
import json
from datetime import datetime, time, timedelta, timezone
from statistics import mean
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from .schemas import SettingsInput

SHANGHAI = ZoneInfo("Asia/Shanghai")
NOTICE = "评分为个人作息参考，不是医学量表；深浅睡由用户填写，系统不自动检测睡眠阶段。"


def utc_string(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def minutes(value):
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def clock(value):
    value %= 1440
    return f"{value // 60:02d}:{value % 60:02d}"


def get_settings(connection):
    row = connection.execute("SELECT * FROM sleep_settings WHERE profile_id=1").fetchone()
    settings = SettingsInput().model_dump()
    if row:
        settings.update({key: row[key] for key in settings})
        settings["weekdays"] = json.loads(settings["weekdays"])
        for key in ("bedtime_enabled", "alarm_enabled", "smart_alarm"):
            settings[key] = bool(settings[key])
    start = minutes(settings["bedtime"])
    latest = minutes(settings["alarm_time"])
    if latest <= start:
        latest += 1440
    candidate = start + ((latest - start) // 90) * 90
    suggested = candidate if candidate > start and latest - candidate <= 30 else latest
    settings["effective_alarm_time"] = clock(suggested if settings["smart_alarm"] else latest)
    settings["reminder_time"] = clock(start - settings["reminder_minutes"])
    return settings


def require_profile(connection):
    if not connection.execute("SELECT 1 FROM profiles WHERE id=1").fetchone():
        raise HTTPException(409, "请先建立本地健康档案")


def describe_record(row, settings):
    result = dict(row)
    sleep_at, wake_at = parse(row["sleep_at"]), parse(row["wake_at"])
    duration = (wake_at - sleep_at).total_seconds() / 60
    local_sleep = sleep_at.astimezone(SHANGHAI)
    deviation = abs(local_sleep.hour * 60 + local_sleep.minute - minutes(settings["bedtime"]))
    deviation = min(deviation, 1440 - deviation)
    dimensions = [
        {"name": "目标时长", "points": round(min(duration / settings["target_minutes"], 1) * 40, 1), "max": 40},
        {"name": "睡眠连续性", "points": max(0, 25 - row["awakenings"] * 5), "max": 25},
        {"name": "作息规律", "points": round(max(0, 1 - deviation / 180) * 15, 1), "max": 15},
    ]
    if row["quality"] is not None:
        dimensions.append({"name": "主观感受", "points": row["quality"] * 4, "max": 20})
    score = round(sum(d["points"] for d in dimensions) / sum(d["max"] for d in dimensions) * 100)
    alerts = []
    if abs(duration - settings["target_minutes"]) >= 120:
        alerts.append("时长偏离个人目标至少 2 小时")
    if row["awakenings"] >= 3:
        alerts.append("本次记录夜醒至少 3 次")
    if deviation >= 120:
        alerts.append("入睡偏离计划至少 2 小时")
    if row["quality"] is not None and row["quality"] <= 2:
        alerts.append("本次主观感受较低")
    result.update(
        sleep_at=utc_string(sleep_at), wake_at=utc_string(wake_at),
        wake_date=wake_at.astimezone(SHANGHAI).date().isoformat(),
        duration_minutes=round(duration, 1), score=score,
        dimensions=dimensions, alerts=alerts,
        stage_unrecorded_minutes=round(duration - (row["deep_minutes"] or 0) - (row["light_minutes"] or 0), 1),
        assessment_complete=row["quality"] is not None,
    )
    return result


def list_records(connection, start=None, end=None):
    for value in (start, end):
        if value and not 1900 <= value.year <= 9998:
            raise HTTPException(422, "日期年份需在 1900 至 9998 之间")
    if start and end and start > end:
        raise HTTPException(422, "开始日期不能晚于结束日期")
    clauses, params = ["profile_id=1"], []
    if start:
        clauses.append("julianday(wake_at) >= julianday(?)")
        params.append(utc_string(datetime.combine(start, time.min, SHANGHAI)))
    if end:
        clauses.append("julianday(wake_at) < julianday(?)")
        params.append(utc_string(datetime.combine(end + timedelta(days=1), time.min, SHANGHAI)))
    rows = connection.execute(
        "SELECT * FROM sleep_records WHERE " + " AND ".join(clauses) + " ORDER BY julianday(wake_at) DESC, id DESC", params
    ).fetchall()
    settings = get_settings(connection)
    return [describe_record(row, settings) for row in rows]


def ensure_no_overlap(connection, payload, exclude_id=0):
    conflict = connection.execute(
        "SELECT id FROM sleep_records WHERE profile_id=1 AND id != ? "
        "AND julianday(sleep_at) < julianday(?) AND julianday(wake_at) > julianday(?)",
        (exclude_id, utc_string(payload.wake_at), utc_string(payload.sleep_at)),
    ).fetchone()
    if conflict:
        raise HTTPException(409, "此时间段与已有睡眠记录重叠，请先编辑原记录")


def analyze(connection, period, end_date=None):
    end = end_date or datetime.now(SHANGHAI).date()
    if end.year < 1901 or end > datetime.now(SHANGHAI).date():
        raise HTTPException(422, "统计截止日期需在 1901 年至今天之间")
    days = 7 if period == "week" else 30
    start = end - timedelta(days=days - 1)
    records = list_records(connection, start, end)
    previous = list_records(connection, start - timedelta(days=days), start - timedelta(days=1))
    settings = get_settings(connection)

    def daily_values(items):
        values = {}
        for record in items:
            values.setdefault(record["wake_date"], []).append(record)
        return values

    grouped, prior = daily_values(records), daily_values(previous)
    daily = []
    for offset in range(days):
        key = (start + timedelta(days=offset)).isoformat()
        items = grouped.get(key, [])
        daily.append({
            "date": key, "count": len(items),
            "duration_minutes": round(sum(r["duration_minutes"] for r in items), 1) if items else None,
            "score": round(mean(r["score"] for r in items)) if items else None,
        })
    recorded_days = [d for d in daily if d["count"]]
    average = round(mean(d["duration_minutes"] for d in recorded_days), 1) if recorded_days else None
    prior_average = mean(sum(r["duration_minutes"] for r in group) for group in prior.values()) if prior else None
    summary = {
        "record_count": len(records), "recorded_days": len(grouped), "period_days": days,
        "average_minutes": average,
        "average_score": round(mean(r["score"] for r in records)) if records else None,
        "target_days": sum(d["duration_minutes"] >= settings["target_minutes"] for d in recorded_days),
        "previous_recorded_days": len(prior),
        "change_minutes": round(average - prior_average, 1) if average is not None and prior_average is not None else None,
        "alert_count": sum(bool(r["alerts"]) for r in records),
    }
    observations = [f"本期记录 {len(records)} 次，覆盖 {len(grouped)}/{days} 天；没有记录的日期不作为零时长参与均值。"]
    if records:
        observations.append(f"已记录日期平均睡眠 {average / 60:.1f} 小时，个人目标 {settings['target_minutes'] / 60:g} 小时。")
        observations.append(f"有 {summary['alert_count']} 条记录触发作息偏离提示，可结合原始记录核对。")
    else:
        observations.append("本期暂无记录，暂不能判断变化或生成评分结论。")
    if len(grouped) < days:
        observations.append("记录不完整，周/月变化仅供对照；缺失数据会影响比较结果。")
    return {
        "period": period, "date_from": start.isoformat(), "date_to": end.isoformat(),
        "settings": settings, "summary": summary, "daily": daily, "records": records,
        "observations": observations, "notice": NOTICE,
        "generated_at": utc_string(datetime.now(timezone.utc)),
    }
