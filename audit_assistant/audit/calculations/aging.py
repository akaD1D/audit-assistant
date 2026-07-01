"""Receivables / payables aging analysis."""

from __future__ import annotations

from audit_assistant.audit.calculations.base import CalculationResult
from audit_assistant.core.exceptions import CalculationError

_DEFAULT_EDGES = (30, 60, 90)


def aging_buckets(
    items: list[tuple[float, int]],
    bucket_edges: tuple[int, ...] = _DEFAULT_EDGES,
) -> CalculationResult:
    """Bucket amounts by days outstanding.

    ``items`` is a list of ``(amount, days_outstanding)``. Buckets are: Current
    (<= 0 days overdue), then edges (e.g. 1–30, 31–60, 61–90), then 90+.
    """
    if not items:
        raise CalculationError("aging_buckets: provide at least one item.")
    edges = sorted(bucket_edges)

    labels = ["Current"]
    prev = 0
    for e in edges:
        labels.append(f"{prev + 1}-{e}")
        prev = e
    labels.append(f"{prev + 1}+")

    totals = {label: 0.0 for label in labels}
    for amount, days in items:
        if days <= 0:
            totals["Current"] += amount
            continue
        placed = False
        prev = 0
        for i, e in enumerate(edges):
            if days <= e:
                totals[labels[i + 1]] += amount
                placed = True
                break
            prev = e
        if not placed:
            totals[labels[-1]] += amount

    grand_total = sum(totals.values())
    percentages = {
        label: (round(totals[label] / grand_total * 100, 2) if grand_total else 0.0)
        for label in labels
    }
    return CalculationResult(
        name="Aging analysis",
        inputs={"item_count": len(items), "bucket_edges": edges},
        outputs={
            "totals": {k: round(v, 2) for k, v in totals.items()},
            "percentages": percentages,
            "grand_total": round(grand_total, 2),
        },
        steps=[f"{label}: {totals[label]:,.2f} ({percentages[label]:.2f}%)" for label in labels],
        summary=f"Total {grand_total:,.2f} across {len(labels)} aging buckets.",
    )
