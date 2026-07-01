"""Core domain models shared across the application.

These are plain dataclasses (no persistence framework) so they can flow freely
between parsers, services, the vector store, and the UI. Persistence mapping
lives in the repository layer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _new_id() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FileType(str, Enum):
    """Supported upload types."""

    PDF = "pdf"
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"
    DOCX = "docx"
    TXT = "txt"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"

    @property
    def is_image(self) -> bool:
        return self in {FileType.PNG, FileType.JPG, FileType.JPEG}

    @property
    def is_spreadsheet(self) -> bool:
        return self in {FileType.XLSX, FileType.XLS, FileType.CSV}


@dataclass(slots=True)
class Table:
    """A tabular region extracted from a document."""

    rows: list[list[str]]
    page: int | None = None
    name: str | None = None  # e.g. sheet name for Excel

    def to_markdown(self) -> str:
        """Render the table as GitHub-flavoured markdown (header = first row)."""
        if not self.rows:
            return ""
        header, *body = self.rows
        cols = len(header)
        lines = [
            "| " + " | ".join(str(c) for c in header) + " |",
            "| " + " | ".join(["---"] * cols) + " |",
        ]
        for row in body:
            padded = list(row) + [""] * (cols - len(row))
            lines.append("| " + " | ".join(str(c) for c in padded[:cols]) + " |")
        return "\n".join(lines)


@dataclass(slots=True)
class DocumentPage:
    """One logical page/section of a parsed document."""

    number: int
    text: str
    tables: list[Table] = field(default_factory=list)


@dataclass(slots=True)
class ParsedDocument:
    """The unified output of every parser, regardless of source file type."""

    filename: str
    file_type: FileType
    pages: list[DocumentPage] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    document_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text)

    @property
    def all_tables(self) -> list[Table]:
        return [t for p in self.pages for t in p.tables]

    @property
    def page_count(self) -> int:
        return len(self.pages)


@dataclass(slots=True)
class Chunk:
    """A retrievable slice of a document, carrying citation metadata."""

    document_id: str
    filename: str
    text: str
    page: int | None = None
    is_table: bool = False
    chunk_id: str = field(default_factory=_new_id)

    def citation_metadata(self) -> dict[str, str | int | bool]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "page": self.page if self.page is not None else -1,
            "is_table": self.is_table,
        }


@dataclass(slots=True)
class Citation:
    """A source reference attached to an answer."""

    filename: str
    page: int | None
    snippet: str
    score: float | None = None

    def label(self) -> str:
        loc = f", p.{self.page}" if self.page and self.page > 0 else ""
        return f"{self.filename}{loc}"


@dataclass(slots=True)
class RetrievedChunk:
    """A chunk returned from the vector store with its relevance score."""

    chunk: Chunk
    score: float


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(slots=True)
class Message:
    """A single conversation turn."""

    role: Role
    content: str
    citations: list[Citation] = field(default_factory=list)
    confidence: str | None = None  # "high" | "medium" | "low"
    created_at: datetime = field(default_factory=_utcnow)
    message_id: str = field(default_factory=_new_id)


@dataclass(slots=True)
class Answer:
    """A grounded assistant answer with provenance."""

    text: str
    citations: list[Citation] = field(default_factory=list)
    confidence: str = "medium"
