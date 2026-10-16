from typing import Literal
from fastapi import APIRouter, Depends
from app.modules.diet.library_router import LibraryRoute, database_path
from app.modules.diet.schemas import CalendarDate
from app.modules.diet.nutrition_schemas import GoalChanges
from app.modules.diet import nutrition_service as service

router=APIRouter(prefix='/diet',tags=['营养分析与目标'],route_class=LibraryRoute)
@router.get('/goals')
def goal(date: CalendarDate, path=Depends(database_path)):
    return service.get_goal(path,date)
@router.get('/goals/history')
def history(path=Depends(database_path)):
    return service.history(path)
@router.put('/goals')
def save(data:GoalChanges,path=Depends(database_path)):
    return service.save_goal(path,data)
@router.get('/nutrition-summary')
def summary(date_from:CalendarDate,date_to:CalendarDate,group_by:Literal['day','week','month']='day',path=Depends(database_path)):
    return service.summary(path,date_from,date_to,group_by)

@router.get('/record-summary')
def record_summary(date_from:CalendarDate | None=None,date_to:CalendarDate | None=None,path=Depends(database_path)):
    if date_from and date_to and date_from>date_to:
        from app.modules.diet.library_service import LibraryError
        raise LibraryError(422,'INVALID_RANGE','起始日期不能晚于结束日期')
    return service.record_summary(path,date_from,date_to)
