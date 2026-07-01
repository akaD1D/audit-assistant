"""Cross-document keyword + value search tests."""

from __future__ import annotations

from audit_assistant.domain.models import DocumentPage, FileType, ParsedDocument, Table
from audit_assistant.services.search_service import SearchService, _to_number


class FakeRepo:
    def __init__(self, docs: list[ParsedDocument]) -> None:
        self._docs = docs

    def list_all(self) -> list[ParsedDocument]:
        return self._docs


def _doc() -> ParsedDocument:
    table = Table(
        rows=[
            ["Vendor", "Amount"],
            ["Acme", "150,000"],
            ["Beta", "50,000"],
            ["Gamma", "SAR 250,000"],
        ],
        page=1,
    )
    return ParsedDocument(
        filename="invoices.pdf",
        file_type=FileType.PDF,
        pages=[
            DocumentPage(
                number=1,
                text="Revenue recognition under IFRS 15.\nMateriality set at 500000.",
                tables=[table],
            )
        ],
        document_id="docA",
    )


def test_to_number_parsing() -> None:
    assert _to_number("SAR 150,000.00") == 150000.0
    assert _to_number("(1,200)") == -1200.0
    assert _to_number("no number") is None
    assert _to_number("42") == 42.0


def test_keyword_search_text_and_table() -> None:
    svc = SearchService(FakeRepo([_doc()]))
    assert any("Revenue recognition" in m.text for m in svc.keyword_search("revenue"))
    acme = svc.keyword_search("acme")
    assert acme and "Acme" in acme[0].text


def test_value_search_threshold() -> None:
    svc = SearchService(FakeRepo([_doc()]))
    matches = svc.value_search(">", 100000)
    values = [m.value for m in matches]
    assert 250000.0 in values
    assert 150000.0 in values
    assert 50000.0 not in values
    # Sorted largest-first by absolute value.
    assert matches[0].value == 250000.0


def test_value_search_less_than() -> None:
    svc = SearchService(FakeRepo([_doc()]))
    matches = svc.value_search("<", 100000)
    assert any(m.value == 50000.0 for m in matches)


def test_document_scope_filter() -> None:
    svc = SearchService(FakeRepo([_doc()]))
    assert svc.keyword_search("revenue", document_ids=["other"]) == []
    assert svc.keyword_search("revenue", document_ids=["docA"])
