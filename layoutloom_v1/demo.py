"""Generate a demo campaign (two product lines + placeholder art) so the v1
pipeline runs out of the box. Real campaigns drop in their own campaign.json
and product cutouts."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from layoutloom_v0.demo_assets import ensure_demo_assets


def ensure_demo_campaign(campaign_path: Path = Path("campaign.json")) -> Path:
    # logo (shared, brand kit default path) + first product art
    ensure_demo_assets(Path("assets/demo-swift.png"), Path("assets/logo.png"))
    nitro = Path("assets/demo-nitro.png")
    if not nitro.is_file():
        nitro.parent.mkdir(parents=True, exist_ok=True)
        im = Image.new("RGBA", (640, 400), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([40, 40, 600, 360], radius=36, fill=(214, 84, 24, 255))
        d.rounded_rectangle([120, 110, 520, 290], radius=20, fill=(255, 236, 190, 255))
        im.save(nitro)
        print(f"[demo] wrote placeholder {nitro}")

    if not campaign_path.is_file():
        campaign_path.write_text(
            json.dumps(
                {
                    "campaign": "demo-laptops",
                    "products": [
                        {
                            "name": "swift",
                            "title": "Swift Go 14",
                            "subtitle": "Thin, light AI laptop with all-day battery",
                            "cta": "Shop Now",
                            "product_image": "assets/demo-swift.png",
                        },
                        {
                            "name": "nitro",
                            "title": "Nitro V 16 Gaming Monster",
                            "subtitle": "Full power, limitless performance",
                            "cta": "Learn More",
                            "product_image": "assets/demo-nitro.png",
                        },
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[demo] wrote {campaign_path}")
    return campaign_path
