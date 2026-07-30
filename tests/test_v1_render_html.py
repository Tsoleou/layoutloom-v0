"""Render HTML node: the composed phrase lines are emitted as explicit <br>
breaks (mirroring v0's Layout Guard), not left to the browser's greedy wrap."""
from __future__ import annotations

from pathlib import Path

from layoutloom_v0.nodes.assets_io import FontAsset, ImageAsset
from layoutloom_v1.nodes.adapt_layout import Placed
from layoutloom_v1.nodes.brand_kit import BrandKit
from layoutloom_v1.nodes.campaign_io import ProductLine
from layoutloom_v1.nodes.layout_catalog import CATALOG
from layoutloom_v1.nodes.master_design import StyleTokens
from layoutloom_v1.nodes.render_html import render_html
from layoutloom_v1.nodes.size_set import Size

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


def _spec(title_lines: tuple[str, ...]) -> dict:
    return {
        "logo": Placed(0, 0, 100, 30),
        "product": Placed(150, 0, 100, 100),
        "title": Placed(0, 40, 135, 70, fs=28, lines=len(title_lines), line_texts=title_lines),
        "cta": Placed(0, 200, 60, 30, fs=14),
    }


def test_multiline_title_emits_br():
    arch = CATALOG["rectangle"]["rect-hero-right"]
    line = ProductLine("x", "限時三天全館優惠", "", "買", Path("p.png"))
    html = render_html(_spec(("限時三天", "全館優惠")), arch, STYLE, line, Size(300, 250), PRODUCT, BRAND)
    assert "限時三天<br>全館優惠" in html


def test_single_line_title_has_no_br():
    arch = CATALOG["rectangle"]["rect-hero-right"]
    line = ProductLine("x", "限時三天", "", "買", Path("p.png"))
    html = render_html(_spec(("限時三天",)), arch, STYLE, line, Size(300, 250), PRODUCT, BRAND)
    assert "<br>" not in html
    assert "限時三天" in html
