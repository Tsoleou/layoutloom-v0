"""Node "Size Set" (deterministic): GDN sizes as data, each classified into a
ratio class (banner / skyscraper / rectangle). The class picks which layout
archetypes apply."""
from __future__ import annotations

from dataclasses import dataclass

from layoutloom_v0.nodes.fitting import classify

RATIO_CLASSES = ("rectangle", "banner", "skyscraper")

__all__ = ["RATIO_CLASSES", "Size", "build_size_set", "classify"]


@dataclass(frozen=True)
class Size:
    width: int
    height: int
    # background is only used by v0's StubRenderer placeholder fill
    background: str = "#ffffff"

    @property
    def ratio_class(self) -> str:
        return classify(self.width, self.height)

    @property
    def name(self) -> str:
        return f"{self.width}x{self.height}"


def build_size_set(sizes: tuple[tuple[int, int], ...]) -> tuple[Size, ...]:
    out = tuple(Size(w, h) for w, h in sizes)
    if not out:
        raise ValueError("size set is empty")
    return out
