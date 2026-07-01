"""Deterministic audit calculator UI (Phase 5).

Renders a form per calculation, runs the pure function (exact arithmetic — no
LLM), shows every step, and records the result to history. Works with no API key.
"""

from __future__ import annotations

import streamlit as st

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
from audit_assistant.core.logging import get_logger
from audit_assistant.services.calculation_service import CATALOG

log = get_logger(__name__)


def _numbers(label: str, default: str = "") -> list[float]:
    raw = st.text_area(label, value=default, help="Comma or newline separated numbers.")
    out: list[float] = []
    for token in raw.replace("\n", ",").split(","):
        token = token.strip()
        if token:
            try:
                out.append(float(token))
            except ValueError:
                st.warning(f"Ignored non-numeric value: {token!r}")
    return out


def _pairs(label: str, default: str, help_text: str) -> list[tuple[float, float]]:
    raw = st.text_area(label, value=default, help=help_text)
    pairs: list[tuple[float, float]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            try:
                pairs.append((float(parts[0]), float(parts[1])))
            except ValueError:
                st.warning(f"Ignored malformed line: {line!r}")
    return pairs


def _desc_pairs(label: str, default: str, help_text: str) -> list[tuple[str, float]]:
    """Parse `description, amount` lines, preserving the text description."""
    raw = st.text_area(label, value=default, help=help_text)
    out: list[tuple[str, float]] = []
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            try:
                out.append((parts[0], float(parts[1])))
            except ValueError:
                st.warning(f"Ignored malformed line: {line!r}")
    return out


def _run(fn, *args, **kwargs):
    """Execute a calculation, render it, and return the result (or None)."""
    try:
        result = fn(*args, **kwargs)
    except CalculationError as exc:
        st.error(f"❌ {exc}")
        return None
    st.markdown(result.explain())
    return result


def _form(label: str):  # noqa: C901 - a flat dispatch table is clearest here
    """Render inputs for the chosen calculation and return a result or None."""
    n = st.number_input  # shorthand

    if label == "Materiality (ISA 320)":
        bench = n("Benchmark value (e.g. profit before tax)", value=1_000_000.0, step=1000.0)
        name = st.text_input("Benchmark name", "profit before tax")
        pct = n("Percentage %", value=5.0, step=0.5)
        return _run(materiality.materiality, benchmark_value=bench, benchmark_name=name, percentage=pct)

    if label == "MUS sample size (ISA 530)":
        pop = n("Population value", value=5_000_000.0, step=1000.0)
        tol = n("Tolerable misstatement", value=250_000.0, step=1000.0)
        conf = n("Confidence %", value=95.0, step=1.0)
        exp = n("Expected misstatement", value=0.0, step=1000.0)
        return _run(sampling.mus_sample_size, population_value=pop, tolerable_misstatement=tol,
                    confidence_pct=conf, expected_misstatement=exp)

    if label == "Attribute sample size (ISA 530)":
        tol = n("Tolerable deviation rate %", value=5.0, step=0.5)
        conf = n("Confidence %", value=95.0, step=1.0)
        exp = n("Expected deviation rate %", value=1.0, step=0.5)
        return _run(sampling.attribute_sample_size, tolerable_deviation_rate=tol,
                    confidence_pct=conf, expected_deviation_rate=exp)

    if label == "Current ratio":
        return _run(ratios.current_ratio, n("Current assets", value=0.0), n("Current liabilities", value=0.0))
    if label == "Quick ratio":
        return _run(ratios.quick_ratio, n("Current assets", value=0.0), n("Inventory", value=0.0),
                    n("Current liabilities", value=0.0))
    if label == "Debt-to-equity":
        return _run(ratios.debt_to_equity, n("Total liabilities", value=0.0), n("Total equity", value=0.0))
    if label == "Gross margin":
        return _run(ratios.gross_margin, n("Revenue", value=0.0), n("COGS", value=0.0))
    if label == "Net margin":
        return _run(ratios.net_margin, n("Net income", value=0.0), n("Revenue", value=0.0))
    if label == "Return on assets":
        return _run(ratios.return_on_assets, n("Net income", value=0.0), n("Total assets", value=0.0))
    if label == "Return on equity":
        return _run(ratios.return_on_equity, n("Net income", value=0.0), n("Total equity", value=0.0))
    if label == "Inventory turnover":
        return _run(ratios.inventory_turnover, n("COGS", value=0.0), n("Average inventory", value=0.0))
    if label == "Days sales outstanding":
        return _run(ratios.receivables_days, n("Average receivables", value=0.0), n("Revenue", value=0.0))

    if label == "Variance analysis":
        return _run(trends.variance, n("Actual", value=0.0), n("Expected/Budget", value=0.0))
    if label == "Percentage difference":
        return _run(trends.percentage_difference, n("Base value", value=0.0), n("Comparison value", value=0.0))
    if label == "Growth rate / CAGR":
        return _run(trends.growth_rate, n("Start value", value=0.0), n("End value", value=0.0),
                    int(n("Periods", value=1, step=1)))
    if label == "Trend analysis":
        vals = _numbers("Series of values (oldest → newest)", "100, 120, 150, 140, 175")
        if len(vals) >= 2:
            return _run(trends.trend_analysis, vals)
        st.info("Enter at least two values.")
        return None

    if label == "Benford's Law (first digit)":
        vals = _numbers("Population of amounts (≥ 30 values)")
        if len(vals) >= 30:
            return _run(benford.benford_first_digit, vals)
        st.info(f"Enter at least 30 values (you have {len(vals)}).")
        return None

    if label == "Add VAT":
        return _run(taxes.add_vat, n("Net amount", value=0.0), n("VAT rate %", value=15.0, step=0.5))
    if label == "Extract VAT":
        return _run(taxes.extract_vat, n("Gross amount", value=0.0), n("VAT rate %", value=15.0, step=0.5))

    if label == "Aging analysis":
        pairs = _pairs("Items: one per line as `amount, days_outstanding`",
                       "10000, 0\n5000, 20\n3000, 45\n2000, 100",
                       "e.g. `1500, 45` = 1500 outstanding 45 days")
        if pairs:
            return _run(aging.aging_buckets, pairs)
        return None

    if label == "Reconcile balances":
        book = n("Book balance", value=0.0)
        ext = n("External balance", value=0.0)
        adj = _desc_pairs("Adjustments: one per line as `description, amount`",
                          "Outstanding cheque, -500\nDeposit in transit, 800",
                          "Signed amounts applied to the book balance.")
        return _run(reconciliation.reconcile_balances, book, ext, adj)

    if label == "Match transactions":
        a = _numbers("Side A amounts (e.g. ledger)")
        b = _numbers("Side B amounts (e.g. bank)")
        if a and b:
            return _run(reconciliation.match_transactions, a, b)
        return None

    if label == "Risk matrix (likelihood × impact)":
        like = int(n("Likelihood (1-5)", value=3, step=1))
        imp = int(n("Impact (1-5)", value=3, step=1))
        return _run(risk.risk_matrix, like, imp)
    if label == "Audit risk model":
        ir = n("Inherent risk (0-1)", value=0.9, step=0.05)
        cr = n("Control risk (0-1)", value=0.6, step=0.05)
        ar = n("Target audit risk (0-1)", value=0.05, step=0.01)
        return _run(risk.audit_risk_model, ir, cr, ar)

    if label == "Inventory — weighted average":
        p = _pairs("Purchases: one per line as `units, unit_cost`",
                   "100, 10\n200, 12\n150, 11", "Each layer of purchases.")
        sold = n("Units sold", value=0.0)
        if p:
            return _run(inventory.weighted_average_cost, p, sold)
        return None
    if label == "Inventory — FIFO":
        p = _pairs("Purchases (oldest → newest): `units, unit_cost`",
                   "100, 10\n200, 12\n150, 11", "Oldest layer first.")
        sold = n("Units sold", value=0.0)
        if p:
            return _run(inventory.fifo_ending_value, p, sold)
        return None

    if label == "Payroll — gross to net":
        gross = n("Gross pay", value=0.0)
        d = _desc_pairs("Deductions: one per line as `description, amount`",
                        "Tax, 500\nPension, 200", "")
        return _run(payroll.gross_to_net, gross_pay=gross, deductions=d)
    if label == "Payroll — overtime":
        nh = n("Normal hours", value=160.0)
        oh = n("Overtime hours", value=10.0)
        rate = n("Hourly rate", value=50.0)
        mult = n("Overtime multiplier", value=1.5, step=0.1)
        return _run(payroll.overtime_pay, normal_hours=nh, overtime_hours=oh,
                    hourly_rate=rate, overtime_multiplier=mult)

    st.info("Select a calculation.")
    return None


def render_calculator(container) -> None:
    st.subheader("🧮 Audit calculator")
    st.caption("Exact, deterministic calculations with full working — no AI, no API key.")

    categories = list(CATALOG.keys())
    category = st.selectbox("Category", categories, key="calc_category")
    label = st.selectbox("Calculation", list(CATALOG[category].keys()), key="calc_label")

    result = _form(label)
    if result is not None and st.button("💾 Save to history", key="calc_save"):
        container.calculation_service.record(result)
        container.audit_log.record("calculation", f"{result.name}: {result.summary}")
        st.success("Saved to calculation history.")

    hist = container.calculation_service.history(limit=10)
    if hist:
        with st.expander("🕑 Recent calculations"):
            for row in hist:
                st.markdown(f"- **{row['name']}** — {row['summary']}")
