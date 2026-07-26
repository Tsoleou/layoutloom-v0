"""End-to-end wiring with the deterministic stubs: no model, no browser, no net."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from layoutloom_v0.config import PipelineConfig
from layoutloom_v0.demo_assets import ensure_demo_assets
from layoutloom_v0.driver import render_banner
from layoutloom_v0.nodes.html2img import StubRenderer
from layoutloom_v0.nodes.planner import StubBannerPlanner


def _cfg(tmp_path: Path, layout: str = "text-left") -> PipelineConfig:
    # a fixed archetype keeps the stub pipeline deterministic (default: random)
    return PipelineConfig(
        product_path=tmp_path / "assets/product.png",
        logo_path=tmp_path / "assets/logo.png",
        font_path=tmp_path / "fonts/missing.ttf",
        html_out=tmp_path / "output/banner.html",
        image_out=tmp_path / "output/banner.png",
        layout=layout,
    )


def test_pipeline_produces_both_exits(tmp_path: Path):
    cfg = _cfg(tmp_path)
    ensure_demo_assets(cfg.product_path, cfg.logo_path)

    result = render_banner("大促銷", "限時三天", cfg, planner=StubBannerPlanner(), renderer=StubRenderer())

    # exit 1: the spec was produced and shown
    assert {"product", "logo", "title", "subtitle"} <= set(result.spec)
    # exit 2: HTML saved and image saved at canvas size x scale
    assert "大促銷" in result.html_path.read_text(encoding="utf-8")
    with Image.open(result.image_path) as im:
        assert im.size == (1200 * cfg.render_scale, 628 * cfg.render_scale)


def test_stub_pipeline_is_reproducible(tmp_path: Path):
    cfg = _cfg(tmp_path)
    ensure_demo_assets(cfg.product_path, cfg.logo_path)
    kwargs = dict(cfg=cfg, planner=StubBannerPlanner(), renderer=StubRenderer())

    first = render_banner("A", "B", **kwargs)
    html1, img1 = first.html_path.read_bytes(), first.image_path.read_bytes()
    second = render_banner("A", "B", **kwargs)
    assert second.html_path.read_bytes() == html1
    assert second.image_path.read_bytes() == img1


def test_every_archetype_renders(tmp_path: Path):
    from layoutloom_v0.nodes.layout_pick import ARCHETYPES

    for name in ARCHETYPES:
        cfg = _cfg(tmp_path, layout=name)
        ensure_demo_assets(cfg.product_path, cfg.logo_path)
        result = render_banner("大促銷", "限時三天", cfg, planner=StubBannerPlanner(), renderer=StubRenderer())
        assert result.layout == name
        assert "大促銷" in result.html_path.read_text(encoding="utf-8")


def test_missing_asset_is_a_clear_error(tmp_path: Path):
    cfg = _cfg(tmp_path)  # no assets created
    try:
        render_banner("A", "B", cfg, planner=StubBannerPlanner(), renderer=StubRenderer())
    except FileNotFoundError as e:
        assert "product" in str(e)
    else:
        raise AssertionError("expected FileNotFoundError for missing product asset")
