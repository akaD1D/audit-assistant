"""Chat service: RAG-grounded, cited, confidence-scored answers.

Orchestrates the full answer flow:
  retrieve context -> build grounded prompt -> call the LLM (with audit system
  prompt + guardrails) -> attach citations + confidence.

Conversation memory is passed in as prior :class:`Message` history so the
service stays stateless and easily testable.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from audit_assistant.audit.prompts.system import AUDIT_SYSTEM_PROMPT, build_grounded_prompt
from audit_assistant.core.logging import get_logger
from audit_assistant.domain.interfaces import LLMProvider
from audit_assistant.domain.models import Answer, Citation, Message, RetrievedChunk, Role
from audit_assistant.services.rag_service import RagService

log = get_logger(__name__)

_CONFIDENCE_RE = re.compile(r"(?:confidence|الثقة)\s*[:：]?\s*(high|medium|low)", re.IGNORECASE)


class ChatService:
    """Produces grounded answers from the indexed corpus."""

    def __init__(
        self,
        *,
        llm: LLMProvider,
        rag_service: RagService,
        default_top_k: int = 5,
        system_prompt: str = AUDIT_SYSTEM_PROMPT,
    ) -> None:
        self._llm = llm
        self._rag = rag_service
        self._default_top_k = default_top_k
        self._system_prompt = system_prompt

    # --- prompt assembly -----------------------------------------------------
    def _assemble(self, history: list[Message] | None, grounded_prompt: str) -> list[Message]:
        messages = list(history or [])
        messages.append(Message(role=Role.USER, content=grounded_prompt))
        return messages

    def _retrieve(self, question: str, top_k: int | None, document_ids: list[str] | None):
        return self._rag.retrieve(
            question, top_k=top_k or self._default_top_k, document_ids=document_ids
        )

    @staticmethod
    def _confidence(text: str, contexts: list[RetrievedChunk]) -> str:
        """Prefer the model's self-reported confidence; fall back to retrieval scores."""
        match = _CONFIDENCE_RE.search(text)
        if match:
            return match.group(1).lower()
        if not contexts:
            return "low"
        top = max(c.score for c in contexts)
        if top >= 0.6:
            return "high"
        if top >= 0.4:
            return "medium"
        return "low"

    # --- public API ----------------------------------------------------------
    def answer(
        self,
        question: str,
        *,
        history: list[Message] | None = None,
        document_ids: list[str] | None = None,
        top_k: int | None = None,
    ) -> Answer:
        """Return a complete grounded answer (non-streaming)."""
        contexts = self._retrieve(question, top_k, document_ids)
        prompt = build_grounded_prompt(question, contexts)
        messages = self._assemble(history, prompt)
        text = self._llm.complete(messages, system=self._system_prompt)
        citations = RagService.to_citations(contexts)
        confidence = self._confidence(text, contexts)
        log.info("Answered (%d sources, confidence=%s)", len(citations), confidence)
        return Answer(text=text, citations=citations, confidence=confidence)

    def stream_answer(
        self,
        question: str,
        *,
        history: list[Message] | None = None,
        document_ids: list[str] | None = None,
        top_k: int | None = None,
    ) -> tuple[Iterator[str], list[Citation]]:
        """Return a token stream plus the citations for the retrieved context.

        The UI streams the tokens, then renders the citations underneath. Final
        confidence can be derived from the assembled text via :meth:`confidence_of`.
        """
        contexts = self._retrieve(question, top_k, document_ids)
        prompt = build_grounded_prompt(question, contexts)
        messages = self._assemble(history, prompt)
        stream = self._llm.stream(messages, system=self._system_prompt)
        citations = RagService.to_citations(contexts)
        self._last_contexts = contexts  # for confidence_of after streaming
        return stream, citations

    def confidence_of(self, text: str) -> str:
        """Confidence for a streamed answer, using the last retrieval context."""
        return self._confidence(text, getattr(self, "_last_contexts", []))
