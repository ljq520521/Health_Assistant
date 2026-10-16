from typing import Literal
from fastapi import APIRouter,Depends
from app.modules.diet.library_router import LibraryRoute,database_path
from app.modules.diet.schemas import CalendarDate
from app.modules.diet.report_service import report
router=APIRouter(prefix='/diet',tags=['饮食报告'],route_class=LibraryRoute)
@router.get('/reports')
def get_report(date:CalendarDate,period:Literal['day','week','month']='day',path=Depends(database_path)):
    return report(path,date,period)
