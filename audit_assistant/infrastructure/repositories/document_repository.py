"""SQLite-backed document metadata repository.

Persists the full :class:`ParsedDocument` as JSON so it survives restarts and
satisfies the :class:`DocumentRepository` port. Chunk vectors live separately in
ChromaDB (Phase 2); this table is the source of truth for document listing and
provenance.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import (
    DocumentPage,
    FileType,
    ParsedDocument,
    Table,
)
from audit_assistant.infrastructure.db import Database

log = get_logger(__name__)


def _serialize(doc: ParsedDocument) -> str:
    payload = {
        "document_id": doc.document_id,
        "filename": doc.filename,
        "file_type": doc.file_type.value,
        "created_at": doc.created_at.isoformat(),
        "metadata": doc.metadata,
        "pages": [
            {
                "number": p.number,
                "text": p.text,
                "tables": [{"rows": t.rows, "page": t.page, "name": t.name} for t in p.tables],
            }
            for p in doc.pages
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def _deserialize(content_json: str) -> ParsedDocument:
    data = json.loads(content_json)
    pages = [
        DocumentPage(
            number=p["number"],
            text=p["text"],
            tables=[Table(rows=t["rows"], page=t.get("page"), name=t.get("name")) for t in p["tables"]],
        )
        for p in data["pages"]
    ]
    return ParsedDocument(
        filename=data["filename"],
        file_type=FileType(data["file_type"]),
        pages=pages,
        metadata=data.get("metadata", {}),
        document_id=data["document_id"],
        created_at=datetime.fromisoformat(data["created_at"]),
    )


class SqliteDocumentRepository:
    """Implements :class:`audit_assistant.domain.interfaces.DocumentRepository`."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def save(self, document: ParsedDocument, *, file_path: str | None = None) -> None:
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents
                    (document_id, filename, file_type, page_count, created_at,
                     file_path, content_json, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document.document_id,
                    document.filename,
                    document.file_type.value,
                    document.page_count,
                    document.created_at.isoformat(),
                    file_path,
                    _serialize(document),
                    json.dumps(document.metadata, ensure_ascii=False),
                ),
            )
        log.info("Persisted document '%s' (%s)", document.filename, document.document_id)

    def get(self, document_id: str) -> ParsedDocument | None:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT content_json FROM documents WHERE document_id = ?",
                (document_id,),
            ).fetchone()
        return _deserialize(row["content_json"]) if row else None

    def list_all(self) -> list[ParsedDocument]:
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT content_json FROM documents ORDER BY created_at DESC"
            ).fetchall()
        return [_deserialize(r["content_json"]) for r in rows]

    def count(self) -> int:
        """Number of documents in the persistent knowledge base (cheap)."""
        with self._db.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()
        return int(row["n"]) if row else 0

    def existing_filenames(self) -> set[str]:
        """Filenames already in the knowledge base (cheap; for idempotent bulk load)."""
        with self._db.connect() as conn:
            rows = conn.execute("SELECT DISTINCT filename FROM documents").fetchall()
        return {r["filename"] for r in rows}

    def list_summaries(self) -> list[dict]:
        """Lightweight metadata rows for the knowledge-base management UI."""
        import json as _json

        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT document_id, filename, file_type, page_count, created_at, "
                "file_path, metadata_json FROM documents ORDER BY created_at DESC"
            ).fetchall()
        out: list[dict] = []
        for r in rows:
            meta = _json.loads(r["metadata_json"] or "{}")
            size = None
            if r["file_path"]:
                try:
                    size = Path(r["file_path"]).stat().st_size
                except OSError:
                    size = None
            out.append(
                {
                    "document_id": r["document_id"],
                    "filename": r["filename"],
                    "file_type": r["file_type"],
                    "pages": r["page_count"],
                    "created_at": r["created_at"],
                    "size_bytes": size,
                    "chunks": int(meta["chunks"]) if str(meta.get("chunks", "")).isdigit() else None,
                    "metadata": meta,
                }
            )
        return out

    def rename(self, document_id: str, new_filename: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE documents SET filename = ? WHERE document_id = ?",
                (new_filename, document_id),
            )
        log.info("Renamed document %s -> %s", document_id, new_filename)

    def file_path(self, document_id: str) -> str | None:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT file_path FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
        return row["file_path"] if row else None

    def delete(self, document_id: str) -> None:
        with self._db.connect() as conn:
            conn.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
        log.info("Deleted document %s", document_id)
