"""Profile, health goals and local account endpoints.

The aggregate ``router`` is what ``app.main`` mounts under ``/api``, so the
public paths are ``/api/profile...`` and ``/api/auth...``. Keeping both routers
inside this module means no other module's files have to change.
"""

from fastapi import APIRouter, Depends, Request, Response

from app.modules.profile import auth_service, service
from app.modules.profile.auth import (
    current_user,
    optional_user,
    require_admin,
    require_admin_consent,
    require_consent,
)
from app.modules.profile.schemas import (
    Goal,
    GoalInput,
    GoalList,
    LoginInput,
    PasswordChangeInput,
    PrivacyInput,
    Profile,
    ProfileInput,
    RegisterInput,
    SetupOut,
    StatusInput,
    TokenOut,
    UserList,
    UserOut,
)


def database_path(request: Request):
    return request.app.state.settings.database_path


auth_router = APIRouter(prefix="/auth", tags=["账号与认证"])
profile_router = APIRouter(prefix="/profile", tags=["用户与基础"])


# --------------------------------------------------------------------------- #
# Account and session
# --------------------------------------------------------------------------- #


@auth_router.get("/setup", response_model=SetupOut)
def setup(path=Depends(database_path)):
    """Tell the page whether the first (admin) account still has to be created."""
    return {"has_accounts": auth_service.has_accounts(path)}


@auth_router.post("/register", response_model=UserOut, status_code=201)
def register(
    data: RegisterInput,
    path=Depends(database_path),
    actor=Depends(optional_user),
):
    return auth_service.register(path, data, actor)


@auth_router.post("/login", response_model=TokenOut)
def login(data: LoginInput, path=Depends(database_path)):
    return auth_service.login(path, data)


@auth_router.get("/me", response_model=UserOut)
def me(user=Depends(current_user)):
    return user


@auth_router.put("/password", response_model=TokenOut)
def change_password(
    data: PasswordChangeInput,
    path=Depends(database_path),
    user=Depends(current_user),
):
    return auth_service.change_password(path, user, data)


@auth_router.put("/privacy", response_model=UserOut)
def update_privacy(
    data: PrivacyInput,
    path=Depends(database_path),
    user=Depends(current_user),
):
    return auth_service.update_privacy(path, user, data)


@auth_router.get("/users", response_model=UserList)
def list_users(path=Depends(database_path), _=Depends(require_admin)):
    return auth_service.list_users(path)


@auth_router.put("/users/{user_id}/status", response_model=UserOut)
def set_user_status(
    user_id: int,
    data: StatusInput,
    path=Depends(database_path),
    actor=Depends(require_admin),
):
    return auth_service.set_status(path, user_id, data, actor)


# --------------------------------------------------------------------------- #
# Health profile and goals
# --------------------------------------------------------------------------- #


@profile_router.get("", response_model=Profile)
def get_profile(path=Depends(database_path), user=Depends(require_consent)):
    return service.get_profile(path, user)


@profile_router.put("", response_model=Profile)
def save_profile(
    data: ProfileInput,
    path=Depends(database_path),
    user=Depends(require_admin_consent),
):
    return service.save_profile(path, data, user)


@profile_router.get("/goals", response_model=GoalList)
def list_goals(path=Depends(database_path), _=Depends(require_consent)):
    return service.list_goals(path)


@profile_router.post("/goals", response_model=Goal, status_code=201)
def create_goal(
    data: GoalInput,
    path=Depends(database_path),
    _=Depends(require_admin_consent),
):
    return service.create_goal(path, data)


@profile_router.get("/goals/{goal_id}", response_model=Goal)
def get_goal(
    goal_id: int,
    path=Depends(database_path),
    _=Depends(require_consent),
):
    return service.get_goal(path, goal_id)


@profile_router.put("/goals/{goal_id}", response_model=Goal)
def update_goal(
    goal_id: int,
    data: GoalInput,
    path=Depends(database_path),
    _=Depends(require_admin_consent),
):
    return service.update_goal(path, goal_id, data)


@profile_router.delete("/goals/{goal_id}", status_code=204)
def delete_goal(
    goal_id: int,
    path=Depends(database_path),
    _=Depends(require_admin_consent),
):
    service.delete_goal(path, goal_id)
    return Response(status_code=204)


router = APIRouter()
router.include_router(auth_router)
router.include_router(profile_router)
