"""Prompts for vision-based understanding of audit evidence images."""

from __future__ import annotations

VISION_SYSTEM = (
    "You are an audit evidence extraction assistant. You read images of invoices, "
    "receipts, financial statements, contracts, and screenshots, and transcribe them "
    "faithfully for an auditor. Reproduce every number EXACTLY as shown — never round, "
    "estimate, or invent figures. If something is illegible, write [illegible]."
)

# Faithful transcription + light analysis, used at ingestion so the content
# becomes searchable and answerable through RAG like any other document.
VISION_TRANSCRIBE_PROMPT = """Transcribe this document image for an audit file. Produce \
Markdown with these sections (omit a section only if truly not present):

## Document type
(invoice / receipt / financial statement / contract / other)

## Key parties
Vendor/supplier, customer, and any identifiers (tax ID, registration no.).

## Dates & references
Invoice/document number, issue date, due date, PO number, etc.

## Line items
A Markdown table of line items with quantities, unit prices, and amounts if present.

## Totals
Subtotal, tax/VAT (with rate), discounts, and grand total — exactly as shown.

## Full text
A faithful transcription of all remaining visible text.

## Potential issues
Bullet any missing mandatory fields (e.g. no tax ID, no date), arithmetic that does \
not add up, or internal inconsistencies you can see. If none are apparent, write "None \
apparent from the image."
"""
