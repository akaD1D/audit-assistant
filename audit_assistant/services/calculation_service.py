"""Calculation service: a catalog of deterministic calculations + history.

The service does not do arithmetic itself — it routes to the pure functions in
``audit.calculations`` and persists each :class:`CalculationResult` to history.
The catalog is structured so it can drive the UI now and be exposed as LLM
tools later without changing the calculation code.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from audit_assistant.audit.calculations import (
    aging,
    benford,
    inventory,
    materiality,
    payroll,
    ratios,
    reconciliation,
    risk,
    sampling,
    taxes,
    trends,
)
from audit_assistant.audit.calculations.base import CalculationResult
from audit_assistant.core.logging import get_logger
from audit_assistant.infrastructure.db import Database

log = get_logger(__name__)

# Catalog grouped by category -> {label: callable}. Callables return CalculationResult.
CATALOG: dict[str, dict[str, object]] = {
    "Materiality & Sampling": {
        "Materiality (ISA 320)": materiality.materiality,
        "MUS sample size (ISA 530)": sampling.mus_sample_size,
        "Attribute sample size (ISA 530)": sampling.attribute_sample_size,
    },
    "Ratios & Analytical": {
        "Current ratio": ratios.current_ratio,
        "Quick ratio": ratios.quick_ratio,
        "Debt-to-equity": ratios.debt_to_equity,
        "Gross margin": ratios.gross_margin,
        "Net margin": ratios.net_margin,
        "Return on assets": ratios.return_on_assets,
        "Return on equity": ratios.return_on_equity,
        "Inventory turnover": ratios.inventory_turnover,
        "Days sales outstanding": ratios.receivables_days,
    },
    "Trends & Variance": {
        "Variance analysis": trends.variance,
        "Percentage difference": trends.percentage_difference,
        "Growth rate / CAGR": trends.growth_rate,
        "Trend analysis": trends.trend_analysis,
    },
    "Fraud & Anomaly": {
        "Benford's Law (first digit)": benford.benford_first_digit,
    },
    "Tax & Aging": {
        "Add VAT": taxes.add_vat,
        "Extract VAT": taxes.extract_vat,
        "Aging analysis": aging.aging_buckets,
    },
    "Reconciliation": {
        "Reconcile balances": reconciliation.reconcile_balances,
        "Match transactions": reconciliation.match_transactions,
    },
    "Risk": {
        "Risk matrix (likelihood × impact)": risk.risk_matrix,
        "Audit risk model": risk.audit_risk_model,
    },
    "Inventory & Payroll": {
        "Inventory — weighted average": inventory.weighted_average_cost,
        "Inventory — FIFO": inventory.fifo_ending_value,
        "Payroll — gross to net": payroll.gross_to_net,
        "Payroll — overtime": payroll.overtime_pay,
    },
}


class CalculationService:
    """Persists calculation results and serves history."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def record(self, result: CalculationResult) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "INSERT INTO calculations (ts, name, inputs_json, outputs_json, summary) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    result.name,
                    json.dumps(result.inputs, default=str, ensure_ascii=False),
                    json.dumps(result.outputs, default=str, ensure_ascii=False),
                    result.summary,
                ),
            )
        log.info("Recorded calculation '%s'", result.name)

    def history(self, limit: int = 20) -> list[dict]:
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT ts, name, summary FROM calculations ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
