"""Image understanding tests (vision primary, OCR fallback) using fakes."""

from __future__ import annotations

from audit_assistant.infrastructure.llm.fake_provider import FakeLLMProvider
from audit_assistant.infrastructure.ocr.tesseract import TesseractOcr
from audit_assistant.services.image_service import _UNAVAILABLE, ImageUnderstandingService


class FakeOcr:
    def __init__(self, text: str = "", available: bool = True) -> None:
        self._text = text
        self._available = available

    def available(self) -> bool:
        return self._available

    def extract_text(self, data: bytes) -> str:
        return self._text


def test_transcribe_prefers_vision() -> None:
    fake = FakeLLMProvider(reply="Invoice total SAR 1,000")
    svc = ImageUnderstandingService(llm=fake, ocr=None)
    out = svc.transcribe(b"imgbytes")
    assert "image analysis" in out
    assert fake.last_images == [b"imgbytes"]


def test_transcribe_falls_back_to_ocr_without_llm() -> None:
    svc = ImageUnderstandingService(llm=None, ocr=FakeOcr(text="RECEIPT 42", available=True))
    out = svc.transcribe(b"x")
    assert "OCR transcription" in out
    assert "RECEIPT 42" in out


def test_transcribe_unavailable_when_no_vision_no_ocr() -> None:
    assert ImageUnderstandingService(llm=None, ocr=None).transcribe(b"x") == _UNAVAILABLE
    svc = ImageUnderstandingService(llm=None, ocr=FakeOcr(available=False))
    assert svc.transcribe(b"x") == _UNAVAILABLE


def test_analyze_requires_vision() -> None:
    fake = FakeLLMProvider(reply="No issues found")
    assert "image analysis" in ImageUnderstandingService(llm=fake).analyze(b"x", "check")
    assert ImageUnderstandingService(llm=None).analyze(b"x", "check") == _UNAVAILABLE


def test_tesseract_availability_is_safe() -> None:
    ocr = TesseractOcr()
    assert isinstance(ocr.available(), bool)
    if not ocr.available():
        # Must not raise when the binary is missing.
        assert ocr.extract_text(b"not-an-image") == ""


def test_ingestion_enriches_image_with_transcription(tmp_path, png_bytes) -> None:
    from audit_assistant.infrastructure.db import Database
    from audit_assistant.infrastructure.parsers.base import build_default_registry
    from audit_assistant.infrastructure.repositories.document_repository import (
        SqliteDocumentRepository,
    )
    from audit_assistant.services.ingestion_service import IngestionService

    analyzer = ImageUnderstandingService(llm=FakeLLMProvider(reply="Vendor: Acme; Total: 500"))
    svc = IngestionService(
        registry=build_default_registry(),
        repository=SqliteDocumentRepository(Database(tmp_path / "t.db")),
        upload_dir=tmp_path,
        max_upload_bytes=5 * 1024 * 1024,
        image_analyzer=analyzer,
    )
    doc = svc.ingest(filename="invoice.png", data=png_bytes)
    assert "image analysis" in doc.pages[0].text
    assert "Acme" in doc.pages[0].text
