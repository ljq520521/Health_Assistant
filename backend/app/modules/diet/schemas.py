from datetime import date
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, BeforeValidator


def calendar_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('日期必须为 YYYY-MM-DD')
    return date.fromisoformat(value)


CalendarDate = Annotated[date, BeforeValidator(calendar_date)]


class DietInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    record_date: CalendarDate
    meal_type: Literal['breakfast', 'lunch', 'dinner', 'snack']
    food_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    amount_g: Annotated[float, Field(gt=0, allow_inf_nan=False, strict=True)]
    calories_kcal: Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)] | None = None
    notes: str = ''
    nutrition_mode: Literal['manual'] = 'manual'
    protein_g: Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)] | None = None
    fat_g: Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)] | None = None
    carbohydrate_g: Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)] | None = None



class CatalogInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nutrition_mode: Literal['catalog']
    record_date: CalendarDate
    meal_type: Literal['breakfast', 'lunch', 'dinner', 'snack']
    amount_g: Annotated[float, Field(gt=0, allow_inf_nan=False, strict=True)]
    food_id: Annotated[int, Field(gt=0, strict=True)]
    notes: str = ''
    refresh_snapshot: Annotated[bool, Field(strict=True)] = False


RecordInput = DietInput | CatalogInput


class DietRecord(BaseModel):
    id: int
    profile_id: int
    record_date: str
    meal_type: str
    food_name: str
    amount_g: float
    calories_kcal: float | None
    notes: str
    created_at: str
    updated_at: str
    nutrition_mode: str = 'manual'
    food_id: int | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbohydrate_g: float | None = None
    snapshot_calories_per_100g: float | None = None
    snapshot_protein_g_per_100g: float | None = None
    snapshot_fat_g_per_100g: float | None = None
    snapshot_carbohydrate_g_per_100g: float | None = None
    food_version_at: str | None = None
    nutrition_source_note: str = ''
    is_example: bool = False


class DietList(BaseModel):
    items: list[DietRecord]
