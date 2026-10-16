from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from app.modules.diet.library_schemas import Name, FoodInput

Positive=Annotated[float,Field(strict=True,ge=.0001,le=1e9,allow_inf_nan=False)]
Nonnegative=Annotated[float,Field(strict=True,ge=0,le=1e9,allow_inf_nan=False)]
ID=Annotated[int,Field(strict=True,gt=0,le=9223372036854775807)]
Text=Annotated[str,StringConstraints(strip_whitespace=True,max_length=2000)]
class Input(BaseModel):
    model_config=ConfigDict(extra='forbid')
class Revision(Input):
    revision: ID
class IngredientInput(Input):
    food_id: ID
    amount_g: Positive
class RecipeInput(Input):
    name: Name
    category_id: ID | None=None
    description: Text=''
    servings: Positive=1
    preparation_minutes: Annotated[int,Field(strict=True,ge=0,le=100000)] | None=None
    nutrition_mode: Literal['calculated','manual']='calculated'
    manual_calories_kcal: Nonnegative | None=None
    manual_protein_g: Nonnegative | None=None
    manual_fat_g: Nonnegative | None=None
    manual_carbohydrate_g: Nonnegative | None=None
    source_type: Literal['user_entered','referenced','example']='user_entered'
    source_note: Text=''
    source_url: Annotated[str,Field(max_length=2000)]=''
    ingredients: Annotated[list[IngredientInput],Field(min_length=1,max_length=100)]
    steps: Annotated[list[Annotated[str,StringConstraints(strip_whitespace=True,min_length=1,max_length=2000)]],Field(min_length=1,max_length=100)]
    revision: ID | None=None

    @model_validator(mode='after')
    def validate_source(self):
        FoodInput(name=self.name,source_type=self.source_type,source_note=self.source_note,source_url=self.source_url)
        if self.nutrition_mode=='manual' and not self.source_note:
            raise ValueError('手动营养必须填写来源说明')
        if self.nutrition_mode=='calculated' and any(getattr(self,'manual_'+k) is not None for k in ('calories_kcal','protein_g','fat_g','carbohydrate_g')):
            raise ValueError('计算模式不接收手动营养值')
        if len({i.food_id for i in self.ingredients})!=len(self.ingredients):
            raise ValueError('食材重复，请合并克重')
        return self
