"""Request and response models for the profile and account module."""

import re
from datetime import date
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.modules.profile.settings import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    USERNAME_PATTERN,
)


def calendar_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("日期必须为 YYYY-MM-DD")
    return date.fromisoformat(value)


CalendarDate = Annotated[date, BeforeValidator(calendar_date)]

DisplayName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]
GoalTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
GoalUnit = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)
]
NoteText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=32,
        pattern=USERNAME_PATTERN,
    ),
]
Password = Annotated[
    str, StringConstraints(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
]


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: DisplayName
    height_cm: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    weight_kg: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    medical_history: NoteText = ""
    allergies: NoteText = ""
    medications: NoteText = ""
    preferences: NoteText = ""


class Profile(BaseModel):
    id: int
    display_name: str
    height_cm: float | None
    weight_kg: float | None
    medical_history: str
    allergies: str
    medications: str
    preferences: str
    # True when the current account asked the server to hide sensitive fields.
    sensitive_masked: bool = False
    created_at: str
    updated_at: str


class GoalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: GoalTitle
    target_value: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    unit: GoalUnit
    current_value: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 0
    due_date: CalendarDate | None = None


class Goal(BaseModel):
    id: int
    profile_id: int
    title: str
    target_value: float
    current_value: float
    unit: str
    due_date: str | None
    progress_percent: float
    created_at: str
    updated_at: str


class GoalList(BaseModel):
    items: list[Goal]


class RegisterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Username
    password: Password

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("密码需同时包含字母和数字")
        return value


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=PASSWORD_MAX_LENGTH)]


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    status: str
    consent_health_data: bool
    mask_sensitive: bool
    analytics_consent: bool
    last_login_at: str | None
    created_at: str
    updated_at: str


class UserList(BaseModel):
    items: list[UserOut]


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut


class SetupOut(BaseModel):
    has_accounts: bool


class PasswordChangeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: Annotated[str, StringConstraints(min_length=1, max_length=PASSWORD_MAX_LENGTH)]
    new_password: Password

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("密码需同时包含字母和数字")
        return value


class PrivacyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_health_data: bool
    mask_sensitive: bool
    analytics_consent: bool


class StatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["active", "disabled"]
