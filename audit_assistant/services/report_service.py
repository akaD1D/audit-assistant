"""Report generation service.

Drafts structured audit reports grounded in the uploaded documents (RAG + LLM),
then hands the :class:`Report` to exporters for PDF / Word / Excel output. The
narrative is LLM-written but every figure it cites is retrieved from documents,
and the audit system prompt forbids invention.
"""

from __future__ import annotations

from audit_assistant.audit.prompts.system import AUDIT_SYSTEM_PROMPT
from audit_assistant.core.exceptions import LLMError
from audit_assistant.core.logging import get_logger
from audit_assistant.domain.interfaces import LLMProvider
from audit_assistant.domain.models import Message, Role
from audit_assistant.reports.exporters import EXPORTERS
from audit_assistant.reports.models import Report, parse_markdown_sections
from audit_assistant.services.rag_service import RagService

log = get_logger(__name__)

# report_type -> (retrieval query, section outline)
REPORT_TYPES: dict[str, tuple[str, list[str]]] = {
    "Executive summary": (
        "key figures, financial highlights, overall conclusions",
        ["Overview", "Key Figures", "Conclusions"],
    ),
    "Audit summary": (
        "audit scope, procedures performed, findings, conclusions",
        ["Scope & Objectives", "Procedures Performed", "Findings", "Conclusion"],
    ),
    "Risk report": (
        "risks, internal controls, materiality, fraud indicators",
        ["Risk Overview", "Key Risks", "Control Environment", "Recommendations"],
    ),
    "Findings & recommendations": (
        "issues, exceptions, misstatements, control weaknesses",
        ["Findings", "Impact", "Recommendations"],
    ),
    "Observations report": (
        "observations, notable items, follow-up matters",
        ["Observations", "Analysis", "Follow-up Actions"],
    ),
}


class ReportService:
    """Generates and exports grounded audit reports."""

    def __init__(self, *, llm: LLMProvider, rag_service: RagService, default_top_k: int = 8) -> None:
        self._llm = llm
        self._rag = rag_service
        self._top_k = default_top_k

    def generate(
        self,
        report_type: str,
        *,
        title: str | None = None,
        document_ids: list[str] | None = None,
        language: str = "English",
    ) -> Report:
        query, outline = REPORT_TYPES.get(report_type, ("summary", ["Summary"]))
        contexts = self._rag.retrieve(query, top_k=self._top_k, document_ids=document_ids)

        source_block = "\n\n".join(
            f"[Source {i}] {rc.chunk.filename}"
            + (f", page {rc.chunk.page}" if rc.chunk.page else "")
            + f":\n{rc.chunk.text}"
            for i, rc in enumerate(contexts, start=1)
        ) or "(No document context retrieved.)"

        outline_text = "\n".join(f"## {h}" for h in outline)
        lang_note = (
            f"Write the ENTIRE report in {language} (professional audit {language}), "
            "translating the section headings into that language. Keep figures, currency "
            "amounts, and standard codes (IFRS 15, ISA 320) as-is."
            if language.lower() != "english"
            else "Write the report in English."
        )
        prompt = (
            f"Write a professional **{report_type}** for an auditor, using ONLY the context "
            f"below. Ground every figure and statement in the sources and cite them as "
            f"[Source N]. If the context lacks something, say so rather than inventing it.\n\n"
            f"{lang_note}\n\n"
            f"Use these section topics as Markdown '## ' headings:\n{outline_text}\n\n"
            f"CONTEXT:\n{source_block}"
        )

        try:
            markdown = self._llm.complete(
                [Message(role=Role.USER, content=prompt)], system=AUDIT_SYSTEM_PROMPT
            )
        except LLMError as exc:
            log.warning("Report generation failed: %s", exc)
            raise

        sections = parse_markdown_sections(markdown, fallback_heading=report_type)
        report = Report(
            title=title or report_type,
            subtitle=f"{report_type} generated from {len(contexts)} source passage(s)",
            sections=sections,
        )
        log.info("Generated '%s' with %d section(s)", report_type, len(sections))
        return report

    @staticmethod
    def export(report: Report, fmt: str) -> bytes:
        exporter = EXPORTERS.get(fmt)
        if exporter is None:
            raise ValueError(f"Unknown export format '{fmt}'. Use one of {list(EXPORTERS)}.")
        return exporter(report)
