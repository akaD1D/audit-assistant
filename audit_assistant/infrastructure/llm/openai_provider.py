"""OpenAI adapter (optional provider — swap in via AUDIT_LLM_PROVIDER=openai)."""

from __future__ import annotations

import base64
from collections.abc import Iterator

from audit_assistant.core.exceptions import LLMError, ProviderNotConfiguredError
from audit_assistant.domain.models import Message, Role


class OpenAIProvider:
    """Implements LLMProvider using the OpenAI Chat Completions API."""

    def __init__(self, api_key: str | None, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key
        self._model_name = model

    @property
    def name(self) -> str:
        return "openai"

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _client(self):
        if not self._api_key:
            raise ProviderNotConfiguredError("OpenAI API key not set (AUDIT_OPENAI_API_KEY).")
        from openai import OpenAI

        return OpenAI(api_key=self._api_key)

    @staticmethod
    def _to_messages(messages: list[Message], system: str | None) -> list[dict]:
        out: list[dict] = []
        if system:
            out.append({"role": "system", "content": system})
        for m in messages:
            role = "assistant" if m.role == Role.ASSISTANT else "user"
            out.append({"role": role, "content": m.content})
        return out

    def complete(self, messages: list[Message], *, system: str | None = None) -> str:
        client = self._client()
        try:
            resp = client.chat.completions.create(
                model=self._model_name, messages=self._to_messages(messages, system)
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"OpenAI request failed: {exc}") from exc

    def stream(self, messages: list[Message], *, system: str | None = None) -> Iterator[str]:
        client = self._client()
        try:
            stream = client.chat.completions.create(
                model=self._model_name,
                messages=self._to_messages(messages, system),
                stream=True,
            )
            for event in stream:
                delta = event.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"OpenAI streaming failed: {exc}") from exc

    def complete_with_images(
        self, prompt: str, images: list[bytes], *, system: str | None = None
    ) -> str:
        client = self._client()
        content: list[dict] = [{"type": "text", "text": prompt}]
        for data in images:
            b64 = base64.b64encode(data).decode()
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
            )
        msgs: list[dict] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": content})
        try:
            resp = client.chat.completions.create(model=self._model_name, messages=msgs)
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"OpenAI vision request failed: {exc}") from exc
