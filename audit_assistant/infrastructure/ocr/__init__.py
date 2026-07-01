"""OCR adapters (fallback text extraction when no vision LLM is available)."""

from audit_assistant.infrastructure.ocr.tesseract import TesseractOcr

__all__ = ["TesseractOcr"]
