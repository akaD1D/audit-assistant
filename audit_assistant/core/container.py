"""Dependency-injection container.

A single composition root that lazily constructs and wires services + adapters.
Phase 0 only holds configuration and logging; each later phase registers its
components here (parsers, embeddings, vector store, LLM providers, services) so
the UI never imports concrete infrastructure directly.
"""

from __future__ import annotations

from functools import cached_property

from audit_assistant.core.config import Settings, get_settings
from audit_assistant.core.logging import configure_logging, get_logger


class Container:
    """Composition root. Build once per process and pass around (or use ``get_container``)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        configure_logging(self.settings.log_level)
        self.log = get_logger("audit_assistant.container")
        self.log.debug("Container initialised (provider=%s)", self.settings.llm_provider)

    # Construction is lazy (cached_property) so importing the container is cheap
    # and heavy deps (parsers, sentence-transformers, chromadb) load on first use.

    # --- Phase 1: ingestion ---------------------------------------------------
    @cached_property
    def database(self):
        from audit_assistant.infrastructure.db import Database

        return Database(self.settings.db_path)

    @cached_property
    def document_repository(self):
        from audit_assistant.infrastructure.repositories.document_repository import (
            SqliteDocumentRepository,
        )

        return SqliteDocumentRepository(self.database)

    @cached_property
    def audit_log(self):
        from audit_assistant.services.audit_log_service import AuditLogService

        return AuditLogService(self.database)

    @cached_property
    def parser_registry(self):
        from audit_assistant.infrastructure.parsers.base import build_default_registry

        return build_default_registry()

    # --- Phase 2: RAG ---------------------------------------------------------
    @cached_property
    def embedding_provider(self):
        from audit_assistant.infrastructure.embeddings.local import LocalEmbeddingProvider

        self.settings.model_cache_dir.mkdir(parents=True, exist_ok=True)
        cache_dir = str(self.settings.model_cache_dir)
        # Provider-hosted embeddings are wired in Phase 3; default to local.
        return LocalEmbeddingProvider(self.settings.local_embedding_model, cache_dir=cache_dir)

    @cached_property
    def vector_store(self):
        from audit_assistant.infrastructure.vectorstore.qdrant_store import QdrantVectorStore

        return QdrantVectorStore(
            self.settings.vector_dir, collection=self.settings.vector_collection
        )

    @cached_property
    def indexing_service(self):
        from audit_assistant.services.indexing_service import IndexingService

        return IndexingService(
            embedder=self.embedding_provider,
            vector_store=self.vector_store,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )

    @cached_property
    def rag_service(self):
        from audit_assistant.services.rag_service import RagService

        return RagService(
            embedder=self.embedding_provider,
            vector_store=self.vector_store,
            default_top_k=self.settings.retrieval_top_k,
        )

    @cached_property
    def search_service(self):
        from audit_assistant.services.search_service import SearchService

        return SearchService(self.document_repository)

    @cached_property
    def ocr(self):
        from audit_assistant.infrastructure.ocr.tesseract import TesseractOcr

        return TesseractOcr(self.settings.tesseract_cmd or None)

    @cached_property
    def vision_provider(self):
        """A vision-capable provider for reading images.

        Ollama text models can't see images, so use a dedicated vision model.
        Cloud providers (Gemini/OpenAI/Anthropic) do vision with their main model.
        """
        if self.settings.llm_provider == "ollama":
            from audit_assistant.infrastructure.llm.ollama_provider import OllamaProvider

            return OllamaProvider(
                self.settings.ollama_base_url, self.settings.ollama_vision_model
            )
        return self.llm_provider

    @cached_property
    def image_service(self):
        from audit_assistant.services.image_service import ImageUnderstandingService

        return ImageUnderstandingService(llm=self.vision_provider, ocr=self.ocr)

    @cached_property
    def ingestion_service(self):
        from audit_assistant.services.ingestion_service import IngestionService

        return IngestionService(
            registry=self.parser_registry,
            repository=self.document_repository,
            upload_dir=self.settings.upload_dir,
            max_upload_bytes=self.settings.max_upload_bytes,
            indexer=self.indexing_service,
            image_analyzer=self.image_service,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )

    @cached_property
    def kb_service(self):
        from audit_assistant.services.knowledge_base_service import KnowledgeBaseService

        return KnowledgeBaseService(
            repository=self.document_repository,
            indexer=self.indexing_service,
            ingestion=self.ingestion_service,
        )

    # --- Phase 3: LLM + chat --------------------------------------------------
    @cached_property
    def llm_provider(self):
        from audit_assistant.infrastructure.llm.factory import build_llm_provider

        return build_llm_provider(self.settings)

    # --- Phase 5: calculations ------------------------------------------------
    @cached_property
    def calculation_service(self):
        from audit_assistant.services.calculation_service import CalculationService

        return CalculationService(self.database)

    # --- Phase 6: Excel + dataset analysis ------------------------------------
    @cached_property
    def excel_service(self):
        from audit_assistant.services.excel_service import ExcelAnalysisService

        return ExcelAnalysisService()

    @cached_property
    def dataset_service(self):
        from audit_assistant.services.dataset_service import DatasetValidationService

        return DatasetValidationService()

    @cached_property
    def chat_service(self):
        from audit_assistant.services.chat_service import ChatService

        return ChatService(
            llm=self.llm_provider,
            rag_service=self.rag_service,
            default_top_k=self.settings.retrieval_top_k,
        )

    # --- Phase 8: reports -----------------------------------------------------
    @cached_property
    def report_service(self):
        from audit_assistant.services.report_service import ReportService

        return ReportService(llm=self.llm_provider, rag_service=self.rag_service)

    @cached_property
    def is_llm_ready(self) -> bool:
        """Whether an LLM provider is configured (used by the UI to gate chat)."""
        return self.llm_provider.is_configured()


_container: Container | None = None


def get_container() -> Container:
    """Return the process-wide container singleton."""
    global _container
    if _container is None:
        _container = Container()
    return _container
