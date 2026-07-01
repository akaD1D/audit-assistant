"""Qdrant vector store (local/embedded mode — no server, no Docker).

Persists chunk vectors + citation payloads to disk under ``vector_dir``. The
collection is created lazily on first write using the embedding dimension, so we
never hard-code vector sizes. Payloads carry everything needed to rebuild a
:class:`Chunk` (and thus a citation) at query time.
"""

from __future__ import annotations

import uuid

from audit_assistant.core.exceptions import RetrievalError
from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import Chunk, RetrievedChunk

log = get_logger(__name__)


def _point_id(chunk_id: str) -> str:
    """Qdrant needs int or UUID-string ids; our chunk_id is a uuid4 hex."""
    return str(uuid.UUID(chunk_id))


class QdrantVectorStore:
    """Implements :class:`audit_assistant.domain.interfaces.VectorStore`."""

    def __init__(self, persist_dir, collection: str = "audit_chunks") -> None:
        from qdrant_client import QdrantClient

        self._client = QdrantClient(path=str(persist_dir))
        self._collection = collection
        self._ready = False

    def _ensure_collection(self, dim: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        if self._ready:
            return
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            log.info("Created Qdrant collection '%s' (dim=%d)", self._collection, dim)
        self._ready = True

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise RetrievalError("chunks and embeddings length mismatch.")
        from qdrant_client.models import PointStruct

        self._ensure_collection(len(embeddings[0]))
        points = [
            PointStruct(
                id=_point_id(chunk.chunk_id),
                vector=vector,
                payload={
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "filename": chunk.filename,
                    "text": chunk.text,
                    "page": chunk.page if chunk.page is not None else -1,
                    "is_table": chunk.is_table,
                },
            )
            for chunk, vector in zip(chunks, embeddings, strict=True)
        ]
        self._client.upsert(collection_name=self._collection, points=points)
        log.info("Indexed %d chunks into '%s'", len(points), self._collection)

    def query(
        self, embedding: list[float], top_k: int, document_ids: list[str] | None = None
    ) -> list[RetrievedChunk]:
        if not self._client.collection_exists(self._collection):
            return []
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchAny,
        )

        query_filter = None
        if document_ids:
            query_filter = Filter(
                must=[FieldCondition(key="document_id", match=MatchAny(any=document_ids))]
            )

        response = self._client.query_points(
            collection_name=self._collection,
            query=embedding,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )

        results: list[RetrievedChunk] = []
        for point in response.points:
            payload = point.payload or {}
            page = payload.get("page", -1)
            chunk = Chunk(
                document_id=payload.get("document_id", ""),
                filename=payload.get("filename", ""),
                text=payload.get("text", ""),
                page=None if page == -1 else int(page),
                is_table=bool(payload.get("is_table", False)),
                chunk_id=payload.get("chunk_id", ""),
            )
            results.append(RetrievedChunk(chunk=chunk, score=float(point.score)))
        return results

    def delete_document(self, document_id: str) -> None:
        if not self._client.collection_exists(self._collection):
            return
        from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

        self._client.delete(
            collection_name=self._collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                )
            ),
        )
        log.info("Deleted vectors for document %s", document_id)
