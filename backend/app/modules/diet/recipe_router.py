from typing import Annotated
from fastapi import APIRouter,Depends,Response,Query
from app.modules.diet.library_router import LibraryRoute,database_path
from app.modules.diet.library_schemas import CategoryInput
from app.modules.diet.recipe_schemas import RecipeInput,Revision
from app.modules.diet import recipe_service as service
router=APIRouter(prefix='/diet',tags=['食谱'],route_class=LibraryRoute)
@router.get('/recipe-categories')
def categories(path=Depends(database_path)): return service.categories(path)
@router.post('/recipe-categories',status_code=201)
def create_category(data:CategoryInput,path=Depends(database_path)): return service.save_category(path,data)
@router.get('/recipe-categories/{id}')
def category(id:int,path=Depends(database_path)): return service.category(path,id)
@router.put('/recipe-categories/{id}')
def update_category(id:int,data:CategoryInput,path=Depends(database_path)): return service.save_category(path,data,id)
@router.delete('/recipe-categories/{id}',status_code=204)
def delete_category(id:int,path=Depends(database_path)): service.delete_category(path,id);return Response(status_code=204)
@router.get('/recipes')
def recipes(q:Annotated[str,Query(max_length=100)]='',category_id:int|None=None,path=Depends(database_path)): return service.recipes(path,q,category_id)
@router.post('/recipes',status_code=201)
def create(data:RecipeInput,path=Depends(database_path)): return service.save(path,data)
@router.get('/recipes/{id}')
def get(id:int,path=Depends(database_path)): return service.get(path,id)
@router.put('/recipes/{id}')
def update(id:int,data:RecipeInput,path=Depends(database_path)): return service.save(path,data,id)
@router.delete('/recipes/{id}',status_code=204)
def archive(id:int,path=Depends(database_path)): service.archive(path,id);return Response(status_code=204)
@router.post('/recipes/{id}/refresh-nutrition')
def refresh(id:int,data:Revision,path=Depends(database_path)): return service.refresh(path,id,data)
