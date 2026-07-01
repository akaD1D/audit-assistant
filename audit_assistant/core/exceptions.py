"""Typed domain exceptions.

A small hierarchy so the UI and service layers can catch categories of failure
and present clean messages instead of leaking raw tracebacks to end users.
"""

from __future__ import annotations


class AuditAssistantError(Exception):
    """Base class for all application-specific errors."""


class ConfigurationError(AuditAssistantError):
    """Invalid or missing configuration (e.g. no API key for the chat step)."""


# --- document ingestion ------------------------------------------------------
class DocumentError(AuditAssistantError):
    """Base for document handling problems."""


class UnsupportedFileTypeError(DocumentError):
    """Uploaded file type is not supported by any parser."""


class FileValidationError(DocumentError):
    """Upload failed validation (size, extension, MIME mismatch, corrupt)."""


class ParsingError(DocumentError):
    """A parser failed to extract content from a file."""


# --- retrieval / RAG ---------------------------------------------------------
class RetrievalError(AuditAssistantError):
    """Vector store or embedding failure during indexing/retrieval."""


# --- LLM ---------------------------------------------------------------------
class LLMError(AuditAssistantError):
    """Base for LLM provider failures."""


class ProviderNotConfiguredError(LLMError):
    """The selected provider is missing required credentials/settings."""


# --- calculations ------------------------------------------------------------
class CalculationError(AuditAssistantError):
    """Invalid inputs to a deterministic audit calculation."""
