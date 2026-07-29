"""The guard emits composed <br> lines (ADR-0006): a wrapping title is broken
at phrase boundaries in the HTML, not left to the browser's greedy auto-wrap."""
from __future__ import annotations

import re
from pathlib import Path

from layoutloom_v0.nodes.assets_io import ImageAsset
from layoutloom_v0.nodes.canvas import Canvas
from layoutloom_v0.nodes.layout_guard import repair_layout
from layoutloom_v0.nodes.layout_pick import pick_layout
from layoutloom_v0.nodes.planner import BannerPlan

CANVAS = Canvas(width=1200, height=628, background="#ffffff")
PRODUCT = ImageAsset(path=Path("assets/product.png"), width=600, height=600)
LOGO = ImageAsset(path=Path("assets/logo.png"), width=300, height=100)
LAYOUT = pick_layout("text-left", CANVAS)


def _html(title: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body {{ margin: 0; }}
.banner {{ position: relative; width: 1200px; height: 628px; background: #ffffff; }}
.el {{ position: absolute; margin: 0; }}
</style></head><body><div class="banner">
<img class="el" src="http://x/assets/logo.png" style="left:40px; top:40px; width:180px;">
<img class="el" src="http://x/assets/product.png" style="left:670px; top:94px; width:440px;">
<h1 class="el" style="left:40px; top:230px; width:540px; font-size:88px; color:#c00;">{title}</h1>
<p class="el" style="left:40px; top:470px; width:540px; font-size:40px; color:#333;">現貨</p>
</div></body></html>"""


def test_wrapping_title_gets_br_at_phrase_boundary():
    # Region is 540px wide; the two chunks (widest "限時三天，" ~5.25u) cap the
    # font near 103px, forcing two lines. The guard writes the phrase break as
    # an explicit <br>, not one auto-wrapped run.
    plan = BannerPlan(
        spec={},
        html=_html("限時三天，全館優惠"),
        chunks={"title": ["限時三天，", "全館優惠"]},
    )
    out, _ = repair_layout(plan, PRODUCT, LOGO, LAYOUT)
    inner = re.search(r"<h1[^>]*>(.*?)</h1>", out.html, re.S).group(1)
    assert inner == "限時三天，<br>全館優惠"
