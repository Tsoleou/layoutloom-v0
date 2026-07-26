"""Node "Pick Layout" (deterministic): choose a layout archetype and resolve it
into pixel regions for this canvas.

Layout diversity lives here and only here. An archetype is data — two disjoint
regions (TEXT holds logo/title/subtitle stacked vertically, PRODUCT holds the
product image) plus typography ranges. Downstream, the model node receives the
resolved regions in its prompt and the Layout Guard clamps the plan into the
same regions, so every archetype gets the same geometric guarantees.

The canvas's ratio class (banner / skyscraper / rectangle) restricts which
archetypes make structural sense: side-by-side columns need width, stacked
bands need height. Margins/gutters scale with the canvas (fixed 40px would
swallow a 90px-tall leaderboard), and font ranges are width-fitted downstream.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .assets_io import ImageAsset
from .canvas import Canvas
from .fitting import LINE_HEIGHT, classify, fit_text


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h


@dataclass(frozen=True)
class Layout:
    name: str
    text: Rect  # holds logo -> title -> subtitle, stacked top to bottom
    product: Rect  # holds only the product image
    align: str  # "left" | "center" — presentation of the text stack
    title_fs: tuple[int, int]  # (min, max) font_size_px
    subtitle_fs: tuple[int, int]
    logo_max_w: int


ARCHETYPES = ("text-left", "text-right", "text-top")

# which archetypes are structurally sound per canvas ratio class
CLASS_ARCHETYPES: dict[str, tuple[str, ...]] = {
    "rectangle": ("text-left", "text-right", "text-top"),
    "banner": ("text-left", "text-right"),  # side-by-side suits wide & short
    "skyscraper": ("text-top",),  # stacked bands suit tall & narrow
}


def _metrics(canvas: Canvas) -> tuple[float, float]:
    """(margin, gutter) proportional to the canvas — capped at the classic 40/20."""
    m = min(max(min(canvas.width, canvas.height) * 0.08, 8.0), 40.0)
    return m, max(m / 2, 6.0)


def _resolve(name: str, canvas: Canvas) -> Layout:
    w, h = canvas.width, canvas.height
    m, g = _metrics(canvas)
    cls = classify(w, h)
    col = w / 2 - g - m  # width of one column in the two-column archetypes
    if cls == "banner":
        # short canvas: tighter type ranges, discreet logo
        title_fs = (h // 4, h // 3)
        subtitle_fs = (h // 8, h // 6)
        logo_max = int(min(220, w / 8))
    else:
        title_fs = (h // 8, h // 6)
        subtitle_fs = (h // 18, h // 14)
        logo_max = 220
    if name == "text-left":
        return Layout(
            name,
            text=Rect(m, m, col, h - 2 * m),
            product=Rect(w / 2 + g, m, col, h - 2 * m),
            align="left",
            title_fs=title_fs,
            subtitle_fs=subtitle_fs,
            logo_max_w=logo_max,
        )
    if name == "text-right":
        return Layout(
            name,
            text=Rect(w / 2 + g, m, col, h - 2 * m),
            product=Rect(m, m, col, h - 2 * m),
            align="left",
            title_fs=title_fs,
            subtitle_fs=subtitle_fs,
            logo_max_w=logo_max,
        )
    if name == "text-top":
        band = h / 2 - g - m  # height of one band
        return Layout(
            name,
            text=Rect(m, m, w - 2 * m, band),
            product=Rect(m, h / 2 + g, w - 2 * m, band),
            align="center",
            title_fs=(h // 12, h // 9),
            subtitle_fs=(h // 22, h // 16),
            logo_max_w=min(160, logo_max),
        )
    raise ValueError(f"unknown layout {name!r}; use one of {ARCHETYPES} or 'random'")


def pick_layout(name: str, canvas: Canvas) -> Layout:
    cls = classify(canvas.width, canvas.height)
    suitable = CLASS_ARCHETYPES[cls]
    if name == "random":
        name = random.choice(suitable)
    elif name in ARCHETYPES and name not in suitable:
        coerced = suitable[0]
        print(f"[pick-layout] {name} unsuitable for {cls} canvas; using {coerced}")
        name = coerced
    return _resolve(name, canvas)


def reference_spec(
    layout: Layout,
    product: ImageAsset,
    logo: ImageAsset,
    title: str | None = None,
    subtitle: str | None = None,
) -> dict:
    """A well-composed spec for this archetype — the prompt's worked example and
    the stub planner's fixed layout. Width-fits the actual copy when given, so
    it stays geometry-valid at any canvas size; a subtitle that cannot reach
    the minimum font size is omitted."""
    t, p = layout.text, layout.product
    gap = min(max(t.h * 0.08, 6.0), 40.0)

    logo_w = min(180, layout.logo_max_w, t.w, 0.28 * t.h * logo.width / logo.height)
    logo_h = logo_w * logo.height / logo.width

    title_budget_h = t.h - logo_h - gap
    title_fs = sum(layout.title_fs) // 2
    title_lines = 1
    if title:
        fitted = fit_text(title, t.w, max(title_budget_h * 0.6, 1), cap=title_fs)
        title_fs, title_lines = fitted if fitted else (9, 2)
    title_h = title_lines * title_fs * LINE_HEIGHT

    ratio = product.height / product.width
    prod_w = min(p.w, p.h / ratio)

    def x_for(width: float) -> float:
        return t.x if layout.align == "left" else t.x + (t.w - width) / 2

    title_y = t.y + logo_h + gap
    spec = {
        "logo": {
            "x": round(x_for(logo_w)),
            "y": round(t.y),
            "width": round(logo_w),
            "height": round(logo_h),
        },
        "product": {
            "x": round(p.x + (p.w - prod_w) / 2),
            "y": round(p.y + (p.h - prod_w * ratio) / 2),
            "width": round(prod_w),
            "height": round(prod_w * ratio),
        },
        "title": {
            "x": round(t.x),
            "y": round(title_y),
            "width": round(t.w),
            "height": round(title_h),
            "font_size_px": round(title_fs),
        },
    }

    subtitle_fs = sum(layout.subtitle_fs) // 2
    subtitle_y = title_y + title_h + gap / 2
    subtitle_budget_h = t.bottom - subtitle_y
    fitted = (
        fit_text(subtitle, t.w, max(subtitle_budget_h, 1), cap=min(subtitle_fs, title_fs * 0.75))
        if subtitle
        else ((subtitle_fs, 1) if subtitle_budget_h >= subtitle_fs * LINE_HEIGHT else None)
    )
    if fitted:
        fs, lines = fitted
        spec["subtitle"] = {
            "x": round(t.x),
            "y": round(subtitle_y),
            "width": round(t.w),
            "height": round(lines * fs * LINE_HEIGHT),
            "font_size_px": round(fs),
        }
    return spec
