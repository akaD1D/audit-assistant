"""Streamlit entry point.

Run with:  ``streamlit run audit_assistant/app/main.py``

Thin presentation layer: renders the layout and delegates all work to services
resolved from the DI container. Feature phases progressively fill in real RAG,
chat, calculations, and reports.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is importable when launched via
# ``streamlit run audit_assistant/app/main.py`` (Streamlit only adds the
# script's own directory to sys.path, not the project root).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from audit_assistant.app.components.analysis_ui import render_analysis
from audit_assistant.app.components.calc_ui import render_calculator
from audit_assistant.app.components.chat_ui import render_chat
from audit_assistant.app.components.report_ui import render_reports
from audit_assistant.app.components.search_ui import render_search
from audit_assistant.app.components.upload_ui import render_document_list, render_uploader
from audit_assistant.app.theme import apply_theme, render_header
from audit_assistant.core.container import get_container


def _init_session() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("documents", {})  # document_id -> ParsedDocument


def render_sidebar(container) -> None:
    with st.sidebar:
        st.markdown("### 🧾 Audit Assistant")
        st.caption("Document-grounded · cited · deterministic maths")

        if st.button("✨ New chat", use_container_width=True):
            st.session_state["messages"] = []
            st.rerun()

        st.divider()
        st.subheader("📁 Documents")
        render_uploader(container)

        st.divider()
        st.subheader("⚙️ Status")
        s = container.settings
        col1, col2 = st.columns(2)
        col1.metric("Provider", s.llm_provider)
        col2.metric("Embeddings", s.embedding_backend)
        if container.is_llm_ready:
            st.success("LLM provider configured.")
        else:
            st.warning("No LLM key — add one in `.env` to enable chat.")
        st.caption("🌗 Tip: switch light/dark via the ☰ menu → Settings → Theme.")


def render_main(container) -> None:
    render_header(
        kb_count=container.document_repository.count(),
        provider=container.settings.llm_provider,
        llm_ready=container.is_llm_ready,
    )

    tab_chat, tab_search, tab_calc, tab_analysis, tab_reports, tab_docs = st.tabs(
        ["💬 Chat", "🔍 Search", "🧮 Calculator", "📊 Analysis", "📄 Reports", "📑 Documents"]
    )
    with tab_chat:
        render_chat(container)
    with tab_search:
        render_search(container)
    with tab_calc:
        render_calculator(container)
    with tab_analysis:
        render_analysis(container)
    with tab_reports:
        render_reports(container)
    with tab_docs:
        render_document_list()
        with st.expander("🧾 Activity log"):
            entries = container.audit_log.recent(limit=50)
            if entries:
                st.dataframe(entries, use_container_width=True)
            else:
                st.caption("No activity recorded yet.")


def main() -> None:
    st.set_page_config(
        page_title="AI Audit Assistant",
        page_icon="🧾",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "about": "AI Audit Assistant — document-grounded audit chatbot. "
            "Answers cite sources; calculations are deterministic (never AI-guessed).",
        },
    )
    apply_theme()
    container = get_container()
    _init_session()
    render_sidebar(container)
    render_main(container)


if __name__ == "__main__":
    main()
