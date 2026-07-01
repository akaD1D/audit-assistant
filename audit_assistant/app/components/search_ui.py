"""Cross-document search & comparison UI (Phases 2 + 7).

Three search modes over all uploaded documents:
  - Semantic (embeddings, keyless)
  - Keyword (literal text/table match, keyless)
  - Value filter (numeric row filter, e.g. amount > 100,000, keyless)
Plus document comparison (LLM), which reuses the grounded chat with the
selected documents scoped as context.
"""

from __future__ import annotations

import streamlit as st

from audit_assistant.core.logging import get_logger

log = get_logger(__name__)

_OPERATORS = {">": ">", "≥": ">=", "<": "<", "≤": "<=", "=": "=="}


def _session_doc_ids() -> list[str]:
    return list(st.session_state.get("documents", {}).keys())


def _semantic(container) -> None:
    query = st.text_input("Semantic search", placeholder="e.g. revenue recognition, materiality…",
                          key="sem_q")
    if not query:
        return
    with st.spinner("Searching…"):
        results = container.rag_service.retrieve(query, top_k=container.settings.retrieval_top_k)
    if not results:
        st.info("No matches found.")
        return
    for i, r in enumerate(results, start=1):
        page = f"p.{r.chunk.page}" if r.chunk.page else "—"
        kind = "📊 table" if r.chunk.is_table else "📄 text"
        with st.expander(f"{i}. {r.chunk.filename} · {page} · {kind} · score {r.score:.2f}"):
            st.markdown(r.chunk.text) if r.chunk.is_table else st.write(r.chunk.text)


def _keyword(container) -> None:
    term = st.text_input("Keyword / phrase", placeholder="e.g. revenue recognition", key="kw_q")
    if not term:
        return
    matches = container.search_service.keyword_search(term, document_ids=_session_doc_ids())
    if not matches:
        st.info("No literal matches found.")
        return
    st.caption(f"{len(matches)} match(es)")
    for m in matches:
        page = f"p.{m.page}" if m.page else "—"
        st.markdown(f"**{m.filename}** · {page}")
        st.caption(m.text)


def _value(container) -> None:
    col1, col2 = st.columns([1, 2])
    op_label = col1.selectbox("Condition", list(_OPERATORS.keys()), key="val_op")
    threshold = col2.number_input("Threshold", value=100000.0, step=1000.0, key="val_thr")
    if not st.button("Filter rows", key="val_go"):
        return
    matches = container.search_service.value_search(
        _OPERATORS[op_label], threshold, document_ids=_session_doc_ids()
    )
    if not matches:
        st.info("No table rows satisfy that condition.")
        return
    st.caption(f"{len(matches)} matching row(s), largest first")
    st.dataframe(
        [
            {"document": m.filename, "page": m.page, "matched value": m.value,
             "row": " | ".join(m.row)}
            for m in matches
        ],
        use_container_width=True,
    )


def _compare(container) -> None:
    docs = st.session_state.get("documents", {})
    if len(docs) < 2:
        st.info("Upload at least two documents to compare them.")
        return
    labels = {f"{d.filename} ({did[:6]})": did for did, d in docs.items()}
    chosen = st.multiselect("Documents to compare", list(labels.keys()))
    instruction = st.text_input(
        "What should I compare?",
        placeholder="e.g. Compare revenue and key figures between these reports.",
        key="cmp_q",
    )
    if not (chosen and instruction and st.button("Compare", key="cmp_go")):
        return
    if not container.is_llm_ready:
        st.warning("Comparison needs an LLM provider — add a Gemini key to `.env`.")
        return
    doc_ids = [labels[c] for c in chosen]
    with st.spinner("Comparing…"):
        answer = container.chat_service.answer(instruction, document_ids=doc_ids)
    st.markdown(answer.text)
    if answer.citations:
        with st.expander(f"📎 Sources ({len(answer.citations)})"):
            for i, c in enumerate(answer.citations, start=1):
                st.markdown(f"**[Source {i}] {c.label()}**")
                st.caption(c.snippet)


def render_search(container) -> None:
    if not st.session_state.get("documents"):
        st.info("Upload documents from the sidebar to search and compare them.")
        return

    st.subheader("🔍 Search & compare documents")
    mode = st.radio(
        "Mode", ["Semantic", "Keyword", "Value filter", "Compare"], horizontal=True, key="search_mode"
    )
    if mode == "Semantic":
        st.caption("Meaning-based search — works offline, no API key.")
        _semantic(container)
    elif mode == "Keyword":
        st.caption("Exact text match across all documents and tables.")
        _keyword(container)
    elif mode == "Value filter":
        st.caption("Find table rows by a numeric condition, e.g. amount > 100,000.")
        _value(container)
    else:
        st.caption("Ask the assistant to compare two or more documents (needs LLM).")
        _compare(container)
