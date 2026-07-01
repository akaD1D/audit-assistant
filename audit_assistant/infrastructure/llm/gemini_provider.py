"""Google Gemini adapter (default provider, free tier, vision-capable)."""

from __future__ import annotations

import io
import time
from collections.abc import Iterator

from audit_assistant.core.exceptions import LLMError, ProviderNotConfiguredError
from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import Message, Role

log = get_logger(__name__)

# Free-tier Gemini enforces a per-minute request quota; retry transient 429s.
_RETRY_DELAYS = (5, 15, 30)


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "quota" in text or "resourceexhausted" in text or "rate limit" in text


def _with_retry(call):
    """Run an API call, retrying on rate-limit (429) errors with backoff."""
    last: Exception | None = None
    for attempt, delay in enumerate((0, *_RETRY_DELAYS)):
        if delay:
            time.sleep(delay)
        try:
            return call()
        except Exception as exc:  # noqa: BLE001
            if not _is_rate_limit(exc):
                raise
            last = exc
            log.warning("Gemini rate-limited (attempt %d); backing off…", attempt + 1)
    raise LLMError(
        "Gemini free-tier rate limit reached (too many requests this minute). "
        "Wait a moment and try again."
    ) from last


class GeminiProvider:
    """Implements :class:`audit_assistant.domain.interfaces.LLMProvider` for Gemini."""

    def __init__(self, api_key: str | None, model: str = "gemini-2.0-flash") -> None:
        self._api_key = api_key
        self._model_name = model

    @property
    def name(self) -> str:
        return "gemini"

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _model(self, system: str | None):
        if not self._api_key:
            raise ProviderNotConfiguredError(
                "Gemini API key not set. Add AUDIT_GEMINI_API_KEY to your .env "
                "(get a free key at https://aistudio.google.com/app/apikey)."
            )
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)
        return genai.GenerativeModel(self._model_name, system_instruction=system)

    @staticmethod
    def _to_contents(messages: list[Message]) -> list[dict]:
        contents: list[dict] = []
        for m in messages:
            if m.role == Role.SYSTEM:
                continue  # system handled via system_instruction
            role = "user" if m.role == Role.USER else "model"
            contents.append({"role": role, "parts": [m.content]})
        return contents

    def complete(self, messages: list[Message], *, system: str | None = None) -> str:
        model = self._model(system)
        try:
            resp = _with_retry(lambda: model.generate_content(self._to_contents(messages)))
            return (resp.text or "").strip()
        except (ProviderNotConfiguredError, LLMError):
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Gemini request failed: {exc}") from exc

    def stream(self, messages: list[Message], *, system: str | None = None) -> Iterator[str]:
        model = self._model(system)
        try:
            for chunk in model.generate_content(self._to_contents(messages), stream=True):
                if getattr(chunk, "text", None):
                    yield chunk.text
        except ProviderNotConfiguredError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Gemini streaming failed: {exc}") from exc

    def complete_with_images(
        self, prompt: str, images: list[bytes], *, system: str | None = None
    ) -> str:
        from PIL import Image

        model = self._model(system)
        try:
            parts: list = [prompt]
            for data in images:
                parts.append(Image.open(io.BytesIO(data)))
            resp = _with_retry(lambda: model.generate_content(parts))
            return (resp.text or "").strip()
        except (ProviderNotConfiguredError, LLMError):
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Gemini vision request failed: {exc}") from exc
