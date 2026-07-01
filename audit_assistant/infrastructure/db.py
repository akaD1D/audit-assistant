"""SQLite database access.

A thin wrapper over the stdlib :mod:`sqlite3` (no ORM dependency for the lean
build). Provides a connection factory with sensible pragmas and idempotent
schema creation. The repository layer builds on top of this.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from audit_assistant.core.logging import get_logger

log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    document_id   TEXT PRIMARY KEY,
    filename      TEXT NOT NULL,
    file_type     TEXT NOT NULL,
    page_count    INTEGER NOT NULL,
    created_at    TEXT NOT NULL,
    file_path     TEXT,
    content_json  TEXT NOT NULL,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,
    action     TEXT NOT NULL,
    detail     TEXT
);

CREATE TABLE IF NOT EXISTS calculations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    name         TEXT NOT NULL,
    inputs_json  TEXT NOT NULL,
    outputs_json TEXT NOT NULL,
    summary      TEXT
);
"""


class Database:
    """Owns the SQLite file and hands out connections."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(_SCHEMA)
        log.debug("SQLite schema ensured at %s", self._db_path)
