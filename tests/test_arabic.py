"""Arabic / RTL report support tests."""

from __future__ import annotations

from audit_assistant.infrastructure.llm.fake_provider import FakeLLMProvider
from audit_assistant.reports.exporters import to_docx, to_pdf, to_xlsx
from audit_assistant.reports.models import Report, ReportSection
from audit_assistant.reports.rtl import contains_arabic, shape_for_pdf
from audit_assistant.services.report_service import ReportService


class StubRag:
    def retrieve(self, query, *, top_k=None, document_ids=None):
        return []


def _arabic_report() -> Report:
    return Report(
        title="ملخص تنفيذي",
        sections=[
            ReportSection("النطاق", "شمل التدقيق إيرادات السنة المالية 2025 بمبلغ 72,337 مليون ريال."),
            ReportSection("الاستنتاج", "لا توجد تحريفات جوهرية."),
        ],
    )


def test_contains_arabic() -> None:
    assert contains_arabic("الأهمية النسبية")
    assert not contains_arabic("Materiality")
    assert contains_arabic("Revenue الإيرادات 100")  # mixed


def test_shape_for_pdf_returns_text() -> None:
    shaped = shape_for_pdf("المخاطر")
    assert isinstance(shaped, str) and shaped


def test_arabic_exports_are_valid() -> None:
    report = _arabic_report()
    assert to_pdf(report)[:4] == b"%PDF"
    assert to_docx(report)[:4] == b"PK\x03\x04"
    assert to_xlsx(report)[:4] == b"PK\x03\x04"


def test_report_generation_in_arabic() -> None:
    fake = FakeLLMProvider(reply="## نظرة عامة\nتم إنجاز التدقيق [Source 1].\nمستوى الثقة: high")
    svc = ReportService(llm=fake, rag_service=StubRag())
    report = svc.generate("Executive summary", title="تقرير", language="Arabic")

    assert report.sections
    # The Arabic language instruction reached the model.
    assert "Arabic" in fake.last_messages[-1].content
    assert to_pdf(report)[:4] == b"%PDF"
