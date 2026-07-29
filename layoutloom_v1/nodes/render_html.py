"""Node "Render HTML" (deterministic): fixed template — absolute positioning,
@font-face, solid or CSS-gradient background, CTA as a rounded div. The spec
supplies all geometry; the style tokens supply all colour; nothing here is a
judgment call."""
from __future__ import annotations

from layoutloom_v0.nodes.assets_io import ImageAsset
from layoutloom_v0.nodes.planner import asset_uri

from .adapt_layout import BannerSpec, Placed
from .brand_kit import BrandKit
from .campaign_io import ProductLine
from .layout_catalog import Archetype
from .master_design import StyleTokens
from .size_set import Size


def _background_css(bg: dict) -> str:
    if bg.get("type") == "gradient":
        return f"linear-gradient({bg['angle']}deg, {bg['from']}, {bg['to']})"
    return bg["color"]


def _pos(p: Placed) -> str:
    return f"left:{p.x:.0f}px; top:{p.y:.0f}px; width:{p.w:.0f}px; height:{p.h:.0f}px;"


def _inner(p: Placed, fallback: str) -> str:
    """The composed phrase lines as explicit <br> breaks — the geometry already
    fitted these lines, so the browser must not re-wrap them (falls back to the
    raw copy when nothing was composed)."""
    return "<br>".join(p.line_texts) if p.line_texts else fallback


def render_html(
    spec: BannerSpec,
    arch: Archetype,
    style: StyleTokens,
    line: ProductLine,
    size: Size,
    product: ImageAsset,
    brand: BrandKit,
    asset_base_url: str | None = None,
) -> str:
    font_face = (
        f'@font-face {{ font-family: "{brand.font.family}"; '
        f'src: url("{asset_uri(brand.font.path, asset_base_url)}"); font-weight: 100 900; }}'
        if brand.font.path
        else ""
    )
    title = spec["title"]
    parts = [
        f'<img class="el" src="{asset_uri(brand.logo.path, asset_base_url)}" '
        f'style="{_pos(spec["logo"])}">',
        f'<img class="el" src="{asset_uri(product.path, asset_base_url)}" '
        f'style="{_pos(spec["product"])}">',
        f'<h1 class="el txt" style="{_pos(title)} font-size:{title.fs:.0f}px; '
        f'color:{style.title_color};">{_inner(title, line.title)}</h1>',
    ]
    if "subtitle" in spec:
        sub = spec["subtitle"]
        parts.append(
            f'<p class="el txt" style="{_pos(sub)} font-size:{sub.fs:.0f}px; '
            f'color:{style.subtitle_color};">{_inner(sub, line.subtitle)}</p>'
        )
    cta = spec["cta"]
    parts.append(
        f'<div class="el cta" style="{_pos(cta)} font-size:{cta.fs:.0f}px; '
        f'line-height:{cta.h:.0f}px; background:{style.cta_bg}; '
        f'color:{style.cta_text_color};">{line.cta}</div>'
    )
    body = "\n".join(parts)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
{font_face}
body {{ margin: 0; }}
.banner {{ position: relative; width: {size.width}px; height: {size.height}px;
           background: {_background_css(style.background)}; overflow: hidden;
           font-family: "{brand.font.family}", sans-serif; }}
.el {{ position: absolute; margin: 0; }}
.txt {{ text-align: {arch.align}; line-height: 1.25; overflow: hidden; }}
.cta {{ text-align: center; border-radius: {brand.cta_radius_px}px; font-weight: 700; }}
</style></head><body><div class="banner">
{body}
</div></body></html>"""
