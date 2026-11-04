import csv
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse

from app.database import connect
from . import service
from .schemas import ContentInput, ContentUpdate, ProfileInput, SettingsInput, SleepInput

router = APIRouter(tags=["睡眠监测"])


def database(request: Request):
    with connect(request.app.state.settings.database_path) as connection:
        yield connection


def record_or_404(connection, record_id):
    row = connection.execute("SELECT * FROM sleep_records WHERE id=? AND profile_id=1", (record_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "睡眠记录不存在")
    return row


@router.get("/sleep/profile")
def profile(connection=Depends(database)):
    row = connection.execute("SELECT id, display_name FROM profiles WHERE id=1").fetchone()
    return {"profile": dict(row) if row else None}


@router.post("/sleep/profile")
def create_profile(payload: ProfileInput, connection=Depends(database)):
    connection.execute("INSERT INTO profiles(id, display_name) VALUES(1, ?) ON CONFLICT(id) DO NOTHING", (payload.display_name,))
    return profile(connection)


@router.get("/sleep-records")
def records(date_from: date | None = None, date_to: date | None = None, connection=Depends(database)):
    return {"items": service.list_records(connection, date_from, date_to)}


@router.post("/sleep-records", status_code=201)
def create_record(payload: SleepInput, connection=Depends(database)):
    connection.execute("BEGIN IMMEDIATE")
    service.require_profile(connection)
    service.ensure_no_overlap(connection, payload)
    data = payload.model_dump()
    data.update(sleep_at=service.utc_string(payload.sleep_at), wake_at=service.utc_string(payload.wake_at))
    fields = list(data)
    cursor = connection.execute(
        f"INSERT INTO sleep_records ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", list(data.values())
    )
    return service.describe_record(record_or_404(connection, cursor.lastrowid), service.get_settings(connection))


@router.get("/sleep-records/{record_id}")
def get_record(record_id: int, connection=Depends(database)):
    return service.describe_record(record_or_404(connection, record_id), service.get_settings(connection))


@router.put("/sleep-records/{record_id}")
def update_record(record_id: int, payload: SleepInput, connection=Depends(database)):
    connection.execute("BEGIN IMMEDIATE")
    record_or_404(connection, record_id)
    service.ensure_no_overlap(connection, payload, record_id)
    data = payload.model_dump()
    data.update(sleep_at=service.utc_string(payload.sleep_at), wake_at=service.utc_string(payload.wake_at), updated_at=service.utc_string(datetime.now(timezone.utc)))
    connection.execute(f"UPDATE sleep_records SET {','.join(key + '=?' for key in data)} WHERE id=?", [*data.values(), record_id])
    return service.describe_record(record_or_404(connection, record_id), service.get_settings(connection))


@router.delete("/sleep-records/{record_id}", status_code=204)
def delete_record(record_id: int, connection=Depends(database)):
    record_or_404(connection, record_id)
    connection.execute("DELETE FROM sleep_records WHERE id=?", (record_id,))


@router.get("/sleep/settings")
def settings(connection=Depends(database)):
    return service.get_settings(connection)


@router.put("/sleep/settings")
def save_settings(payload: SettingsInput, connection=Depends(database)):
    service.require_profile(connection)
    data = payload.model_dump()
    data["weekdays"] = json.dumps(data["weekdays"])
    data["updated_at"] = service.utc_string(datetime.now(timezone.utc))
    fields = list(data)
    connection.execute(
        f"INSERT INTO sleep_settings (profile_id,{','.join(fields)}) VALUES (1,{','.join('?' for _ in fields)}) "
        f"ON CONFLICT(profile_id) DO UPDATE SET {','.join(key+'=excluded.'+key for key in fields)}", list(data.values())
    )
    return service.get_settings(connection)


@router.get("/sleep/analysis")
def analysis(period: Literal["week", "month"] = "week", end_date: date | None = None, connection=Depends(database)):
    return service.analyze(connection, period, end_date)


@router.get("/sleep/report")
def report(period: Literal["week", "month"] = "week", end_date: date | None = None,
           format: Literal["json", "csv"] = "json", connection=Depends(database)):
    data = service.analyze(connection, period, end_date)
    if format == "json":
        return data
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["睡眠报告", data["date_from"], data["date_to"], "时区 Asia/Shanghai"])
    writer.writerow(["醒来日期", "入睡时间", "醒来时间", "时长(分钟)", "深睡(分钟)", "浅睡(分钟)", "夜醒次数", "主观评分", "作息分", "备注"])
    for record in data["records"]:
        note = record["notes"]
        if note.lstrip().startswith(("=", "+", "-", "@")) or note.startswith(("\t", "\r", "\n")):
            note = "'" + note
        writer.writerow([record["wake_date"], service.parse(record["sleep_at"]).astimezone(service.SHANGHAI).isoformat(),
                         service.parse(record["wake_at"]).astimezone(service.SHANGHAI).isoformat(),
                         record["duration_minutes"], record["deep_minutes"], record["light_minutes"],
                         record["awakenings"], record["quality"], record["score"], note])
    writer.writerow([])
    writer.writerow(["记录天数", data["summary"]["recorded_days"], "周期天数", data["summary"]["period_days"]])
    writer.writerow(["平均时长(分钟)", data["summary"]["average_minutes"]])
    for text in data["observations"] + [service.NOTICE]:
        writer.writerow([text])
    return Response("\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="sleep-{data["date_from"]}-{data["date_to"]}.csv"'})


def content_result(row):
    item = dict(row)
    item["favorite"] = bool(item["favorite"])
    if item["source_type"] == "upload":
        item["source"] = f'/api/sleep/content/{item["id"]}/audio'
    return item


def content_or_404(connection, content_id):
    row = connection.execute("SELECT * FROM sleep_content WHERE id=?", (content_id,)).fetchone()
    if not row:
        raise HTTPException(404, "音频不存在")
    return row


@router.get("/sleep/content")
def content(connection=Depends(database)):
    return {"items": [content_result(row) for row in connection.execute("SELECT * FROM sleep_content ORDER BY favorite DESC, id ASC")]}


@router.post("/sleep/content", status_code=201)
def create_content(payload: ContentInput, connection=Depends(database)):
    cursor = connection.execute("INSERT INTO sleep_content(title,category,source_type,source) VALUES (?,?,'url',?)", (payload.title, payload.category, str(payload.url)))
    return content_result(content_or_404(connection, cursor.lastrowid))


@router.post("/sleep/content/upload", status_code=201)
async def upload(request: Request, title: str = Query(min_length=1, max_length=100), category: Literal["noise", "meditation"] = "meditation"):
    title = title.strip()
    if not title:
        raise HTTPException(422, "请填写音频标题")
    media = request.headers.get("content-type", "").split(";")[0]
    extensions = {"audio/mpeg": ".mp3", "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/ogg": ".ogg", "audio/mp4": ".m4a", "audio/x-m4a": ".m4a"}
    if media not in extensions:
        raise HTTPException(415, "仅支持 MP3、WAV、OGG 和 M4A 音频")
    db_path = request.app.state.settings.database_path
    folder = db_path.parent / "sleep-audio"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (uuid4().hex + extensions[media])
    try:
        size = 0
        with path.open("wb") as output:
            async for chunk in request.stream():
                size += len(chunk)
                if size > 20 * 1024 * 1024:
                    raise HTTPException(413, "音频不能超过 20 MB")
                output.write(chunk)
        if not size:
            raise HTTPException(422, "不能上传空文件")
        with path.open("rb") as uploaded:
            signature = uploaded.read(16)
        valid = {
            ".mp3": signature.startswith(b"ID3") or (len(signature) >= 2 and signature[0] == 255 and signature[1] & 224 == 224),
            ".wav": signature.startswith(b"RIFF") and signature[8:12] == b"WAVE",
            ".ogg": signature.startswith(b"OggS"),
            ".m4a": signature[4:8] == b"ftyp",
        }[path.suffix]
        if not valid:
            raise HTTPException(422, "文件内容与音频类型不符，请选择有效音频")
        with connect(db_path) as connection:
            cursor = connection.execute("INSERT INTO sleep_content(title,category,source_type,source) VALUES (?,?,'upload',?)", (title, category, path.name))
            return content_result(content_or_404(connection, cursor.lastrowid))
    except BaseException:
        path.unlink(missing_ok=True)
        raise


@router.get("/sleep/content/{content_id}/audio")
def audio(content_id: int, request: Request, connection=Depends(database)):
    item = content_or_404(connection, content_id)
    if item["source_type"] != "upload":
        raise HTTPException(404, "该条目没有上传文件")
    path = request.app.state.settings.database_path.parent / "sleep-audio" / Path(item["source"]).name
    if not path.is_file():
        raise HTTPException(404, "音频文件已丢失，请重新上传")
    return FileResponse(path, headers={"X-Content-Type-Options": "nosniff"})


@router.put("/sleep/content/{content_id}")
def update_content(content_id: int, payload: ContentUpdate, connection=Depends(database)):
    content_or_404(connection, content_id)
    connection.execute("UPDATE sleep_content SET title=?,category=?,favorite=? WHERE id=?", (payload.title, payload.category, payload.favorite, content_id))
    return content_result(content_or_404(connection, content_id))


@router.delete("/sleep/content/{content_id}", status_code=204)
def delete_content(content_id: int, request: Request, connection=Depends(database)):
    item = content_or_404(connection, content_id)
    connection.execute("DELETE FROM sleep_content WHERE id=?", (content_id,))
    if item["source_type"] == "upload":
        path = request.app.state.settings.database_path.parent / "sleep-audio" / Path(item["source"]).name
        path.unlink(missing_ok=True)
