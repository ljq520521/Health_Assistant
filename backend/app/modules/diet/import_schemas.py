"""Reviewed offline import contract, separate from pending preparation drafts."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Category = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Hash = Annotated[str, StringConstraints(pattern=r'^[a-f0-9]{64}$')]
Positive = Annotated[float, Field(gt=0, le=1e9, allow_inf_nan=False)]
Macro = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
Energy = Annotated[float, Field(ge=0, le=1000, allow_inf_nan=False)]
ReviewStatus = Literal['approved', 'pending_final_confirmation']

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class FileRef(Strict):
    path: Text
    sha256: Hash

class Source(FileRef):
    url: Text
    release: Text
    data_type: Literal['SR Legacy', 'Foundation']
    retrieved_at: Text

class Manifest(Strict):
    schema_version: Literal[1]
    package_id: Name
    package_version: Annotated[int, Field(gt=0)]
    purpose: Literal['reviewed_data', 'test_fixture', 'temporary_review', 'course_demo'] = 'reviewed_data'
    review_status: ReviewStatus
    reviewer: Name
    reviewed_at: Text
    mapping_policy: Literal['usda-per100-v1']
    format: Literal['json', 'csv']
    files: dict[str, FileRef]
    sources: Annotated[list[Source], Field(min_length=1)]
    documentation: list[FileRef] = []

class Food(Strict):
    source_key: Text
    fdc_id: Annotated[int, Field(gt=0)]
    source_archive: Text
    original_english_name: Text
    name_zh: Name
    category: Category
    food_state: Text
    edible_part: Text
    match_evidence: Text
    basis_g: Literal[100]
    energy_unit: Literal['kcal']
    nutrient_unit: Literal['g']
    calories_per_100g: Energy | None
    protein_g_per_100g: Macro | None
    fat_g_per_100g: Macro | None
    carbohydrate_g_per_100g: Macro | None
    source_url: Text
    review_status: ReviewStatus

    @model_validator(mode='after')
    def identity(self):
        if self.source_key != f'usda:fdc:{self.fdc_id}':
            raise ValueError('source_key与FDC ID不一致')
        if self.source_url != f'https://fdc.nal.usda.gov/food-details/{self.fdc_id}/nutrients':
            raise ValueError('来源必须是对应FDC ID的官方详情页')
        return self

class Ingredient(Strict):
    food_source_key: Text
    amount_g: Positive

class Recipe(Strict):
    recipe_key: Annotated[str, StringConstraints(pattern=r'^health-assistant:recipe:[a-z0-9-]+$')]
    recipe_version: Annotated[int, Field(gt=0)]
    name: Name
    category: Category
    description: Annotated[str, StringConstraints(max_length=2000)]
    servings: Positive
    preparation_minutes: Annotated[int, Field(ge=0, le=100000)] | None
    time_evidence: Text | None
    source_note: Text
    ingredients: Annotated[list[Ingredient], Field(min_length=1, max_length=100)]
    steps: Annotated[list[Text], Field(min_length=1, max_length=100)]
    review_status: ReviewStatus

    @model_validator(mode='after')
    def provenance(self):
        if '项目团队自编' not in self.source_note or 'AI' not in self.source_note:
            raise ValueError('自编配方须保留团队及AI辅助来源说明')
        if self.preparation_minutes is not None and not self.time_evidence:
            raise ValueError('制作时间必须提供核验依据')
        if len({i.food_source_key for i in self.ingredients}) != len(self.ingredients):
            raise ValueError('同一食材应合并克重')
        return self
