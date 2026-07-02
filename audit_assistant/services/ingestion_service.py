"""Ingestion service — granular steps so the UI can show progress and choose
whether a document is a *temporary session* upload or a permanent *knowledge
base* entry.

Pipeline (each step is exposed so the UI can render stages and pick a target):
    validate + parse  ->  (image) transcribe  ->  chunk + embed
    then either: keep in the in-memory session index, OR persist + index into
    the knowledge base (SQLite + Qdrant).
"""

from __future__ import annotations

from pathlib import Path

from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import Chunk, FileType, ParsedDocument
from audit_assistant.infrastructure.parsers.base import ParserRegistry
from audit_assistant.infrastructure.repositories.document_repository import (
    SqliteDocumentRepository,
)
from audit_assistant.infrastructure.validation import validate_upload
from audit_assistant.services.chunking import chunk_document
from audit_assistant.services.image_service import ImageUnderstandingService
from audit_assistant.services.indexing_service import IndexingService


log = get_logger(__name__)


class IngestionService:
    """Parses uploads and routes them to the session index or the knowledge base."""

    def __init__(
        self,
        *,
        registry: ParserRegistry,
        repository: SqliteDocumentRepository,
        upload_dir: Path,
        max_upload_bytes: int,
        indexer: IndexingService | None = None,
        image_analyzer: ImageUnderstandingService | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ) -> None:
        self._registry = registry
        self._repository = repository
        self._upload_dir = upload_dir
        self._max_upload_bytes = max_upload_bytes
        self._indexer = indexer
        self._image_analyzer = image_analyzer
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    # --- granular steps ------------------------------------------------------
    def validate(self, *, filename: str, data: bytes) -> FileType:
        return validate_upload(filename=filename, data=data, max_bytes=self._max_upload_bytes)

    def parse(self, *, filename: str, data: bytes, file_type: FileType) -> ParsedDocument:
        """Extract text/tables (no persistence, no indexing)."""
        return self._registry.parse(filename=filename, data=data, file_type=file_type)

    def is_image(self, file_type: FileType) -> bool:
        return file_type.is_image

    def transcribe_image(self, document: ParsedDocument, data: bytes) -> None:
        """Fill an image document's text via the vision/OCR pipeline (in place)."""
        if self._image_analyzer is not None and document.pages:
            document.pages[0].text = self._image_analyzer.transcribe(data)
            log.info("Transcribed image '%s'", document.filename)

    def embed(self, document: ParsedDocument) -> tuple[list[Chunk], list[list[float]]]:
        """Chunk + embed a document; returns chunks and their vectors."""
        chunks = [c for c in chunk_document(document, self._chunk_size, self._chunk_overlap) if c.text.strip()]
        if not chunks or self._indexer is None:
            return chunks, []
        embeddings = self._indexer.embedder.embed_documents([c.text for c in chunks])
        document.metadata["chunks"] = str(len(chunks))
        return chunks, embeddings

    def persist_to_kb(
        self, document: ParsedDocument, data: bytes, chunks: list[Chunk], embeddings: list[list[float]]
    ) -> None:
        """Save bytes + metadata to SQLite and vectors to Qdrant (permanent)."""
        suffix = Path(document.filename).suffix.lower()
        stored_path = self._upload_dir / f"{document.document_id}{suffix}"
        stored_path.write_bytes(data)
        self._repository.save(document, file_path=str(stored_path))
        if self._indexer is not None and chunks:
            self._indexer.vector_store.add(chunks, embeddings)
        log.info("Added '%s' to knowledge base (%s)", document.filename, document.document_id)

    # --- convenience (used by the bulk-ingest CLI) ---------------------------
    def ingest(self, *, filename: str, data: bytes) -> ParsedDocument:
        """One-shot: parse + (transcribe) + embed + add to the knowledge base."""
        file_type = self.validate(filename=filename, data=data)
        document = self.parse(filename=filename, data=data, file_type=file_type)
        if self.is_image(file_type):
            self.transcribe_image(document, data)
        chunks, embeddings = self.embed(document)
        self.persist_to_kb(document, data, chunks, embeddings)
        return document
