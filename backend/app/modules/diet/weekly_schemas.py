"""Strict client commands. Generated recipe/nutrient snapshots are never accepted."""
from datetime import date, timedelta
from typing import Annotated, Literal
from pydantic import Field, model_validator
from app.modules.diet.recipe_schemas import Input, ID, Text
from app.modules.diet.schemas import CalendarDate

Fingerprint = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]
Ratio = Annotated[float, Field(strict=True, gt=0, le=1, allow_inf_nan=False)]
Portions = Annotated[float, Field(strict=True, ge=.0001, le=10000, allow_inf_nan=False)]
Statuses = Literal['pending', 'completed', 'not_completed', 'partial', 'not_applicable']
MEALS = ('breakfast', 'lunch', 'dinner')
STATUS_VALUES = ('pending', 'completed', 'not_completed', 'partial', 'not_applicable')


class MealRatios(Input):
    breakfast: Ratio | None = None
    lunch: Ratio | None = None
    dinner: Ratio | None = None

    @model_validator(mode='after')
    def no_more_than_daily(self):
        if sum(value for value in self.model_dump().values() if value is not None) > 1 + 1e-9:
            raise ValueError('已填写的三餐目标占比之和不能超过100%')
        return self


class PlanInput(Input):
    start_date: CalendarDate
    portions: Portions = 1
    meal_ratios: MealRatios = Field(default_factory=MealRatios)
    selected_goal_ids: Annotated[list[ID], Field(max_length=50)] = Field(default_factory=list)
    expected_context_hash: Fingerprint

    @model_validator(mode='after')
    def valid_week(self):
        if self.start_date > date.max - timedelta(days=6):
            raise ValueError('计划开始日期不能超过9999-12-25')
        if len(set(self.selected_goal_ids)) != len(self.selected_goal_ids):
            raise ValueError('健康目标ID不能重复')
        return self


class ConfirmInput(Input):
    profile_fingerprint: Fingerprint
    rules_fingerprint: Fingerprint
    allergy_rule_ids: Annotated[list[ID], Field(max_length=200)] = Field(default_factory=list)
    preference_rule_ids: Annotated[list[ID], Field(max_length=200)] = Field(default_factory=list)

    @model_validator(mode='after')
    def unique_ids(self):
        for values in (self.allergy_rule_ids, self.preference_rule_ids):
            if len(set(values)) != len(values):
                raise ValueError('规则ID不能重复')
        return self


class RefreshInput(Input):
    expected_context_hash: Fingerprint
    expected_plan_revision: ID


class FeedbackInput(Input):
    expected_revision: Annotated[int, Field(strict=True, ge=0, le=9223372036854775807)]
    status: Statuses
    note: Text = ''
    reason: Text = ''
