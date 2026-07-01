"""CSV parser: whole file as a single table + markdown text rendering."""

from __future__ import annotations

import io

import pandas as pd

from audit_assistant.core.exceptions import ParsingError
from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import DocumentPage, FileType, ParsedDocument, Table

log = get_logger(__name__)


class CsvParser:
    """Parses CSV files with pandas (encoding-tolerant)."""

    def supports(self, file_type: FileType) -> bool:
        return file_type == FileType.CSV

    def parse(self, *, filename: str, data: bytes, file_type: FileType) -> ParsedDocument:
        try:
            try:
                df = pd.read_csv(io.BytesIO(data))
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(data), encoding="latin-1")
        except Exception as exc:  # noqa: BLE001
            raise ParsingError(f"Failed to parse CSV '{filename}': {exc}") from exc

        header = [str(c) for c in df.columns]
        body = [[("" if pd.isna(v) else str(v)) for v in row] for row in df.itertuples(index=False)]
        table = Table(rows=[header, *body], page=1, name=filename)

        log.info("Parsed CSV '%s': %d rows x %d cols", filename, len(df), len(df.columns))
        return ParsedDocument(
            filename=filename,
            file_type=file_type,
            pages=[DocumentPage(number=1, text=table.to_markdown(), tables=[table])],
            metadata={"rows": str(len(df)), "columns": str(len(df.columns))},
        )
