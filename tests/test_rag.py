"""End-to-end RAG tests: local embeddings + Qdrant retrieval.

These exercise the real fastembed model and an embedded Qdrant store. The first
run downloads the small ONNX model (~130 MB), so this module is marked slow.
"""

from __future__ import annotations

import pytest

from audit_assistant.domain.models import Chunk
from audit_assistant.infrastructure.embeddings.local import LocalEmbeddingProvider
from audit_assistant.infrastructure.vectorstore.qdrant_store import QdrantVectorStore

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def embedder() -> LocalEmbeddingProvider:
    return LocalEmbeddingProvider()


@pytest.fixture
def store(tmp_path):
    return QdrantVectorStore(tmp_path / "qdrant", collection="test_chunks")


def _chunk(text: str, doc_id: str, page: int) -> Chunk:
    return Chunk(document_id=doc_id, filename=f"{doc_id}.pdf", text=text, page=page)


def test_embedding_dimension(embedder) -> None:
    dim = embedder.dimension
    assert dim > 0
    vec = embedder.embed_query("materiality threshold")
    assert len(vec) == dim


def test_index_and_retrieve_relevant_chunk(embedder, store) -> None:
    chunks = [
        _chunk("Materiality is the threshold above which misstatements matter.", "d1", 1),
        _chunk("The office cafeteria serves lunch at noon.", "d1", 2),
        _chunk("Sampling selects a subset of transactions for testing.", "d1", 3),
    ]
    embeddings = embedder.embed_documents([c.text for c in chunks])
    store.add(chunks, embeddings)

    results = store.query(embedder.embed_query("What is materiality?"), top_k=1)
    assert len(results) == 1
    assert "Materiality" in results[0].chunk.text
    assert results[0].score > 0


def test_document_scoped_filter(embedder, store) -> None:
    a = _chunk("Revenue recognition under IFRS 15.", "docA", 1)
    b = _chunk("Revenue recognition under IFRS 15.", "docB", 1)
    embs = embedder.embed_documents([a.text, b.text])
    store.add([a, b], embs)

    results = store.query(
        embedder.embed_query("revenue recognition"), top_k=5, document_ids=["docB"]
    )
    assert results
    assert all(r.chunk.document_id == "docB" for r in results)


def test_delete_document(embedder, store) -> None:
    c = _chunk("Internal controls over financial reporting.", "gone", 1)
    store.add([c], embedder.embed_documents([c.text]))
    assert store.query(embedder.embed_query("internal controls"), top_k=5)

    store.delete_document("gone")
    assert store.query(embedder.embed_query("internal controls"), top_k=5) == []
