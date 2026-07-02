"""Tests for session index and knowledge-base management."""

from __future__ import annotations

import pytest

from audit_assistant.domain.models import Chunk
from audit_assistant.infrastructure.db import Database
from audit_assistant.infrastructure.parsers.base import build_default_registry
from audit_assistant.infrastructure.repositories.document_repository import (
    SqliteDocumentRepository,
)
from audit_assistant.services.indexing_service import IndexingService
from audit_assistant.services.ingestion_service import IngestionService
from audit_assistant.services.knowledge_base_service import KnowledgeBaseService
from audit_assistant.services.session_store import SessionIndex


def _chunk(text: str, doc_id: str) -> Chunk:
    return Chunk(document_id=doc_id, filename=f"{doc_id}.txt", text=text)


def test_session_index_retrieval_and_removal() -> None:
    idx = SessionIndex()
    idx.add([_chunk("materiality threshold", "d1"), _chunk("cafeteria lunch", "d1")],
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    results = idx.query([0.9, 0.1, 0.0], top_k=1)
    assert results and results[0].chunk.text == "materiality threshold"
    assert idx.chunk_count == 2
    idx.remove_document("d1")
    assert idx.chunk_count == 0
    assert idx.query([1.0, 0.0, 0.0], top_k=1) == []


class FakeVectorStore:
    def __init__(self) -> None:
        self.documents: set[str] = set()

    def add(self, chunks, embeddings) -> None:
        for c in chunks:
            self.documents.add(c.document_id)

    def query(self, embedding, top_k, document_ids=None):
        return []

    def delete_document(self, document_id: str) -> None:
        self.documents.discard(document_id)


class FakeEmbedder:
    def embed_documents(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    def embed_query(self, text):
        return [0.1, 0.2, 0.3]


@pytest.fixture
def kb(tmp_path):
    db = Database(tmp_path / "kb.db")
    repo = SqliteDocumentRepository(db)
    vs = FakeVectorStore()
    indexer = IndexingService(embedder=FakeEmbedder(), vector_store=vs, chunk_size=1000, chunk_overlap=100)
    ingestion = IngestionService(
        registry=build_default_registry(), repository=repo,
        upload_dir=tmp_path, max_upload_bytes=10 * 1024 * 1024, indexer=indexer,
    )
    return KnowledgeBaseService(repository=repo, indexer=indexer, ingestion=ingestion), ingestion, vs


def test_kb_add_list_rename_delete(kb) -> None:
    kb_service, ingestion, vs = kb
    doc = ingestion.ingest(filename="policy.txt", data=b"Revenue recognition under IFRS 15.")
    assert kb_service.count() == 1
    assert vs.documents == {doc.document_id}

    summary = kb_service.list()[0]
    assert summary["filename"] == "policy.txt"
    assert summary["chunks"] and summary["chunks"] >= 1

    kb_service.rename(doc.document_id, "renamed.txt")
    assert kb_service.list()[0]["filename"] == "renamed.txt"

    kb_service.delete(doc.document_id)
    assert kb_service.count() == 0
    assert vs.documents == set()  # vectors removed too


def test_kb_replace_preserves_identity(kb) -> None:
    kb_service, ingestion, vs = kb
    doc = ingestion.ingest(filename="v1.txt", data=b"Version one content about audit risk.")
    original_id = doc.document_id

    replaced = kb_service.replace(original_id, filename="v2.txt", data=b"Version two content about sampling.")
    assert replaced.document_id == original_id  # identity preserved
    assert kb_service.count() == 1  # no duplicate
    assert kb_service.list()[0]["filename"] == "v2.txt"
    fetched = kb_service._repo.get(original_id)
    assert "sampling" in fetched.full_text
