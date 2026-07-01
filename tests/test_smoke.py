"""Phase 0 smoke tests: the scaffold imports and core wiring works."""

from __future__ import annotations

from audit_assistant.core.config import Settings, get_settings
from audit_assistant.core.container import get_container
from audit_assistant.domain.models import FileType, ParsedDocument, Table


def test_settings_load_with_defaults() -> None:
    settings = get_settings()
    assert settings.app_name
    assert settings.llm_provider in {"gemini", "openai", "anthropic", "ollama"}
    assert settings.chunk_overlap < settings.chunk_size


def test_settings_singleton() -> None:
    assert get_settings() is get_settings()


def test_container_builds() -> None:
    container = get_container()
    assert container.settings is get_settings()
    # No key set by default -> chat gated off.
    assert isinstance(container.is_llm_ready, bool)


def test_max_upload_bytes() -> None:
    s = Settings(max_upload_mb=10)
    assert s.max_upload_bytes == 10 * 1024 * 1024


def test_filetype_helpers() -> None:
    assert FileType.PNG.is_image
    assert FileType.CSV.is_spreadsheet
    assert not FileType.PDF.is_image


def test_table_to_markdown() -> None:
    table = Table(rows=[["Account", "Amount"], ["Cash", "1000"], ["AR", "500"]])
    md = table.to_markdown()
    assert "| Account | Amount |" in md
    assert "| --- | --- |" in md
    assert "| Cash | 1000 |" in md


def test_parsed_document_aggregates() -> None:
    from audit_assistant.domain.models import DocumentPage

    doc = ParsedDocument(
        filename="report.pdf",
        file_type=FileType.PDF,
        pages=[
            DocumentPage(number=1, text="Revenue recognition policy."),
            DocumentPage(number=2, text="Materiality threshold.", tables=[Table(rows=[["a"]])]),
        ],
    )
    assert doc.page_count == 2
    assert "Revenue" in doc.full_text
    assert len(doc.all_tables) == 1
