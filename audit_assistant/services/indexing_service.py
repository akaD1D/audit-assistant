"""Indexing service: chunk -> embed -> store in the vector index.

Separated from ingestion (single responsibility) so it can also be used for
re-indexing or background jobs. Called by :class:`IngestionService` when a
vector store + embedder are wired in.
"""

from __future__ import annotations

from audit_assistant.core.logging import get_logger
from audit_assistant.domain.interfaces import EmbeddingProvider, VectorStore
from audit_assistant.domain.models import ParsedDocument
from audit_assistant.services.chunking import chunk_document

log = get_logger(__name__)


class IndexingService:
    """Turns a parsed document into searchable vectors."""

    def __init__(
        self,
        *,
        embedder: EmbeddingProvider,
        vector_store: VectorStore,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def index(self, document: ParsedDocument) -> int:
        """Chunk, embed, and store a document. Returns the chunk count."""
        chunks = chunk_document(document, self._chunk_size, self._chunk_overlap)
        chunks = [c for c in chunks if c.text.strip()]
        if not chunks:
            log.info("No indexable text in '%s'", document.filename)
            return 0
        embeddings = self._embedder.embed_documents([c.text for c in chunks])
        self._vector_store.add(chunks, embeddings)
        log.info("Indexed '%s' -> %d chunks", document.filename, len(chunks))
        return len(chunks)

    def remove(self, document_id: str) -> None:
        self._vector_store.delete_document(document_id)
