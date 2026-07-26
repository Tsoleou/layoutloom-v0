"""v0 at non-default canvas sizes (the regression the web UI exposed): the
stub pipeline must produce disjoint, in-bounds geometry at every ratio class,
with long copy, including the classic 1200x628."""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import pytest

from layoutloom_v0.config import CanvasConfig, PipelineConfig
from layoutloom_v0.demo_assets import ensure_demo_assets
from layoutloom_v0.driver import render_banner
from layoutloom_v0.nodes.html2img import StubRenderer
from layoutloom_v0.nodes.layout_pick import CLASS_ARCHETYPES, pick_layout
from layoutloom_v0.nodes.canvas import Canvas
from layoutloom_v0.nodes.planner import StubBannerPlanner

SIZES = [(1200, 628), (300, 250), (728, 90), (160, 600), (970, 250), (336, 280)]
LONG = ("大促銷全面五折限時開跑", "這是一段非常長的副標題文案需要縮小或捨棄")
SHORT = ("大促銷", "限時三天")


def _cfg(tmp_path: Path, w: int, h: int) -> PipelineConfig:
    return PipelineConfig(
        canvas=CanvasConfig(width=w, height=h),
        layout="random",
        product_path=tmp_path / "assets/product.png",
        logo_path=tmp_path / "assets/logo.png",
        font_path=tmp_path / "fonts/missing.ttf",
        html_out=tmp_path / "output/banner.html",
        image_out=tmp_path / "output/banner.png",
    )


def _overlap(a: dict, b: dict) -> bool:
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


@pytest.mark.parametrize(("w", "h"), SIZES, ids=[f"{w}x{h}" for w, h in SIZES])
@pytest.mark.parametrize("copy", [SHORT, LONG], ids=["short", "long"])
def test_spec_disjoint_and_inside_at_any_size(tmp_path: Path, w: int, h: int, copy):
    cfg = _cfg(tmp_path, w, h)
    ensure_demo_assets(cfg.product_path, cfg.logo_path)
    result = render_banner(copy[0], copy[1], cfg, planner=StubBannerPlanner(), renderer=StubRenderer())

    boxes = {k: v for k, v in result.spec.items() if isinstance(v, dict) and "width" in v}
    assert {"product", "logo", "title"} <= set(boxes)  # subtitle may be dropped
    for name, e in boxes.items():
        assert e["x"] >= -1 and e["y"] >= -1, f"{w}x{h} {name} out of canvas"
        assert e["x"] + e["width"] <= w + 1, f"{w}x{h} {name} out of canvas"
        assert e["y"] + e["height"] <= h + 1, f"{w}x{h} {name} out of canvas"
    for (na, a), (nb, b) in combinations(boxes.items(), 2):
        assert not _overlap(a, b), f"{w}x{h}: {na} overlaps {nb}"


@pytest.mark.parametrize(
    ("w", "h", "cls"),
    [(728, 90, "banner"), (160, 600, "skyscraper"), (300, 250, "rectangle")],
)
def test_unsuitable_archetype_coerced(w: int, h: int, cls: str):
    canvas = Canvas(width=w, height=h, background="#fff")
    for requested in ("text-left", "text-right", "text-top"):
        layout = pick_layout(requested, canvas)
        assert layout.name in CLASS_ARCHETYPES[cls]


def test_margins_scale_with_canvas():
    tall = pick_layout("text-top", Canvas(width=160, height=600, background="#fff"))
    assert tall.text.x < 20  # not the fixed 40px margin
    classic = pick_layout("text-left", Canvas(width=1200, height=628, background="#fff"))
    assert classic.text.x == 40  # backward compatible at the default size