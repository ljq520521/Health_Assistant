"""Local accounts: registration, login, passwords, privacy and status."""

from fastapi import HTTPException

from app.database import connect
from app.modules.profile.schemas import (
    LoginInput,
    PasswordChangeInput,
    PrivacyInput,
    RegisterInput,
    StatusInput,
)
from app.modules.profile.security import (
    create_token,
    get_or_create_secret,
    hash_password,
    verify_password,
)
from app.modules.profile.settings import TOKEN_TTL_SECONDS, utc_now


def public_user(row) -> dict:
    user = dict(row)
    user.pop("password_hash", None)
    user.pop("token_version", None)
    return user


def _issue_token(connection, row) -> str:
    secret = get_or_create_secret(connection)
    return create_token(
        user_id=row["id"],
        role=row["role"],
        token_version=row["token_version"],
        secret=secret,
    )


def _token_payload(connection, row) -> dict:
    return {
        "access_token": _issue_token(connection, row),
        "token_type": "bearer",
        "expires_in": TOKEN_TTL_SECONDS,
        "user": public_user(row),
    }


def has_accounts(path) -> bool:
    with connect(path) as connection:
        return connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0


def list_users(path) -> dict:
    with connect(path) as connection:
        rows = connection.execute("SELECT * FROM users ORDER BY id").fetchall()
    return {"items": [public_user(row) for row in rows]}


def register(path, data: RegisterInput, actor) -> dict:
    username = data.username.lower()
    now = utc_now()
    with connect(path) as connection:
        total = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if total == 0:
            # First account on a fresh installation becomes the owner.
            role = "admin"
        else:
            if actor is None or actor["role"] != "admin":
                raise HTTPException(403, "已有账号，只有管理员可以创建新账号")
            # Additional accounts are read-only viewers; no privilege escalation.
            role = "viewer"

        if (
            connection.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            is not None
        ):
            raise HTTPException(409, "用户名已存在")

        cursor = connection.execute(
            """INSERT INTO users
                   (username, password_hash, role, status, consent_health_data,
                    mask_sensitive, analytics_consent, token_version,
                    created_at, updated_at)
               VALUES (?, ?, ?, 'active', 1, 0, 0, 0, ?, ?)""",
            (username, hash_password(data.password), role, now, now),
        )
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return public_user(row)


def login(path, data: LoginInput) -> dict:
    username = data.username.lower()
    with connect(path) as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row is None or not verify_password(data.password, row["password_hash"]):
            raise HTTPException(401, "用户名或密码不正确")
        if row["status"] != "active":
            raise HTTPException(403, "账号已停用，请联系管理员")

        now = utc_now()
        connection.execute(
            "UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?",
            (now, now, row["id"]),
        )
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?", (row["id"],)
        ).fetchone()
        return _token_payload(connection, row)


def change_password(path, user, data: PasswordChangeInput) -> dict:
    with connect(path) as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
        if not verify_password(data.current_password, row["password_hash"]):
            raise HTTPException(400, "当前密码不正确")
        if verify_password(data.new_password, row["password_hash"]):
            raise HTTPException(400, "新密码不能与当前密码相同")

        now = utc_now()
        # Bumping token_version invalidates every token issued before the change.
        connection.execute(
            """UPDATE users
               SET password_hash = ?, token_version = token_version + 1, updated_at = ?
               WHERE id = ?""",
            (hash_password(data.new_password), now, user["id"]),
        )
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
        return _token_payload(connection, row)


def update_privacy(path, user, data: PrivacyInput) -> dict:
    now = utc_now()
    with connect(path) as connection:
        connection.execute(
            """UPDATE users
               SET consent_health_data = ?, mask_sensitive = ?, analytics_consent = ?,
                   updated_at = ?
               WHERE id = ?""",
            (
                int(data.consent_health_data),
                int(data.mask_sensitive),
                int(data.analytics_consent),
                now,
                user["id"],
            ),
        )
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
    return public_user(row)


def set_status(path, user_id: int, data: StatusInput, actor) -> dict:
    if user_id == actor["id"]:
        raise HTTPException(400, "不能修改当前登录账号的状态")
    with connect(path) as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, "账号不存在")
        now = utc_now()
        connection.execute(
            """UPDATE users
               SET status = ?, token_version = token_version + 1, updated_at = ?
               WHERE id = ?""",
            (data.status, now, user_id),
        )
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return public_user(row)
