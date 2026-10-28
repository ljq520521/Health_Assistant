"""HTTP endpoints for exercise records (member C).

Paths are mounted under ``/api`` by ``app.main``, so the public routes are
``/api/exercise-records``. Status codes follow ``docs/05-api.md``: 201 on
create, 200 on read/update, 204 on delete, 404 for an unknown id, 409 when the
local profile has not been created yet and 422 for invalid input.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from . import schemas, service

records_router = APIRouter(prefix="/exercise-records", tags=["运动健身"])


def database_path(request: Request):
    return request.app.state.settings.database_path


@records_router.get("", response_model=schemas.ExerciseList)
def list_records(
    path=Depends(database_path),
    date_from: date | None = None,
    date_to: date | None = None,
):
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=422, detail="起始日期不能晚于结束日期")
    return service.list_records(path, date_from, date_to)


@records_router.post("", response_model=schemas.ExerciseRecord, status_code=201)
def create_record(data: schemas.ExerciseInput, path=Depends(database_path)):
    return service.create_record(path, data)


@records_router.get("/recommendation", response_model=schemas.ExerciseRecommendation)
def get_recommendation(path=Depends(database_path)):
    """Profile-driven advice; declared before ``/{record_id}`` so the literal path wins."""
    return service.get_recommendation(path)


@records_router.get("/{record_id}", response_model=schemas.ExerciseRecord)
def get_record(record_id: int, path=Depends(database_path)):
    return service.get_record(path, record_id)


@records_router.put("/{record_id}", response_model=schemas.ExerciseRecord)
def update_record(record_id: int, data: schemas.ExerciseInput, path=Depends(database_path)):
    return service.update_record(path, record_id, data)


@records_router.delete("/{record_id}", status_code=204)
def delete_record(record_id: int, path=Depends(database_path)):
    service.delete_record(path, record_id)
    return Response(status_code=204)


router = APIRouter()
router.include_router(records_router)
