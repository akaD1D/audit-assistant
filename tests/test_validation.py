"""Upload validation tests: size, extension, and content-signature checks."""

from __future__ import annotations

import pytest

from audit_assistant.core.exceptions import (
    FileValidationError,
    UnsupportedFileTypeError,
)
from audit_assistant.domain.models import FileType
from audit_assistant.infrastructure.validation import validate_upload

MAX = 10 * 1024 * 1024


def test_valid_pdf_signature(pdf_bytes) -> None:
    assert validate_upload(filename="a.pdf", data=pdf_bytes, max_bytes=MAX) == FileType.PDF


def test_valid_png_signature(png_bytes) -> None:
    assert validate_upload(filename="a.png", data=png_bytes, max_bytes=MAX) == FileType.PNG


def test_empty_file_rejected() -> None:
    with pytest.raises(FileValidationError):
        validate_upload(filename="a.pdf", data=b"", max_bytes=MAX)


def test_oversized_file_rejected() -> None:
    with pytest.raises(FileValidationError):
        validate_upload(filename="a.txt", data=b"x" * 100, max_bytes=10)


def test_unsupported_extension_rejected() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validate_upload(filename="a.zip", data=b"PK\x03\x04data", max_bytes=MAX)


def test_signature_mismatch_rejected() -> None:
    # Claims to be a PDF but content is not.
    with pytest.raises(FileValidationError):
        validate_upload(filename="fake.pdf", data=b"this is not a pdf", max_bytes=MAX)


def test_csv_no_signature_passes() -> None:
    # CSV has no magic bytes; extension + non-empty is enough.
    assert validate_upload(filename="a.csv", data=b"h1,h2\n1,2\n", max_bytes=MAX) == FileType.CSV
