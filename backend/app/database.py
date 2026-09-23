"""SQLite helpers. Each request should open and close its own connection."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import PROJECT_ROOT

SCHEMA_PATH = PROJECT_ROOT / "backend" / "sql" / "init.sql"


@contextmanager
def connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(database_path) as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def check_database(database_path: Path) -> None:
    # Do not silently recreate a deleted database during a health check.
    if not database_path.is_file():
        raise sqlite3.OperationalError("Database does not exist")
    with connect(database_path) as connection:
        connection.execute("SELECT id FROM profiles LIMIT 1").fetchone()
