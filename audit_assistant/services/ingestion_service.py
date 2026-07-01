"""Ingestion service: validate -> persist bytes -> parse -> store metadata.

Phase 1 scope. Phase 2 extends :meth:`ingest` to also chunk, embed, and index
the parsed document into the vector store for RAG.
"""

from __future__ import annotations

from pathlib import Path

from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import ParsedDocument
from audit_assistant.infrastructure.parsers.base import ParserRegistry
from audit_assistant.infrastructure.repositories.document_repository import (
    SqliteDocumentRepository,
)
from audit_assistant.infrastructure.validation import validate_upload
from audit_assistant.services.image_service import ImageUnderstandingService
from audit_assistant.services.indexing_service import IndexingService

log = get_logger(__name__)


class IngestionService:
    """Turns an uploaded file into a persisted, parsed, and indexed document."""

    def __init__(
        self,
        *,
        registry: ParserRegistry,
        repository: SqliteDocumentRepository,
        upload_dir: Path,
        max_upload_bytes: int,
        indexer: IndexingService | None = None,
        image_analyzer: ImageUnderstandingService | None = None,
    ) -> None:
        self._registry = registry
        self._repository = repository
        self._upload_dir = upload_dir
        self._max_upload_bytes = max_upload_bytes
        self._indexer = indexer
        self._image_analyzer = image_analyzer

    def ingest(self, *, filename: str, data: bytes) -> ParsedDocument:
        """Validate, store, and parse a single uploaded file.

        Raises :class:`FileValidationError` / :class:`UnsupportedFileTypeError`
        / :class:`ParsingError` on failure (caller decides how to surface).
        """
        file_type = validate_upload(
            filename=filename, data=data, max_bytes=self._max_upload_bytes
        )

        document = self._registry.parse(filename=filename, data=data, file_type=file_type)

        # Images carry only a placeholder after parsing — enrich them with a
        # vision/OCR transcription so their content becomes searchable + citable.
        if file_type.is_image and self._image_analyzer is not None and document.pages:
            transcription = self._image_analyzer.transcribe(data)
            document.pages[0].text = transcription
            log.info("Transcribed image '%s' (%d chars)", filename, len(transcription))

        # Persist raw bytes under a collision-free name (needed by on-demand
        # vision analysis, which re-reads image files from disk).
        stored_path = self._upload_dir / f"{document.document_id}{Path(filename).suffix.lower()}"
        stored_path.write_bytes(data)

        self._repository.save(document, file_path=str(stored_path))

        if self._indexer is not None:
            chunk_count = self._indexer.index(document)
            document.metadata["chunks"] = str(chunk_count)

        log.info(
            "Ingested '%s' -> %s (%d pages)",
            filename,
            document.document_id,
            document.page_count,
        )
        return document
