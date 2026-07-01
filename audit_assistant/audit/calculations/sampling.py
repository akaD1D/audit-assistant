"""Audit sampling calculations (ISA 530): MUS and attribute sampling."""

from __future__ import annotations

import math

from audit_assistant.audit.calculations.base import CalculationResult, require_positive
from audit_assistant.core.exceptions import CalculationError

# Reliability (Poisson) factors for zero expected misstatements/deviations.
_RELIABILITY_FACTORS: dict[int, float] = {
    99: 4.61,
    95: 3.00,
    90: 2.31,
    85: 1.90,
    80: 1.61,
    75: 1.39,
}


def _reliability_factor(confidence_pct: float) -> float:
    key = int(round(confidence_pct))
    if key not in _RELIABILITY_FACTORS:
        nearest = min(_RELIABILITY_FACTORS, key=lambda k: abs(k - key))
        return _RELIABILITY_FACTORS[nearest]
    return _RELIABILITY_FACTORS[key]


def mus_sample_size(
    *,
    population_value: float,
    tolerable_misstatement: float,
    confidence_pct: float = 95.0,
    expected_misstatement: float = 0.0,
) -> CalculationResult:
    """Monetary Unit Sampling: sample size and sampling interval.

    sampling_interval = (tolerable − expected × expansion) / reliability_factor
    sample_size       = ceil(population_value / sampling_interval)
    """
    require_positive("population_value", population_value)
    require_positive("tolerable_misstatement", tolerable_misstatement)
    if expected_misstatement < 0:
        raise CalculationError("expected_misstatement must not be negative.")
    if expected_misstatement >= tolerable_misstatement:
        raise CalculationError("expected_misstatement must be below tolerable_misstatement.")

    rf = _reliability_factor(confidence_pct)
    # Simple expansion factor of 1.0 when expected = 0; otherwise a common 1.6.
    expansion = 1.0 if expected_misstatement == 0 else 1.6
    net_tolerable = tolerable_misstatement - expected_misstatement * expansion
    sampling_interval = net_tolerable / rf
    sample_size = math.ceil(population_value / sampling_interval)

    steps = [
        f"Reliability factor for {confidence_pct:.0f}% confidence = {rf:.2f}",
        f"Net tolerable = tolerable − expected × expansion "
        f"= {tolerable_misstatement:,.2f} − {expected_misstatement:,.2f} × {expansion:.1f} "
        f"= {net_tolerable:,.2f}",
        f"Sampling interval = net tolerable / reliability factor "
        f"= {net_tolerable:,.2f} / {rf:.2f} = {sampling_interval:,.2f}",
        f"Sample size = ceil(population / interval) "
        f"= ceil({population_value:,.2f} / {sampling_interval:,.2f}) = {sample_size}",
    ]
    return CalculationResult(
        name="MUS Sample Size (ISA 530)",
        inputs={
            "population_value": population_value,
            "tolerable_misstatement": tolerable_misstatement,
            "confidence_pct": confidence_pct,
            "expected_misstatement": expected_misstatement,
        },
        outputs={
            "reliability_factor": rf,
            "sampling_interval": round(sampling_interval, 2),
            "sample_size": sample_size,
        },
        steps=steps,
        summary=f"Select {sample_size} monetary units at an interval of {sampling_interval:,.2f}.",
    )


def attribute_sample_size(
    *,
    tolerable_deviation_rate: float,
    confidence_pct: float = 95.0,
    expected_deviation_rate: float = 0.0,
) -> CalculationResult:
    """Attribute (controls-testing) sample size, Poisson approximation.

    Rates are in percent. n = reliability_factor / (tolerable − expected) rate.
    """
    require_positive("tolerable_deviation_rate", tolerable_deviation_rate)
    if expected_deviation_rate < 0:
        raise CalculationError("expected_deviation_rate must not be negative.")
    if expected_deviation_rate >= tolerable_deviation_rate:
        raise CalculationError("expected_deviation_rate must be below tolerable_deviation_rate.")

    rf = _reliability_factor(confidence_pct)
    net_rate = (tolerable_deviation_rate - expected_deviation_rate) / 100.0
    sample_size = math.ceil(rf / net_rate)

    steps = [
        f"Reliability factor for {confidence_pct:.0f}% confidence = {rf:.2f}",
        f"Net deviation rate = ({tolerable_deviation_rate:.2f}% − "
        f"{expected_deviation_rate:.2f}%) = {net_rate:.4f}",
        f"Sample size = ceil(reliability factor / net rate) "
        f"= ceil({rf:.2f} / {net_rate:.4f}) = {sample_size}",
    ]
    return CalculationResult(
        name="Attribute Sample Size (ISA 530)",
        inputs={
            "tolerable_deviation_rate": tolerable_deviation_rate,
            "confidence_pct": confidence_pct,
            "expected_deviation_rate": expected_deviation_rate,
        },
        outputs={"reliability_factor": rf, "sample_size": sample_size},
        steps=steps,
        summary=f"Test a sample of {sample_size} items for control operating effectiveness.",
    )
