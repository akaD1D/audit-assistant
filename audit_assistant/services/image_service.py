"""Image understanding: transcribe + analyse audit evidence images.

Strategy (best first):
  1. Vision LLM (Gemini by default) — faithful transcription + light issue
     detection. Best quality, needs a configured provider.
  2. Tesseract OCR — offline raw-text fallback when no vision provider is set.

The transcription is written back into the document's text at ingestion time so
image content becomes searchable and answerable through the normal RAG flow.
"""

from __future__ import annotations

from audit_assistant.audit.prompts.vision import VISION_SYSTEM, VISION_TRANSCRIBE_PROMPT
from audit_assistant.core.exceptions import LLMError
from audit_assistant.core.logging import get_logger

log = get_logger(__name__)

_UNAVAILABLE = (
    "[Image could not be read automatically: no vision model is configured and "
    "offline OCR (Tesseract) is not installed. Add a Gemini key or install Tesseract.]"
)


class ImageUnderstandingService:
    """Transcribes and analyses images of audit evidence."""

    def __init__(self, *, llm=None, ocr=None) -> None:
        self._llm = llm
        self._ocr = ocr

    def _vision_available(self) -> bool:
        return self._llm is not None and self._llm.is_configured()

    def transcribe(self, data: bytes) -> str:
        """Faithful transcription of an image (for indexing + search)."""
        if self._vision_available():
            try:
                text = self._llm.complete_with_images(
                    VISION_TRANSCRIBE_PROMPT, [data], system=VISION_SYSTEM
                )
                if text.strip():
                    return text.strip()
                log.info("Vision returned empty text; trying OCR fallback.")
            except LLMError as exc:
                log.warning("Vision transcription failed (%s); trying OCR fallback.", exc)

        if self._ocr is not None and self._ocr.available():
            ocr_text = self._ocr.extract_text(data)
            if ocr_text:
                return f"[OCR transcription]\n{ocr_text}"

        return _UNAVAILABLE

    def analyze(self, data: bytes, instruction: str) -> str:
        """Answer a specific question about an image via the vision LLM."""
        if not self._vision_available():
            return _UNAVAILABLE
        try:
            return self._llm.complete_with_images(instruction, [data], system=VISION_SYSTEM)
        except LLMError as exc:
            return f"[Vision analysis failed: {exc}]"
