"""The geometry guardrail: overlapping/clipping template HTML comes out disjoint
and inside the canvas; already-valid layouts pass through untouched."""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

from layoutloom_v0.nodes.assets_io import ImageAsset
from layoutloom_v0.nodes.canvas import Canvas
from layoutloom_v0.nodes.layout_guard import TEXT_LINE, repair_layout
from layoutloom_v0.nodes.layout_pick import pick_layout
from layoutloom_v0.nodes.planner import BannerPlan

CANVAS = Canvas(width=1200, height=628, background="#ffffff")
PRODUCT = ImageAsset(path=Path("assets/product.png"), width=600, height=600)
LOGO = ImageAsset(path=Path("assets/logo.png"), width=300, height=100)
LAYOUT = pick_layout("text-left", CANVAS)


def _html(logo_css: str, product_css: str, title_css: str, subtitle_css: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body {{ margin: 0; }}
.banner {{ position: relative; width: 1200px; height: 628px; background: #ffffff; }}
.el {{ position: absolute; margin: 0; }}
</style></head><body><div class="banner">
<img class="el" src="http://x/assets/logo.png" style="{logo_css}">
<img class="el" src="http://x/assets/product.png" style="{product_css}">
<h1 class="el" style="{title_css}">大促銷</h1>
<p class="el" style="{subtitle_css}">限時三天</p>
</div></body></html>"""


def _boxes(html: str) -> dict[str, tuple[float, float, float, float]]:
    plan = BannerPlan(spec={}, html=html)
    els = __import__("layoutloom_v0.nodes.layout_guard", fromlist=["_parse"])._parse(html, LOGO)
    assert els is not None
    out = {}
    for name, el in els.items():
        if name == "logo":
            h = el.w * LOGO.height / LOGO.width
        elif name == "product":
            h = el.w * PRODUCT.height / PRODUCT.width
        else:
            h = (el.fs or 0) * TEXT_LINE
        out[name] = (el.x, el.y, el.w, h)
    return out


def _overlap(a, b) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def test_overlapping_layout_is_repaired():
    # title/subtitle collide, product overflows both column and canvas bottom
    html = _html(
        "left:100px; top:50px; width:300px;",
        "left:560px; top:94px; width:600px;",
        "left:40px; top:230px; width:520px; font-size:88px; color:#c00;",
        "left:40px; top:250px; width:520px; font-size:42px; color:#333;",
    )
    plan, fixes = repair_layout(BannerPlan(spec={}, html=html), PRODUCT, LOGO, LAYOUT)
    assert fixes
    boxes = _boxes(plan.html)
    for a, b in combinations(boxes.values(), 2):
        assert not _overlap(a, b)
    for x, y, w, h in boxes.values():
        assert x >= 0 and y >= 0 and x + w <= 1200 and y + h <= 628


def test_valid_layout_untouched():
    html = _html(
        "left:40px; top:40px; width:180px;",
        "left:670px; top:94px; width:440px;",
        "left:40px; top:230px; width:520px; font-size:88px; color:#c00;",
        "left:40px; top:372px; width:520px; font-size:42px; color:#333;",
    )
    plan, fixes = repair_layout(BannerPlan(spec={"title": {}}, html=html), PRODUCT, LOGO, LAYOUT)
    assert fixes == []
    assert plan.html == html


def test_spec_mirrors_repaired_geometry():
    html = _html(
        "left:100px; top:50px; width:300px;",
        "left:560px; top:94px; width:600px;",
        "left:40px; top:230px; width:520px; font-size:88px; color:#c00;",
        "left:40px; top:250px; width:520px; font-size:42px; color:#333;",
    )
    plan, _ = repair_layout(BannerPlan(spec={}, html=html), PRODUCT, LOGO, LAYOUT)
    boxes = _boxes(plan.html)
    for name, (x, y, w, _h) in boxes.items():
        assert plan.spec[name]["x"] == round(x)
        assert plan.spec[name]["y"] == round(y)
        assert plan.spec[name]["width"] == round(w)


def test_mangled_stylesheet_gets_inline_positioning():
    # regression: model wrote `el { position: absolute }` (missing the dot),
    # so nothing was absolutely positioned and left/top were ignored
    html = _html(
        "left:40px; top:40px; width:180px;",
        "left:660px; top:94px; width:440px;",
        "left:40px; top:230px; width:520px; font-size:88px; color:#c00;",
        "left:40px; top:372px; width:520px; font-size:42px; color:#333;",
    ).replace(".el { position: absolute; margin: 0; }", "el { position: absolute; margin: 0; }")
    plan, fixes = repair_layout(BannerPlan(spec={}, html=html), PRODUCT, LOGO, LAYOUT)
    assert any("position:absolute" in f for f in fixes)
    for m in __import__("re").finditer(r'class="el"[^>]*style="([^"]*)"', plan.html):
        assert "position:absolute" in m.group(1)


def test_img_height_is_stripped():
    # regression: an explicit height on <img> distorts the source aspect ratio
    html = _html(
        "left:40px; top:40px; width:180px;",
        "left:660px; top:94px; width:440px; height:360px;",
        "left:40px; top:230px; width:520px; font-size:88px; color:#c00;",
        "left:40px; top:372px; width:520px; font-size:42px; color:#333;",
    )
    plan, fixes = repair_layout(BannerPlan(spec={}, html=html), PRODUCT, LOGO, LAYOUT)
    assert any("aspect ratio" in f for f in fixes)
    import re

    for m in re.finditer(r'<img[^>]*style="([^"]*)"', plan.html):
        assert "height" not in m.group(1)


def test_center_archetype_centres_text():
    # text-top aligns the text stack centered; guard must centre, not pin left
    layout = pick_layout("text-top", CANVAS)
    html = _html(
        "left:40px; top:40px; width:120px;",
        "left:400px; top:380px; width:200px;",
        "left:40px; top:150px; width:400px; font-size:60px; color:#c00;",
        "left:40px; top:250px; width:300px; font-size:32px; color:#333;",
    )
    plan, _ = repair_layout(BannerPlan(spec={}, html=html), PRODUCT, LOGO, layout)
    t = layout.text
    for name in ("title", "subtitle", "logo"):
        e = plan.spec[name]
        assert abs(e["x"] - (t.x + (t.w - e["width"]) / 2)) <= 1, f"{name} not centred"
    # glyphs must centre too: text-align enforced inline on the text elements
    import re

    text_styles = re.findall(r'<(?:h1|p)[^>]*style="([^"]*)"', plan.html)
    assert all("text-align:center" in s for s in text_styles)


def test_non_template_html_left_untouched():
    plan = BannerPlan(spec={"a": 1}, html="<html><body><p>free-form</p></body></html>")
    out, fixes = repair_layout(plan, PRODUCT, LOGO, LAYOUT)
    assert out.html == plan.html and out.spec == plan.spec
    assert fixes == ["html does not match the template; left untouched"]
