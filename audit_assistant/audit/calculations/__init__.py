"""Deterministic audit calculations.

Every function here is pure Python (no LLM) and returns a
:class:`CalculationResult` carrying the numeric outputs *and* a step-by-step
explanation. This is the anti-hallucination core: the assistant explains and
routes, but the numbers are computed exactly by this code.
"""

from audit_assistant.audit.calculations.base import CalculationResult

__all__ = ["CalculationResult"]
