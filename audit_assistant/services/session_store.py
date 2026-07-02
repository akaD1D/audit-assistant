"""In-memory session document index (temporary, never persisted).

Session documents live only for the current chat: their chunks + embeddings are
held in memory (Streamlit ``session_state``) and retrieved by brute-force cosine
similarity. Nothing touches SQLite or Qdrant, so when the session ends the data
simply disappears — the opposite of the persistent knowledge base.
"""

from __future__ import annotations

import numpy as np

from audit_assistant.domain.interfaces import EmbeddingProvider
from audit_assistant.domain.models import Chunk, Citation, RetrievedChunk


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class SessionIndex:
    """Brute-force in-memory vector index for the current session's documents."""

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._embeddings: np.ndarray | None = None  # (n, dim), L2-normalized

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        arr = _normalize(np.asarray(embeddings, dtype=np.float32))
        self._chunks.extend(chunks)
        self._embeddings = arr if self._embeddings is None else np.vstack([self._embeddings, arr])

    def query(
        self, embedding: list[float], top_k: int, document_ids: list[str] | None = None
    ) -> list[RetrievedChunk]:
        if self._embeddings is None or not self._chunks:
            return []
        q = np.asarray(embedding, dtype=np.float32)
        q = q / (np.linalg.norm(q) or 1.0)
        sims = self._embeddings @ q  # cosine similarity (both normalized)

        wanted = set(document_ids) if document_ids else None
        order = np.argsort(sims)[::-1]
        results: list[RetrievedChunk] = []
        for i in order:
            chunk = self._chunks[int(i)]
            if wanted and chunk.document_id not in wanted:
                continue
            results.append(RetrievedChunk(chunk=chunk, score=float(sims[int(i)])))
            if len(results) >= top_k:
                break
        return results

    def remove_document(self, document_id: str) -> None:
        keep = [i for i, c in enumerate(self._chunks) if c.document_id != document_id]
        self._chunks = [self._chunks[i] for i in keep]
        self._embeddings = self._embeddings[keep] if self._embeddings is not None and keep else None
        if not keep:
            self._embeddings = None

    @property
    def document_ids(self) -> set[str]:
        return {c.document_id for c in self._chunks}

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)


class SessionRetriever:
    """Retriever over a :class:`SessionIndex` (same interface the chat expects)."""

    def __init__(self, embedder: EmbeddingProvider, index: SessionIndex) -> None:
        self._embedder = embedder
        self._index = index

    def retrieve(
        self, question: str, *, top_k: int | None = None, document_ids: list[str] | None = None
    ) -> list[RetrievedChunk]:
        if not question.strip():
            return []
        embedding = self._embedder.embed_query(question)
        return self._index.query(embedding, top_k or 5, document_ids)

    @staticmethod
    def to_citations(results: list[RetrievedChunk]) -> list[Citation]:
        from audit_assistant.services.rag_service import RagService

        return RagService.to_citations(results)
