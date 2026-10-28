"""Authentication dependencies for the profile and account endpoints."""

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import connect
from app.modules.profile.security import decode_token, get_or_create_secret

bearer_scheme = HTTPBearer(
    auto_error=False, description="登录接口返回的 Bearer Token"
)


def database_path(request: Request):
    return request.app.state.settings.database_path


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(401, message, headers={"WWW-Authenticate": "Bearer"})


def _authenticate(
    request: Request, credentials: HTTPAuthorizationCredentials
) -> dict:
    path = database_path(request)
    try:
        with connect(path) as connection:
            secret = get_or_create_secret(connection)
        payload = decode_token(credentials.credentials, secret)
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _unauthorized("登录状态无效，请重新登录") from exc

    with connect(path) as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        raise _unauthorized("账号不存在，请重新登录")

    user = dict(row)
    if user["status"] != "active":
        raise HTTPException(403, "账号已停用，请联系管理员")
    if int(payload.get("ver", -1)) != user["token_version"]:
        raise _unauthorized("登录状态已失效，请重新登录")
    return user


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise _unauthorized("请先登录")
    return _authenticate(request, credentials)


def optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict | None:
    """Registration is public only until the first account exists."""
    if credentials is None:
        return None
    return _authenticate(request, credentials)


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "仅管理员可以执行此操作")
    return user


def require_consent(user: dict = Depends(current_user)) -> dict:
    if not user["consent_health_data"]:
        raise HTTPException(403, "尚未授权处理健康数据，请先在账户隐私中开启")
    return user


def require_admin_consent(user: dict = Depends(require_admin)) -> dict:
    if not user["consent_health_data"]:
        raise HTTPException(403, "尚未授权处理健康数据，请先在账户隐私中开启")
    return user
