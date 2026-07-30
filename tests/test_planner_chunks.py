"""BannerPlan carries phrase chunks (ADR-0006): the stub planner segments
title/subtitle deterministically so the guard's composer has boundaries."""
from __future__ import annotations

from pathlib import Path

from layoutloom_v0.nodes.assets_io import FontAsset, ImageAsset
from layoutloom_v0.nodes.canvas import Canvas
from layoutloom_v0.nodes.layout_pick import pick_layout
from layoutloom_v0.nodes.planner import StubBannerPlanner

CANVAS = Canvas(width=1200, height=628, background="#ffffff")
PRODUCT = ImageAsset(path=Path("assets/product.png"), width=600, height=600)
LOGO = ImageAsset(path=Path("assets/logo.png"), width=300, height=100)
FONT = FontAsset(path=None, family="sans-serif")
LAYOUT = pick_layout("text-left", CANVAS)


def test_stub_plan_segments_title_and_subtitle():
    plan = StubBannerPlanner().plan(
        CANVAS, PRODUCT, LOGO, FONT, "限時三天，全館優惠", "現貨供應", LAYOUT
    )
    # title has a clause break; subtitle has none -> stays a single chunk.
    assert plan.chunks == {"title": ["限時三天，", "全館優惠"], "subtitle": ["現貨供應"]}
