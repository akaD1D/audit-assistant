"""Repository implementations (persistence adapters)."""

from audit_assistant.infrastructure.repositories.document_repository import (
    SqliteDocumentRepository,
)

__all__ = ["SqliteDocumentRepository"]
