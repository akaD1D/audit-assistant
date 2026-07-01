"""Basic payroll analysis: gross-to-net and overtime."""

from __future__ import annotations

from audit_assistant.audit.calculations.base import (
    CalculationResult,
    require_non_negative,
)


def gross_to_net(
    *,
    gross_pay: float,
    deductions: list[tuple[str, float]] | None = None,
) -> CalculationResult:
    """Net pay = gross pay − sum of deductions (each ``(description, amount)``)."""
    require_non_negative("gross_pay", gross_pay)
    deductions = deductions or []
    total_deductions = sum(a for _, a in deductions)
    net = gross_pay - total_deductions
    steps = [f"Gross pay = {gross_pay:,.2f}"]
    steps.extend(f"− {desc} = {amt:,.2f}" for desc, amt in deductions)
    steps.append(f"Total deductions = {total_deductions:,.2f}")
    steps.append(f"Net pay = gross − deductions = {net:,.2f}")
    return CalculationResult(
        name="Payroll — gross to net",
        inputs={"gross_pay": gross_pay, "deductions": deductions},
        outputs={"total_deductions": round(total_deductions, 2), "net_pay": round(net, 2)},
        steps=steps,
        summary=f"Net pay = {net:,.2f} (deductions {total_deductions:,.2f}).",
    )


def overtime_pay(
    *,
    normal_hours: float,
    overtime_hours: float,
    hourly_rate: float,
    overtime_multiplier: float = 1.5,
) -> CalculationResult:
    """Total pay including overtime at a premium multiplier (default 1.5×)."""
    for label, v in (("normal_hours", normal_hours), ("overtime_hours", overtime_hours),
                     ("hourly_rate", hourly_rate)):
        require_non_negative(label, v)
    normal_pay = normal_hours * hourly_rate
    ot_rate = hourly_rate * overtime_multiplier
    ot_pay = overtime_hours * ot_rate
    total = normal_pay + ot_pay
    return CalculationResult(
        name="Payroll — overtime",
        inputs={"normal_hours": normal_hours, "overtime_hours": overtime_hours,
                "hourly_rate": hourly_rate, "overtime_multiplier": overtime_multiplier},
        outputs={"normal_pay": round(normal_pay, 2), "overtime_pay": round(ot_pay, 2),
                 "total_pay": round(total, 2)},
        steps=[
            f"Normal pay = {normal_hours:,.2f} h × {hourly_rate:,.2f} = {normal_pay:,.2f}",
            f"Overtime rate = {hourly_rate:,.2f} × {overtime_multiplier:.2f} = {ot_rate:,.2f}",
            f"Overtime pay = {overtime_hours:,.2f} h × {ot_rate:,.2f} = {ot_pay:,.2f}",
            f"Total pay = {normal_pay:,.2f} + {ot_pay:,.2f} = {total:,.2f}",
        ],
        summary=f"Total pay = {total:,.2f} (overtime {ot_pay:,.2f}).",
    )
