"""LLM provider factory — selects an adapter from configuration."""

from __future__ import annotations

from audit_assistant.core.config import Settings
from audit_assistant.core.exceptions import ConfigurationError
from audit_assistant.domain.interfaces import LLMProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    """Construct the configured LLM provider (imports are lazy per provider)."""
    provider = settings.llm_provider

    if provider == "gemini":
        from audit_assistant.infrastructure.llm.gemini_provider import GeminiProvider

        return GeminiProvider(settings.gemini_api_key, settings.gemini_model)

    if provider == "openai":
        from audit_assistant.infrastructure.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(settings.openai_api_key, settings.openai_model)

    if provider == "anthropic":
        from audit_assistant.infrastructure.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)

    if provider == "ollama":
        from audit_assistant.infrastructure.llm.ollama_provider import OllamaProvider

        return OllamaProvider(settings.ollama_base_url, settings.ollama_model)

    raise ConfigurationError(f"Unknown LLM provider: {provider!r}")
