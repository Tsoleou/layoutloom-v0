"""build_prompt asks the model for phrase segmentation (ADR-0006), teaching it
by a worked example just like the spec/html sections do."""
from __future__ import annotations

from pathlib import Path

from layoutloom_v0.nodes.assets_io import FontAsset, ImageAsset
from layoutloom_v0.nodes.canvas import Canvas
from layoutloom_v0.nodes.layout_pick import pick_layout
from layoutloom_v0.nodes.planner import build_prompt

CANVAS = Canvas(width=1200, height=628, background="#ffffff")
PRODUCT = ImageAsset(path=Path("assets/product.png"), width=600, height=600)
LOGO = ImageAsset(path=Path("assets/logo.png"), width=300, height=100)
FONT = FontAsset(path=None, family="sans-serif")
LAYOUT = pick_layout("text-left", CANVAS)


def test_prompt_requests_chunks_with_a_worked_example():
    prompt = build_prompt(CANVAS, PRODUCT, LOGO, FONT, "限時三天，全館優惠", "現貨供應", LAYOUT)
    # the third required key, plus a concrete segmentation example for the title
    # (break kept on the chunk after the clause-ending comma)
    assert '"chunks"' in prompt
    assert '["限時三天，", "全館優惠"]' in prompt
