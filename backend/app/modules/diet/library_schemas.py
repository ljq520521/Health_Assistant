from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, TypeAdapter, field_validator, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Nutrient = Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)]


class CategoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class CategoryRecord(CategoryInput):
    id: int
    profile_id: int
    created_at: str
    updated_at: str


class CategoryList(BaseModel):
    items: list[CategoryRecord]


class FoodInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    category_id: Annotated[int, Field(gt=0, strict=True)] | None = None
    calories_per_100g: Nutrient | None = None
    protein_g_per_100g: Nutrient | None = None
    fat_g_per_100g: Nutrient | None = None
    carbohydrate_g_per_100g: Nutrient | None = None
    source_type: Literal['user_entered', 'referenced', 'example'] = 'user_entered'
    source_note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ''
    source_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] = ''

    @field_validator('source_url')
    @classmethod
    def safe_source_url(cls, value):
        if value:
            TypeAdapter(HttpUrl).validate_python(value)
        return value

    @model_validator(mode='after')
    def require_reference(self):
        if self.source_type == 'referenced' and not (self.source_note or self.source_url):
            raise ValueError('参考资料来源必须填写来源说明或链接')
        return self


class FoodRecord(FoodInput):
    id: int
    profile_id: int
    is_example: bool
    deleted_at: str | None
    created_at: str
    updated_at: str


class FoodList(BaseModel):
    items: list[FoodRecord]
