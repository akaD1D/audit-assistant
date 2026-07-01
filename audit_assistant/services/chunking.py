"""Structure-aware chunking.

Splits a :class:`ParsedDocument` into retrievable :class:`Chunk` objects while
preserving provenance (page number) and keeping tables intact as their own
chunks (tables lose meaning when split mid-row). Text is packed paragraph-first
with character overlap so retrieval keeps surrounding context.
"""

from __future__ import annotations

import re

from audit_assistant.domain.models import Chunk, ParsedDocument

_WS = re.compile(r"[ \t]+")
_PARA = re.compile(r"\n\s*\n")


def _hard_window(text: str, size: int, overlap: int) -> list[str]:
    """Fixed-width windows with overlap for a paragraph larger than ``size``."""
    step = max(1, size - overlap)
    out: list[str] = []
    for i in range(0, len(text), step):
        out.append(text[i : i + size])
        if i + size >= len(text):
            break
    return out or [text]


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split free text into overlapping, paragraph-respecting chunks."""
    text = _WS.sub(" ", text).strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    paragraphs = [p.strip() for p in _PARA.split(text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)

        if len(para) <= chunk_size:
            tail = current[-overlap:] if (current and overlap) else ""
            current = f"{tail}\n\n{para}".strip() if tail else para
        else:
            pieces = _hard_window(para, chunk_size, overlap)
            chunks.extend(pieces[:-1])
            current = pieces[-1]

    if current:
        chunks.append(current)
    return chunks


def chunk_document(document: ParsedDocument, chunk_size: int, overlap: int) -> list[Chunk]:
    """Produce citation-tagged chunks for every page and table in a document."""
    chunks: list[Chunk] = []
    for page in document.pages:
        for piece in chunk_text(page.text, chunk_size, overlap):
            chunks.append(
                Chunk(
                    document_id=document.document_id,
                    filename=document.filename,
                    text=piece,
                    page=page.number,
                    is_table=False,
                )
            )
        for table in page.tables:
            md = table.to_markdown()
            if md:
                chunks.append(
                    Chunk(
                        document_id=document.document_id,
                        filename=document.filename,
                        text=md,
                        page=page.number,
                        is_table=True,
                    )
                )
    return chunks
