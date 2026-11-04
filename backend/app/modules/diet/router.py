from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.modules.diet import service
from app.modules.diet.library_router import LibraryRoute, router as library_router
from app.modules.diet.nutrition_router import router as nutrition_router
from app.modules.diet.recipe_preference_router import router as recipe_preference_router
from app.modules.diet.recipe_recommendation_router import router as recipe_recommendation_router
from app.modules.diet.recipe_router import router as recipe_router
from app.modules.diet.report_router import router as report_router
from app.modules.diet.schemas import CalendarDate, DietList, DietRecord, RecordInput
from app.modules.diet.water_router import router as water_router

records_router = APIRouter(
    prefix="/diet-records", tags=["饮食营养"], route_class=LibraryRoute
)


def database_path(request: Request):
    return request.app.state.settings.database_path


@records_router.get("", response_model=DietList)
def list_records(
    path=Depends(database_path),
    date_from: CalendarDate | None = None,
    date_to: CalendarDate | None = None,
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "起始日期不能晚于结束日期")
    return service.list_records(path, date_from, date_to)


@records_router.post("", response_model=DietRecord, status_code=201)
def create_record(data: RecordInput, path=Depends(database_path)):
    return service.save_record(path, data)


@records_router.get("/{id}", response_model=DietRecord)
def get_record(id: int, path=Depends(database_path)):
    return service.get_record(path, id)


@records_router.put("/{id}", response_model=DietRecord)
def update_record(id: int, data: RecordInput, path=Depends(database_path)):
    return service.save_record(path, data, id)


@records_router.delete("/{id}", status_code=204)
def delete_record(id: int, path=Depends(database_path)):
    service.delete_record(path, id)
    return Response(status_code=204)


from app.modules.diet.access import private_access
from app.modules.diet.catalog_router import router as catalog_router
from app.modules.diet.weekly_router import router as weekly_router

private_router = APIRouter(dependencies=[Depends(private_access)])
router = private_router
router.include_router(records_router)
router.include_router(library_router)
router.include_router(nutrition_router)
router.include_router(water_router)
router.include_router(recipe_router)
router.include_router(recipe_preference_router)
router.include_router(recipe_recommendation_router)
router.include_router(report_router)
router.include_router(weekly_router)
router = APIRouter()
router.include_router(catalog_router)
router.include_router(private_router)
