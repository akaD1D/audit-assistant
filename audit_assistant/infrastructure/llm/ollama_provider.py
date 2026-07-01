"""Ollama adapter (optional, fully offline). Talks HTTP via httpx — no SDK."""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator

import httpx

from audit_assistant.core.exceptions import LLMError
from audit_assistant.domain.models import Message, Role

_TIMEOUT = 300.0  # local models can be slow to load on first call


class OllamaProvider:
    """Implements LLMProvider against a local Ollama server."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1",
        num_ctx: int = 8192,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_name = model
        # Ollama defaults to a 2048-token context, which truncates RAG prompts.
        self._options = {"num_ctx": num_ctx}

    @property
    def name(self) -> str:
        return "ollama"

    def is_configured(self) -> bool:
        return bool(self._base_url)

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
        payload = {
            "model": self._model_name,
            "messages": self._to_messages(messages, system),
            "stream": False,
            "options": self._options,
        }
        try:
            resp = httpx.post(f"{self._base_url}/api/chat", json=payload, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Ollama request failed: {exc}") from exc

    def stream(self, messages: list[Message], *, system: str | None = None) -> Iterator[str]:
        payload = {
            "model": self._model_name,
            "messages": self._to_messages(messages, system),
            "stream": True,
            "options": self._options,
        }
        try:
            with httpx.stream(
                "POST", f"{self._base_url}/api/chat", json=payload, timeout=_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    token = data.get("message", {}).get("content")
                    if token:
                        yield token
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Ollama streaming failed: {exc}") from exc

    def complete_with_images(
        self, prompt: str, images: list[bytes], *, system: str | None = None
    ) -> str:
        # Requires a vision-capable Ollama model (e.g. llava, llama3.2-vision).
        payload = {
            "model": self._model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [base64.b64encode(d).decode() for d in images],
                }
            ],
            "stream": False,
            "options": self._options,
        }
        try:
            resp = httpx.post(f"{self._base_url}/api/chat", json=payload, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Ollama vision request failed: {exc}") from exc
