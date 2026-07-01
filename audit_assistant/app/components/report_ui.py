"""Report generation & export UI (Phase 8)."""

from __future__ import annotations

import streamlit as st

from audit_assistant.core.exceptions import LLMError
from audit_assistant.core.logging import get_logger
from audit_assistant.reports.exporters import EXTENSIONS, MIME_TYPES
from audit_assistant.services.report_service import REPORT_TYPES

log = get_logger(__name__)


def render_reports(container) -> None:
    st.subheader("📄 Generate an audit report")
    st.caption("Grounded in your documents, exportable to PDF, Word, or Excel.")

    docs = st.session_state.get("documents", {})
    if not docs:
        st.info("Upload documents first — reports are generated from their content.")
        return
    if not container.is_llm_ready:
        st.warning("Report drafting needs an LLM provider — add a Gemini key to `.env`.")
        return

    col_type, col_lang = st.columns([2, 1])
    report_type = col_type.selectbox("Report type", list(REPORT_TYPES.keys()))
    language = col_lang.selectbox("Language", ["English", "Arabic"])
    title = st.text_input("Report title", value=report_type)
    labels = {f"{d.filename} ({did[:6]})": did for did, d in docs.items()}
    chosen = st.multiselect(
        "Documents to include (leave empty for all)", list(labels.keys())
    )
    doc_ids = [labels[c] for c in chosen] if chosen else None

    if st.button("✍️ Generate report"):
        with st.spinner("Drafting report from your documents…"):
            try:
                report = container.report_service.generate(
                    report_type, title=title, document_ids=doc_ids, language=language
                )
            except LLMError as exc:
                st.error(f"Report generation failed: {exc}")
                return
        st.session_state["last_report"] = report
        container.audit_log.record("report_generated", f"{report_type}: {title}")

    report = st.session_state.get("last_report")
    if not report:
        return

    st.divider()
    st.markdown(report.to_markdown())

    st.divider()
    st.markdown("**Export**")
    cols = st.columns(3)
    for col, fmt in zip(cols, ("PDF", "Word", "Excel"), strict=True):
        try:
            data = container.report_service.export(report, fmt)
        except Exception as exc:  # noqa: BLE001
            log.exception("Export to %s failed", fmt)
            col.error(f"{fmt}: {exc}")
            continue
        safe = "".join(c if c.isalnum() else "_" for c in report.title)[:40] or "report"
        col.download_button(
            f"⬇️ {fmt}",
            data=data,
            file_name=f"{safe}.{EXTENSIONS[fmt]}",
            mime=MIME_TYPES[fmt],
            key=f"dl_{fmt}",
        )
