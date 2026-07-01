"""Audit/activity log.

Persists a trail of user-facing actions (uploads, questions, calculations,
reports) to the ``audit_log`` table. In a single-user local build this is an
activity history; the same table underpins compliance audit trails in the
multi-user upgrade path.
"""

from __future__ import annotations

from datetime import datetime, timezone

from audit_assistant.core.logging import get_logger
from audit_assistant.infrastructure.db import Database

log = get_logger(__name__)


class AuditLogService:
    """Records and retrieves activity-log entries."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def record(self, action: str, detail: str = "") -> None:
        try:
            with self._db.connect() as conn:
                conn.execute(
                    "INSERT INTO audit_log (ts, action, detail) VALUES (?, ?, ?)",
                    (datetime.now(timezone.utc).isoformat(timespec="seconds"), action, detail),
                )
        except Exception:  # noqa: BLE001 - logging must never break the app
            log.exception("Failed to write audit-log entry")

    def recent(self, limit: int = 50) -> list[dict]:
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT ts, action, detail FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
