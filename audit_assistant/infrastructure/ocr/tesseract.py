"""Tesseract OCR adapter.

The ``pytesseract`` pip package only wraps the Tesseract *binary*, which must be
installed separately (e.g. ``winget install UB-Mannheim.TesseractOCR``). This
adapter degrades gracefully: :meth:`available` reports whether the binary is
present, and the caller falls back to the vision LLM (the primary path) when it
is not.
"""

from __future__ import annotations

import io

from audit_assistant.core.logging import get_logger

log = get_logger(__name__)


class TesseractOcr:
    """Offline OCR via the Tesseract binary (optional)."""

    def __init__(self, tesseract_cmd: str | None = None) -> None:
        self._cmd = tesseract_cmd
        self._checked = False
        self._available = False

    def available(self) -> bool:
        """Whether the Tesseract binary is callable (result cached)."""
        if self._checked:
            return self._available
        self._checked = True
        try:
            import pytesseract

            if self._cmd:
                pytesseract.pytesseract.tesseract_cmd = self._cmd
            pytesseract.get_tesseract_version()
            self._available = True
        except Exception as exc:  # noqa: BLE001 - any failure => unavailable
            log.info("Tesseract OCR not available: %s", exc)
            self._available = False
        return self._available

    def extract_text(self, data: bytes) -> str:
        """Return OCR text for an image, or empty string if unavailable/failed."""
        if not self.available():
            return ""
        import pytesseract
        from PIL import Image

        try:
            with Image.open(io.BytesIO(data)) as img:
                return pytesseract.image_to_string(img).strip()
        except Exception as exc:  # noqa: BLE001
            log.warning("Tesseract OCR failed: %s", exc)
            return ""
