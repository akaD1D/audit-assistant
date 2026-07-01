"""Tests for bulk knowledge-base ingestion helpers and repository count."""

from __future__ import annotations

from pathlib import Path

from audit_assistant.infrastructure.db import Database
from audit_assistant.infrastructure.repositories.document_repository import (
    SqliteDocumentRepository,
)
from audit_assistant.services.bulk_ingest import discover_files


def test_discover_files_recursive_and_filtered(tmp_path: Path) -> None:
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "b.txt").write_text("hi")
    (tmp_path / "ignore.zip").write_bytes(b"PK")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.csv").write_text("x,y")

    found = discover_files(tmp_path, {".pdf", ".txt", ".csv"})
    names = {p.name for p in found}
    assert names == {"a.pdf", "b.txt", "c.csv"}
    assert not any(p.name == "ignore.zip" for p in found)


def test_repository_count(tmp_path: Path) -> None:
    from audit_assistant.domain.models import DocumentPage, FileType, ParsedDocument

    repo = SqliteDocumentRepository(Database(tmp_path / "kb.db"))
    assert repo.count() == 0
    for i in range(3):
        repo.save(
            ParsedDocument(
                filename=f"doc{i}.pdf",
                file_type=FileType.PDF,
                pages=[DocumentPage(number=1, text="content")],
            )
        )
    assert repo.count() == 3
