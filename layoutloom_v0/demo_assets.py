"""Generate placeholder product/logo images so the pipeline runs out of the box.

The contract's io nodes expect assets/product.png and assets/logo.png to
exist; real projects drop their own files there.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def ensure_demo_assets(product: Path, logo: Path) -> None:
    if not product.is_file():
        product.parent.mkdir(parents=True, exist_ok=True)
        im = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([60, 60, 540, 540], fill=(30, 90, 180, 255))
        d.ellipse([180, 180, 420, 420], fill=(255, 255, 255, 255))
        im.save(product)
        print(f"[demo] wrote placeholder {product}")
    if not logo.is_file():
        logo.parent.mkdir(parents=True, exist_ok=True)
        im = Image.new("RGBA", (300, 100), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, 299, 99], radius=20, fill=(20, 20, 20, 255))
        d.rectangle([30, 35, 270, 65], fill=(240, 200, 40, 255))
        im.save(logo)
        print(f"[demo] wrote placeholder {logo}")
