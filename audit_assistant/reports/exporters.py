"""Report exporters: Report -> PDF / Word / Excel bytes."""

from __future__ import annotations

import io

from audit_assistant.reports.models import Report


def _latin1_safe(text: str) -> str:
    """fpdf2 core fonts are Latin-1 only; replace unsupported glyphs."""
    return text.encode("latin-1", "replace").decode("latin-1")


def to_pdf(report: Report) -> bytes:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def block(text: str, size: int, style: str = "") -> None:
        # new_x=LMARGIN keeps the cursor at the left margin so the next block
        # has the full page width (fpdf2 otherwise leaves x at the right edge).
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(0, size * 0.5 + 2, _latin1_safe(text),
                       new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    block(report.title, 18, "B")
    if report.subtitle:
        block(report.subtitle, 12, "I")
    block(f"{report.author} — {report.report_date}", 10)
    pdf.ln(4)

    for section in report.sections:
        block(section.heading, 13, "B")
        block(section.body, 11)
        pdf.ln(3)

    return bytes(pdf.output())  # fpdf2 >=2.8 returns a bytearray


def to_docx(report: Report) -> bytes:
    import docx

    document = docx.Document()
    document.add_heading(report.title, level=0)
    if report.subtitle:
        document.add_paragraph(report.subtitle, style="Intense Quote")
    document.add_paragraph(f"{report.author} — {report.report_date}")

    for section in report.sections:
        document.add_heading(section.heading, level=1)
        for para in section.body.split("\n\n"):
            if para.strip():
                document.add_paragraph(para.strip())

    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def to_xlsx(report: Report) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Report"

    ws["A1"] = report.title
    ws["A1"].font = Font(bold=True, size=16)
    ws["A2"] = report.subtitle
    ws["A3"] = f"{report.author} — {report.report_date}"

    row = 5
    for section in report.sections:
        cell = ws.cell(row=row, column=1, value=section.heading)
        cell.font = Font(bold=True, size=12)
        row += 1
        body_cell = ws.cell(row=row, column=1, value=section.body)
        body_cell.alignment = body_cell.alignment.copy(wrap_text=True, vertical="top")
        row += 2

    ws.column_dimensions[get_column_letter(1)].width = 100
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


EXPORTERS = {"PDF": to_pdf, "Word": to_docx, "Excel": to_xlsx}
EXTENSIONS = {"PDF": "pdf", "Word": "docx", "Excel": "xlsx"}
MIME_TYPES = {
    "PDF": "application/pdf",
    "Word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "Excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
