"""Node "Layout Catalog" (deterministic): archetypes per ratio class as pure
data. Each archetype gives every element its own fractional rect (0..1 of the
canvas); the rects are disjoint by construction, so any geometry derived from
them is overlap-free. The same catalog feeds the model's layout choice and the
Adapt Layout expansion — one source of truth."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FracRect:
    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class Archetype:
    name: str
    ratio_class: str
    align: str  # text alignment: "left" | "center"
    elements: dict[str, FracRect] = field(default_factory=dict)


def _a(name: str, cls: str, align: str, **rects: tuple[float, float, float, float]) -> Archetype:
    return Archetype(name, cls, align, {k: FracRect(*v) for k, v in rects.items()})


CATALOG: dict[str, dict[str, Archetype]] = {
    "rectangle": {
        "rect-hero-right": _a(
            "rect-hero-right", "rectangle", "left",
            logo=(0.05, 0.06, 0.30, 0.12),
            title=(0.05, 0.24, 0.45, 0.28),
            subtitle=(0.05, 0.56, 0.45, 0.12),
            cta=(0.05, 0.74, 0.38, 0.15),
            product=(0.55, 0.08, 0.40, 0.84),
        ),
        "rect-hero-left": _a(
            "rect-hero-left", "rectangle", "left",
            product=(0.05, 0.08, 0.40, 0.84),
            logo=(0.52, 0.06, 0.30, 0.12),
            title=(0.52, 0.24, 0.43, 0.28),
            subtitle=(0.52, 0.56, 0.43, 0.12),
            cta=(0.52, 0.74, 0.38, 0.15),
        ),
    },
    "banner": {
        "banner-product-right": _a(
            "banner-product-right", "banner", "left",
            logo=(0.02, 0.20, 0.10, 0.60),
            title=(0.15, 0.08, 0.36, 0.48),
            subtitle=(0.15, 0.60, 0.36, 0.32),
            cta=(0.54, 0.25, 0.16, 0.50),
            product=(0.73, 0.04, 0.25, 0.92),
        ),
        "banner-product-left": _a(
            "banner-product-left", "banner", "left",
            product=(0.02, 0.04, 0.25, 0.92),
            logo=(0.30, 0.20, 0.10, 0.60),
            title=(0.43, 0.08, 0.36, 0.48),
            subtitle=(0.43, 0.60, 0.36, 0.32),
            cta=(0.82, 0.25, 0.16, 0.50),
        ),
    },
    "skyscraper": {
        "sky-product-mid": _a(
            "sky-product-mid", "skyscraper", "center",
            logo=(0.10, 0.03, 0.80, 0.07),
            title=(0.06, 0.13, 0.88, 0.14),
            subtitle=(0.06, 0.29, 0.88, 0.07),
            product=(0.10, 0.39, 0.80, 0.37),
            cta=(0.15, 0.81, 0.70, 0.09),
        ),
        "sky-product-top": _a(
            "sky-product-top", "skyscraper", "center",
            product=(0.10, 0.03, 0.80, 0.34),
            logo=(0.10, 0.41, 0.80, 0.06),
            title=(0.06, 0.50, 0.88, 0.14),
            subtitle=(0.06, 0.66, 0.88, 0.07),
            cta=(0.15, 0.78, 0.70, 0.09),
        ),
    },
}


def archetype_names(ratio_class: str) -> tuple[str, ...]:
    return tuple(CATALOG[ratio_class])


def default_archetype(ratio_class: str) -> Archetype:
    return next(iter(CATALOG[ratio_class].values()))


def get_archetype(ratio_class: str, name: str) -> Archetype:
    """Unknown names fall back to the class default — mechanical enforcement,
    no re-asking the model (the no-rework principle)."""
    return CATALOG[ratio_class].get(name) or default_archetype(ratio_class)
