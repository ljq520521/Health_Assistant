from typing import Annotated,Literal
from pydantic import Field,model_validator
from app.modules.diet.recipe_schemas import Input,ID,Nonnegative,Text
from app.modules.diet.library_schemas import Name

class InventoryInput(Input):
    food_id: ID
    quantity_g: Nonnegative
    notes: Text=''
    revision: ID | None=None
class TermInput(Input):
    name: Name
    kind: Literal['ingredient','allergen']='ingredient'
    aliases: Annotated[list[Name],Field(max_length=50)]=[]
class CompositionTerm(Input):
    term_id: ID
    relation: Literal['contains','may_contain']
class CompositionInput(Input):
    ingredient_status: Literal['unknown','partial','declared_complete']='unknown'
    allergen_status: Literal['unknown','partial','declared_complete']='unknown'
    assessed_food_updated_at: Annotated[str,Field(min_length=1,max_length=100)]
    source_note: Text=''
    terms: Annotated[list[CompositionTerm],Field(max_length=200)]=[]
    @model_validator(mode='after')
    def checked(self):
        if 'declared_complete' in (self.ingredient_status,self.allergen_status) and not self.source_note:
            raise ValueError('声明已完整核对时必须填写核对依据')
        if len({(t.term_id,t.relation) for t in self.terms})!=len(self.terms):
            raise ValueError('组成成分重复')
        return self
class PreferenceInput(Input):
    food_id: ID | None=None
    term_id: ID | None=None
    rule_type: Literal['like','dislike','allergy','forbidden']
    notes: Text=''
    @model_validator(mode='after')
    def target(self):
        if (self.food_id is None)==(self.term_id is None):raise ValueError('必须且只能选择一种食物或规范术语')
        return self
