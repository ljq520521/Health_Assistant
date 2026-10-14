from pydantic import BaseModel, field_validator
from typing import Optional


class CycleRecordCreate(BaseModel):
    start_date: str
    end_date: Optional[str] = None
    flow_level: Optional[str] = None      # light / medium / heavy
    symptoms: str = ""
    mood: str = ""
    notes: str = ""

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        if v and "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("结束日期不能早于开始日期")
        return v

    @field_validator("flow_level")
    @classmethod
    def flow_valid(cls, v):
        if v is not None and v not in ("light", "medium", "heavy"):
            raise ValueError("flow_level 只能是 light / medium / heavy")
        return v


class CycleRecordOut(BaseModel):
    id: int
    profile_id: int
    start_date: str
    end_date: Optional[str] = None
    flow_level: Optional[str] = None
    symptoms: str
    mood: str
    notes: str
    created_at: str
    updated_at: str
