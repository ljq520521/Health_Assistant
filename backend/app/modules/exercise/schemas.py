"""Request / response models for the exercise module (member C).

Field names and rules mirror ``docs/04-database.md`` and ``docs/05-api.md``:
``duration_minutes`` is a positive integer, ``intensity`` is one of
``low/medium/high`` and ``notes`` defaults to an empty string. No calorie,
heart-rate or training-plan field is stored in this version.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Intensity = Literal["low", "medium", "high"]

# One day has 1440 minutes; anything larger is a data-entry mistake.
MAX_DURATION_MINUTES = 1440
MAX_NOTES_LENGTH = 500


class ExerciseInput(BaseModel):
    """Payload accepted by POST /api/exercise-records and PUT /{id}."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    record_date: date
    exercise_type: str = Field(min_length=1, max_length=50)
    duration_minutes: int = Field(ge=1, le=MAX_DURATION_MINUTES)
    intensity: Intensity
    notes: str = Field(default="", max_length=MAX_NOTES_LENGTH)


class ExerciseRecord(BaseModel):
    """A stored exercise record, with server-owned fields included."""

    id: int
    profile_id: int
    record_date: date
    exercise_type: str
    duration_minutes: int
    intensity: Intensity
    notes: str
    created_at: str
    updated_at: str


class ExerciseList(BaseModel):
    items: list[ExerciseRecord]
