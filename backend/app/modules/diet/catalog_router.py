from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from app.modules.profile.auth import require_admin_consent
from app.modules.diet.library_router import LibraryRoute, database_path
from app.modules.diet import catalog_repository as repository, catalog_links

router=APIRouter(prefix='/diet/catalog',tags=['公共参考目录'],route_class=LibraryRoute)

class FoodReference(BaseModel):
    model_config=ConfigDict(extra='forbid')
    food_key: str=Field(min_length=1,max_length=150)

class RecipeReference(BaseModel):
    model_config=ConfigDict(extra='forbid')
    recipe_key: str=Field(min_length=1,max_length=150)

@router.get('/status')
def status():return repository.metadata()
@router.get('/food-categories')
def food_categories():return repository.categories('food')
@router.get('/recipe-categories')
def recipe_categories():return repository.categories('recipe')
@router.get('/foods')
def foods(q:str='',category:str|None=None):return repository.foods(q,category)
@router.get('/foods/{key}')
def food(key:str):return repository.foods(key=key)
@router.get('/recipes')
def recipes(q:str='',category:str|None=None):
    foods={f['food_key']:f for f in repository.foods()['items']}
    return {'items':[catalog_links.public_recipe(r,foods) for r in repository.recipes(q,category)['items']]}
@router.get('/recipes/{key}')
def recipe(key:str):
    foods={f['food_key']:f for f in repository.foods()['items']}
    return catalog_links.public_recipe(repository.recipes(key=key),foods)
@router.post('/food-references')
def reference(data:FoodReference,path=Depends(database_path),user=Depends(require_admin_consent)):
    return catalog_links.reference(path,data.food_key)
@router.post('/recipe-copies',status_code=201)
def copy(data:RecipeReference,path=Depends(database_path),user=Depends(require_admin_consent)):
    return catalog_links.copy_recipe(path,data.recipe_key)
