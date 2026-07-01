"""Deterministic correctness tests for every audit calculation."""

from __future__ import annotations

import pytest

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
from audit_assistant.core.exceptions import CalculationError

A = pytest.approx


def test_materiality() -> None:
    r = materiality.materiality(benchmark_value=1_000_000, percentage=5)
    assert r.outputs["overall_materiality"] == A(50_000)
    assert r.outputs["performance_materiality"] == A(37_500)
    assert r.outputs["clearly_trivial_threshold"] == A(2_500)
    with pytest.raises(CalculationError):
        materiality.materiality(benchmark_value=-1, percentage=5)


def test_mus_sample_size() -> None:
    r = sampling.mus_sample_size(population_value=5_000_000, tolerable_misstatement=250_000)
    assert r.outputs["reliability_factor"] == 3.0
    assert r.outputs["sample_size"] == 60
    with pytest.raises(CalculationError):
        sampling.mus_sample_size(population_value=100, tolerable_misstatement=10,
                                 expected_misstatement=10)


def test_attribute_sample_size() -> None:
    r = sampling.attribute_sample_size(tolerable_deviation_rate=5, expected_deviation_rate=1)
    assert r.outputs["sample_size"] == 75


def test_ratios() -> None:
    assert ratios.current_ratio(200, 100).outputs["Current ratio"] == A(2.0)
    assert ratios.quick_ratio(200, 50, 100).outputs["Quick ratio"] == A(1.5)
    assert ratios.debt_to_equity(300, 150).outputs["Debt-to-equity"] == A(2.0)
    assert ratios.gross_margin(1000, 600).outputs["Gross margin"] == A(40.0)
    assert ratios.net_margin(100, 1000).outputs["Net margin"] == A(10.0)
    assert ratios.return_on_assets(100, 2000).outputs["Return on assets"] == A(5.0)
    it = ratios.inventory_turnover(1200, 300)
    assert it.outputs["Inventory turnover"] == A(4.0)
    assert it.outputs["days_inventory_outstanding"] == A(91.25, abs=0.1)
    assert ratios.receivables_days(200, 1460).outputs["days_sales_outstanding"] == A(50.0)
    with pytest.raises(CalculationError):
        ratios.current_ratio(100, 0)


def test_trends() -> None:
    v = trends.variance(1200, 1000)
    assert v.outputs["absolute_variance"] == A(200)
    assert v.outputs["percentage_variance"] == A(20.0)
    assert trends.percentage_difference(100, 150).outputs["percentage_change"] == A(50.0)
    g = trends.growth_rate(100, 200, periods=4)
    assert g.outputs["total_growth_pct"] == A(100.0)
    assert g.outputs["cagr_pct"] == A(18.92, abs=0.01)
    t = trends.trend_analysis([100, 120, 150])
    assert t.outputs["period_changes_pct"] == [A(20.0), A(25.0)]
    assert t.outputs["cagr_pct"] == A(22.47, abs=0.01)
    with pytest.raises(CalculationError):
        trends.percentage_difference(0, 5)


def test_benford() -> None:
    r = benford.benford_first_digit([1000 + i for i in range(30)])  # all lead with 1
    assert r.outputs["distribution"][1]["count"] == 30
    assert r.outputs["conformity"] == "nonconformity (investigate)"
    with pytest.raises(CalculationError):
        benford.benford_first_digit([1, 2, 3])


def test_vat() -> None:
    a = taxes.add_vat(100, 15)
    assert a.outputs["vat"] == A(15.0)
    assert a.outputs["gross_amount"] == A(115.0)
    e = taxes.extract_vat(115, 15)
    assert e.outputs["net_amount"] == A(100.0)
    assert e.outputs["vat"] == A(15.0)


def test_aging() -> None:
    r = aging.aging_buckets([(10000, 0), (5000, 20), (3000, 45), (2000, 100)])
    totals = r.outputs["totals"]
    assert totals["Current"] == A(10000)
    assert totals["1-30"] == A(5000)
    assert totals["31-60"] == A(3000)
    assert totals["91+"] == A(2000)
    assert r.outputs["grand_total"] == A(20000)
    assert r.outputs["percentages"]["Current"] == A(50.0)


def test_reconciliation() -> None:
    r = reconciliation.reconcile_balances(
        1000, 1300, [("Deposit in transit", 800), ("Outstanding cheque", -500)]
    )
    assert r.outputs["adjusted_book_balance"] == A(1300)
    assert r.outputs["reconciles"] is True

    m = reconciliation.match_transactions([100, 200, 300], [200, 300, 400])
    assert m.outputs["matched_count"] == 2
    assert m.outputs["unmatched_a"] == [100]
    assert m.outputs["unmatched_b"] == [400]


def test_risk() -> None:
    assert risk.risk_matrix(4, 4).outputs["risk_rating"] == "High"
    assert risk.risk_matrix(5, 5).outputs["risk_rating"] == "Critical"
    dr = risk.audit_risk_model(0.9, 0.6, 0.05).outputs["acceptable_detection_risk"]
    assert dr == A(0.0926, abs=0.001)
    with pytest.raises(CalculationError):
        risk.risk_matrix(0, 3)


def test_inventory() -> None:
    wa = inventory.weighted_average_cost([(100, 10), (200, 12), (150, 11)], 300)
    assert wa.outputs["average_unit_cost"] == A(11.2222, abs=0.001)
    assert wa.outputs["cogs"] == A(3366.67, abs=0.01)
    assert wa.outputs["ending_inventory_value"] == A(1683.33, abs=0.01)

    fifo = inventory.fifo_ending_value([(100, 10), (200, 12), (150, 11)], 300)
    assert fifo.outputs["cogs"] == A(3400.0)
    assert fifo.outputs["ending_inventory_value"] == A(1650.0)


def test_payroll() -> None:
    g = payroll.gross_to_net(gross_pay=5000, deductions=[("Tax", 500), ("Pension", 200)])
    assert g.outputs["net_pay"] == A(4300)
    o = payroll.overtime_pay(normal_hours=160, overtime_hours=10, hourly_rate=50)
    assert o.outputs["total_pay"] == A(8750)


def test_result_explain_renders() -> None:
    text = materiality.materiality(benchmark_value=1000, percentage=5).explain()
    assert "Materiality" in text
    assert "Steps" in text
    assert "Results" in text


def test_calculation_service_history(tmp_path) -> None:
    from audit_assistant.infrastructure.db import Database
    from audit_assistant.services.calculation_service import CalculationService

    svc = CalculationService(Database(tmp_path / "c.db"))
    svc.record(materiality.materiality(benchmark_value=1000, percentage=5))
    hist = svc.history()
    assert len(hist) == 1
    assert "Materiality" in hist[0]["name"]
