from fastapi import APIRouter

# Business endpoints are planned in docs/05-api.md; no mock success responses.
router = APIRouter(prefix="/profile", tags=["用户与基础"])
