"""Variance, percentage-difference, growth, and trend analysis."""

from __future__ import annotations

from audit_assistant.audit.calculations.base import CalculationResult
from audit_assistant.core.exceptions import CalculationError


def variance(actual: float, expected: float) -> CalculationResult:
    """Absolute and percentage variance of actual vs expected/budget."""
    abs_var = actual - expected
    pct_var = (abs_var / expected * 100) if expected != 0 else float("nan")
    steps = [
        f"Absolute variance = actual − expected = {actual:,.2f} − {expected:,.2f} = {abs_var:,.2f}",
    ]
    if expected != 0:
        steps.append(
            f"Percentage variance = variance / expected × 100 "
            f"= {abs_var:,.2f} / {expected:,.2f} × 100 = {pct_var:,.2f}%"
        )
    direction = "favourable/increase" if abs_var >= 0 else "unfavourable/decrease"
    return CalculationResult(
        name="Variance analysis",
        inputs={"actual": actual, "expected": expected},
        outputs={"absolute_variance": round(abs_var, 2),
                 "percentage_variance": None if expected == 0 else round(pct_var, 2)},
        steps=steps,
        summary=f"Variance of {abs_var:,.2f} ({direction}).",
    )


def percentage_difference(value_a: float, value_b: float) -> CalculationResult:
    """Percentage change from value_a (base) to value_b."""
    if value_a == 0:
        raise CalculationError("percentage_difference: base value must not be zero.")
    diff = value_b - value_a
    pct = diff / value_a * 100
    return CalculationResult(
        name="Percentage difference",
        inputs={"base": value_a, "comparison": value_b},
        outputs={"absolute_change": round(diff, 2), "percentage_change": round(pct, 2)},
        steps=[f"% change = (comparison − base) / base × 100 "
               f"= ({value_b:,.2f} − {value_a:,.2f}) / {value_a:,.2f} × 100 = {pct:,.2f}%"],
        summary=f"{pct:,.2f}% change from {value_a:,.2f} to {value_b:,.2f}.",
    )


def growth_rate(start_value: float, end_value: float, periods: int = 1) -> CalculationResult:
    """Total growth and CAGR over a number of periods."""
    if start_value <= 0:
        raise CalculationError("growth_rate: start value must be positive.")
    if periods < 1:
        raise CalculationError("growth_rate: periods must be >= 1.")
    total_growth = (end_value - start_value) / start_value * 100
    cagr = ((end_value / start_value) ** (1 / periods) - 1) * 100
    return CalculationResult(
        name="Growth rate",
        inputs={"start_value": start_value, "end_value": end_value, "periods": periods},
        outputs={"total_growth_pct": round(total_growth, 2), "cagr_pct": round(cagr, 2)},
        steps=[
            f"Total growth = (end − start) / start × 100 "
            f"= ({end_value:,.2f} − {start_value:,.2f}) / {start_value:,.2f} × 100 "
            f"= {total_growth:,.2f}%",
            f"CAGR = (end / start)^(1/periods) − 1 "
            f"= ({end_value:,.2f} / {start_value:,.2f})^(1/{periods}) − 1 = {cagr:,.2f}%",
        ],
        summary=f"CAGR of {cagr:,.2f}% over {periods} period(s).",
    )


def trend_analysis(series: list[float]) -> CalculationResult:
    """Period-over-period changes plus overall CAGR for a numeric series."""
    if len(series) < 2:
        raise CalculationError("trend_analysis: provide at least two values.")
    changes = []
    steps = []
    for i in range(1, len(series)):
        prev, cur = series[i - 1], series[i]
        pct = ((cur - prev) / prev * 100) if prev != 0 else float("nan")
        changes.append(round(pct, 2))
        steps.append(f"Period {i}→{i + 1}: {prev:,.2f} → {cur:,.2f} = {pct:,.2f}%")
    overall = None
    if series[0] > 0:
        overall = ((series[-1] / series[0]) ** (1 / (len(series) - 1)) - 1) * 100
        steps.append(f"Overall CAGR = {overall:,.2f}%")
    return CalculationResult(
        name="Trend analysis",
        inputs={"series": series},
        outputs={"period_changes_pct": changes,
                 "cagr_pct": None if overall is None else round(overall, 2)},
        steps=steps,
        summary=f"{len(series)} periods analysed; {len(changes)} period-over-period changes.",
    )
