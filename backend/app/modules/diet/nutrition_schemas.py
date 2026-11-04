from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.modules.diet.schemas import CalendarDate

Target = Annotated[float, Field(gt=0, allow_inf_nan=False, strict=True)]
class GoalChanges(BaseModel):
    model_config = ConfigDict(extra='forbid')
    effective_from: CalendarDate
    calories_kcal: Target | None = None
    protein_g: Target | None = None
    fat_g: Target | None = None
    carbohydrate_g: Target | None = None
    water_ml: Target | None = None

    @model_validator(mode='after')
    def changed(self):
        if not (self.model_fields_set - {'effective_from'}):
            raise ValueError('至少提交一个需要修改的目标；null表示明确清空')
        return self
