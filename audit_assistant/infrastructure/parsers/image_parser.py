"""Image parser (Phase 1: metadata only).

Full understanding of images — OCR and vision-LLM extraction of invoices,
receipts, and statements — lands in Phase 4. Here we validate the image and
record its properties; the raw bytes are persisted to disk by the ingestion
service so the Phase-4 vision path can read them back.
"""

from __future__ import annotations

import io

from audit_assistant.core.exceptions import ParsingError
from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import DocumentPage, FileType, ParsedDocument

log = get_logger(__name__)

_PENDING_NOTE = (
    "[Image uploaded. Transcription is added during ingestion by the image "
    "understanding service (vision LLM, with OCR fallback).]"
)


class ImageParser:
    """Validates images and records dimensions/format; no OCR yet."""

    def supports(self, file_type: FileType) -> bool:
        return file_type.is_image

    def parse(self, *, filename: str, data: bytes, file_type: FileType) -> ParsedDocument:
        from PIL import Image

        try:
            with Image.open(io.BytesIO(data)) as img:
                width, height = img.size
                fmt = img.format or file_type.value.upper()
        except Exception as exc:  # noqa: BLE001
            raise ParsingError(f"Failed to read image '{filename}': {exc}") from exc

        log.info("Registered image '%s': %dx%d %s", filename, width, height, fmt)
        return ParsedDocument(
            filename=filename,
            file_type=file_type,
            pages=[DocumentPage(number=1, text=_PENDING_NOTE)],
            metadata={"width": str(width), "height": str(height), "format": fmt},
        )
