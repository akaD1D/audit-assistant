"""Unit tests for structure-aware chunking."""

from __future__ import annotations

from audit_assistant.domain.models import DocumentPage, FileType, ParsedDocument, Table
from audit_assistant.services.chunking import chunk_document, chunk_text

CHUNK = 200
OVERLAP = 40


def test_empty_text() -> None:
    assert chunk_text("", CHUNK, OVERLAP) == []


def test_short_text_single_chunk() -> None:
    chunks = chunk_text("Short audit note.", CHUNK, OVERLAP)
    assert chunks == ["Short audit note."]


def test_long_multiparagraph_splits() -> None:
    text = "\n\n".join(f"Paragraph {i} about audit risk and controls." for i in range(30))
    chunks = chunk_text(text, CHUNK, OVERLAP)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)
    assert all(len(c) <= CHUNK + OVERLAP + 5 for c in chunks)
    # Content preserved.
    joined = " ".join(chunks)
    assert "Paragraph 0" in joined
    assert "Paragraph 29" in joined


def test_single_huge_paragraph_hard_windowed() -> None:
    text = "x" * 1000  # no paragraph breaks
    chunks = chunk_text(text, CHUNK, OVERLAP)
    assert len(chunks) > 1
    assert all(len(c) <= CHUNK for c in chunks)


def test_chunk_document_tags_pages_and_tables() -> None:
    doc = ParsedDocument(
        filename="report.pdf",
        file_type=FileType.PDF,
        pages=[
            DocumentPage(number=1, text="Revenue recognition under IFRS 15."),
            DocumentPage(
                number=2,
                text="Materiality assessment.",
                tables=[Table(rows=[["Account", "Amount"], ["Cash", "1000"]], page=2)],
            ),
        ],
    )
    chunks = chunk_document(doc, CHUNK, OVERLAP)
    pages = {c.page for c in chunks}
    assert pages == {1, 2}
    table_chunks = [c for c in chunks if c.is_table]
    assert len(table_chunks) == 1
    assert "Account" in table_chunks[0].text
    assert all(c.document_id == doc.document_id for c in chunks)
