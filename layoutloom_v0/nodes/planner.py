"""Node "LLM Banner Plan" (model): the pipeline's only model touchpoint.

The contract says this node takes canvas + assets + title/subtitle and emits
a layout Spec plus renderable HTML. Everything around the call is
deterministic and unit-testable: prompt building and response parsing are
pure functions; the network call lives in OllamaBannerPlanner; StubBannerPlanner
is the offline reference implementation for tests.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import requests

from ..config import ModelConfig
from .assets_io import FontAsset, ImageAsset
from .canvas import Canvas
from .fitting import segment_text
from .layout_pick import Layout, reference_spec


@dataclass(frozen=True)
class BannerPlan:
    spec: dict
    html: str
    # phrase segmentation per text field (title/subtitle) — the composer's input
    chunks: dict[str, list[str]] = field(default_factory=dict)


def asset_uri(path: Path, base_url: str | None) -> str:
    """URL for an asset file referenced by the emitted HTML.

    With base_url set, an HTTP URL under that origin (so the banner is viewable
    over HTTP — e.g. the web preview iframe, where file:// refs would be blocked).
    Otherwise a file:// URI, which loads from disk for the offline CLI/Playwright
    paths. The relative asset path becomes the URL path, matching the API's
    /assets and /fonts static mounts.
    """
    if base_url:
        return f"{base_url.rstrip('/')}/{path.as_posix()}"
    return path.resolve().as_uri()


class BannerPlanner(Protocol):
    def plan(
        self,
        canvas: Canvas,
        product: ImageAsset,
        logo: ImageAsset,
        font: FontAsset,
        title: str,
        subtitle: str,
        layout: Layout,
    ) -> BannerPlan: ...


def build_prompt(
    canvas: Canvas,
    product: ImageAsset,
    logo: ImageAsset,
    font: FontAsset,
    title: str,
    subtitle: str,
    layout: Layout,
    asset_base_url: str | None = None,
) -> str:
    font_face = (
        f'@font-face {{ font-family: "{font.family}"; '
        f'src: url("{asset_uri(font.path, asset_base_url)}"); font-weight: 100 900; }}'
        if font.path
        else "(no font file; use a sans-serif stack)"
    )
    t, p = layout.text, layout.product
    ratio = product.height / product.width
    max_prod_w = round(min(p.w, p.h / ratio))
    align_desc = (
        f"to the shared left edge x = {round(t.x)}"
        if layout.align == "left"
        else "centered horizontally inside the TEXT region (text-align: center)"
    )
    example = json.dumps(reference_spec(layout, product, logo, title, subtitle), indent=2)
    chunks_example = json.dumps(
        {"title": segment_text(title), "subtitle": segment_text(subtitle)},
        ensure_ascii=False,
    )
    return f"""You are a banner layout designer. Design a single static banner.

Canvas: {canvas.width}x{canvas.height}px, background {canvas.background}.
Product image: "{asset_uri(product.path, asset_base_url)}" ({product.width}x{product.height}px).
Logo: "{asset_uri(logo.path, asset_base_url)}" ({logo.width}x{logo.height}px).
Font: family "{font.family}". In the HTML <style>, include: {font_face}
Title: {title}
Subtitle: {subtitle}

Respond with ONLY a JSON object, no markdown fences, with exactly three keys:
  "spec": an object describing each element's size, position and font size
          (keys: product, logo, title, subtitle; values: objects with x, y,
          width, height, and font_size_px for text; a text box's height is
          roughly its font_size_px),
  "chunks": phrase segmentation for the title and subtitle — each split into a
          list of atomic semantic chunks that must never be broken across
          lines, keeping any punctuation on the chunk it ends. Segment by
          meaning, not width; code composes the lines. For this copy:
          {chunks_example}
  "html": a complete self-contained HTML document that renders the banner
          exactly per the spec. It MUST follow exactly this structure — same
          tags, same classes, one absolutely-positioned element each, inline
          left/top/width/font-size taken from the spec. Only substitute the
          UPPERCASE placeholders and the colours; do not add other elements,
          never use <title> in the body, no flexbox, and set only width (not
          height) on <img> so the browser preserves the aspect ratio:

<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
{font_face if font.path else ""}
body {{ margin: 0; }}
.banner {{ position: relative; width: {canvas.width}px; height: {canvas.height}px;
           background: {canvas.background}; overflow: hidden;
           font-family: "{font.family}", sans-serif; }}
.el {{ position: absolute; margin: 0; }}
</style></head><body><div class="banner">
<img class="el" src="LOGO_URL" style="left:Xpx; top:Ypx; width:Wpx;">
<img class="el" src="PRODUCT_URL" style="left:Xpx; top:Ypx; width:Wpx;">
<h1 class="el" style="left:Xpx; top:Ypx; width:Wpx; font-size:Npx; color:TITLE_COLOUR; text-align:{layout.align};">TITLE</h1>
<p class="el" style="left:Xpx; top:Ypx; width:Wpx; font-size:Npx; color:SUBTITLE_COLOUR; text-align:{layout.align};">SUBTITLE</p>
</div></body></html>

Layout rules (hard constraints):
- Every element stays fully inside the canvas: x >= 0, y >= 0,
  x + width <= {canvas.width}, and y + height <= {canvas.height}.
- NO TWO ELEMENTS MAY OVERLAP. Treat each element as its bounding box
  (x, y, width, height) and keep all four boxes disjoint.
- This banner uses the "{layout.name}" layout: two separate regions, and no
  element may cross its region's edges:
  * TEXT region (x {round(t.x)} to {round(t.right)}, y {round(t.y)} to {round(t.bottom)})
    holds the logo, title and subtitle, stacked top to bottom in that order
    with >= 24px vertical gaps.
  * PRODUCT region (x {round(p.x)} to {round(p.right)}, y {round(p.y)} to {round(p.bottom)})
    holds ONLY the product image.

Design rules (make it look professionally composed):
- Align the logo, title and subtitle {align_desc}.
- Typography scale: title font_size_px about 2x the subtitle's, title between
  {layout.title_fs[0]} and {layout.title_fs[1]}, subtitle between
  {layout.subtitle_fs[0]} and {layout.subtitle_fs[1]}. Text colour must contrast
  strongly with the background; you may use one accent colour on the title.
- Vertical rhythm: logo near the top of the TEXT region, generous whitespace —
  do not fill every gap.
- Product image: the browser renders its height as width x {product.height}/{product.width}
  (aspect ratio preserved automatically). Its width MUST be at most {max_prod_w}px;
  center it inside the PRODUCT region.
- Text needs breathing room: the subtitle's top must be at least
  title_top + title_font_size x 1.6, and the title's top at least
  logo_top + logo_rendered_height + 40 (logo rendered height = logo width x
  {logo.height}/{logo.width}).
- Logo: keep it small and discreet (width <= {layout.logo_max_w}px).

Example of a valid, well-composed spec for the "{layout.name}" layout on this
{canvas.width}x{canvas.height} canvas (keep this structure; adjust sizes to
the text and image):
{example}"""


def parse_plan_response(text: str) -> BannerPlan:
    """Extract the {spec, html} object from a model response.

    Tolerates markdown fences and leading/trailing prose by slicing to the
    outermost braces before parsing.
    """
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("model response contains no JSON object")
    data = json.loads(text[start : end + 1])
    spec, html = data.get("spec"), data.get("html")
    if not isinstance(spec, dict) or not isinstance(html, str) or not html.strip():
        raise ValueError("model response missing 'spec' object or 'html' string")
    # Optional phrase segmentation. Keep only well-formed {field: [str, ...]}
    # entries; anything malformed is ignored so the guard falls back per field.
    raw = data.get("chunks")
    chunks: dict[str, list[str]] = {}
    if isinstance(raw, dict):
        for field_name, parts in raw.items():
            if isinstance(parts, list) and all(isinstance(p, str) for p in parts) and parts:
                chunks[field_name] = parts
    return BannerPlan(spec=spec, html=html, chunks=chunks)


class OllamaBannerPlanner:
    def __init__(self, cfg: ModelConfig, asset_base_url: str | None = None) -> None:
        self.cfg = cfg
        self.asset_base_url = asset_base_url

    def plan(
        self,
        canvas: Canvas,
        product: ImageAsset,
        logo: ImageAsset,
        font: FontAsset,
        title: str,
        subtitle: str,
        layout: Layout,
    ) -> BannerPlan:
        prompt = build_prompt(
            canvas, product, logo, font, title, subtitle, layout, self.asset_base_url
        )
        payload: dict = {
            "model": self.cfg.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.cfg.temperature,
                "num_predict": self.cfg.max_tokens,
            },
        }
        # Cap reasoning effort for thinking models; omit entirely for models
        # that don't support it (they reject the field).
        if self.cfg.reasoning_effort is not None:
            payload["think"] = self.cfg.reasoning_effort
        resp = requests.post(f"{self.cfg.base_url}/api/generate", json=payload, timeout=300)
        resp.raise_for_status()
        return parse_plan_response(resp.json()["response"])


class StubBannerPlanner:
    """Deterministic reference planner: the archetype's reference_spec, no model."""

    def __init__(self, asset_base_url: str | None = None) -> None:
        self.asset_base_url = asset_base_url

    def plan(
        self,
        canvas: Canvas,
        product: ImageAsset,
        logo: ImageAsset,
        font: FontAsset,
        title: str,
        subtitle: str,
        layout: Layout,
    ) -> BannerPlan:
        base = self.asset_base_url
        spec = reference_spec(layout, product, logo, title, subtitle)
        font_face = (
            f'@font-face {{ font-family: "{font.family}"; '
            f'src: url("{asset_uri(font.path, base)}"); font-weight: 100 900; }}'
            if font.path
            else ""
        )

        def pos(name: str) -> str:
            e = spec[name]
            return f"left:{e['x']}px; top:{e['y']}px; width:{e['width']}px;"

        def txt(name: str) -> str:
            return f"{pos(name)} font-size:{spec[name]['font_size_px']}px; text-align:{layout.align};"

        subtitle_el = (
            f'\n<p class="el" style="{txt("subtitle")}">{subtitle}</p>' if "subtitle" in spec else ""
        )
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
{font_face}
body {{ margin: 0; }}
.banner {{ position: relative; width: {canvas.width}px; height: {canvas.height}px;
           background: {canvas.background}; overflow: hidden;
           font-family: "{font.family}", sans-serif; }}
.el {{ position: absolute; margin: 0; }}
</style></head><body><div class="banner">
<img class="el" src="{asset_uri(logo.path, base)}" style="{pos('logo')}">
<img class="el" src="{asset_uri(product.path, base)}" style="{pos('product')}">
<h1 class="el" style="{txt('title')}">{title}</h1>{subtitle_el}
</div></body></html>"""
        chunks = {"title": segment_text(title)}
        if "subtitle" in spec:
            chunks["subtitle"] = segment_text(subtitle)
        return BannerPlan(spec=spec, html=html, chunks=chunks)
