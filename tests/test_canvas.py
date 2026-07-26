from __future__ import annotations

import pytest

from layoutloom_v0.config import CanvasConfig
from layoutloom_v0.nodes.canvas import make_canvas


def test_canvas_uses_contract_defaults():
    c = make_canvas(CanvasConfig())
    assert (c.width, c.height, c.background) == (1200, 628, "#ffffff")


def test_canvas_rejects_nonpositive_size():
    with pytest.raises(ValueError):
        make_canvas(CanvasConfig(width=0, height=628))
