"""Mock campaign data + programmatic product art for the v1 pipeline.

Generates a fictional laptop brand ("LUMOS", four product lines echoing the
Acer GDN reference: thin-and-light / business / home / gaming) with stylised
laptop cutouts on transparent backgrounds, a wordmark logo, and a matching
campaign-mock.json. Everything is drawn with PIL at 4x supersampling and
downscaled (smooth edges, no external downloads, fully reproducible).

Run: python -m layoutloom_v1 --mock [--stub]
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

MOCK_DIR = Path("assets/mock")
MOCK_CAMPAIGN = Path("campaign-mock.json")
# brand palette the mock art is designed around (navy / gold / mist / white)
MOCK_PALETTE = ("#14213d", "#fca311", "#e8ecf4", "#ffffff")

S = 4  # supersampling factor


def _canvas(w: int, h: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def _down(im: Image.Image, w: int, h: int) -> Image.Image:
    return im.resize((w, h), Image.LANCZOS)


def _vgradient(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int], top: str, bottom: str) -> None:
    from PIL import ImageColor

    x0, y0, x1, y1 = box
    c0, c1 = ImageColor.getrgb(top), ImageColor.getrgb(bottom)
    for i in range(y0, y1):
        t = (i - y0) / max(1, y1 - y0)
        d.line(
            [(x0, i), (x1, i)],
            fill=tuple(round(a + (b - a) * t) for a, b in zip(c0, c1)),
        )


def _laptop(
    path: Path,
    screen_top: str,
    screen_bottom: str,
    body: str,
    accent: str,
    motif: str,
) -> None:
    """Front-view laptop cutout: bezel + gradient screen (with a per-line
    motif), hinge, keyboard deck, soft drop shadow. Transparent background."""
    if path.is_file():
        return
    W, H = 640, 460
    im, d = _canvas(W, H)

    # soft shadow under the deck
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        [60 * S, 400 * S, 580 * S, 444 * S], fill=(10, 10, 20, 90)
    )
    im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10 * S)))
    d = ImageDraw.Draw(im)

    # screen: dark bezel, rounded
    d.rounded_rectangle([120 * S, 20 * S, 520 * S, 330 * S], radius=18 * S, fill="#1a1d24")
    # panel (gradient) inside the bezel — draw on a sub-image then paste
    px0, py0, px1, py1 = 138 * S, 38 * S, 502 * S, 312 * S
    panel = Image.new("RGBA", (px1 - px0, py1 - py0))
    pd = ImageDraw.Draw(panel)
    _vgradient(pd, (0, 0, panel.width, panel.height), screen_top, screen_bottom)

    # per-line motif on the panel
    pw, ph = panel.width, panel.height
    if motif == "sun":  # thin & light: horizon + sun
        pd.ellipse([pw * 0.62, ph * 0.12, pw * 0.86, ph * 0.55], fill=accent)
        pd.rectangle([0, ph * 0.68, pw, ph], fill=screen_bottom)
    elif motif == "chart":  # business: rising bars
        for i, bh in enumerate((0.28, 0.42, 0.36, 0.58, 0.74)):
            x = pw * (0.12 + i * 0.16)
            pd.rounded_rectangle(
                [x, ph * (0.86 - bh), x + pw * 0.09, ph * 0.86], radius=6 * S, fill=accent
            )
    elif motif == "waves":  # home: gentle arcs
        for i in range(3):
            y = ph * (0.35 + i * 0.2)
            pd.arc([-pw * 0.2, y, pw * 1.2, y + ph * 0.5], 200, 340, fill=accent, width=8 * S)
    elif motif == "blaze":  # gaming: diagonal energy stripes
        for i in range(4):
            x = pw * (0.15 + i * 0.22)
            pd.polygon(
                [(x, ph), (x + pw * 0.10, ph * 0.18), (x + pw * 0.20, ph * 0.18), (x + pw * 0.10, ph)],
                fill=accent if i % 2 == 0 else "#ffffff22",
            )
    im.paste(panel, (px0, py0))
    d = ImageDraw.Draw(im)

    # camera dot + hinge + deck
    d.ellipse([318 * S, 26 * S, 324 * S, 32 * S], fill="#3a3f4a")
    d.rounded_rectangle([150 * S, 330 * S, 490 * S, 342 * S], radius=5 * S, fill="#0e1015")
    d.rounded_rectangle([60 * S, 342 * S, 580 * S, 408 * S], radius=16 * S, fill=body)
    # keyboard hint + touchpad
    d.rounded_rectangle([130 * S, 352 * S, 510 * S, 380 * S], radius=6 * S, fill="#1a1d24")
    d.rounded_rectangle([270 * S, 386 * S, 370 * S, 402 * S], radius=6 * S, fill="#3a3f4a")
    # accent power light
    d.ellipse([556 * S, 370 * S, 566 * S, 380 * S], fill=accent)

    _down(im, W, H).save(path)
    print(f"[mock] wrote {path}")


def _logo(path: Path, font_path: Path) -> None:
    """Wordmark logo: gold rounded-square icon with an 'L' cut + LUMOS text."""
    if path.is_file():
        return
    W, H = 560, 150
    im, d = _canvas(W, H)
    d.rounded_rectangle([10 * S, 15 * S, 130 * S, 135 * S], radius=26 * S, fill=MOCK_PALETTE[1])
    d.rectangle([48 * S, 40 * S, 72 * S, 110 * S], fill=MOCK_PALETTE[0])
    d.rectangle([48 * S, 86 * S, 104 * S, 110 * S], fill=MOCK_PALETTE[0])
    try:
        font = ImageFont.truetype(str(font_path), 88 * S)
        d.text((160 * S, 28 * S), "LUMOS", font=font, fill=MOCK_PALETTE[0])
    except OSError:
        d.rectangle([160 * S, 45 * S, 520 * S, 105 * S], fill=MOCK_PALETTE[0])
    _down(im, W, H).save(path)
    print(f"[mock] wrote {path}")


PRODUCTS = [
    {
        "name": "aero",
        "product_name": "Aero 14",
        "title": "Aero 14 Ultralight",
        "subtitle": "997g all-magnesium body, 28-hour battery",
        "cta": "Shop Now",
        "art": ("#8ecae6", "#e8f4fb", "#c9ccd4", "#fca311", "sun"),
    },
    {
        "name": "travelpro",
        "product_name": "TravelPro 15",
        "title": "TravelPro 15 for Business",
        "subtitle": "Military-grade durable, one-tap video calls",
        "cta": "See Plans",
        "art": ("#2b3a55", "#5a6b8c", "#3c414c", "#fca311", "chart"),
    },
    {
        "name": "vista",
        "product_name": "Vista 16",
        "title": "Vista 16 Big-Screen at Home",
        "subtitle": "16-inch 2.5K eye-care display, share with the family",
        "cta": "View Deals",
        "art": ("#2a9d8f", "#bde8e2", "#e3e6ec", "#fca311", "waves"),
    },
    {
        "name": "strike",
        "product_name": "Strike 17",
        "title": "Strike 17 Gaming Beast",
        "subtitle": "RTX 5080, 240Hz blazing-fast display",
        "cta": "Go All Out",
        "art": ("#1a1d24", "#4a1020", "#14161c", "#fca311", "blaze"),
    },
]


def ensure_mock_campaign(
    campaign_path: Path = MOCK_CAMPAIGN,
    font_path: Path = Path("fonts/NotoSansTC-Bold.ttf"),
) -> Path:
    MOCK_DIR.mkdir(parents=True, exist_ok=True)
    _logo(MOCK_DIR / "logo.png", font_path)
    for p in PRODUCTS:
        _laptop(MOCK_DIR / f"{p['name']}.png", *p["art"])

    if not campaign_path.is_file():
        campaign_path.write_text(
            json.dumps(
                {
                    "campaign": "lumos-laptops-2026-q3",
                    "products": [
                        {
                            "name": p["name"],
                            "product_name": p["product_name"],
                            "title": p["title"],
                            "subtitle": p["subtitle"],
                            "cta": p["cta"],
                            "product_image": str(MOCK_DIR / f"{p['name']}.png"),
                        }
                        for p in PRODUCTS
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[mock] wrote {campaign_path}")
    return campaign_path
