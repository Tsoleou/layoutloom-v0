"""Node "Load Campaign" (io): read the campaign file — one row per product line.

Fields per product: name / title / subtitle / cta / product_image.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProductLine:
    name: str
    title: str
    subtitle: str
    cta: str
    product_image: Path
    product_name: str = ""  # the part of the title that must own its own line (ADR-0008)


@dataclass(frozen=True)
class Campaign:
    name: str
    products: tuple[ProductLine, ...]


def load_campaign(path: Path) -> Campaign:
    if not path.is_file():
        raise FileNotFoundError(f"campaign file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    products = data.get("products")
    if not isinstance(products, list) or not products:
        raise ValueError(f"campaign file has no products: {path}")
    lines = []
    for i, p in enumerate(products):
        missing = [k for k in ("name", "title", "product_image") if not p.get(k)]
        if missing:
            raise ValueError(f"campaign product #{i} missing fields: {missing}")
        lines.append(
            ProductLine(
                name=str(p["name"]),
                title=str(p["title"]),
                subtitle=str(p.get("subtitle", "")),
                cta=str(p.get("cta", "Learn More")),
                product_image=Path(p["product_image"]),
                product_name=str(p.get("product_name", "")),
            )
        )
    return Campaign(name=str(data.get("campaign", path.stem)), products=tuple(lines))
