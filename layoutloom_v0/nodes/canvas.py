"""Node "Canva" (deterministic): blank canvas per config, the banner's size basis."""
from __future__ import annotations

from dataclasses import dataclass

from ..config import CanvasConfig


@dataclass(frozen=True)
class Canvas:
    width: int
    height: int
    background: str


def make_canvas(cfg: CanvasConfig) -> Canvas:
    if cfg.width <= 0 or cfg.height <= 0:
        raise ValueError(f"canvas size must be positive, got {cfg.width}x{cfg.height}")
    return Canvas(width=cfg.width, height=cfg.height, background=cfg.background)
