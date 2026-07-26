"""Shared geometry helpers: ratio classification + width-aware text fitting.

Single source of truth used by both pipelines — v0's Pick Layout / Layout
Guard and v1's Size Set / Adapt Layout. Text width is estimated per character
(CJK vs Latin factor), not browser-measured; templates clip overflow.
"""
from __future__ import annotations

MIN_FS = 9.0  # below this a subtitle is dropped, a title is clamped
LINE_HEIGHT = 1.25  # rendered text height ~ font-size * LINE_HEIGHT


def classify(w: float, h: float) -> str:
    """Ratio class: banner (wide & short) / skyscraper (tall & narrow) / rectangle."""
    if w / h >= 3:
        return "banner"
    if h / w >= 1.8:
        return "skyscraper"
    return "rectangle"


def text_units(text: str) -> float:
    """Estimated width of the text in font-size units (CJK wider than Latin)."""
    return sum(1.05 if ord(c) > 0x2E80 else 0.6 for c in text) or 0.6


def fit_text(text: str, w: float, h: float, cap: float | None = None) -> tuple[float, int] | None:
    """Largest font size (and line count, max 2) that fits the box, or None.

    Both line counts are evaluated and the larger font wins: a long title in a
    narrow column reads far better as two big lines than one tiny line.
    Two-line wrap budgets a bit over half the width (wrap points are uneven).
    """
    units = text_units(text)
    limit = cap or 1e9
    one = min(w / units, h / LINE_HEIGHT, limit)
    two = min(w / (units * 0.55), h / (2 * LINE_HEIGHT * 1.04), limit)
    fs, lines = max((one, 1), (two, 2), key=lambda t: t[0])
    if fs >= MIN_FS:
        return fs, lines
    return None


def line_count(text: str, fs: float, w: float) -> int:
    """Lines the text will occupy at a given font size (1 or 2)."""
    return 1 if fs * text_units(text) <= w else 2
