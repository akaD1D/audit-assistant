"""Materiality calculations (ISA 320 / ISA 450)."""

from __future__ import annotations

from audit_assistant.audit.calculations.base import CalculationResult, require_positive


def materiality(
    *,
    benchmark_value: float,
    benchmark_name: str = "profit before tax",
    percentage: float = 5.0,
    performance_ratio: float = 0.75,
    trivial_ratio: float = 0.05,
) -> CalculationResult:
    """Overall materiality, performance materiality, and clearly-trivial threshold.

    - Overall materiality = benchmark × percentage
    - Performance materiality = overall × performance_ratio (typically 50–75%)
    - Clearly trivial threshold = overall × trivial_ratio (typically ~5%)
    """
    require_positive("benchmark_value", benchmark_value)
    require_positive("percentage", percentage)

    overall = benchmark_value * percentage / 100.0
    performance = overall * performance_ratio
    trivial = overall * trivial_ratio

    steps = [
        f"Overall materiality = {benchmark_name} × percentage "
        f"= {benchmark_value:,.2f} × {percentage:.2f}% = {overall:,.2f}",
        f"Performance materiality = overall × {performance_ratio:.0%} "
        f"= {overall:,.2f} × {performance_ratio:.2f} = {performance:,.2f}",
        f"Clearly trivial threshold = overall × {trivial_ratio:.0%} "
        f"= {overall:,.2f} × {trivial_ratio:.2f} = {trivial:,.2f}",
    ]
    return CalculationResult(
        name="Materiality (ISA 320)",
        inputs={
            "benchmark_value": benchmark_value,
            "benchmark_name": benchmark_name,
            "percentage": percentage,
            "performance_ratio": performance_ratio,
            "trivial_ratio": trivial_ratio,
        },
        outputs={
            "overall_materiality": round(overall, 2),
            "performance_materiality": round(performance, 2),
            "clearly_trivial_threshold": round(trivial, 2),
        },
        steps=steps,
        summary=(
            f"Based on {percentage:.2f}% of {benchmark_name} "
            f"({benchmark_value:,.2f}), overall materiality is {overall:,.2f}."
        ),
    )
