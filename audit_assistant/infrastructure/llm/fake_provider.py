"""Deterministic in-memory LLM provider for tests and offline demos."""

from __future__ import annotations

from collections.abc import Iterator

from audit_assistant.domain.models import Message

_DEFAULT_REPLY = "Based on the provided documents, the answer is X [Source 1].\nConfidence: high"


class FakeLLMProvider:
    """Records the last call and returns a canned reply. Implements LLMProvider."""

    def __init__(self, reply: str = _DEFAULT_REPLY) -> None:
        self._reply = reply
        self.last_messages: list[Message] | None = None
        self.last_system: str | None = None
        self.last_images: list[bytes] | None = None

    @property
    def name(self) -> str:
        return "fake"

    def is_configured(self) -> bool:
        return True

    def complete(self, messages: list[Message], *, system: str | None = None) -> str:
        self.last_messages = messages
        self.last_system = system
        return self._reply

    def stream(self, messages: list[Message], *, system: str | None = None) -> Iterator[str]:
        self.last_messages = messages
        self.last_system = system
        for word in self._reply.split(" "):
            yield word + " "

    def complete_with_images(
        self, prompt: str, images: list[bytes], *, system: str | None = None
    ) -> str:
        self.last_system = system
        self.last_images = images
        return f"[image analysis] {self._reply}"
