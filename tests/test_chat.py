"""Chat service tests using a fake LLM + stub retriever (no model download)."""

from __future__ import annotations

from audit_assistant.audit.prompts.system import AUDIT_SYSTEM_PROMPT
from audit_assistant.core.config import Settings
from audit_assistant.domain.models import Chunk, RetrievedChunk
from audit_assistant.infrastructure.llm.factory import build_llm_provider
from audit_assistant.infrastructure.llm.fake_provider import FakeLLMProvider
from audit_assistant.services.chat_service import ChatService


class StubRag:
    """Minimal RagService stand-in returning preset retrieval results."""

    def __init__(self, results: list[RetrievedChunk]) -> None:
        self._results = results

    def retrieve(self, question, *, top_k=None, document_ids=None):
        return self._results


def _rc(text: str, filename: str, page: int, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(document_id="d1", filename=filename, text=text, page=page),
        score=score,
    )


def test_answer_is_grounded_and_cited() -> None:
    fake = FakeLLMProvider(reply="Materiality is the threshold [Source 1].\nConfidence: high")
    contexts = [_rc("Materiality threshold is defined in ISA 320.", "audit.pdf", 3, 0.82)]
    svc = ChatService(llm=fake, rag_service=StubRag(contexts))

    answer = svc.answer("What is materiality?")

    assert "[Source 1]" in answer.text
    assert answer.confidence == "high"
    assert len(answer.citations) == 1
    assert answer.citations[0].filename == "audit.pdf"
    assert answer.citations[0].page == 3
    # The audit system prompt + context were passed to the model.
    assert fake.last_system == AUDIT_SYSTEM_PROMPT
    assert "ISA 320" in fake.last_messages[-1].content


def test_no_context_answer_flags_uncertainty() -> None:
    fake = FakeLLMProvider(reply="General guidance (not from your documents): ...")
    svc = ChatService(llm=fake, rag_service=StubRag([]))

    answer = svc.answer("What is my company's revenue?")

    assert answer.citations == []
    assert answer.confidence == "low"
    assert "No relevant content" in fake.last_messages[-1].content


def test_confidence_falls_back_to_scores_when_absent() -> None:
    fake = FakeLLMProvider(reply="An answer without a confidence line.")
    high = ChatService(llm=fake, rag_service=StubRag([_rc("x", "f.pdf", 1, 0.9)]))
    assert high.answer("q").confidence == "high"

    mid = ChatService(llm=fake, rag_service=StubRag([_rc("x", "f.pdf", 1, 0.5)]))
    assert mid.answer("q").confidence == "medium"

    low = ChatService(llm=fake, rag_service=StubRag([_rc("x", "f.pdf", 1, 0.2)]))
    assert low.answer("q").confidence == "low"


def test_streaming_yields_tokens_and_citations() -> None:
    fake = FakeLLMProvider(reply="Streamed answer here.")
    contexts = [_rc("Some context.", "a.pdf", 2, 0.7)]
    svc = ChatService(llm=fake, rag_service=StubRag(contexts))

    stream, citations = svc.stream_answer("q")
    text = "".join(stream)
    assert "Streamed answer" in text
    assert len(citations) == 1
    assert svc.confidence_of(text) == "high"


def test_factory_builds_configured_provider() -> None:
    gem = build_llm_provider(Settings(llm_provider="gemini", gemini_api_key="k"))
    assert gem.name == "gemini"
    assert gem.is_configured()

    unset = build_llm_provider(Settings(llm_provider="gemini", gemini_api_key=None))
    assert not unset.is_configured()
