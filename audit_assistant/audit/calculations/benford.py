"""Benford's Law first-digit analysis (fraud / anomaly detection)."""

from __future__ import annotations

import math

from audit_assistant.audit.calculations.base import CalculationResult
from audit_assistant.core.exceptions import CalculationError

# Expected first-digit proportions under Benford's Law.
BENFORD_EXPECTED = {d: math.log10(1 + 1 / d) for d in range(1, 10)}


def _leading_digit(value: float) -> int | None:
    value = abs(value)
    if value == 0:
        return None
    while value < 1:
        value *= 10
    while value >= 10:
        value /= 10
    return int(value)


def _mad_conformity(mad: float) -> str:
    # Nigrini's mean absolute deviation thresholds (first digit).
    if mad < 0.006:
        return "close conformity"
    if mad < 0.012:
        return "acceptable conformity"
    if mad < 0.015:
        return "marginally acceptable conformity"
    return "nonconformity (investigate)"


def benford_first_digit(numbers: list[float]) -> CalculationResult:
    """Compare observed leading-digit frequencies to Benford's Law.

    Reports per-digit observed vs expected, mean absolute deviation (MAD) with a
    Nigrini conformity verdict, and the chi-square statistic.
    """
    digits = [d for d in (_leading_digit(n) for n in numbers) if d is not None]
    n = len(digits)
    if n < 30:
        raise CalculationError(
            f"Benford analysis needs at least ~30 non-zero values (got {n})."
        )

    observed_counts = {d: 0 for d in range(1, 10)}
    for d in digits:
        observed_counts[d] += 1

    observed_prop = {d: observed_counts[d] / n for d in range(1, 10)}
    abs_devs = [abs(observed_prop[d] - BENFORD_EXPECTED[d]) for d in range(1, 10)]
    mad = sum(abs_devs) / 9

    chi_square = 0.0
    for d in range(1, 10):
        expected_count = BENFORD_EXPECTED[d] * n
        chi_square += (observed_counts[d] - expected_count) ** 2 / expected_count

    verdict = _mad_conformity(mad)
    distribution = {
        d: {
            "observed_pct": round(observed_prop[d] * 100, 2),
            "expected_pct": round(BENFORD_EXPECTED[d] * 100, 2),
            "count": observed_counts[d],
        }
        for d in range(1, 10)
    }
    return CalculationResult(
        name="Benford's Law — first digit",
        inputs={"sample_size": n},
        outputs={
            "mad": round(mad, 5),
            "conformity": verdict,
            "chi_square": round(chi_square, 3),
            "chi_square_critical_0.05": 15.507,  # df = 8
            "distribution": distribution,
        },
        steps=[
            f"Analysed {n} leading digits.",
            f"Mean absolute deviation (MAD) = {mad:.5f} → {verdict}.",
            f"Chi-square = {chi_square:.3f} (critical value at 5%, df=8 is 15.507). "
            + ("Exceeds critical value — distribution differs from Benford."
               if chi_square > 15.507 else "Within critical value."),
        ],
        summary=f"MAD {mad:.5f} indicates {verdict}.",
    )
