"""Audit/activity log service tests."""

from __future__ import annotations

from audit_assistant.infrastructure.db import Database
from audit_assistant.services.audit_log_service import AuditLogService


def test_record_and_recent(tmp_path) -> None:
    svc = AuditLogService(Database(tmp_path / "a.db"))
    svc.record("document_uploaded", "acme.pdf (3 pages)")
    svc.record("chat_answer", "Q: what is materiality (confidence=high)")

    entries = svc.recent()
    assert len(entries) == 2
    # Most recent first.
    assert entries[0]["action"] == "chat_answer"
    assert "acme.pdf" in entries[1]["detail"]


def test_record_never_raises(tmp_path) -> None:
    # Even against a broken DB path, logging must not crash the caller.
    svc = AuditLogService(Database(tmp_path / "b.db"))
    svc._db._db_path = tmp_path / "nonexistent" / "dir" / "x.db"  # force write failure
    svc.record("action", "detail")  # should swallow the error, not raise
