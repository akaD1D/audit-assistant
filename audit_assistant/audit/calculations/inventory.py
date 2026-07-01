"""Inventory valuation (weighted-average and FIFO ending value)."""

from __future__ import annotations

from audit_assistant.audit.calculations.base import CalculationResult
from audit_assistant.core.exceptions import CalculationError


def weighted_average_cost(
    purchases: list[tuple[float, float]], units_sold: float
) -> CalculationResult:
    """Weighted-average cost valuation.

    ``purchases`` is a list of ``(units, unit_cost)``. Returns average cost,
    COGS, and ending inventory value for the given units sold.
    """
    if not purchases:
        raise CalculationError("weighted_average_cost: provide at least one purchase.")
    total_units = sum(u for u, _ in purchases)
    total_cost = sum(u * c for u, c in purchases)
    if units_sold > total_units:
        raise CalculationError("units_sold exceeds units available.")
    avg_cost = total_cost / total_units
    cogs = units_sold * avg_cost
    ending_units = total_units - units_sold
    ending_value = ending_units * avg_cost
    return CalculationResult(
        name="Inventory — weighted average cost",
        inputs={"purchases": purchases, "units_sold": units_sold},
        outputs={
            "average_unit_cost": round(avg_cost, 4),
            "cogs": round(cogs, 2),
            "ending_units": ending_units,
            "ending_inventory_value": round(ending_value, 2),
        },
        steps=[
            f"Total units = {total_units:,.2f}; total cost = {total_cost:,.2f}",
            f"Average unit cost = total cost / total units = {avg_cost:,.4f}",
            f"COGS = units sold × avg cost = {units_sold:,.2f} × {avg_cost:,.4f} = {cogs:,.2f}",
            f"Ending inventory = {ending_units:,.2f} × {avg_cost:,.4f} = {ending_value:,.2f}",
        ],
        summary=f"Avg cost {avg_cost:,.4f}; ending inventory {ending_value:,.2f}.",
    )


def fifo_ending_value(
    purchases: list[tuple[float, float]], units_sold: float
) -> CalculationResult:
    """FIFO: value remaining inventory using the most recent purchase layers."""
    if not purchases:
        raise CalculationError("fifo_ending_value: provide at least one purchase.")
    total_units = sum(u for u, _ in purchases)
    if units_sold > total_units:
        raise CalculationError("units_sold exceeds units available.")

    remaining = units_sold
    layers = list(purchases)
    cogs = 0.0
    # Consume oldest layers first.
    for i, (units, cost) in enumerate(layers):
        if remaining <= 0:
            break
        take = min(units, remaining)
        cogs += take * cost
        layers[i] = (units - take, cost)
        remaining -= take
    ending_value = sum(u * c for u, c in layers)
    ending_units = total_units - units_sold
    return CalculationResult(
        name="Inventory — FIFO",
        inputs={"purchases": purchases, "units_sold": units_sold},
        outputs={
            "cogs": round(cogs, 2),
            "ending_units": ending_units,
            "ending_inventory_value": round(ending_value, 2),
        },
        steps=[
            f"Consumed {units_sold:,.2f} units from oldest layers first.",
            f"COGS = {cogs:,.2f}",
            f"Ending inventory (newest layers) = {ending_value:,.2f}",
        ],
        summary=f"FIFO COGS {cogs:,.2f}; ending inventory {ending_value:,.2f}.",
    )
