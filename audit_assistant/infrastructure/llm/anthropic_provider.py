"""Anthropic (Claude) adapter (optional provider)."""

from __future__ import annotations

import base64
from collections.abc import Iterator

from audit_assistant.core.exceptions import LLMError, ProviderNotConfiguredError
from audit_assistant.domain.models import Message, Role

_MAX_TOKENS = 2048


class AnthropicProvider:
    """Implements LLMProvider using the Anthropic Messages API."""

    def __init__(self, api_key: str | None, model: str = "claude-sonnet-5") -> None:
        self._api_key = api_key
        self._model_name = model

    @property
    def name(self) -> str:
        return "anthropic"

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _client(self):
        if not self._api_key:
            raise ProviderNotConfiguredError("Anthropic API key not set (AUDIT_ANTHROPIC_API_KEY).")
        import anthropic

        return anthropic.Anthropic(api_key=self._api_key)

    @staticmethod
    def _to_messages(messages: list[Message]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            role = "assistant" if m.role == Role.ASSISTANT else "user"
            out.append({"role": role, "content": m.content})
        return out

    def complete(self, messages: list[Message], *, system: str | None = None) -> str:
        client = self._client()
        try:
            resp = client.messages.create(
                model=self._model_name,
                max_tokens=_MAX_TOKENS,
                system=system or "",
                messages=self._to_messages(messages),
            )
            return "".join(block.text for block in resp.content if block.type == "text").strip()
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Anthropic request failed: {exc}") from exc

    def stream(self, messages: list[Message], *, system: str | None = None) -> Iterator[str]:
        client = self._client()
        try:
            with client.messages.stream(
                model=self._model_name,
                max_tokens=_MAX_TOKENS,
                system=system or "",
                messages=self._to_messages(messages),
            ) as stream:
                yield from stream.text_stream
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Anthropic streaming failed: {exc}") from exc

    def complete_with_images(
        self, prompt: str, images: list[bytes], *, system: str | None = None
    ) -> str:
        client = self._client()
        content: list[dict] = [{"type": "text", "text": prompt}]
        for data in images:
            b64 = base64.b64encode(data).decode()
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": b64},
                }
            )
        try:
            resp = client.messages.create(
                model=self._model_name,
                max_tokens=_MAX_TOKENS,
                system=system or "",
                messages=[{"role": "user", "content": content}],
            )
            return "".join(block.text for block in resp.content if block.type == "text").strip()
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Anthropic vision request failed: {exc}") from exc
