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


def compose_lines(chunks: list[str], max_units: float, max_lines: int = 2) -> list[str]:
    """Compose phrase chunks into balanced lines, each within ``max_units``
    (font-size units, per :func:`text_units`), never splitting a chunk unless
    it alone overflows. Fill-first: if everything fits on one line, keep it.
    """
    def fits(s: str) -> bool:  # tolerate float drift when a budget lands on a char boundary
        return text_units(s) <= max_units + 1e-6

    joined = "".join(chunks)
    if fits(joined):
        return [joined]
    atoms: list[str] = []
    for chunk in chunks:
        if fits(chunk):
            atoms.append(chunk)
            continue
        # No boundary to break at: fall back to greedy character breaking.
        run = ""
        for ch in chunk:
            if run and not fits(run + ch):
                atoms.append(run)
                run = ch
            else:
                run += ch
        if run:
            atoms.append(run)
    def pack(cap: float) -> list[str]:  # greedy fill with a per-line width cap
        lines: list[str] = []
        cur = ""
        for atom in atoms:
            if cur and text_units(cur + atom) > cap + 1e-6:
                lines.append(cur)
                cur = atom
            else:
                cur += atom
        if cur:
            lines.append(cur)
        return lines

    # Keep the minimum line count, then shrink the width cap as far as it can go
    # without needing another line — this balances the lines instead of leaving
    # a full first line and an orphaned tail.
    target = len(pack(max_units))
    lo = max((text_units(a) for a in atoms), default=0.0)
    hi = max_units
    for _ in range(50):
        mid = (lo + hi) / 2
        if len(pack(mid)) <= target:
            hi = mid
        else:
            lo = mid
    return pack(hi)


def line_count(text: str, fs: float, w: float) -> int:
    """Lines the text will occupy at a given font size (1 or 2)."""
    return 1 if fs * text_units(text) <= w else 2
