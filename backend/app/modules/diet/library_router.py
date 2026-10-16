from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from app.modules.diet import library_service as service
from app.modules.diet.library_schemas import CategoryInput, CategoryList, CategoryRecord, FoodInput, FoodList, FoodRecord
from app.modules.diet.settings import BUSINESS_TIME_ZONE


class LibraryRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def handle(request):
            try:
                return await handler(request)
            except service.LibraryError as exc:
                return JSONResponse(status_code=exc.status, content={'detail': exc.detail, 'code': exc.code})
            except RequestValidationError as exc:
                # Do not echo non-finite inputs into JSON error responses.
                errors = [{key: error[key] for key in ('type', 'loc', 'msg')} for error in exc.errors()]
                return JSONResponse(status_code=422, content={'detail': errors})
        return handle


router = APIRouter(prefix='/diet', tags=['食物营养库'], route_class=LibraryRoute)


def database_path(request: Request):
    return request.app.state.settings.database_path


@router.get('/config')
def config(request: Request):
    result = {'time_zone': BUSINESS_TIME_ZONE}
    demo = getattr(request.app.state, 'diet_demo', None)
    if demo is not None:
        result['demo'] = demo
    return result


@router.get('/food-categories', response_model=CategoryList)
def categories(path=Depends(database_path)):
    return service.categories(path)


@router.post('/food-categories', response_model=CategoryRecord, status_code=201)
def create_category(data: CategoryInput, path=Depends(database_path)):
    return service.save_category(path, data)


@router.get('/food-categories/{id}', response_model=CategoryRecord)
def get_category(id: int, path=Depends(database_path)):
    return service.get_category(path, id)


@router.put('/food-categories/{id}', response_model=CategoryRecord)
def update_category(id: int, data: CategoryInput, path=Depends(database_path)):
    return service.save_category(path, data, id)


@router.delete('/food-categories/{id}', status_code=204)
def delete_category(id: int, path=Depends(database_path)):
    service.delete_category(path, id)
    return Response(status_code=204)


@router.get('/foods', response_model=FoodList)
def foods(path=Depends(database_path), q: Annotated[str, Query(max_length=100)] = '', category_id: Annotated[int | None, Query(gt=0)] = None, uncategorized: bool = False):
    if category_id is not None and uncategorized:
        raise service.LibraryError(422, 'INVALID_FILTER', '具体分类与未分类不能同时筛选')
    return service.foods(path, q.strip(), category_id, uncategorized)


@router.post('/foods', response_model=FoodRecord, status_code=201)
def create_food(data: FoodInput, path=Depends(database_path)):
    return service.save_food(path, data)


@router.get('/foods/{id}', response_model=FoodRecord)
def get_food(id: int, path=Depends(database_path)):
    return service.get_food(path, id)


@router.put('/foods/{id}', response_model=FoodRecord)
def update_food(id: int, data: FoodInput, path=Depends(database_path)):
    return service.save_food(path, data, id)


@router.delete('/foods/{id}', status_code=204)
def archive_food(id: int, path=Depends(database_path)):
    service.archive_food(path, id)
    return Response(status_code=204)
