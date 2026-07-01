"""Retrieval service: the 'R' in RAG.

Embeds a question and fetches the most relevant chunks, optionally scoped to a
subset of documents. Returns chunks with scores and ready-made citations so the
chat layer (Phase 3) can ground answers and cite sources.
"""

from __future__ import annotations

from audit_assistant.core.logging import get_logger
from audit_assistant.domain.interfaces import EmbeddingProvider, VectorStore
from audit_assistant.domain.models import Citation, RetrievedChunk

log = get_logger(__name__)

_SNIPPET_LEN = 300


class RagService:
    """Semantic retrieval over the indexed corpus."""

    def __init__(
        self,
        *,
        embedder: EmbeddingProvider,
        vector_store: VectorStore,
        default_top_k: int = 5,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._default_top_k = default_top_k

    def retrieve(
        self,
        question: str,
        *,
        top_k: int | None = None,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Return the top-k most relevant chunks for a question."""
        if not question.strip():
            return []
        embedding = self._embedder.embed_query(question)
        results = self._vector_store.query(
            embedding, top_k or self._default_top_k, document_ids
        )
        log.debug("Retrieved %d chunks for query %r", len(results), question[:60])
        return results

    @staticmethod
    def to_citations(results: list[RetrievedChunk]) -> list[Citation]:
        """Collapse retrieved chunks into de-duplicated citations."""
        citations: list[Citation] = []
        seen: set[tuple[str, int | None]] = set()
        for r in results:
            key = (r.chunk.filename, r.chunk.page)
            if key in seen:
                continue
            seen.add(key)
            snippet = r.chunk.text[:_SNIPPET_LEN].strip()
            citations.append(
                Citation(
                    filename=r.chunk.filename,
                    page=r.chunk.page,
                    snippet=snippet,
                    score=r.score,
                )
            )
        return citations
