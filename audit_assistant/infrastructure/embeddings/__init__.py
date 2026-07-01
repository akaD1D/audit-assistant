"""Embedding adapters (implement the EmbeddingProvider port)."""

from audit_assistant.infrastructure.embeddings.local import LocalEmbeddingProvider

__all__ = ["LocalEmbeddingProvider"]
