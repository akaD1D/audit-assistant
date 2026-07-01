"""Parser registry and file-type detection."""

from __future__ import annotations

from pathlib import Path

from audit_assistant.core.exceptions import UnsupportedFileTypeError
from audit_assistant.domain.interfaces import Parser
from audit_assistant.domain.models import FileType, ParsedDocument

# Map lower-case extension (without dot) -> FileType.
_EXTENSION_MAP: dict[str, FileType] = {
    "pdf": FileType.PDF,
    "xlsx": FileType.XLSX,
    "xlsm": FileType.XLSX,
    "xls": FileType.XLS,
    "csv": FileType.CSV,
    "docx": FileType.DOCX,
    "txt": FileType.TXT,
    "text": FileType.TXT,
    "png": FileType.PNG,
    "jpg": FileType.JPG,
    "jpeg": FileType.JPEG,
}


def detect_file_type(filename: str) -> FileType:
    """Infer :class:`FileType` from a filename extension.

    Raises :class:`UnsupportedFileTypeError` if the extension is unknown.
    """
    ext = Path(filename).suffix.lower().lstrip(".")
    file_type = _EXTENSION_MAP.get(ext)
    if file_type is None:
        raise UnsupportedFileTypeError(f"Unsupported file extension: '.{ext}' ({filename})")
    return file_type


def supported_extensions() -> list[str]:
    """Extensions accepted by the app (for the UI uploader)."""
    return sorted(_EXTENSION_MAP.keys())


class ParserRegistry:
    """Routes a :class:`FileType` to the parser that handles it."""

    def __init__(self, parsers: list[Parser]) -> None:
        self._parsers = parsers

    def for_type(self, file_type: FileType) -> Parser:
        for parser in self._parsers:
            if parser.supports(file_type):
                return parser
        raise UnsupportedFileTypeError(f"No parser registered for {file_type.value}")

    def parse(self, *, filename: str, data: bytes, file_type: FileType | None = None) -> ParsedDocument:
        """Detect (if needed) and parse a document from raw bytes."""
        ft = file_type or detect_file_type(filename)
        return self.for_type(ft).parse(filename=filename, data=data, file_type=ft)


def build_default_registry() -> ParserRegistry:
    """Construct the registry with all built-in parsers.

    Imports are local so that importing this module stays cheap and a missing
    optional dependency only fails when that specific parser is used.
    """
    from audit_assistant.infrastructure.parsers.csv_parser import CsvParser
    from audit_assistant.infrastructure.parsers.docx_parser import DocxParser
    from audit_assistant.infrastructure.parsers.excel_parser import ExcelParser
    from audit_assistant.infrastructure.parsers.image_parser import ImageParser
    from audit_assistant.infrastructure.parsers.pdf_parser import PdfParser
    from audit_assistant.infrastructure.parsers.txt_parser import TxtParser

    return ParserRegistry(
        [
            PdfParser(),
            ExcelParser(),
            CsvParser(),
            DocxParser(),
            TxtParser(),
            ImageParser(),
        ]
    )
