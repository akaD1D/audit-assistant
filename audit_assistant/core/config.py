"""Application configuration.

All settings are read from environment variables (prefixed ``AUDIT_``) or a
local ``.env`` file via :mod:`pydantic-settings`. Access the singleton through
:func:`get_settings` — never instantiate :class:`Settings` directly in app code,
so the ``lru_cache`` guarantees one consistent config object per process.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["gemini", "openai", "anthropic", "ollama"]
EmbeddingBackend = Literal["local", "gemini", "openai"]


class Settings(BaseSettings):
    """Strongly-typed application settings loaded from env / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AUDIT_",
        extra="ignore",
        case_sensitive=False,
    )

    # --- app -----------------------------------------------------------------
    app_name: str = "AI Audit Assistant"
    environment: Literal["dev", "prod"] = "dev"
    log_level: str = "INFO"

    # --- filesystem paths ----------------------------------------------------
    data_dir: Path = Path("data")
    upload_dir: Path = Path("data/uploads")
    db_path: Path = Path("data/audit_assistant.db")
    vector_dir: Path = Path("data/qdrant")
    vector_collection: str = "audit_chunks"
    model_cache_dir: Path = Path("data/models")  # stable fastembed cache

    # --- LLM provider --------------------------------------------------------
    llm_provider: ProviderName = "gemini"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash-lite"  # more generous free-tier quota

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # Optional path to the Tesseract binary (offline OCR fallback). Empty = auto.
    tesseract_cmd: str = ""

    # --- embeddings ----------------------------------------------------------
    embedding_backend: EmbeddingBackend = "local"
    local_embedding_model: str = "BAAI/bge-small-en-v1.5"  # fastembed ONNX model

    # --- RAG tuning ----------------------------------------------------------
    chunk_size: int = Field(default=1000, ge=200, le=8000)
    chunk_overlap: int = Field(default=150, ge=0, le=2000)
    retrieval_top_k: int = Field(default=5, ge=1, le=50)

    # --- uploads -------------------------------------------------------------
    max_upload_mb: int = Field(default=50, ge=1, le=500)

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def ensure_dirs(self) -> None:
        """Create runtime directories if they do not yet exist."""
        for path in (self.data_dir, self.upload_dir, self.vector_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton (directories ensured)."""
    settings = Settings()
    settings.ensure_dirs()
    return settings
