"""Ports (interfaces) the service layer depends on.

Using :class:`typing.Protocol` gives us structural typing: infrastructure
adapters satisfy these contracts without importing the domain, keeping the
dependency arrows pointing inward (clean architecture).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Protocol, runtime_checkable

from audit_assistant.domain.models import (
    Answer,
    Chunk,
    FileType,
    Message,
    ParsedDocument,
    RetrievedChunk,
)


@runtime_checkable
class Parser(Protocol):
    """Extracts a :class:`ParsedDocument` from raw file bytes."""

    def supports(self, file_type: FileType) -> bool: ...

    def parse(self, *, filename: str, data: bytes, file_type: FileType) -> ParsedDocument: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Turns text into dense vectors."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


@runtime_checkable
class VectorStore(Protocol):
    """Persists and retrieves chunks by semantic similarity."""

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None: ...

    def query(
        self, embedding: list[float], top_k: int, document_ids: list[str] | None = None
    ) -> list[RetrievedChunk]: ...

    def delete_document(self, document_id: str) -> None: ...


@runtime_checkable
class LLMProvider(Protocol):
    """A chat-completion backend (Gemini, OpenAI, Anthropic, Ollama)."""

    @property
    def name(self) -> str: ...

    def is_configured(self) -> bool: ...

    def complete(self, messages: list[Message], *, system: str | None = None) -> str: ...

    def stream(
        self, messages: list[Message], *, system: str | None = None
    ) -> Iterator[str]: ...

    def complete_with_images(
        self, prompt: str, images: list[bytes], *, system: str | None = None
    ) -> str:
        """Vision call. Providers without vision may raise ``LLMError``."""
        ...


@runtime_checkable
class DocumentRepository(Protocol):
    """Persists document metadata (not the file bytes)."""

    def save(self, document: ParsedDocument) -> None: ...

    def get(self, document_id: str) -> ParsedDocument | None: ...

    def list_all(self) -> list[ParsedDocument]: ...

    def delete(self, document_id: str) -> None: ...


class AnswerBuilder(Protocol):
    """Assembles a grounded :class:`Answer` from retrieved context."""

    def build(self, question: str, contexts: Iterable[RetrievedChunk]) -> Answer: ...
