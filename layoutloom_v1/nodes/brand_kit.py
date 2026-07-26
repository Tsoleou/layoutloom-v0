"""Node "Brand Kit" (io): brand constraints — palette, font, logo, CTA style.
The model's style decisions are confined to this space; rendering pulls the
physical assets from here."""
from __future__ import annotations

from dataclasses import dataclass

from layoutloom_v0.nodes.assets_io import FontAsset, ImageAsset, load_font, load_image_asset

from ..config import BrandKitConfig


@dataclass(frozen=True)
class BrandKit:
    palette: tuple[str, ...]
    font: FontAsset
    logo: ImageAsset
    cta_radius_px: int


def load_brand_kit(cfg: BrandKitConfig) -> BrandKit:
    return BrandKit(
        palette=tuple(c.lower() for c in cfg.palette),
        font=load_font(cfg.font_path),
        logo=load_image_asset(cfg.logo_path),
        cta_radius_px=cfg.cta_radius_px,
    )
