"""Node "Optimize Image" (deterministic): every PNG is unconditionally
downscaled to the exact slot size (screenshots are taken at 2x for crisp
text; GDN assets must match the slot pixel-for-pixel) and palette-quantized
to leave headroom under the 150KB cap."""
from __future__ import annotations

import io

from PIL import Image

from .size_set import Size


def optimize_png(png: bytes, size: Size) -> bytes:
    im = Image.open(io.BytesIO(png)).convert("RGB")
    if im.size != (size.width, size.height):
        im = im.resize((size.width, size.height), Image.LANCZOS)
    im = im.quantize(colors=256)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
