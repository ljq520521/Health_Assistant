import sqlite3
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import __version__
from app.config import Settings, get_settings
from app.database import check_database, init_database
from app.modules.catalog import MODULES, ModuleInfo
from app.modules.cycle.router import router as cycle_router
from app.modules.diet.router import router as diet_router
from app.modules.exercise.router import router as exercise_router
from app.modules.profile.router import router as profile_router
from app.modules.sleep.router import router as sleep_router


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    database: Literal["ok"] = "ok"
    version: str = __version__


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        init_database(settings.database_path)
        yield

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="v0.1 项目骨架，仅开放健康检查与模块目录。业务接口见项目文档。",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @application.get("/health", tags=["系统"], response_model=HealthResponse)
    def health() -> HealthResponse:
        try:
            check_database(settings.database_path)
        except sqlite3.Error as exc:
            raise HTTPException(status_code=503, detail="数据库不可用") from exc
        return HealthResponse()

    @application.get("/api/modules", tags=["系统"], response_model=list[ModuleInfo])
    def modules() -> list[ModuleInfo]:
        return MODULES

    for router in (profile_router, diet_router, exercise_router, sleep_router, cycle_router):
        application.include_router(router, prefix="/api")

    return application


app = create_app()
