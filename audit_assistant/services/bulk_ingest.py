"""Helpers for bulk knowledge-base ingestion (used by scripts/ingest_folder.py)."""

from __future__ import annotations

from pathlib import Path


def discover_files(folder: Path, extensions: set[str]) -> list[Path]:
    """Return supported files under ``folder`` (recursive), sorted by name.

    ``extensions`` are lower-case and dotted, e.g. ``{".pdf", ".csv"}``.
    """
    return sorted(
        p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in extensions
    )
