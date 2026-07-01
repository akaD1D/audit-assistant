"""Local embedding provider backed by fastembed (ONNX, offline, free).

fastembed downloads a small quantised ONNX model on first use and runs on CPU
with no PyTorch dependency — ideal for a lean, shareable deployment. The model
is loaded lazily and cached for the process lifetime.
"""

from __future__ import annotations

import os

from audit_assistant.core.exceptions import RetrievalError
from audit_assistant.core.logging import get_logger

log = get_logger(__name__)


class LocalEmbeddingProvider:
    """Implements :class:`audit_assistant.domain.interfaces.EmbeddingProvider`."""

    def __init__(
        self, model_name: str = "BAAI/bge-small-en-v1.5", cache_dir: str | None = None
    ) -> None:
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._model = None  # lazy: first embed() call triggers model download/load
        self._dim: int | None = None

    def _ensure_model(self):
        if self._model is None:
            # Windows without Developer Mode cannot create the symlinks
            # HuggingFace uses by default (WinError 1314) — force file copies.
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:  # pragma: no cover
                raise RetrievalError("fastembed is not installed.") from exc
            log.info("Loading local embedding model '%s' (first run downloads it)…", self._model_name)
            self._model = TextEmbedding(model_name=self._model_name, cache_dir=self._cache_dir)
        return self._model

    @property
    def dimension(self) -> int:
        """Vector dimension (probed once via a tiny embedding)."""
        if self._dim is None:
            self._dim = len(self.embed_query("dimension probe"))
        return self._dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._ensure_model()
        return [[float(x) for x in vec] for vec in model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        model = self._ensure_model()
        vec = next(iter(model.embed([text])))
        return [float(x) for x in vec]
