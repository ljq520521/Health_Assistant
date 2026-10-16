from fastapi import APIRouter, Depends, Response
from app.modules.diet.library_router import LibraryRoute, database_path
from app.modules.diet.schemas import CalendarDate
from app.modules.diet.water_schemas import WaterInput, ReminderInput
from app.modules.diet import water_service as service

router=APIRouter(prefix='/diet',tags=['饮水管理'],route_class=LibraryRoute)

@router.get('/water-records')
def records(date_from:CalendarDate | None=None,date_to:CalendarDate | None=None,path=Depends(database_path)):
    return service.records(path,date_from,date_to)

@router.post('/water-records',status_code=201)
def create(data:WaterInput,path=Depends(database_path)):
    return service.save(path,data)

@router.get('/water-records/{id}')
def get(id:int,path=Depends(database_path)):
    return service.get(path,id)

@router.put('/water-records/{id}')
def update(id:int,data:WaterInput,path=Depends(database_path)):
    return service.save(path,data,id)

@router.delete('/water-records/{id}',status_code=204)
def delete(id:int,path=Depends(database_path)):
    service.delete(path,id)
    return Response(status_code=204)

@router.get('/water-summary')
def summary(date:CalendarDate,path=Depends(database_path)):
    return service.summary(path,date)

@router.get('/water-reminder-settings')
def reminder(path=Depends(database_path)):
    return service.get_reminder(path)

@router.put('/water-reminder-settings')
def save_reminder(data:ReminderInput,path=Depends(database_path)):
    return service.save_reminder(path,data)
