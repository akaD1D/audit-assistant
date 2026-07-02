"""Report wizard (Phase 8 + redesign).

Guided flow: (1) ensure a document exists → (2) choose report type + language →
(3) generate → preview + export to PDF / Word / Excel. Reports draw from the
uploaded session document(s) or the knowledge base.
"""

from __future__ import annotations

import hashlib

import streamlit as st

from audit_assistant.app.components.upload_ui import _process_file
from audit_assistant.core.exceptions import LLMError
from audit_assistant.core.logging import get_logger
from audit_assistant.reports.exporters import EXTENSIONS, MIME_TYPES
from audit_assistant.services.report_service import REPORT_TYPES

log = get_logger(__name__)

_ACCEPTED = ["pdf", "xlsx", "xls", "csv", "docx", "txt", "png", "jpg", "jpeg"]


def _upload_for_report(container, key: str) -> None:
    files = st.file_uploader(
        "Upload a document (PDF, Excel, CSV, Word, or an image)",
        type=_ACCEPTED,
        accept_multiple_files=True,
        key=key,
    )
    processed: set[str] = st.session_state.setdefault("processed_hashes", set())
    changed = False
    for up in files or []:
        data = up.getvalue()
        marker = f"{hashlib.sha256(data).hexdigest()}:report"
        if marker in processed:
            continue
        _process_file(container, name=up.name, data=data, to_kb=False)
        processed.add(marker)
        changed = True
    if changed:
        st.rerun()


def _session_retriever(container):
    from audit_assistant.services.session_store import SessionRetriever

    return SessionRetriever(container.embedding_provider, st.session_state["session_index"])


def render_reports(container) -> None:
    st.subheader("📄 Report Wizard")

    session_docs = st.session_state.get("session_docs", {})
    kb_count = container.kb_service.count()

    # --- Step 1: ensure a document ------------------------------------------
    if not session_docs and kb_count == 0:
        st.info("**Step 1 — Upload a document** to base your report on.")
        _upload_for_report(container, key="report_upload_first")
        return

    if not container.is_llm_ready:
        st.warning("Report drafting needs an AI model — start Ollama or add a Gemini key.")
        return

    # --- Step 2: choose the source ------------------------------------------
    if session_docs and kb_count:
        source = st.radio(
            "Base the report on",
            [f"🗂️ Session documents ({len(session_docs)})", f"📚 Knowledge base ({kb_count})"],
            horizontal=True,
        )
        use_session = source.startswith("🗂️")
    else:
        use_session = bool(session_docs)
        st.caption(
            f"Using: {'🗂️ session documents' if use_session else '📚 knowledge base'}"
        )

    with st.expander("➕ Add another document"):
        _upload_for_report(container, key="report_upload_more")

    # --- Step 3: report type -------------------------------------------------
    st.markdown("**What type of report would you like to generate?**")
    report_type = st.selectbox("Report type", list(REPORT_TYPES.keys()))
    c1, c2 = st.columns([2, 1])
    title = c1.text_input("Report title", value=report_type)
    language = c2.selectbox("Language", ["English", "Arabic"])

    custom_instructions = None
    if report_type == "Custom Report":
        custom_instructions = st.text_area(
            "Describe what the report should cover",
            placeholder="e.g. Summarise revenue and margins, list the top risks, and check VAT compliance.",
        )

    # --- Step 4: generate ----------------------------------------------------
    if st.button("✍️ Generate report", type="primary"):
        retriever = _session_retriever(container) if use_session else None
        with st.spinner("Drafting your report…"):
            try:
                report = container.report_service.generate(
                    report_type,
                    title=title,
                    language=language,
                    retriever=retriever,
                    custom_instructions=custom_instructions or None,
                )
            except LLMError as exc:
                st.error(f"Report generation failed: {exc}")
                return
        st.session_state["last_report"] = report
        st.session_state.setdefault("recent_reports", []).append(f"{title} · {language}")
        container.audit_log.record("report_generated", f"{report_type} [{language}]")

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
            f"⬇️ {fmt}", data=data, file_name=f"{safe}.{EXTENSIONS[fmt]}",
            mime=MIME_TYPES[fmt], key=f"dl_{fmt}", use_container_width=True,
        )
