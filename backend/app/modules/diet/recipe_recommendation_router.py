from fastapi import APIRouter,Depends
from app.modules.diet.library_router import LibraryRoute,database_path
from app.modules.diet.recipe_recommendation import RecommendationInput,recommend
router=APIRouter(prefix='/diet',tags=['本地食谱推荐'],route_class=LibraryRoute)
@router.post('/recipe-recommendations/preview')
def preview(data:RecommendationInput,path=Depends(database_path)):
    return recommend(path,data)
