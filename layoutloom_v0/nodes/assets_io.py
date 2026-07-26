"""Nodes "Load Product Image" / "Load Logo" / "Load Font" (io): asset loading.

Assumption: the planner receives asset *metadata* (path + pixel size), not
pixels — the HTML references the files directly. Reading dimensions here is
the only Pillow touch.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class ImageAsset:
    path: Path
    width: int
    height: int


@dataclass(frozen=True)
class FontAsset:
    path: Path | None
    family: str


def load_image_asset(path: Path) -> ImageAsset:
    if not path.is_file():
        raise FileNotFoundError(f"asset not found: {path}")
    with Image.open(path) as im:
        w, h = im.size
    return ImageAsset(path=path, width=w, height=h)


def load_font(path: Path, family: str = "NotoSansTC") -> FontAsset:
    # A missing font degrades to a system sans-serif stack rather than failing
    # the whole render; the HTML template only emits @font-face when path is set.
    if not path.is_file():
        return FontAsset(path=None, family="sans-serif")
    return FontAsset(path=path, family=family)
