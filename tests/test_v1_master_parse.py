"""LLM Master Design parsing: tolerant extraction plus mechanical constraint
enforcement (palette snap, contrast fix, unknown-layout fallback)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from layoutloom_v0.nodes.assets_io import FontAsset, ImageAsset
from layoutloom_v1.nodes.brand_kit import BrandKit
from layoutloom_v1.nodes.campaign_io import Campaign, ProductLine
from layoutloom_v1.nodes.master_design import (
    StubMasterDesigner,
    contrast,
    parse_master_design,
    snap_to_palette,
)
from layoutloom_v1.nodes.size_set import Size

BRAND = BrandKit(
    palette=("#0f4c81", "#83c5be", "#111111", "#ffffff"),
    font=FontAsset(path=None, family="sans-serif"),
    logo=ImageAsset(path=Path("assets/logo.png"), width=300, height=100),
    cta_radius_px=6,
)
CAMPAIGN = Campaign(
    name="t",
    products=(
        ProductLine("swift", "Swift Go 14", "輕薄 AI 筆電", "立即選購", Path("a.png")),
    ),
)


def _payload(**style_over) -> str:
    style = {
        "background": {"type": "solid", "color": "#ffffff"},
        "title_color": "#0f4c81",
        "subtitle_color": "#111111",
        "cta": {"bg": "#0f4c81", "text_color": "#ffffff"},
        "type_scale": 1.1,
        **style_over,
    }
    return json.dumps(
        {"products": [{
            "name": "swift",
            "layouts": {"rectangle": "rect-hero-left", "banner": "banner-product-right",
                        "skyscraper": "sky-product-mid"},
            "style": style,
        }]}
    )


def test_parses_clean_json():
    d = parse_master_design(_payload(), CAMPAIGN, BRAND)
    p = d.products["swift"]
    assert p.layouts["rectangle"] == "rect-hero-left"
    assert p.style.title_color == "#0f4c81"
    assert p.style.type_scale == 1.1
    assert p.notes == ()


def test_tolerates_fences_and_prose():
    d = parse_master_design("Sure!\n```json\n" + _payload() + "\n```", CAMPAIGN, BRAND)
    assert "swift" in d.products


@pytest.mark.parametrize("bad", ["no json", '{"nope": 1}'])
def test_rejects_missing_products(bad: str):
    with pytest.raises(ValueError):
        parse_master_design(bad, CAMPAIGN, BRAND)


def test_off_palette_colour_snapped():
    d = parse_master_design(_payload(title_color="#0e4b80"), CAMPAIGN, BRAND)  # near navy
    p = d.products["swift"]
    assert p.style.title_color == "#0f4c81"
    assert any("off-palette" in n for n in p.notes)


def test_low_contrast_title_fixed():
    # white-ish title on white background must be replaced by a contrasting colour
    d = parse_master_design(_payload(title_color="#ffffff"), CAMPAIGN, BRAND)
    p = d.products["swift"]
    assert contrast(p.style.title_color, "#ffffff") >= 3.0


def test_wide_gradient_softened_and_text_reads_on_both_ends():
    # navy->white defeats every palette colour, so the far end must be pulled
    # toward navy and the final text colours must read on BOTH final endpoints
    d = parse_master_design(
        _payload(
            background={"type": "gradient", "from": "#0f4c81", "to": "#ffffff", "angle": 135},
            subtitle_color="#83c5be",
        ),
        CAMPAIGN,
        BRAND,
    )
    p = d.products["swift"]
    bg = p.style.background
    assert bg["to"] != "#ffffff"  # softened
    assert any("softened" in n for n in p.notes)
    for endpoint in (bg["from"], bg["to"]):
        assert contrast(p.style.title_color, endpoint) >= 3.0
        assert contrast(p.style.subtitle_color, endpoint) >= 3.0


def test_unknown_layout_falls_back():
    raw = json.loads(_payload())
    raw["products"][0]["layouts"]["banner"] = "diagonal-madness"
    d = parse_master_design(json.dumps(raw), CAMPAIGN, BRAND)
    p = d.products["swift"]
    assert p.layouts["banner"] == "banner-product-right"  # class default
    assert any("unknown banner layout" in n for n in p.notes)


def test_missing_product_gets_defaults():
    d = parse_master_design('{"products": []}', CAMPAIGN, BRAND)
    p = d.products["swift"]
    assert p.layouts["rectangle"] in ("rect-hero-right", "rect-hero-left")
    assert any("missing" in n for n in p.notes)


def test_snap_to_palette_invalid_input():
    assert snap_to_palette("not-a-colour", BRAND.palette) == BRAND.palette[0]


def test_reads_model_supplied_chunks():
    raw = json.loads(_payload())
    raw["products"][0]["chunks"] = {
        "title": ["Swift Go", "14"],
        "subtitle": ["輕薄", "AI 筆電"],
    }
    d = parse_master_design(json.dumps(raw), CAMPAIGN, BRAND)
    p = d.products["swift"]
    assert p.chunks["title"] == ["Swift Go", "14"]
    assert p.chunks["subtitle"] == ["輕薄", "AI 筆電"]


def test_missing_chunks_fall_back_to_segment_text():
    campaign = Campaign(
        name="t",
        products=(ProductLine("swift", "限時三天，全館優惠", "買一送一！超值", "立即選購", Path("a.png")),),
    )
    raw = json.loads(_payload())  # no "chunks" key
    d = parse_master_design(json.dumps(raw), campaign, BRAND)
    p = d.products["swift"]
    assert p.chunks["title"] == ["限時三天，", "全館優惠"]  # break after 、，
    assert p.chunks["subtitle"] == ["買一送一！", "超值"]


def test_stub_designer_segments_chunks():
    campaign = Campaign(
        name="t",
        products=(ProductLine("swift", "限時三天，全館優惠", "買一送一！超值", "立即選購", Path("a.png")),),
    )
    assets = {"swift": ImageAsset(path=Path("a.png"), width=600, height=600)}
    d = StubMasterDesigner().design(campaign, assets, BRAND, (Size(300, 250),))
    p = d.products["swift"]
    assert p.chunks["title"] == ["限時三天，", "全館優惠"]
    assert p.chunks["subtitle"] == ["買一送一！", "超值"]
