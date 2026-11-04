from datetime import datetime, timezone
from typing import Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProfileInput(Input):
    display_name: str = Field(min_length=1, max_length=50)


class SleepInput(Input):
    sleep_at: AwareDatetime
    wake_at: AwareDatetime
    deep_minutes: int | None = Field(default=None, ge=0, le=1440, strict=True)
    light_minutes: int | None = Field(default=None, ge=0, le=1440, strict=True)
    awakenings: int = Field(default=0, ge=0, le=50, strict=True)
    quality: int | None = Field(default=None, ge=1, le=5, strict=True)
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def check_times(self):
        if self.sleep_at.year < 1900 or self.wake_at.year < 1900:
            raise ValueError("睡眠记录日期不能早于 1900 年")
        self.sleep_at = self.sleep_at.astimezone(timezone.utc)
        self.wake_at = self.wake_at.astimezone(timezone.utc)
        duration = (self.wake_at - self.sleep_at).total_seconds() / 60
        if not 1 <= duration <= 1440:
            raise ValueError("醒来必须晚于入睡，单条记录时长为 1 分钟至 24 小时")
        if self.wake_at > datetime.now(timezone.utc):
            raise ValueError("不能记录尚未结束的睡眠")
        if (self.deep_minutes or 0) + (self.light_minutes or 0) > duration:
            raise ValueError("深睡与浅睡之和不能超过总时长；未记录部分可留空")
        return self


class SettingsInput(Input):
    target_minutes: int = Field(default=480, ge=180, le=720, strict=True)
    bedtime: str = Field(default="23:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    alarm_time: str = Field(default="07:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    reminder_minutes: int = Field(default=30, ge=0, le=120, strict=True)
    bedtime_enabled: bool = False
    alarm_enabled: bool = False
    smart_alarm: bool = False
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)), min_length=1, max_length=7)

    @field_validator("weekdays")
    @classmethod
    def check_days(cls, days):
        if any(day not in range(7) for day in days) or len(set(days)) != len(days):
            raise ValueError("星期必须是 0（周一）至 6（周日）的不重复整数")
        return sorted(days)


class ContentInput(Input):
    title: str = Field(min_length=1, max_length=100)
    category: Literal["noise", "meditation"]
    url: HttpUrl


class ContentUpdate(Input):
    title: str = Field(min_length=1, max_length=100)
    category: Literal["noise", "meditation"]
    favorite: bool = False
