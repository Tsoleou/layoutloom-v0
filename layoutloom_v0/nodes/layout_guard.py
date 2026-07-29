"""Node "Layout Guard" (deterministic): geometry post-pass over the model's plan.

Small local models reliably follow the HTML template but not the geometry
(they don't do arithmetic), so the split of responsibilities is: the model
owns the *design* (colours, font sizes, relative proportions) and this node
owns the *geometry*. It clamps every element into the regions of the Layout
chosen by the "Pick Layout" node, restacks the text column with proportional
gaps, and rewrites the inline styles + spec to match.

Text handling is width-aware: font sizes are fitted to the actual copy (the
inner text is parsed from the HTML) with a two-line budget, stacked using the
real wrapped height — not a one-line guess — and a subtitle that cannot reach
the minimum font size is dropped rather than squeezed. This is what keeps the
layout intact at any canvas size, not just the default 1200x628.

HTML that doesn't match the template is returned untouched — there is nothing
safe to repair.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .assets_io import ImageAsset
from .fitting import LINE_HEIGHT, MIN_FS, compose_lines, fit_chunks, segment_text
from .layout_pick import Layout
from .planner import BannerPlan

# kept as the public single-line height factor (tests and callers use it)
TEXT_LINE = LINE_HEIGHT

_EL = re.compile(r'<(img|h1|p)\b[^>]*class="el"[^>]*>', re.I)


def _px(style: str, prop: str) -> float | None:
    m = re.search(rf"{prop}\s*:\s*(-?\d+(?:\.\d+)?)px", style)
    return float(m.group(1)) if m else None


def _style_of(tag_html: str) -> str | None:
    m = re.search(r'style="([^"]*)"', tag_html)
    return m.group(1) if m else None


def _set_px(style: str, prop: str, value: float) -> str:
    v = f"{prop}:{value:.0f}px"
    if re.search(rf"{prop}\s*:\s*[^;\"]+", style):
        return re.sub(rf"{prop}\s*:\s*[^;\"]+", v, style, count=1)
    return f"{style.rstrip('; ')}; {v};"


@dataclass
class _El:
    name: str
    tag_html: str  # the opening tag (style rewrites happen here)
    outer: str  # full element html (used when an element is dropped)
    style: str
    text: str  # inner text for h1/p, "" for img
    x: float
    y: float
    w: float
    fs: float | None  # font-size for text elements


def _parse(html: str, logo: ImageAsset) -> dict[str, _El] | None:
    els: dict[str, _El] = {}
    for m in _EL.finditer(html):
        tag_html, kind = m.group(0), m.group(1).lower()
        style = _style_of(tag_html)
        if style is None:
            return None
        text, outer = "", tag_html
        if kind == "img":
            src = re.search(r'src="([^"]*)"', tag_html)
            name = "logo" if src and "logo" in src.group(1).lower() else "product"
        else:
            name = "title" if kind == "h1" else "subtitle"
            m2 = re.search(re.escape(tag_html) + rf"(.*?)</{kind}>", html, re.S)
            if m2:
                outer = m2.group(0)
                text = re.sub(r"<[^>]+>", "", m2.group(1)).strip()
        x, y, w = _px(style, "left"), _px(style, "top"), _px(style, "width")
        fs = _px(style, "font-size")
        if None in (x, y, w) or (name in ("title", "subtitle") and fs is None):
            return None
        els[name] = _El(name, tag_html, outer, style, text, x, y, w, fs)
    # subtitle is optional (short canvases may omit it); the rest are required
    return els if {"logo", "product", "title"} <= set(els) else None


def repair_layout(
    plan: BannerPlan, product: ImageAsset, logo: ImageAsset, layout: Layout
) -> tuple[BannerPlan, list[str]]:
    """Clamp the plan's geometry into the archetype's disjoint regions.

    Returns the (possibly rewritten) plan and a list of human-readable fixes;
    an empty list means the model's geometry was already valid.
    """
    els = _parse(plan.html, logo)
    if els is None:
        return plan, ["html does not match the template; left untouched"]

    fixes: list[str] = []
    t, p = layout.text, layout.product
    gap = min(max(t.h * 0.08, 6.0), 40.0)

    def fix(el: _El, prop: str, value: float, why: str) -> None:
        current = {"left": el.x, "top": el.y, "width": el.w, "font-size": el.fs}[prop]
        if current is not None and abs(current - value) < 0.5:
            return
        fixes.append(f"{el.name}: {prop} {current:.0f} -> {value:.0f} ({why})")
        setattr(el, {"left": "x", "top": "y", "width": "w", "font-size": "fs"}[prop], value)

    lg, ttl, prd = els["logo"], els["title"], els["product"]
    sub = els.get("subtitle")

    def chunks_of(el: _El) -> list[str]:
        # the model's phrase segmentation, or a deterministic fallback per field
        return plan.chunks.get(el.name) or segment_text(el.text or "字")

    def composed(el: _El) -> list[str]:
        # the actual lines at the element's final width and font size
        assert el.fs
        return compose_lines(chunks_of(el), min(el.w, t.w) / el.fs)

    # Title font: clamp into the archetype's range, then never above what the
    # actual composed lines fit in the region (chunk-aware, larger font wins).
    assert ttl.fs
    lo, hi = layout.title_fs
    fitted = fit_chunks(chunks_of(ttl), min(ttl.w, t.w), t.h * 0.6, cap=hi)
    fix(ttl, "font-size", min(max(ttl.fs, lo), hi, fitted[0] if fitted else MIN_FS), "title scale/fit")
    title_line_list = composed(ttl)
    title_h = len(title_line_list) * ttl.fs * LINE_HEIGHT

    # Logo: cap by archetype, region width AND region height share.
    max_logo_w = min(layout.logo_max_w, t.w, 0.28 * t.h * logo.width / logo.height)
    fix(lg, "width", min(lg.w, max_logo_w), "logo kept discreet")
    logo_h = lg.w * logo.height / logo.width

    # Subtitle font — or drop it when it cannot fit above the minimum size.
    dropped_subtitle = False
    sub_line_list: list[str] = []
    if sub is not None:
        assert sub.fs
        s_lo, s_hi = layout.subtitle_fs
        budget_h = t.h - logo_h - gap - title_h - gap / 2
        s_fitted = fit_chunks(
            chunks_of(sub), min(sub.w, t.w), max(budget_h, 1), cap=min(s_hi, ttl.fs * 0.75)
        )
        if s_fitted is None:
            fixes.append("subtitle: dropped (cannot fit at readable size)")
            dropped_subtitle = True
        else:
            fix(sub, "font-size", min(max(sub.fs, s_lo), s_hi, s_fitted[0]), "subtitle scale/fit")
            sub_line_list = composed(sub)

    def aligned_x(width: float) -> float:
        return t.x if layout.align == "left" else t.x + (t.w - width) / 2

    text_els = [ttl] if dropped_subtitle or sub is None else [ttl, sub]
    for el in text_els:
        fix(el, "width", min(el.w, t.w), "fit text region")
        fix(el, "left", aligned_x(el.w), "align in text region")
    fix(lg, "left", aligned_x(lg.w), "align logo")
    fix(lg, "top", min(max(lg.y, t.y), t.y + t.h / 4), "logo near the top")

    # Restack with real (wrapped) text heights and proportional gaps.
    fix(ttl, "top", max(ttl.y, lg.y + logo_h + gap), "clear the logo")
    bottom = ttl.y + title_h
    if sub is not None and not dropped_subtitle:
        assert sub.fs
        fix(sub, "top", max(sub.y, ttl.y + title_h + gap / 2), "clear the title")
        bottom = sub.y + len(sub_line_list) * sub.fs * LINE_HEIGHT
    # Pull the stack back up if it would clip the region bottom.
    overflow = bottom - t.bottom
    if overflow > 0:
        fix(ttl, "top", max(ttl.y - overflow, lg.y + logo_h + gap / 2), "avoid clipping")
        if sub is not None and not dropped_subtitle:
            fix(sub, "top", max(sub.y - overflow, ttl.y + title_h + gap / 4), "avoid clipping")

    # PRODUCT region: fit and centre.
    ratio = product.height / product.width
    max_w = min(p.w, p.h / ratio)
    fix(prd, "width", min(prd.w, max_w), "fit product region")
    fix(prd, "left", p.x + (p.w - prd.w) / 2, "centre in product region")
    fix(prd, "top", p.y + (p.h - prd.w * ratio) / 2, "centre in product region")

    # The inline left/top only work under position:absolute. The template puts
    # that on a `.el` stylesheet rule, but models sometimes mangle the selector
    # (e.g. `el` without the dot) — in that case guarantee it inline, per element.
    stylesheet_ok = re.search(r"\.el\s*\{[^}]*position\s*:\s*absolute", plan.html)
    if not stylesheet_ok:
        for el in els.values():
            if not re.search(r"position\s*:\s*absolute", el.style):
                fixes.append(f"{el.name}: enforce position:absolute inline")

    # Images must carry width only — an explicit height distorts the source
    # aspect ratio (the template forbids it, but models add it anyway).
    for el in (lg, prd):
        if _px(el.style, "height") is not None:
            fixes.append(f"{el.name}: drop explicit height (preserve aspect ratio)")

    # Text alignment is part of the archetype (a full-width text box without
    # text-align renders left even in a centred layout) — enforce it inline.
    # CSS defaults to left, so only non-left archetypes need it.
    if layout.align != "left":
        for el in text_els:
            if not re.search(rf"text-align\s*:\s*{layout.align}", el.style):
                fixes.append(f"{el.name}: text-align {layout.align}")

    # Composing multi-line text is an explicit rewrite of the inner HTML (the
    # phrase break replaces the browser's auto-wrap), so record it — otherwise a
    # geometrically-valid banner would keep its unbroken single run.
    if len(title_line_list) > 1:
        fixes.append(f"title: composed {len(title_line_list)} lines")
    if sub is not None and not dropped_subtitle and len(sub_line_list) > 1:
        fixes.append(f"subtitle: composed {len(sub_line_list)} lines")

    if not fixes:
        return plan, []

    # Rewrite inline styles in the HTML and mirror the geometry into the spec.
    html = plan.html
    spec = dict(plan.spec)
    if dropped_subtitle and sub is not None:
        html = html.replace(sub.outer, "", 1)
        spec.pop("subtitle", None)

    heights = {
        "logo": lg.w * logo.height / logo.width,
        "product": prd.w * ratio,
        "title": title_h,
    }
    line_lists = {"title": title_line_list, "subtitle": sub_line_list}
    if sub is not None and not dropped_subtitle:
        assert sub.fs
        heights["subtitle"] = len(sub_line_list) * sub.fs * LINE_HEIGHT

    for el in [lg, prd, *text_els]:
        new_style = el.style
        for prop, value in (("left", el.x), ("top", el.y), ("width", el.w)):
            new_style = _set_px(new_style, prop, value)
        if el.fs is not None:
            new_style = _set_px(new_style, "font-size", el.fs)
        if el.name in ("logo", "product"):
            new_style = re.sub(r"height\s*:\s*[^;\"]+;?\s*", "", new_style)
        if (
            layout.align != "left"
            and el.name in ("title", "subtitle")
            and not re.search(rf"text-align\s*:\s*{layout.align}", new_style)
        ):
            new_style = re.sub(r"text-align\s*:\s*[^;\"]+;?\s*", "", new_style)
            new_style = f"{new_style.rstrip('; ')}; text-align:{layout.align};"
        if not stylesheet_ok and not re.search(r"position\s*:\s*absolute", new_style):
            new_style = f"position:absolute; margin:0; {new_style.lstrip()}"
        new_open = el.tag_html.replace(el.style, new_style)
        if el.name in ("title", "subtitle"):
            # rewrite the whole element so the inner text carries the composed
            # <br> line breaks, not just the opening tag's styles
            kind = "h1" if el.name == "title" else "p"
            inner = "<br>".join(line_lists[el.name])
            html = html.replace(el.outer, f"{new_open}{inner}</{kind}>", 1)
        else:
            html = html.replace(el.tag_html, new_open, 1)
        entry = dict(spec.get(el.name) or {})
        entry.update(x=round(el.x), y=round(el.y), width=round(el.w), height=round(heights[el.name]))
        if el.fs is not None:
            entry["font_size_px"] = round(el.fs)
        spec[el.name] = entry

    return BannerPlan(spec=spec, html=html), fixes
