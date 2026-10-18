from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import date

# 创建路由实例
router = APIRouter()

# 1. 定义数据模型（对应前端传过来的数据）
class ExerciseRecord(BaseModel):
    type: str           # 运动类型
    duration: int       # 时长（分钟）
    intensity: str      # 强度
    calories: int       # 估算消耗
    record_date: str    # 日期

# 2. 模拟一个“数据库”（实际开发中这里会连 SQLite，现在用列表暂存方便测试）
fake_db = [
    {
        "id": 1,
        "type": "跑步",
        "duration": 30,
        "intensity": "中等",
        "calories": 300,
        "record_date": "2026-10-15"
    }
]

# 3. 写接口：获取所有运动记录 (GET)
@router.get("/records")
def get_records():
    # 返回模拟数据库里的所有记录
    return {"code": 200, "message": "获取成功", "data": fake_db}

# 4. 写接口：添加一条运动记录 (POST)
@router.post("/records")
def add_record(record: ExerciseRecord):
    # 简单校验一下
    if record.duration <= 0:
        raise HTTPException(status_code=400, detail="运动时长必须大于0")

    # 生成一个新的 ID 和记录
    new_record = {
        "id": len(fake_db) + 1,
        "type": record.type,
        "duration": record.duration,
        "intensity": record.intensity,
        "calories": record.calories,
        "record_date": record.record_date
    }
    
    # 保存到“数据库”
    fake_db.append(new_record)
    
    return {"code": 200, "message": "添加成功", "data": new_record}
