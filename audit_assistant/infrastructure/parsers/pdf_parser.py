"""PDF parser: single-pass text + tables via PyMuPDF.

Uses PyMuPDF (fitz) for both text and table detection in one pass. This is far
faster on large reports than re-opening the file with pdfplumber, which matters
for 100+ page annual reports. Table detection is best-effort per page and never
fails the whole parse.
"""

from __future__ import annotations

from audit_assistant.core.exceptions import ParsingError
from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import DocumentPage, FileType, ParsedDocument, Table

log = get_logger(__name__)


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


class PdfParser:
    """Parses PDFs page-by-page, preserving page numbers and tables."""

    def supports(self, file_type: FileType) -> bool:
        return file_type == FileType.PDF

    def parse(self, *, filename: str, data: bytes, file_type: FileType) -> ParsedDocument:
        import fitz  # PyMuPDF

        pages: list[DocumentPage] = []
        try:
            with fitz.open(stream=data, filetype="pdf") as doc:
                doc_metadata = {k: str(v) for k, v in (doc.metadata or {}).items() if v}
                for idx, page in enumerate(doc, start=1):
                    text = page.get_text("text")
                    tables = self._extract_tables(page, idx)
                    pages.append(DocumentPage(number=idx, text=text.strip(), tables=tables))
        except Exception as exc:  # noqa: BLE001 - surface any backend failure uniformly
            raise ParsingError(f"Failed to parse PDF '{filename}': {exc}") from exc

        log.info("Parsed PDF '%s': %d pages", filename, len(pages))
        return ParsedDocument(
            filename=filename,
            file_type=file_type,
            pages=pages,
            metadata=doc_metadata,
        )

    @staticmethod
    def _extract_tables(page, page_number: int) -> list[Table]:
        """Best-effort table extraction; never raises."""
        tables: list[Table] = []
        try:
            found = page.find_tables()
        except Exception:  # noqa: BLE001 - table detection is optional
            return tables
        for tbl in getattr(found, "tables", []):
            try:
                rows = tbl.extract()
            except Exception:  # noqa: BLE001
                continue
            cleaned = [[_clean(c) for c in row] for row in rows if row]
            if cleaned:
                tables.append(Table(rows=cleaned, page=page_number))
        return tables
