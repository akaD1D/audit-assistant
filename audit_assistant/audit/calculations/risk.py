"""Risk scoring: likelihood × impact matrix and the audit risk model."""

from __future__ import annotations

from audit_assistant.audit.calculations.base import CalculationResult
from audit_assistant.core.exceptions import CalculationError


def _band(score: int) -> str:
    if score <= 4:
        return "Low"
    if score <= 9:
        return "Moderate"
    if score <= 16:
        return "High"
    return "Critical"


def risk_matrix(likelihood: int, impact: int) -> CalculationResult:
    """Score a risk on a 5×5 likelihood/impact matrix (each 1–5)."""
    for label, v in (("likelihood", likelihood), ("impact", impact)):
        if not 1 <= v <= 5:
            raise CalculationError(f"{label} must be between 1 and 5 (got {v}).")
    score = likelihood * impact
    band = _band(score)
    return CalculationResult(
        name="Risk scoring (likelihood × impact)",
        inputs={"likelihood": likelihood, "impact": impact},
        outputs={"risk_score": score, "risk_rating": band},
        steps=[f"Risk score = likelihood × impact = {likelihood} × {impact} = {score}",
               f"Score {score} falls in the '{band}' band."],
        summary=f"Risk score {score}/25 — {band}.",
    )


def audit_risk_model(
    inherent_risk: float, control_risk: float, target_audit_risk: float = 0.05
) -> CalculationResult:
    """Detection risk implied by the audit risk model: AR = IR × CR × DR.

    Risks are probabilities in (0, 1]. Returns the detection risk the auditor
    can accept to hit the target overall audit risk.
    """
    for label, v in (("inherent_risk", inherent_risk), ("control_risk", control_risk),
                     ("target_audit_risk", target_audit_risk)):
        if not 0 < v <= 1:
            raise CalculationError(f"{label} must be in (0, 1] (got {v}).")
    detection_risk = target_audit_risk / (inherent_risk * control_risk)
    detection_risk = min(detection_risk, 1.0)
    return CalculationResult(
        name="Audit risk model",
        inputs={"inherent_risk": inherent_risk, "control_risk": control_risk,
                "target_audit_risk": target_audit_risk},
        outputs={"acceptable_detection_risk": round(detection_risk, 4)},
        steps=[
            f"AR = IR × CR × DR ⇒ DR = AR / (IR × CR)",
            f"DR = {target_audit_risk:.4f} / ({inherent_risk:.2f} × {control_risk:.2f}) "
            f"= {detection_risk:.4f}",
        ],
        summary=f"Acceptable detection risk = {detection_risk:.2%} "
                "(lower DR ⇒ more substantive testing).",
    )
