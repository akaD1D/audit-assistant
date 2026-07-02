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

    kb_count = container.kb_service.count()
    sess_count = len(st.session_state.get("session_docs", {}))
    # Focus on session uploads by default when they exist.
    default_index = 0 if sess_count else 1
    scope = st.radio(
        "Answer from",
        ["🗂️ Session documents", "📚 Knowledge base"],
        index=default_index,
        horizontal=True,
        key="chat_scope",
        help="Session documents = files you uploaded this chat. Knowledge base = "
        "documents you saved permanently.",
    )
    st.caption(f"🗂️ {sess_count} session doc(s)  ·  📚 {kb_count} in knowledge base")

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
            "⚠️ **No AI model available.** Start Ollama (or add a Gemini key to `.env`) "
            "to enable chat. Document upload and the Calculator work without it."
        )
        st.session_state["messages"].append({"role": "assistant", "content": warning})
        with st.chat_message("assistant"):
            st.markdown(warning)
        return

    history = _history_as_messages()[:-1]  # exclude the just-added user turn
    if scope.startswith("🗂️"):
        from audit_assistant.services.session_store import SessionRetriever

        retriever = SessionRetriever(container.embedding_provider, st.session_state["session_index"])
    else:
        retriever = None  # None -> KB (Qdrant) via the default rag_service

    with st.chat_message("assistant"):
        try:
            stream, citations = container.chat_service.stream_answer(
                prompt, history=history, retriever=retriever
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
