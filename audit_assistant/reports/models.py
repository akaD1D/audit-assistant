"""Report data model (source-format-independent)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class ReportSection:
    heading: str
    body: str


@dataclass(slots=True)
class Report:
    """A structured report that exporters render to PDF / Word / Excel."""

    title: str
    sections: list[ReportSection] = field(default_factory=list)
    subtitle: str = ""
    author: str = "AI Audit Assistant"
    report_date: str = field(default_factory=lambda: date.today().isoformat())

    def to_markdown(self) -> str:
        lines = [f"# {self.title}"]
        if self.subtitle:
            lines.append(f"_{self.subtitle}_")
        lines.append(f"\n*{self.author} — {self.report_date}*\n")
        for section in self.sections:
            lines.append(f"\n## {section.heading}\n")
            lines.append(section.body)
        return "\n".join(lines)


def parse_markdown_sections(markdown: str, *, fallback_heading: str = "Report") -> list[ReportSection]:
    """Split LLM markdown into sections on ``##`` headings.

    Content before the first ``##`` (and any ``#`` title) becomes an intro
    section so nothing is lost.
    """
    sections: list[ReportSection] = []
    current_heading = fallback_heading
    current_body: list[str] = []

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_body:
                sections.append(ReportSection(current_heading, "\n".join(current_body).strip()))
                current_body = []
            current_heading = stripped[3:].strip()
        elif stripped.startswith("# "):
            continue  # top-level title handled separately
        else:
            current_body.append(line)

    if current_body:
        sections.append(ReportSection(current_heading, "\n".join(current_body).strip()))
    return [s for s in sections if s.body]
