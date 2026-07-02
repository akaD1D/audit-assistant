"""Knowledge base management: list, rename, delete, replace, and re-index.

Coordinates the SQLite repository, the vector store, and stored files so KB
operations stay consistent (deleting a document also removes its vectors and
file; replacing preserves the document's identity).
"""

from __future__ import annotations

from pathlib import Path

from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import ParsedDocument
from audit_assistant.infrastructure.repositories.document_repository import (
    SqliteDocumentRepository,
)
from audit_assistant.services.indexing_service import IndexingService
from audit_assistant.services.ingestion_service import IngestionService

log = get_logger(__name__)


class KnowledgeBaseService:
    """User-facing operations for the persistent knowledge base."""

    def __init__(
        self,
        *,
        repository: SqliteDocumentRepository,
        indexer: IndexingService,
        ingestion: IngestionService,
    ) -> None:
        self._repo = repository
        self._indexer = indexer
        self._ingestion = ingestion

    def list(self) -> list[dict]:
        return self._repo.list_summaries()

    def count(self) -> int:
        return self._repo.count()

    def rename(self, document_id: str, new_filename: str) -> None:
        self._repo.rename(document_id, new_filename.strip())

    def delete(self, document_id: str) -> None:
        """Remove a document's metadata, vectors, and stored file."""
        path = self._repo.file_path(document_id)
        self._indexer.remove(document_id)  # vectors
        self._repo.delete(document_id)  # metadata
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError as exc:  # noqa: BLE001
                log.warning("Could not delete file %s: %s", path, exc)
        log.info("Deleted document %s from knowledge base", document_id)

    def reindex(self, document_id: str) -> int:
        """Re-chunk and re-embed a stored document (e.g. after model change)."""
        document = self._repo.get(document_id)
        if document is None:
            return 0
        self._indexer.remove(document_id)
        count = self._indexer.index(document)
        document.metadata["chunks"] = str(count)
        self._repo.save(document, file_path=self._repo.file_path(document_id))
        return count

    def replace(self, document_id: str, *, filename: str, data: bytes) -> ParsedDocument:
        """Replace a document with a new version, preserving its identity (id)."""
        file_type = self._ingestion.validate(filename=filename, data=data)
        document = self._ingestion.parse(filename=filename, data=data, file_type=file_type)
        document.document_id = document_id  # preserve identity
        if self._ingestion.is_image(file_type):
            self._ingestion.transcribe_image(document, data)
        chunks, embeddings = self._ingestion.embed(document)
        self._indexer.remove(document_id)  # drop old vectors
        self._ingestion.persist_to_kb(document, data, chunks, embeddings)
        log.info("Replaced document %s with new version '%s'", document_id, filename)
        return document
