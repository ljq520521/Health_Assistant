"""Password hashing and HS256 token helpers.

Only the Python standard library is used on purpose: the profile module can
then be dropped into the existing project without changing requirements.txt,
so teammates do not need to reinstall dependencies before their modules still
start. PBKDF2-HMAC-SHA256 is adequate for a local course project; a production
deployment should switch to a maintained library such as argon2 or bcrypt plus
PyJWT.
"""

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import sqlite3
import time

from app.modules.profile.settings import TOKEN_TTL_SECONDS

PBKDF2_ITERATIONS = 210_000
PASSWORD_SCHEME = "pbkdf2_sha256"


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    """Return ``pbkdf2_sha256$iterations$salt$digest`` for storage."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"{PASSWORD_SCHEME}${PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt, digest = stored.split("$")
        if scheme != PASSWORD_SCHEME:
            return False
        expected = _b64decode(digest)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _b64decode(salt), int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (AttributeError, TypeError, ValueError, binascii.Error):
        return False


def create_token(
    *,
    user_id: int,
    role: str,
    token_version: int,
    secret: str,
    issued_at: float | None = None,
) -> str:
    issued = int(time.time() if issued_at is None else issued_at)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "role": role,
        "ver": int(token_version),
        "iat": issued,
        "exp": issued + TOKEN_TTL_SECONDS,
    }
    segments = [
        _b64encode(
            json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ),
        _b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ),
    ]
    signing_input = ".".join(segments).encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    segments.append(_b64encode(signature))
    return ".".join(segments)


def decode_token(token: str, secret: str, now: float | None = None) -> dict:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except (AttributeError, ValueError) as exc:
        raise ValueError("token 格式不正确") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        signature = _b64decode(signature_b64)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("token 签名无效") from exc
    if not hmac.compare_digest(expected, signature):
        raise ValueError("token 签名无效")

    try:
        header = json.loads(_b64decode(header_b64))
        payload = json.loads(_b64decode(payload_b64))
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise ValueError("token 内容无效") from exc

    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ValueError("token 内容无效")
    if header.get("alg") != "HS256":
        raise ValueError("token 算法不支持")
    if int(payload.get("exp", 0)) <= (time.time() if now is None else now):
        raise ValueError("登录已过期")
    return payload


def get_or_create_secret(connection: sqlite3.Connection) -> str:
    """The signing key lives next to the data, so restarts keep tokens valid."""
    row = connection.execute("SELECT secret FROM auth_secrets WHERE id = 1").fetchone()
    if row is not None:
        return row["secret"] if isinstance(row, sqlite3.Row) else row[0]

    secret = secrets.token_urlsafe(48)
    try:
        connection.execute(
            "INSERT INTO auth_secrets (id, secret) VALUES (1, ?)", (secret,)
        )
    except sqlite3.IntegrityError:
        # Another request created it first; read the winner below.
        pass
    row = connection.execute("SELECT secret FROM auth_secrets WHERE id = 1").fetchone()
    return row["secret"] if isinstance(row, sqlite3.Row) else row[0]
