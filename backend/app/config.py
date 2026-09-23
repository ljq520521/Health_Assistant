"""Read one shared .env from the repository root."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str
    database_path: Path
    allowed_origins: tuple[str, ...]


def get_settings() -> Settings:
    database_path = Path(os.getenv("HEALTH_DB_PATH", "backend/data/health.db"))
    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path
    return Settings(
        app_name=os.getenv("APP_NAME", "Health Management System"),
        database_path=database_path,
        allowed_origins=tuple(
            origin.strip()
            for origin in os.getenv(
                "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if origin.strip()
        ),
    )
