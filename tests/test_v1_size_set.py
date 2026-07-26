"""Size Set node: GDN sizes classify into the expected ratio classes."""
from __future__ import annotations

import pytest

from layoutloom_v1.nodes.size_set import build_size_set, classify


@pytest.mark.parametrize(
    ("w", "h", "expected"),
    [
        (300, 250, "rectangle"),
        (336, 280, "rectangle"),
        (250, 250, "rectangle"),
        (728, 90, "banner"),
        (970, 250, "banner"),
        (320, 100, "banner"),
        (468, 60, "banner"),
        (300, 600, "skyscraper"),
        (160, 600, "skyscraper"),
        (120, 600, "skyscraper"),
    ],
)
def test_gdn_sizes_classify(w: int, h: int, expected: str):
    assert classify(w, h) == expected


def test_build_size_set_carries_class_and_name():
    sizes = build_size_set(((728, 90), (300, 600)))
    assert sizes[0].name == "728x90" and sizes[0].ratio_class == "banner"
    assert sizes[1].name == "300x600" and sizes[1].ratio_class == "skyscraper"


def test_empty_size_set_rejected():
    with pytest.raises(ValueError):
        build_size_set(())
