"""Diet-local weekly plans; real shared authentication and consent remain in force."""
from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query
from app.modules.profile.auth import require_consent, require_admin_consent
from app.modules.diet.library_router import LibraryRoute, database_path
from app.modules.diet.library_service import LibraryError
from app.modules.diet.schemas import CalendarDate
from app.modules.diet.weekly_schemas import ConfirmInput, FeedbackInput, PlanInput, RefreshInput
from app.modules.diet import weekly_context as contexts, weekly_service as service

router = APIRouter(prefix='/diet', tags=['一周食谱计划与执行反馈'], route_class=LibraryRoute)
PathID = Annotated[int, Path(ge=1, le=9223372036854775807)]


def access_result(result, user):
    return result | {'can_write':user['role'] == 'admin' and bool(user['consent_health_data']),
                     'profile_scope':'shared_local_profile', 'profile_id':1,
                     'scope_notice':'当前为本机共享单档案，账号角色控制访问权限，不代表多用户档案隔离。'}


def goal_ids(raw):
    if not raw:
        return []
    parts = raw.split(',')
    if len(parts) > 50 or any(not p.strip().isascii() or not p.strip().isdigit() for p in parts):
        raise LibraryError(422, 'INVALID_GOAL_IDS', '健康目标必须为至多50个逗号分隔的正整数ID')
    ids = [int(part) for part in parts]
    if any(id <= 0 or id > 9223372036854775807 for id in ids) or len(set(ids)) != len(ids):
        raise LibraryError(422, 'INVALID_GOAL_IDS', '健康目标ID应为不重复的正整数')
    return sorted(ids)


@router.get('/weekly-plan-context')
def context(start_date: CalendarDate | None = None, selected_goal_ids: str = Query('',max_length=1100),
            path=Depends(database_path), user=Depends(require_consent)):
    return access_result(contexts.get_context(path,start_date or service.business_today(),goal_ids(selected_goal_ids)),user)


@router.post('/weekly-plan-context/confirm',status_code=201)
def confirm(data: ConfirmInput, path=Depends(database_path), user=Depends(require_admin_consent)):
    return access_result(contexts.confirm_context(path,data,user['id']),user)


@router.post('/weekly-plans/preview')
def preview(data: PlanInput, path=Depends(database_path), user=Depends(require_consent)):
    return access_result(service.preview(path,data),user)


@router.post('/weekly-plans',status_code=201)
def save(data: PlanInput, path=Depends(database_path), user=Depends(require_admin_consent)):
    return access_result(service.save(path,data,user['id']),user)


@router.get('/weekly-plans')
def plans(limit: int = Query(30,ge=1,le=100), offset: int = Query(0,ge=0,le=9223372036854775807),
          path=Depends(database_path), user=Depends(require_consent)):
    return access_result(service.list_plans(path,limit,offset),user)


@router.get('/weekly-plans/{id}')
def plan(id: PathID, path=Depends(database_path), user=Depends(require_consent)):
    return access_result(service.get(path,id),user)


@router.post('/weekly-plans/{id}/refresh-preview')
def refresh_preview(id: PathID, data: RefreshInput, path=Depends(database_path), user=Depends(require_consent)):
    return access_result(service.refresh_preview(path,id,data),user)


@router.post('/weekly-plans/{id}/refresh')
def refresh(id: PathID, data: RefreshInput, path=Depends(database_path), user=Depends(require_admin_consent)):
    return access_result(service.refresh(path,id,data,user['id']),user)


@router.get('/weekly-plans/{id}/versions')
def versions(id: PathID, path=Depends(database_path), user=Depends(require_consent)):
    return access_result(service.versions(path,id),user)


@router.put('/weekly-plan-items/{id}/feedback')
def feedback(id: PathID, data: FeedbackInput, path=Depends(database_path), user=Depends(require_admin_consent)):
    return access_result(service.save_feedback(path,id,data,user['id']),user)


@router.get('/weekly-plan-items/{id}/feedback-history')
def feedback_history(id: PathID, path=Depends(database_path), user=Depends(require_consent)):
    return access_result(service.feedback_history(path,id),user)
