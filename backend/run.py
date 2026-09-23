"""Run from backend/: python run.py. Environment is loaded by app.config."""

import os

import uvicorn

from app.config import get_settings

if __name__ == "__main__":
    get_settings()
    uvicorn.run(
        "app.main:app",
        host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        reload=True,
    )
