"""Pick Layout node: archetypes resolve to disjoint in-canvas regions, and
every archetype's reference_spec is itself geometry-valid (the prompt example
and the stub planner both rely on that)."""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import pytest

from layoutloom_v0.nodes.assets_io import ImageAsset
from layoutloom_v0.nodes.canvas import Canvas
from layoutloom_v0.nodes.layout_pick import ARCHETYPES, pick_layout, reference_spec

CANVAS = Canvas(width=1200, height=628, background="#ffffff")
PRODUCT = ImageAsset(path=Path("assets/product.png"), width=600, height=600)
LOGO = ImageAsset(path=Path("assets/logo.png"), width=300, height=100)


def _overlap(a, b) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


@pytest.mark.parametrize("name", ARCHETYPES)
def test_regions_disjoint_and_inside_canvas(name: str):
    lay = pick_layout(name, CANVAS)
    for r in (lay.text, lay.product):
        assert r.x >= 0 and r.y >= 0
        assert r.right <= CANVAS.width and r.bottom <= CANVAS.height
    assert not _overlap(
        (lay.text.x, lay.text.y, lay.text.w, lay.text.h),
        (lay.product.x, lay.product.y, lay.product.w, lay.product.h),
    )


@pytest.mark.parametrize("name", ARCHETYPES)
def test_reference_spec_is_geometry_valid(name: str):
    lay = pick_layout(name, CANVAS)
    spec = reference_spec(lay, PRODUCT, LOGO)
    boxes = {k: (v["x"], v["y"], v["width"], v["height"]) for k, v in spec.items()}
    for (a, ba), (b, bb) in combinations(boxes.items(), 2):
        assert not _overlap(ba, bb), f"{name}: {a} overlaps {b}"
    for k, (x, y, w, h) in boxes.items():
        assert x >= 0 and y >= 0, f"{name}: {k} out of canvas"
        assert x + w <= CANVAS.width and y + h <= CANVAS.height, f"{name}: {k} out of canvas"


def test_random_draws_a_known_archetype():
    assert pick_layout("random", CANVAS).name in ARCHETYPES


def test_unknown_name_raises():
    with pytest.raises(ValueError):
        pick_layout("diagonal", CANVAS)
