"""Chat UI (Phase 3): streamed, grounded answers with citations + confidence."""

from __future__ import annotations

import streamlit as st

from audit_assistant.core.exceptions import LLMError, ProviderNotConfiguredError
from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import Message, Role

log = get_logger(__name__)

_CONFIDENCE_COLOR = {"high": "green", "medium": "orange", "low": "red"}


def _history_as_messages(limit: int = 8) -> list[Message]:
    """Recent turns as domain Messages for conversational memory."""
    out: list[Message] = []
    for m in st.session_state.get("messages", [])[-limit:]:
        role = Role.ASSISTANT if m["role"] == "assistant" else Role.USER
        out.append(Message(role=role, content=m["content"]))
    return out


def _render_citations(citations) -> None:
    if not citations:
        return
    with st.expander(f"📎 Sources ({len(citations)})"):
        for i, c in enumerate(citations, start=1):
            score = f" · score {c.score:.2f}" if c.score is not None else ""
            st.markdown(f"**[Source {i}] {c.label()}**{score}")
            st.caption(c.snippet)


def _render_confidence(level: str) -> None:
    color = _CONFIDENCE_COLOR.get(level, "gray")
    st.markdown(f":{color}[**Confidence: {level}**]")


_SUGGESTIONS = [
    "What are the five steps of revenue recognition under IFRS 15?",
    "Explain materiality and how it's calculated under ISA 320.",
    "What are the five components of internal control under COSO?",
    "Summarise the key risks disclosed in the uploaded reports.",
]


def _render_welcome() -> None:
    st.markdown(
        "#### 👋 Ask me anything about auditing or your documents\n"
        "I answer from your **knowledge base** with source citations and a confidence level. "
        "Try one of these:"
    )
    cols = st.columns(2)
    for i, suggestion in enumerate(_SUGGESTIONS):
        if cols[i % 2].button(suggestion, key=f"sugg_{i}", use_container_width=True):
            st.session_state["suggested_prompt"] = suggestion
            st.rerun()


def render_chat(container) -> None:
    st.subheader("💬 Ask the audit assistant")

    kb_count = container.document_repository.count()
    # If the user has uploaded something this session, focus on it by default —
    # otherwise a fresh invoice gets drowned out by the whole knowledge base.
    default_index = 1 if st.session_state.get("documents") else 0
    scope = st.radio(
        "Answer from",
        ["📚 Entire knowledge base", "📎 Only this session's uploads"],
        index=default_index,
        horizontal=True,
        key="chat_scope",
        help="Uploaded a file to ask about? Use 'this session's uploads' so the answer "
        "comes from it, not the whole library.",
    )
    st.caption(f"📚 Knowledge base: {kb_count} document(s) indexed.")

    # Welcome / empty state with clickable suggestions.
    if not st.session_state["messages"]:
        _render_welcome()

    # Replay history.
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("citations"):
                _render_citations(msg["citations"])
            if msg.get("confidence"):
                _render_confidence(msg["confidence"])

    # A suggestion click (below) prefills the turn.
    prompt = st.chat_input("Ask an audit question about your documents…")
    prompt = prompt or st.session_state.pop("suggested_prompt", None)
    if not prompt:
        return

    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not container.is_llm_ready:
        warning = (
            "⚠️ **No LLM provider configured.** Add a free Gemini key to `.env` "
            "(`AUDIT_GEMINI_API_KEY=...`) from https://aistudio.google.com/app/apikey, "
            "then restart. Meanwhile, the **🔍 Search** box above works with no key."
        )
        st.session_state["messages"].append({"role": "assistant", "content": warning})
        with st.chat_message("assistant"):
            st.markdown(warning)
        return

    history = _history_as_messages()[:-1]  # exclude the just-added user turn
    if scope.startswith("📎"):
        doc_ids = list(st.session_state.get("documents", {}).keys()) or None
    else:
        doc_ids = None  # search the entire persistent knowledge base

    with st.chat_message("assistant"):
        try:
            stream, citations = container.chat_service.stream_answer(
                prompt, history=history, document_ids=doc_ids
            )
            full_text = st.write_stream(stream)
            confidence = container.chat_service.confidence_of(full_text)
            _render_citations(citations)
            _render_confidence(confidence)
        except ProviderNotConfiguredError as exc:
            full_text = f"⚠️ {exc}"
            citations, confidence = [], "low"
            st.warning(full_text)
        except LLMError as exc:
            full_text = f"❌ The model request failed: {exc}"
            citations, confidence = [], "low"
            st.error(full_text)
        except Exception as exc:  # noqa: BLE001
            log.exception("Chat failed")
            full_text = f"❌ Unexpected error: {exc}"
            citations, confidence = [], "low"
            st.error(full_text)

    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": full_text,
            "citations": citations,
            "confidence": confidence,
        }
    )
    container.audit_log.record("chat_answer", f"Q: {prompt[:80]} (confidence={confidence})")
