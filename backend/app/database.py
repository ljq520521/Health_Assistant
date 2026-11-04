"""SQLite helpers. Each request should open and close its own connection."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import PROJECT_ROOT

SCHEMA_PATH = PROJECT_ROOT / "backend" / "sql" / "init.sql"


@contextmanager
def connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    # FastAPI may resume a synchronous dependency on a different worker thread.
    # Each request still owns one connection and uses it sequentially.
    connection = sqlite3.connect(database_path, timeout=5, check_same_thread=False)
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
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
        connection.commit()
        for migration in sorted((SCHEMA_PATH.parent / "migrations").glob("*.sql")):
            connection.execute("BEGIN IMMEDIATE")
            if not connection.execute("SELECT 1 FROM schema_migrations WHERE name=?", (migration.name,)).fetchone():
                statement = ""
                for line in migration.read_text(encoding="utf-8").splitlines(keepends=True):
                    statement += line
                    if sqlite3.complete_statement(statement):
                        connection.execute(statement)
                        statement = ""
                connection.execute("INSERT INTO schema_migrations VALUES (?)", (migration.name,))
            connection.commit()


def check_database(database_path: Path) -> None:
    # Do not silently recreate a deleted database during a health check.
    if not database_path.is_file():
        raise sqlite3.OperationalError("Database does not exist")
    with connect(database_path) as connection:
        connection.execute("SELECT id FROM profiles LIMIT 1").fetchone()
