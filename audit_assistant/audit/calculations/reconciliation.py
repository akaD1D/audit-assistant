"""Reconciliation helpers: balance reconciliation and transaction matching."""

from __future__ import annotations

from audit_assistant.audit.calculations.base import CalculationResult


def reconcile_balances(
    book_balance: float,
    external_balance: float,
    adjustments: list[tuple[str, float]] | None = None,
) -> CalculationResult:
    """Reconcile a book balance to an external balance via signed adjustments.

    Each adjustment is ``(description, amount)`` applied to the book balance.
    Reconciles when adjusted book balance equals the external balance.
    """
    adjustments = adjustments or []
    adjusted = book_balance + sum(a for _, a in adjustments)
    difference = round(adjusted - external_balance, 2)
    reconciles = abs(difference) < 0.005

    steps = [f"Book balance = {book_balance:,.2f}"]
    for desc, amt in adjustments:
        steps.append(f"Adjustment ({desc}) = {amt:,.2f}")
    steps.append(f"Adjusted book balance = {adjusted:,.2f}")
    steps.append(f"External balance = {external_balance:,.2f}")
    steps.append(f"Unreconciled difference = {difference:,.2f}")

    return CalculationResult(
        name="Balance reconciliation",
        inputs={"book_balance": book_balance, "external_balance": external_balance,
                "adjustments": adjustments},
        outputs={"adjusted_book_balance": round(adjusted, 2),
                 "unreconciled_difference": difference, "reconciles": reconciles},
        steps=steps,
        summary=("Reconciled — no residual difference." if reconciles
                 else f"Does NOT reconcile — difference of {difference:,.2f} remains."),
    )


def match_transactions(
    side_a: list[float], side_b: list[float], tolerance: float = 0.005
) -> CalculationResult:
    """Match amounts between two lists (e.g. ledger vs bank); report unmatched."""
    remaining_b = list(side_b)
    matched: list[float] = []
    unmatched_a: list[float] = []

    for amount in side_a:
        hit = next((b for b in remaining_b if abs(b - amount) <= tolerance), None)
        if hit is None:
            unmatched_a.append(amount)
        else:
            remaining_b.remove(hit)
            matched.append(amount)

    return CalculationResult(
        name="Transaction matching",
        inputs={"count_a": len(side_a), "count_b": len(side_b)},
        outputs={
            "matched_count": len(matched),
            "unmatched_a": unmatched_a,
            "unmatched_b": remaining_b,
            "unmatched_a_total": round(sum(unmatched_a), 2),
            "unmatched_b_total": round(sum(remaining_b), 2),
        },
        steps=[
            f"Matched {len(matched)} of {len(side_a)} items from side A.",
            f"Unmatched on side A: {len(unmatched_a)} (total {sum(unmatched_a):,.2f}).",
            f"Unmatched on side B: {len(remaining_b)} (total {sum(remaining_b):,.2f}).",
        ],
        summary=f"{len(matched)} matched; "
                f"{len(unmatched_a)}+{len(remaining_b)} unmatched.",
    )
