"""Node "LLM Master Design" (model): the pipeline's only model touchpoint.

One call for the whole campaign: the model sees every product line's copy
lengths, product image aspect ratios, the brand constraints, the size classes
and the archetype catalog, then commits — per product line — to a layout per
ratio class plus style tokens. It emits no pixel geometry and no HTML.

Everything around the call is deterministic and unit-testable: build_prompt
and parse_master_design are pure functions. Parsing enforces the brand
constraints mechanically (snap off-palette colours, fix low-contrast text,
fall back on unknown archetype names) and records every correction in notes —
the model is never re-asked (the no-rework principle).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol

import requests

from layoutloom_v0.nodes.assets_io import ImageAsset

from ..config import ModelConfig
from .brand_kit import BrandKit
from .campaign_io import Campaign
from .layout_catalog import CATALOG, archetype_names, default_archetype
from .size_set import RATIO_CLASSES, Size


@dataclass(frozen=True)
class StyleTokens:
    background: dict  # {"type":"solid","color":..} | {"type":"gradient","from":..,"to":..,"angle":..}
    title_color: str
    subtitle_color: str
    cta_bg: str
    cta_text_color: str
    type_scale: float = 1.0


@dataclass(frozen=True)
class ProductDesign:
    name: str
    layouts: dict[str, str]  # ratio class -> archetype name
    style: StyleTokens
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class MasterDesign:
    products: dict[str, ProductDesign] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


class MasterDesigner(Protocol):
    def design(
        self,
        campaign: Campaign,
        assets: dict[str, ImageAsset],
        brand: BrandKit,
        sizes: tuple[Size, ...],
    ) -> MasterDesign: ...


# --- colour helpers (pure) ---


def _rgb(hex_color: str) -> tuple[int, int, int]:
    s = hex_color.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def snap_to_palette(color: str, palette: tuple[str, ...]) -> str:
    """Nearest palette colour by RGB distance; invalid input -> first colour."""
    try:
        r, g, b = _rgb(color)
    except (ValueError, IndexError):
        return palette[0]
    return min(palette, key=lambda p: sum((a - c) ** 2 for a, c in zip(_rgb(p), (r, g, b))))


def _mix(c1: str, c2: str, t: float) -> str:
    """Linear RGB blend: t=0 -> c1, t=1 -> c2."""
    a, b = _rgb(c1), _rgb(c2)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def _luminance(color: str) -> float:
    def chan(v: int) -> float:
        v_ = v / 255
        return v_ / 12.92 if v_ <= 0.03928 else ((v_ + 0.055) / 1.055) ** 2.4

    r, g, b = _rgb(color)
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast(c1: str, c2: str) -> float:
    l1, l2 = sorted((_luminance(c1), _luminance(c2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


# --- prompt (pure) ---


def build_prompt(
    campaign: Campaign,
    assets: dict[str, ImageAsset],
    brand: BrandKit,
    sizes: tuple[Size, ...],
) -> str:
    classes_used = sorted({s.ratio_class for s in sizes})
    size_lines = "\n".join(
        f"  - {s.name} ({s.ratio_class})" for s in sizes
    )
    catalog_lines = "\n".join(
        f"  - {cls}: {', '.join(archetype_names(cls))}" for cls in classes_used
    )
    product_lines = []
    for p in campaign.products:
        a = assets[p.name]
        product_lines.append(
            f'  - name "{p.name}": title "{p.title}" ({len(p.title)} chars), '
            f'subtitle "{p.subtitle}" ({len(p.subtitle)} chars), CTA "{p.cta}", '
            f"product image aspect ratio {a.width}:{a.height}"
        )
    products = "\n".join(product_lines)
    layouts_example = ", ".join(f'"{c}": "<archetype>"' for c in classes_used)
    return f"""You are the art director for a GDN display-ad campaign. Decide the design
system ONCE for the whole campaign — every product line, every size class.
Deterministic code will expand your decisions into exact geometry and HTML;
nothing is revisited later, so weigh everything now (copy lengths vs layout
capacity, product image aspect ratios vs product regions, palette contrast).

Brand palette (you may ONLY use these colours): {", ".join(brand.palette)}
CTA corner radius: {brand.cta_radius_px}px (fixed).

Sizes to cover:
{size_lines}

Available layout archetypes per size class (choose from these names only):
{catalog_lines}

Product lines:
{products}

Respond with ONLY a JSON object:
{{"products": [
  {{"name": "<product name>",
    "layouts": {{{layouts_example}}},
    "style": {{
      "background": {{"type": "solid", "color": "<palette>"}}
                    or {{"type": "gradient", "from": "<palette>", "to": "<palette>", "angle": 135}},
      "title_color": "<palette>", "subtitle_color": "<palette>",
      "cta": {{"bg": "<palette>", "text_color": "<palette>"}},
      "type_scale": 1.0
    }}}}
]}}

Rules: text colours must contrast strongly with the background; the CTA must
stand out; long titles prefer layouts with wide text regions; tall product
images prefer layouts with tall product regions; keep the campaign visually
coherent across product lines (same background treatment family) while giving
each line its own accent. type_scale between 0.9 and 1.2."""


# --- parsing + mechanical constraint enforcement (pure) ---


def parse_master_design(
    text: str, campaign: Campaign, brand: BrandKit
) -> MasterDesign:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("model response contains no JSON object")
    data = json.loads(text[start : end + 1])
    raw_products = data.get("products")
    if not isinstance(raw_products, list):
        raise ValueError("model response missing 'products' list")

    by_name = {str(p.get("name", "")): p for p in raw_products if isinstance(p, dict)}
    products: dict[str, ProductDesign] = {}
    global_notes: list[str] = []

    for line in campaign.products:
        raw = by_name.get(line.name)
        notes: list[str] = []
        if raw is None:
            notes.append("missing from model output; using defaults")
            raw = {}

        layouts: dict[str, str] = {}
        raw_layouts = raw.get("layouts") if isinstance(raw.get("layouts"), dict) else {}
        for cls in RATIO_CLASSES:
            choice = str(raw_layouts.get(cls, ""))
            if choice not in CATALOG[cls]:
                if choice:
                    notes.append(f"unknown {cls} layout {choice!r}; using default")
                choice = default_archetype(cls).name
            layouts[cls] = choice

        style = _parse_style(raw.get("style"), brand, notes)
        products[line.name] = ProductDesign(
            name=line.name, layouts=layouts, style=style, notes=tuple(notes)
        )

    for name in by_name:
        if name and name not in products:
            global_notes.append(f"model invented product {name!r}; ignored")
    return MasterDesign(products=products, notes=tuple(global_notes))


def _parse_style(raw: object, brand: BrandKit, notes: list[str]) -> StyleTokens:
    raw = raw if isinstance(raw, dict) else {}
    pal = brand.palette

    def snap(key: str, value: object, fallback: str) -> str:
        v = str(value) if value else fallback
        snapped = snap_to_palette(v, pal)
        if snapped.lower() != v.lower():
            notes.append(f"{key} {v!r} off-palette; snapped to {snapped}")
        return snapped

    bg_raw = raw.get("background") if isinstance(raw.get("background"), dict) else {}
    if bg_raw.get("type") == "gradient":
        background = {
            "type": "gradient",
            "from": snap("background.from", bg_raw.get("from"), pal[0]),
            "to": snap("background.to", bg_raw.get("to"), pal[-1]),
            "angle": int(bg_raw.get("angle") or 135),
        }
        # Text must stay readable across the whole gradient, so contrast is
        # checked against BOTH endpoints. If the gradient spans dark->light so
        # widely that NO palette colour can read on both ends, fix the
        # background rather than muddying the text: pull the far end toward
        # the near end (a designer's move — keep the gradient, shrink its
        # luminance span).
        if not any(
            min(contrast(p, background["from"]), contrast(p, background["to"])) >= 3.0
            for p in pal
        ):
            softened = _mix(background["from"], background["to"], 0.35)
            notes.append(
                f"gradient {background['from']}->{background['to']} defeats every "
                f"palette colour; softened far end to {softened}"
            )
            background["to"] = softened
        bg_refs = (background["from"], background["to"])
    else:
        background = {"type": "solid", "color": snap("background.color", bg_raw.get("color"), pal[-1])}
        bg_refs = (background["color"],)

    def contrasting(key: str, value: object, fallback: str) -> str:
        c = snap(key, value, fallback)
        if min(contrast(c, b) for b in bg_refs) < 3.0:
            best = max(pal, key=lambda p: min(contrast(p, b) for b in bg_refs))
            notes.append(f"{key} {c} low contrast on {'/'.join(bg_refs)}; snapped to {best}")
            return best
        return c

    cta_raw = raw.get("cta") if isinstance(raw.get("cta"), dict) else {}
    cta_bg = contrasting("cta.bg", cta_raw.get("bg"), pal[0])
    try:
        type_scale = min(max(float(raw.get("type_scale") or 1.0), 0.9), 1.2)
    except (TypeError, ValueError):
        type_scale = 1.0

    return StyleTokens(
        background=background,
        title_color=contrasting("title_color", raw.get("title_color"), pal[0]),
        subtitle_color=contrasting("subtitle_color", raw.get("subtitle_color"), pal[0]),
        cta_bg=cta_bg,
        cta_text_color=(
            lambda c: c if contrast(c, cta_bg) >= 3.0 else max(pal, key=lambda p: contrast(p, cta_bg))
        )(snap("cta.text_color", cta_raw.get("text_color"), pal[-1])),
        type_scale=type_scale,
    )


# --- implementations ---


class OllamaMasterDesigner:
    def __init__(self, cfg: ModelConfig) -> None:
        self.cfg = cfg

    def design(
        self,
        campaign: Campaign,
        assets: dict[str, ImageAsset],
        brand: BrandKit,
        sizes: tuple[Size, ...],
    ) -> MasterDesign:
        payload: dict = {
            "model": self.cfg.model,
            "prompt": build_prompt(campaign, assets, brand, sizes),
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.cfg.temperature,
                "num_predict": self.cfg.max_tokens,
            },
        }
        if self.cfg.reasoning_effort is not None:
            payload["think"] = self.cfg.reasoning_effort
        resp = requests.post(f"{self.cfg.base_url}/api/generate", json=payload, timeout=300)
        resp.raise_for_status()
        return parse_master_design(resp.json()["response"], campaign, brand)


class StubMasterDesigner:
    """Deterministic reference designer: class-default layouts, fixed palette
    assignment. Keeps the whole pipeline runnable offline."""

    def design(
        self,
        campaign: Campaign,
        assets: dict[str, ImageAsset],
        brand: BrandKit,
        sizes: tuple[Size, ...],
    ) -> MasterDesign:
        pal = brand.palette
        products = {}
        for line in campaign.products:
            style = StyleTokens(
                background={"type": "solid", "color": pal[-1]},
                title_color=pal[0],
                subtitle_color=snap_to_palette("#111111", pal),
                cta_bg=pal[0],
                cta_text_color=pal[-1],
                type_scale=1.0,
            )
            products[line.name] = ProductDesign(
                name=line.name,
                layouts={cls: default_archetype(cls).name for cls in RATIO_CLASSES},
                style=style,
            )
        return MasterDesign(products=products)
