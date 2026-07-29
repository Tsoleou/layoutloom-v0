"""Shared geometry helpers: ratio classification + width-aware text fitting.

Single source of truth used by both pipelines — v0's Pick Layout / Layout
Guard and v1's Size Set / Adapt Layout. Text width is estimated per character
(CJK vs Latin factor), not browser-measured; templates clip overflow.
"""
from __future__ import annotations

MIN_FS = 9.0  # below this a subtitle is dropped, a title is clamped
LINE_HEIGHT = 1.25  # rendered text height ~ font-size * LINE_HEIGHT

# 行頭禁則: characters that may not begin a line (closing/trailing punctuation).
# When a break leaves one at a line start, it is pulled up onto the prior line.
KINSOKU_HEAD = frozenset("。、，．・？！；：」』）】》〉、…ー～")

# Clause-ending punctuation the deterministic segmenter breaks *after* (the mark
# stays on the preceding chunk). ASCII counterparts included for Latin copy.
SEGMENT_AFTER = frozenset("。、，．？！；：…" + ",.?!;:")


def segment_text(text: str) -> list[str]:
    """Split text into phrase chunks at clause-ending punctuation.

    The deterministic fallback for when the model supplies no phrase
    segmentation: breaks *after* a mark in :data:`SEGMENT_AFTER`, keeping the
    mark on its chunk. Text with no such punctuation stays a single chunk (the
    composer char-breaks it only if it can't fit).
    """
    chunks: list[str] = []
    cur = ""
    for ch in text:
        cur += ch
        if ch in SEGMENT_AFTER:
            chunks.append(cur)
            cur = ""
    if cur:
        chunks.append(cur)
    return chunks or [text]


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


def _balanced_two_line_units(text: str) -> float:
    """Width (units) of the longest line in the best balanced two-line split.

    Measures the actual longest composed line — the split point that minimises
    the wider of the two halves — instead of guessing it as a fixed fraction of
    the total, so :func:`fit_text` and the composed render agree.
    """
    if len(text) < 2:
        return text_units(text)
    return min(
        max(text_units(text[:k]), text_units(text[k:]))
        for k in range(1, len(text))
    )


def fit_text(text: str, w: float, h: float, cap: float | None = None) -> tuple[float, int] | None:
    """Largest font size (and line count, max 2) that fits the box, or None.

    Both line counts are evaluated and the larger font wins: a long title in a
    narrow column reads far better as two big lines than one tiny line. The
    two-line branch sizes from the real longest composed line, not a guess.
    """
    units = text_units(text)
    limit = cap or 1e9
    one = min(w / units, h / LINE_HEIGHT, limit)
    two = min(w / _balanced_two_line_units(text), h / (2 * LINE_HEIGHT * 1.04), limit)
    fs, lines = max((one, 1), (two, 2), key=lambda t: t[0])
    if fs >= MIN_FS:
        return fs, lines
    return None


def _break_units(text: str) -> list[str]:
    """Split an overflowing chunk into breakable units at word boundaries: after
    each space and after each hyphen, keeping the delimiter on the unit it ends
    (so a following line never starts with a stray space, and a hyphen stays on
    the leading line). Text with no such boundary stays a single unit — the
    caller then character-breaks it as a last resort."""
    units: list[str] = []
    cur = ""
    for ch in text:
        cur += ch
        if ch in (" ", "-"):
            units.append(cur)
            cur = ""
    if cur:
        units.append(cur)
    return units or [text]


def _char_break(unit: str, fits) -> list[str]:
    """Last resort for a single unit wider than the box: greedily pack it into
    character runs that each satisfy ``fits`` (used only when a word/segment has
    no space or hyphen to break at)."""
    atoms: list[str] = []
    run = ""
    for ch in unit:
        if run and not fits(run + ch):
            atoms.append(run)
            run = ch
        else:
            run += ch
    if run:
        atoms.append(run)
    return atoms


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
        # Overflowing chunk: break at word boundaries first (space / hyphen),
        # falling back to character breaking only for a single unit that alone
        # overflows — so space-delimited copy never splits mid-word.
        for unit in _break_units(chunk):
            if fits(unit):
                atoms.append(unit)
            else:
                atoms.extend(_char_break(unit, fits))
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
    # Trim the whitespace left at word-boundary break points, dropping any line
    # that was whitespace-only.
    return [ln.strip() for ln in _apply_kinsoku(pack(hi)) if ln.strip()]


def _apply_kinsoku(lines: list[str]) -> list[str]:
    """Pull any 行頭禁則 punctuation off a line start onto the prior line's end,
    accepting slight overflow rather than orphaning the mark (追い込み)."""
    for i in range(1, len(lines)):
        while lines[i] and lines[i][0] in KINSOKU_HEAD:
            lines[i - 1] += lines[i][0]
            lines[i] = lines[i][1:]
    return [ln for ln in lines if ln]


def fit_chunks(
    chunks: list[str],
    w: float,
    h: float,
    cap: float | None = None,
    max_lines: int = 2,
) -> tuple[float, list[str]] | None:
    """Largest font size and the composed lines that fit ``w`` x ``h``, or None.

    Sizes from the *actual* composition — ``compose_lines`` respects phrase
    boundaries, so the font is never so large that a chunk must char-break into
    an extra line. Feasibility is monotonic in font size (a bigger font shrinks
    the width budget, so line count and total height only grow), so a bisection
    finds the largest font whose composition stays within ``max_lines`` and
    ``h``. Returns None when even that font is below the readable minimum.
    """
    def feasible(fs: float) -> bool:
        if fs <= 0:
            return True
        lines = compose_lines(chunks, w / fs, max_lines)
        return len(lines) <= max_lines and len(lines) * fs * LINE_HEIGHT <= h + 1e-6

    hi = cap or 1e4
    if feasible(hi):
        fs = hi
    else:
        lo = 0.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if feasible(mid):
                lo = mid
            else:
                hi = mid
        fs = lo
    if fs < MIN_FS:
        return None
    return fs, compose_lines(chunks, w / fs, max_lines)


def line_count(text: str, fs: float, w: float) -> int:
    """Lines the text will occupy at a given font size (1 or 2)."""
    return 1 if fs * text_units(text) <= w else 2
