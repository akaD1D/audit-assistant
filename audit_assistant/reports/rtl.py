"""Arabic / right-to-left text helpers for report export.

- ``contains_arabic`` detects Arabic script.
- ``shape_for_pdf`` reshapes + bidi-reorders text so fpdf2 (which has no Arabic
  shaping) renders connected, correctly-ordered glyphs.
Word and Excel do their own shaping, so they only need RTL direction flags.
"""

from __future__ import annotations

import re
from pathlib import Path

# Arabic Unicode blocks (base + presentation forms).
_ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")

ARABIC_FONT_PATH = Path(__file__).parent / "fonts" / "Amiri-Regular.ttf"


def contains_arabic(text: str) -> bool:
    return bool(_ARABIC_RE.search(text or ""))


def shape_for_pdf(text: str) -> str:
    """Reshape Arabic letters and apply the bidi algorithm for PDF rendering."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(text))
    except Exception:  # noqa: BLE001 - never fail export over shaping
        return text
