"""Shared result type and helpers for audit calculations."""

from __future__ import annotations

from dataclasses import dataclass, field


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


@dataclass(slots=True)
class CalculationResult:
    """The outcome of a deterministic audit calculation.

    ``outputs`` holds the named numeric results; ``steps`` holds the ordered,
    human-readable working so the assistant can show every step.
    """

    name: str
    inputs: dict[str, object]
    outputs: dict[str, object]
    steps: list[str] = field(default_factory=list)
    summary: str = ""

    def explain(self) -> str:
        """Render the calculation as Markdown (title, steps, results)."""
        lines = [f"### {self.name}"]
        if self.summary:
            lines.append(self.summary)
        if self.steps:
            lines.append("\n**Steps**")
            lines.extend(f"{i}. {s}" for i, s in enumerate(self.steps, start=1))
        lines.append("\n**Results**")
        lines.extend(f"- **{k}**: {_fmt(v)}" for k, v in self.outputs.items())
        return "\n".join(lines)


def require_positive(name: str, value: float) -> None:
    from audit_assistant.core.exceptions import CalculationError

    if value <= 0:
        raise CalculationError(f"{name} must be greater than zero (got {value}).")


def require_non_negative(name: str, value: float) -> None:
    from audit_assistant.core.exceptions import CalculationError

    if value < 0:
        raise CalculationError(f"{name} must not be negative (got {value}).")
