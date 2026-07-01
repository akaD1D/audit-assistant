"""End-to-end ingestion + repository round-trip tests."""

from __future__ import annotations

import pytest

from audit_assistant.infrastructure.db import Database
from audit_assistant.infrastructure.parsers.base import build_default_registry
from audit_assistant.infrastructure.repositories.document_repository import (
    SqliteDocumentRepository,
)
from audit_assistant.services.ingestion_service import IngestionService


@pytest.fixture
def service(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    db = Database(tmp_path / "test.db")
    repo = SqliteDocumentRepository(db)
    svc = IngestionService(
        registry=build_default_registry(),
        repository=repo,
        upload_dir=upload_dir,
        max_upload_bytes=10 * 1024 * 1024,
    )
    return svc, repo, upload_dir


def test_ingest_persists_file_and_metadata(service, pdf_bytes) -> None:
    svc, repo, upload_dir = service
    doc = svc.ingest(filename="audit.pdf", data=pdf_bytes)

    # Raw bytes stored on disk.
    stored = list(upload_dir.iterdir())
    assert len(stored) == 1
    assert stored[0].read_bytes() == pdf_bytes

    # Metadata retrievable and faithful.
    fetched = repo.get(doc.document_id)
    assert fetched is not None
    assert fetched.filename == "audit.pdf"
    assert fetched.page_count == 2
    assert "Materiality" in fetched.full_text


def test_repository_list_and_delete(service, csv_bytes, txt_bytes) -> None:
    svc, repo, _ = service
    d1 = svc.ingest(filename="a.csv", data=csv_bytes)
    d2 = svc.ingest(filename="b.txt", data=txt_bytes)

    assert len(repo.list_all()) == 2

    repo.delete(d1.document_id)
    remaining = repo.list_all()
    assert len(remaining) == 1
    assert remaining[0].document_id == d2.document_id


def test_ingest_rejects_bad_signature(service) -> None:
    from audit_assistant.core.exceptions import FileValidationError

    svc, _, _ = service
    with pytest.raises(FileValidationError):
        svc.ingest(filename="fake.pdf", data=b"not a real pdf")
