"""Excel parser: one page per worksheet, each sheet preserved as a table.

Uses pandas (openpyxl engine for .xlsx, xlrd for legacy .xls). Sheets become
both a :class:`Table` (structure preserved) and a text rendering (so the RAG
layer can embed sheet content).
"""

from __future__ import annotations

import io

import pandas as pd

from audit_assistant.core.exceptions import ParsingError
from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import DocumentPage, FileType, ParsedDocument, Table

log = get_logger(__name__)


def _df_to_table(df: pd.DataFrame, sheet_name: str, page: int) -> Table:
    header = [str(c) for c in df.columns]
    body = [[("" if pd.isna(v) else str(v)) for v in row] for row in df.itertuples(index=False)]
    return Table(rows=[header, *body], page=page, name=sheet_name)


class ExcelParser:
    """Parses .xlsx/.xls workbooks, one worksheet per page."""

    def supports(self, file_type: FileType) -> bool:
        return file_type in {FileType.XLSX, FileType.XLS}

    def parse(self, *, filename: str, data: bytes, file_type: FileType) -> ParsedDocument:
        engine = "xlrd" if file_type == FileType.XLS else "openpyxl"
        try:
            sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, engine=engine)
        except Exception as exc:  # noqa: BLE001
            raise ParsingError(f"Failed to parse Excel '{filename}': {exc}") from exc

        pages: list[DocumentPage] = []
        for idx, (sheet_name, df) in enumerate(sheets.items(), start=1):
            df = df.dropna(how="all").dropna(axis=1, how="all")
            table = _df_to_table(df, sheet_name, idx)
            text = f"Sheet: {sheet_name}\n{table.to_markdown()}"
            pages.append(DocumentPage(number=idx, text=text, tables=[table]))

        log.info("Parsed Excel '%s': %d sheet(s)", filename, len(pages))
        return ParsedDocument(
            filename=filename,
            file_type=file_type,
            pages=pages,
            metadata={"sheets": ", ".join(sheets.keys())},
        )
