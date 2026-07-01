"""Cross-document search: keyword and numeric-value filters.

Complements the semantic RAG search (:class:`RagService`) with deterministic,
keyless searches across every ingested document:
  - keyword search: literal text match in page text and table cells;
  - value search: numeric filter over table rows (e.g. "amount > 100,000").

Operates on the persisted document repository, so it covers all uploads.
"""

from __future__ import annotations

import operator
import re
from dataclasses import dataclass

from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import ParsedDocument

log = get_logger(__name__)

_OPERATORS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
}

# Extract the first number from a cell like "SAR 150,000.00" or "(1,200)".
_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def _to_number(cell: str) -> float | None:
    text = str(cell).strip()
    negative = text.startswith("(") and text.endswith(")")  # accounting negatives
    match = _NUMBER_RE.search(text.replace(" ", ""))
    if not match:
        return None
    try:
        value = float(match.group(0).replace(",", ""))
    except ValueError:
        return None
    return -value if negative else value


@dataclass(slots=True)
class KeywordMatch:
    document_id: str
    filename: str
    page: int | None
    text: str


@dataclass(slots=True)
class RowMatch:
    document_id: str
    filename: str
    page: int | None
    row: list[str]
    value: float


class SearchService:
    """Keyword and value search over the ingested corpus."""

    def __init__(self, repository) -> None:
        self._repo = repository

    def _documents(self, document_ids: list[str] | None) -> list[ParsedDocument]:
        docs = self._repo.list_all()
        if document_ids:
            wanted = set(document_ids)
            docs = [d for d in docs if d.document_id in wanted]
        return docs

    def keyword_search(
        self, term: str, *, document_ids: list[str] | None = None, limit: int = 50
    ) -> list[KeywordMatch]:
        term_l = term.strip().lower()
        if not term_l:
            return []
        matches: list[KeywordMatch] = []
        for doc in self._documents(document_ids):
            for page in doc.pages:
                for line in page.text.splitlines():
                    if term_l in line.lower():
                        matches.append(KeywordMatch(doc.document_id, doc.filename, page.number, line.strip()))
                        if len(matches) >= limit:
                            return matches
                for table in page.tables:
                    for row in table.rows:
                        if any(term_l in str(c).lower() for c in row):
                            matches.append(
                                KeywordMatch(doc.document_id, doc.filename, page.number,
                                             " | ".join(str(c) for c in row))
                            )
                            if len(matches) >= limit:
                                return matches
        return matches

    def value_search(
        self,
        op: str,
        threshold: float,
        *,
        document_ids: list[str] | None = None,
        limit: int = 100,
    ) -> list[RowMatch]:
        """Return table rows containing a number satisfying ``value <op> threshold``."""
        if op not in _OPERATORS:
            raise ValueError(f"Unsupported operator '{op}'. Use one of {list(_OPERATORS)}.")
        compare = _OPERATORS[op]
        matches: list[RowMatch] = []
        for doc in self._documents(document_ids):
            for page in doc.pages:
                for table in page.tables:
                    header = table.rows[0] if table.rows else []
                    for row in table.rows[1:] if len(table.rows) > 1 else table.rows:
                        best: float | None = None
                        for cell in row:
                            num = _to_number(cell)
                            if num is not None and compare(num, threshold):
                                best = num if best is None else max(best, num, key=abs)
                        if best is not None:
                            matches.append(
                                RowMatch(doc.document_id, doc.filename, page.number,
                                         [str(c) for c in row], best)
                            )
                            if len(matches) >= limit:
                                return matches
        matches.sort(key=lambda m: abs(m.value), reverse=True)
        return matches
