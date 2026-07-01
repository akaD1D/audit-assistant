"""Per-parser tests against real in-memory sample files."""

from __future__ import annotations

import pytest

from audit_assistant.core.exceptions import UnsupportedFileTypeError
from audit_assistant.domain.models import FileType
from audit_assistant.infrastructure.parsers.base import (
    build_default_registry,
    detect_file_type,
)


@pytest.fixture
def registry():
    return build_default_registry()


def test_detect_file_type() -> None:
    assert detect_file_type("report.PDF") == FileType.PDF
    assert detect_file_type("data.xlsx") == FileType.XLSX
    assert detect_file_type("photo.JPEG") == FileType.JPEG
    with pytest.raises(UnsupportedFileTypeError):
        detect_file_type("archive.zip")


def test_pdf_parser(registry, pdf_bytes) -> None:
    doc = registry.parse(filename="report.pdf", data=pdf_bytes)
    assert doc.page_count == 2
    assert "Materiality" in doc.full_text
    assert doc.pages[1].number == 2


def test_excel_parser_multisheet(registry, xlsx_bytes) -> None:
    doc = registry.parse(filename="workbook.xlsx", data=xlsx_bytes)
    assert doc.page_count == 2  # one page per sheet
    names = {t.name for t in doc.all_tables}
    assert {"TrialBalance", "Payables"} <= names
    assert "Cash" in doc.full_text


def test_csv_parser(registry, csv_bytes) -> None:
    doc = registry.parse(filename="tb.csv", data=csv_bytes)
    assert len(doc.all_tables) == 1
    table = doc.all_tables[0]
    assert table.rows[0] == ["Account", "Amount"]
    assert doc.metadata["rows"] == "2"


def test_docx_parser(registry, docx_bytes) -> None:
    doc = registry.parse(filename="policy.docx", data=docx_bytes)
    assert "IFRS 15" in doc.full_text
    assert len(doc.all_tables) == 1
    assert doc.all_tables[0].rows[0] == ["Account", "Amount"]


def test_txt_parser(registry, txt_bytes) -> None:
    doc = registry.parse(filename="notes.txt", data=txt_bytes)
    assert "ISA 315" in doc.full_text


def test_image_parser_registers_metadata(registry, png_bytes) -> None:
    doc = registry.parse(filename="invoice.png", data=png_bytes)
    assert doc.file_type == FileType.PNG
    assert doc.metadata["width"] == "80"
    assert doc.metadata["format"] == "PNG"
