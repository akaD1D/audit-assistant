"""VAT calculations (add, extract, verify)."""

from __future__ import annotations

from audit_assistant.audit.calculations.base import CalculationResult, require_non_negative


def add_vat(net_amount: float, vat_rate: float = 15.0) -> CalculationResult:
    """Add VAT to a net (VAT-exclusive) amount. Rate in percent."""
    require_non_negative("net_amount", net_amount)
    vat = net_amount * vat_rate / 100.0
    gross = net_amount + vat
    return CalculationResult(
        name="Add VAT",
        inputs={"net_amount": net_amount, "vat_rate": vat_rate},
        outputs={"vat": round(vat, 2), "gross_amount": round(gross, 2)},
        steps=[
            f"VAT = net × rate = {net_amount:,.2f} × {vat_rate:.2f}% = {vat:,.2f}",
            f"Gross = net + VAT = {net_amount:,.2f} + {vat:,.2f} = {gross:,.2f}",
        ],
        summary=f"Gross = {gross:,.2f} (VAT {vat:,.2f} at {vat_rate:.2f}%).",
    )


def extract_vat(gross_amount: float, vat_rate: float = 15.0) -> CalculationResult:
    """Extract the VAT component from a gross (VAT-inclusive) amount."""
    require_non_negative("gross_amount", gross_amount)
    net = gross_amount / (1 + vat_rate / 100.0)
    vat = gross_amount - net
    return CalculationResult(
        name="Extract VAT",
        inputs={"gross_amount": gross_amount, "vat_rate": vat_rate},
        outputs={"net_amount": round(net, 2), "vat": round(vat, 2)},
        steps=[
            f"Net = gross / (1 + rate) = {gross_amount:,.2f} / (1 + {vat_rate:.2f}%) = {net:,.2f}",
            f"VAT = gross − net = {gross_amount:,.2f} − {net:,.2f} = {vat:,.2f}",
        ],
        summary=f"Net = {net:,.2f}, VAT = {vat:,.2f} (from gross {gross_amount:,.2f}).",
    )
