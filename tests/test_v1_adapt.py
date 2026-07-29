"""Adapt Layout node: for every archetype x sample size x short/long copy,
all placed boxes stay disjoint and inside the canvas; an unfittable subtitle
is omitted rather than squeezed."""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import pytest

from layoutloom_v0.nodes.assets_io import FontAsset, ImageAsset
from layoutloom_v1.nodes.adapt_layout import adapt_layout
from layoutloom_v1.nodes.brand_kit import BrandKit
from layoutloom_v1.nodes.campaign_io import ProductLine
from layoutloom_v1.nodes.layout_catalog import CATALOG
from layoutloom_v1.nodes.master_design import ProductDesign, StyleTokens
from layoutloom_v1.nodes.size_set import RATIO_CLASSES, Size

BRAND = BrandKit(
    palette=("#0f4c81", "#ffffff"),
    font=FontAsset(path=None, family="sans-serif"),
    logo=ImageAsset(path=Path("assets/logo.png"), width=300, height=100),
    cta_radius_px=6,
)
PRODUCT = ImageAsset(path=Path("assets/p.png"), width=600, height=600)
STYLE = StyleTokens(
    background={"type": "solid", "color": "#ffffff"},
    title_color="#0f4c81",
    subtitle_color="#0f4c81",
    cta_bg="#0f4c81",
    cta_text_color="#ffffff",
)
SIZES = {
    "rectangle": [Size(300, 250), Size(336, 280)],
    "banner": [Size(728, 90), Size(970, 250), Size(320, 100)],
    "skyscraper": [Size(300, 600), Size(160, 600)],
}
COPY = [
    ("大促銷", "限時三天", "買"),
    ("超長標題的年度旗艦筆記型電腦大型促銷活動開跑", "這是一段非常非常長的副標題文案,長到幾乎一定需要換行或縮小字級", "立即選購"),
]


def _design(cls: str, name: str) -> ProductDesign:
    layouts = {c: next(iter(CATALOG[c])) for c in RATIO_CLASSES}
    layouts[cls] = name
    return ProductDesign(name="x", layouts=layouts, style=STYLE)


def _overlap(a, b) -> bool:
    return not (a.x + a.w <= b.x or b.x + b.w <= a.x or a.y + a.h <= b.y or b.y + b.h <= a.y)


CASES = [
    (cls, name, size, copy)
    for cls, archs in CATALOG.items()
    for name in archs
    for size in SIZES[cls]
    for copy in COPY
]


@pytest.mark.parametrize(
    ("cls", "name", "size", "copy"),
    CASES,
    ids=[f"{n}-{s.name}-{'long' if len(c[0]) > 10 else 'short'}" for _, n, s, c in CASES],
)
def test_placed_boxes_disjoint_and_inside(cls, name, size, copy):
    title, subtitle, cta = copy
    line = ProductLine("x", title, subtitle, cta, Path("p.png"))
    spec, arch = adapt_layout(_design(cls, name), line, size, PRODUCT, BRAND)

    assert arch.name == name
    assert {"product", "logo", "title", "cta"} <= set(spec)
    for el, p in spec.items():
        assert p.x >= -0.5 and p.y >= -0.5, f"{el} out of canvas"
        assert p.x + p.w <= size.width + 0.5 and p.y + p.h <= size.height + 0.5, f"{el} out of canvas"
    for (ea, pa), (eb, pb) in combinations(spec.items(), 2):
        assert not _overlap(pa, pb), f"{ea} overlaps {eb}"


def test_title_composed_at_chunk_boundary_carried_on_placed():
    # 135x70px title box: one line (235px) overflows, so it wraps to two lines —
    # exactly at the chunk boundary, never splitting 「限時三天」.
    design = ProductDesign(
        name="x",
        layouts={c: next(iter(CATALOG[c])) for c in RATIO_CLASSES},
        style=STYLE,
        chunks={"title": ["限時三天", "全館優惠"]},
    )
    line = ProductLine("x", "限時三天全館優惠", "", "買", Path("p.png"))
    spec, _ = adapt_layout(design, line, Size(300, 250), PRODUCT, BRAND)
    t = spec["title"]
    assert t.line_texts == ("限時三天", "全館優惠")
    assert t.lines == 2


def test_product_name_forced_onto_its_own_first_line():
    # On a wide banner the full title "Aero 14 Ultralight" would otherwise fit a
    # single line (larger font). An explicit product_name forces it onto its own
    # first line, with the tagline composed beneath (ADR-0008).
    design = ProductDesign(
        name="x",
        layouts={c: next(iter(CATALOG[c])) for c in RATIO_CLASSES},
        style=STYLE,
    )
    line = ProductLine("x", "Aero 14 Ultralight", "", "Shop", Path("p.png"), product_name="Aero 14")
    # forced onto its own line on both a wide banner and a tall skyscraper
    for size in (Size(728, 90), Size(300, 600)):
        t = adapt_layout(design, line, size, PRODUCT, BRAND)[0]["title"]
        assert t.line_texts == ("Aero 14", "Ultralight"), size.name
        assert t.lines == 2
    # tiny leaderboard + long subtitle: subtitle must be dropped, not squeezed
    line = ProductLine("x", "促銷", "這是一段塞不進小橫幅的超長副標題文案內容", "買", Path("p.png"))
    spec, _ = adapt_layout(_design("banner", "banner-product-right"), line, Size(320, 50), PRODUCT, BRAND)
    assert "subtitle" not in spec
    assert spec["title"].fs is not None and spec["title"].fs >= 9
