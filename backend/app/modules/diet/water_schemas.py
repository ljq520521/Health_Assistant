import re
from datetime import datetime, timezone
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, BeforeValidator, model_validator

def timestamp(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})',value):
        raise ValueError('时间必须为带时区的 ISO 8601 字符串')
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return parsed.astimezone(timezone.utc)
    except (ValueError,OverflowError):
        raise ValueError('时间超出可支持范围')

class WaterInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    drank_at: Annotated[datetime,BeforeValidator(timestamp)]
    amount_ml: Annotated[int,Field(strict=True,gt=0,le=1000000)]
    notes: Annotated[str,Field(max_length=2000)] = ''

Clock = Annotated[str,Field(pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$')]
class ReminderInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    enabled: Annotated[bool,Field(strict=True)] = False
    mode: Literal['fixed_times','interval'] = 'interval'
    fixed_times: Annotated[list[Clock],Field(max_length=48)] = []
    interval_minutes: Annotated[int,Field(strict=True,ge=1,le=1440)] = 60
    active_start: Clock = '09:00'
    active_end: Clock = '18:00'
    pause_when_goal_met: Annotated[bool,Field(strict=True)] = True

    @model_validator(mode='after')
    def schedule(self):
        if self.active_start >= self.active_end:
            raise ValueError('提醒结束时间必须晚于开始时间，不支持跨午夜')
        self.fixed_times=sorted(set(self.fixed_times))
        if self.mode=='fixed_times':
            if not self.fixed_times or any(t<self.active_start or t>self.active_end for t in self.fixed_times):
                raise ValueError('固定提醒至少一个，且全部位于活动窗口内')
        else:
            minutes=lambda s: int(s[:2])*60+int(s[3:])
            if self.interval_minutes > minutes(self.active_end)-minutes(self.active_start):
                raise ValueError('提醒间隔不能大于活动窗口')
        return self
