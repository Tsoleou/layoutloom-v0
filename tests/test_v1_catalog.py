"""Layout Catalog node: every archetype's fractional rects are disjoint and
inside [0,1] — the property all downstream overlap-freedom rests on."""
from __future__ import annotations

from itertools import combinations

import pytest

from layoutloom_v1.nodes.layout_catalog import CATALOG, get_archetype

ALL = [(cls, name, arch) for cls, d in CATALOG.items() for name, arch in d.items()]


def _overlap(a, b) -> bool:
    return not (
        a.x + a.w <= b.x or b.x + b.w <= a.x or a.y + a.h <= b.y or b.y + b.h <= a.y
    )


@pytest.mark.parametrize(("cls", "name", "arch"), ALL, ids=[n for _, n, _ in ALL])
def test_rects_disjoint_and_in_bounds(cls, name, arch):
    assert set(arch.elements) == {"logo", "title", "subtitle", "cta", "product"}
    for el, r in arch.elements.items():
        assert 0 <= r.x and 0 <= r.y and r.x + r.w <= 1 and r.y + r.h <= 1, f"{name}.{el}"
    for (ea, ra), (eb, rb) in combinations(arch.elements.items(), 2):
        assert not _overlap(ra, rb), f"{name}: {ea} overlaps {eb}"


def test_unknown_archetype_falls_back_to_class_default():
    assert get_archetype("rectangle", "nope").name == next(iter(CATALOG["rectangle"]))
