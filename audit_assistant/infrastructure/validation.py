"""Secure upload validation: extension, size, and content-signature checks.

We verify the file's *magic bytes* against its claimed extension rather than
trusting the name alone — a ``.pdf`` that is really an executable is rejected.
Signature checking is done in-process (no external ``libmagic`` dependency),
which is both safer and more portable on Windows.
"""

from __future__ import annotations

from audit_assistant.core.exceptions import FileValidationError
from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import FileType
from audit_assistant.infrastructure.parsers.base import detect_file_type

log = get_logger(__name__)

# Leading magic-byte signatures per family. Types with no reliable signature
# (plain text, CSV) are validated by extension + successful parse instead.
_ZIP = b"PK\x03\x04"  # .xlsx / .docx are ZIP containers (OOXML)
_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # legacy .xls (OLE2)

_SIGNATURES: dict[FileType, tuple[bytes, ...]] = {
    FileType.PDF: (b"%PDF",),
    FileType.PNG: (b"\x89PNG\r\n\x1a\n",),
    FileType.JPG: (b"\xff\xd8\xff",),
    FileType.JPEG: (b"\xff\xd8\xff",),
    FileType.XLSX: (_ZIP,),
    FileType.DOCX: (_ZIP,),
    FileType.XLS: (_OLE,),
}


def validate_upload(*, filename: str, data: bytes, max_bytes: int) -> FileType:
    """Validate an uploaded file and return its resolved :class:`FileType`.

    Raises :class:`FileValidationError` on any failure and
    :class:`UnsupportedFileTypeError` for unknown extensions.
    """
    if not data:
        raise FileValidationError(f"'{filename}' is empty.")

    if len(data) > max_bytes:
        mb = max_bytes / (1024 * 1024)
        raise FileValidationError(
            f"'{filename}' exceeds the {mb:.0f} MB upload limit "
            f"({len(data) / (1024 * 1024):.1f} MB)."
        )

    file_type = detect_file_type(filename)  # raises UnsupportedFileTypeError

    signatures = _SIGNATURES.get(file_type)
    if signatures and not any(data.startswith(sig) for sig in signatures):
        raise FileValidationError(
            f"'{filename}' content does not match a valid {file_type.value.upper()} "
            "file (signature mismatch). The file may be corrupt or mislabelled."
        )

    log.debug("Validated upload '%s' as %s (%d bytes)", filename, file_type.value, len(data))
    return file_type
