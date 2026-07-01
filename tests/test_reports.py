"""Report model, exporters, and generation tests."""

from __future__ import annotations

from audit_assistant.domain.models import Chunk, RetrievedChunk
from audit_assistant.infrastructure.llm.fake_provider import FakeLLMProvider
from audit_assistant.reports.exporters import to_docx, to_pdf, to_xlsx
from audit_assistant.reports.models import Report, ReportSection, parse_markdown_sections
from audit_assistant.services.report_service import ReportService


class StubRag:
    def __init__(self, results):
        self._results = results

    def retrieve(self, query, *, top_k=None, document_ids=None):
        return self._results


def _report() -> Report:
    return Report(
        title="Audit Summary",
        sections=[
            ReportSection("Scope", "The audit covered FY2025 revenue."),
            ReportSection("Findings", "Materiality was SAR 500,000."),
        ],
    )


def test_parse_markdown_sections() -> None:
    md = "# Title\nIntro text.\n## Overview\nBody one.\n## Conclusions\nBody two."
    sections = parse_markdown_sections(md, fallback_heading="Report")
    headings = [s.heading for s in sections]
    assert "Overview" in headings
    assert "Conclusions" in headings
    assert any("Intro text" in s.body for s in sections)


def test_report_to_markdown() -> None:
    md = _report().to_markdown()
    assert "# Audit Summary" in md
    assert "## Scope" in md


def test_pdf_export_is_valid() -> None:
    data = to_pdf(_report())
    assert data[:4] == b"%PDF"


def test_pdf_export_handles_unicode() -> None:
    # Non-latin-1 characters (riyal sign, em dash, accented) must not crash.
    report = Report(title="VAT ﷼ café — report", sections=[ReportSection("H", "Total ﷼ 1,000 — ok")])
    data = to_pdf(report)
    assert data[:4] == b"%PDF"


def test_docx_and_xlsx_are_zip_containers() -> None:
    assert to_docx(_report())[:4] == b"PK\x03\x04"
    assert to_xlsx(_report())[:4] == b"PK\x03\x04"


def test_report_generation_with_fake_llm() -> None:
    fake = FakeLLMProvider(
        reply="## Overview\nRevenue was 100 [Source 1].\n## Conclusions\nSatisfactory.\nConfidence: high"
    )
    contexts = [
        RetrievedChunk(
            chunk=Chunk(document_id="d1", filename="fs.pdf", text="Revenue 100.", page=2),
            score=0.8,
        )
    ]
    svc = ReportService(llm=fake, rag_service=StubRag(contexts))
    report = svc.generate("Executive summary", title="Q4 Exec Summary")

    assert report.title == "Q4 Exec Summary"
    headings = [s.heading for s in report.sections]
    assert "Overview" in headings and "Conclusions" in headings
    # Context was fed to the model.
    assert "Revenue 100." in fake.last_messages[-1].content
    # And it exports.
    assert svc.export(report, "PDF")[:4] == b"%PDF"
