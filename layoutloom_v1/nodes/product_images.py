"""Node "Load Product Images" (io): measure each product image's pixel size /
aspect ratio — needed by both the master-design evaluation and the geometry
adaptation. Reuses v0's ImageAsset (path + measured size)."""
from __future__ import annotations

from layoutloom_v0.nodes.assets_io import ImageAsset, load_image_asset

from .campaign_io import Campaign


def load_product_images(campaign: Campaign) -> dict[str, ImageAsset]:
    return {p.name: load_image_asset(p.product_image) for p in campaign.products}
