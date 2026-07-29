"""Node "Adapt Layout" (deterministic): mechanically expand the master design
to one (product line x size). Takes the chosen archetype's fractional rects,
fits each element's content inside its own rect (font shrink-to-fit with a
2-line budget, aspect-preserving image fit, CTA pill sizing) and emits exact
pixel geometry. Overlap-freedom is inherited from the catalog's disjoint
rects; a subtitle that cannot reach the minimum font size is omitted rather
than squeezed (the small-leaderboard reality).

Text width is estimated per character (CJK vs Latin factor), not measured in
a browser — an accepted approximation; the HTML template clips overflow.
"""
from __future__ import annotations

from dataclasses import dataclass

from layoutloom_v0.nodes.assets_io import ImageAsset
from layoutloom_v0.nodes.fitting import (
    MIN_FS,
    compose_lines,
    fit_chunks,
    segment_text,
    text_units,
)

from .brand_kit import BrandKit
from .campaign_io import ProductLine
from .layout_catalog import Archetype, FracRect, get_archetype
from .master_design import ProductDesign
from .size_set import Size

CTA_PAD_FACTOR = 1.2  # horizontal padding as a multiple of font size


@dataclass(frozen=True)
class Placed:
    x: float
    y: float
    w: float
    h: float
    fs: float | None = None  # font size for text elements
    lines: int = 1
    line_texts: tuple[str, ...] = ()  # composed <br> lines for text elements


BannerSpec = dict[str, Placed]  # element -> geometry; subtitle may be absent


def _px(r: FracRect, size: Size) -> tuple[float, float, float, float]:
    return r.x * size.width, r.y * size.height, r.w * size.width, r.h * size.height


def _fit_image(asset: ImageAsset, x: float, y: float, w: float, h: float) -> Placed:
    ratio = asset.height / asset.width
    fw = min(w, h / ratio)
    fh = fw * ratio
    return Placed(x + (w - fw) / 2, y + (h - fh) / 2, fw, fh)


def adapt_layout(
    design: ProductDesign,
    line: ProductLine,
    size: Size,
    product: ImageAsset,
    brand: BrandKit,
) -> tuple[BannerSpec, Archetype]:
    arch = get_archetype(size.ratio_class, design.layouts[size.ratio_class])
    spec: BannerSpec = {}

    def chunks_of(el: str, text: str) -> list[str]:
        # model phrase segmentation, else the deterministic fallback segmenter
        return design.chunks.get(el) or segment_text(text or "字")

    # images: aspect-preserving fit, centred in their rects
    spec["product"] = _fit_image(product, *_px(arch.elements["product"], size))
    spec["logo"] = _fit_image(brand.logo, *_px(arch.elements["logo"], size))

    # title: never dropped; clamp to MIN_FS if the composition says tight. Fit
    # from the phrase chunks so the font never assumes a break the composer
    # can't make (chunk-aware, mirroring v0's Layout Guard).
    tx, ty, tw, th = _px(arch.elements["title"], size)
    cap = size.height * 0.5 * design.style.type_scale
    t_chunks = chunks_of("title", line.title)
    fitted = fit_chunks(t_chunks, tw, th, cap=cap)
    if fitted:
        fs, t_lines = fitted
    else:
        fs, t_lines = MIN_FS, compose_lines(t_chunks, tw / MIN_FS)
    spec["title"] = Placed(tx, ty, tw, th, fs=fs, lines=len(t_lines), line_texts=tuple(t_lines))

    # subtitle: dropped when it cannot reach the minimum font size
    if line.subtitle and "subtitle" in arch.elements:
        sx, sy, sw, sh = _px(arch.elements["subtitle"], size)
        fitted = fit_chunks(chunks_of("subtitle", line.subtitle), sw, sh, cap=fs * 0.6)
        if fitted:
            s_fs, s_lines = fitted
            spec["subtitle"] = Placed(
                sx, sy, sw, sh, fs=s_fs, lines=len(s_lines), line_texts=tuple(s_lines)
            )

    # CTA: pill sized to its label, centred in its rect
    cx, cy, cw, ch = _px(arch.elements["cta"], size)
    cta_fs = max(min(ch * 0.42, cw / (text_units(line.cta) + CTA_PAD_FACTOR)), MIN_FS)
    pill_w = min(cw, cta_fs * (text_units(line.cta) + CTA_PAD_FACTOR))
    pill_h = min(ch, cta_fs * 2.2)
    spec["cta"] = Placed(cx + (cw - pill_w) / 2, cy + (ch - pill_h) / 2, pill_w, pill_h, fs=cta_fs)

    return spec, arch
