"""Plain-text parser with encoding fallback."""

from __future__ import annotations

from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import DocumentPage, FileType, ParsedDocument

log = get_logger(__name__)


class TxtParser:
    """Parses .txt files, trying UTF-8 then Latin-1."""

    def supports(self, file_type: FileType) -> bool:
        return file_type == FileType.TXT

    def parse(self, *, filename: str, data: bytes, file_type: FileType) -> ParsedDocument:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1", errors="replace")

        log.info("Parsed text file '%s': %d chars", filename, len(text))
        return ParsedDocument(
            filename=filename,
            file_type=file_type,
            pages=[DocumentPage(number=1, text=text.strip())],
        )
