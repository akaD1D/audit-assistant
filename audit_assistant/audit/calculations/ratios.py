"""Financial ratio calculations for analytical procedures."""

from __future__ import annotations

from audit_assistant.audit.calculations.base import CalculationResult
from audit_assistant.core.exceptions import CalculationError


def _ratio(name: str, numerator: float, denominator: float, *, as_percent: bool = False,
           num_label: str = "numerator", den_label: str = "denominator",
           unit: str = "") -> CalculationResult:
    if denominator == 0:
        raise CalculationError(f"{name}: {den_label} must not be zero.")
    raw = numerator / denominator
    value = raw * 100 if as_percent else raw
    suffix = "%" if as_percent else (f" {unit}".rstrip())
    steps = [
        f"{name} = {num_label} / {den_label} = {numerator:,.2f} / {denominator:,.2f} "
        f"= {raw:,.4f}" + (f" → {value:,.2f}%" if as_percent else ""),
    ]
    return CalculationResult(
        name=name,
        inputs={num_label: numerator, den_label: denominator},
        outputs={name: round(value, 4)},
        steps=steps,
        summary=f"{name} = {value:,.2f}{suffix}",
    )


def current_ratio(current_assets: float, current_liabilities: float) -> CalculationResult:
    return _ratio("Current ratio", current_assets, current_liabilities,
                  num_label="current assets", den_label="current liabilities", unit="x")


def quick_ratio(current_assets: float, inventory: float, current_liabilities: float) -> CalculationResult:
    r = _ratio("Quick ratio", current_assets - inventory, current_liabilities,
               num_label="current assets − inventory", den_label="current liabilities", unit="x")
    r.inputs["inventory"] = inventory
    return r


def debt_to_equity(total_liabilities: float, total_equity: float) -> CalculationResult:
    return _ratio("Debt-to-equity", total_liabilities, total_equity,
                  num_label="total liabilities", den_label="total equity", unit="x")


def gross_margin(revenue: float, cogs: float) -> CalculationResult:
    return _ratio("Gross margin", revenue - cogs, revenue, as_percent=True,
                  num_label="gross profit (revenue − COGS)", den_label="revenue")


def net_margin(net_income: float, revenue: float) -> CalculationResult:
    return _ratio("Net margin", net_income, revenue, as_percent=True,
                  num_label="net income", den_label="revenue")


def return_on_assets(net_income: float, total_assets: float) -> CalculationResult:
    return _ratio("Return on assets", net_income, total_assets, as_percent=True,
                  num_label="net income", den_label="total assets")


def return_on_equity(net_income: float, total_equity: float) -> CalculationResult:
    return _ratio("Return on equity", net_income, total_equity, as_percent=True,
                  num_label="net income", den_label="total equity")


def inventory_turnover(cogs: float, average_inventory: float) -> CalculationResult:
    r = _ratio("Inventory turnover", cogs, average_inventory,
               num_label="COGS", den_label="average inventory", unit="x")
    if cogs > 0:
        days = 365 * average_inventory / cogs
        r.outputs["days_inventory_outstanding"] = round(days, 1)
        r.steps.append(f"Days inventory outstanding = 365 / turnover = {days:,.1f} days")
    return r


def receivables_days(average_receivables: float, revenue: float) -> CalculationResult:
    if revenue == 0:
        raise CalculationError("Receivables days: revenue must not be zero.")
    days = 365 * average_receivables / revenue
    return CalculationResult(
        name="Days sales outstanding",
        inputs={"average_receivables": average_receivables, "revenue": revenue},
        outputs={"days_sales_outstanding": round(days, 1)},
        steps=[f"DSO = 365 × average receivables / revenue "
               f"= 365 × {average_receivables:,.2f} / {revenue:,.2f} = {days:,.1f} days"],
        summary=f"Days sales outstanding = {days:,.1f} days",
    )
