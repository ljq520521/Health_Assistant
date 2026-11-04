"""Use the account module's live token, consent and administrator checks."""

from fastapi import Depends, HTTPException, Response

from app.modules.profile.auth import require_consent


def read_access(response: Response, user: dict = Depends(require_consent)) -> dict:
    if user["role"] != "admin" and user["mask_sensitive"]:
        raise HTTPException(403, "当前隐私设置隐藏敏感资料，暂不提供个人睡眠数据")
    response.headers["Cache-Control"] = "no-store"
    return user
