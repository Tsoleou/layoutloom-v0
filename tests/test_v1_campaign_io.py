"""Load Campaign node: the campaign file may carry an explicit product_name per
product line (the part that must own its own title line — ADR-0008)."""
from __future__ import annotations

import json
from pathlib import Path

from layoutloom_v1.nodes.campaign_io import load_campaign


def _write(tmp_path: Path, product: dict) -> Path:
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"products": [product]}, ensure_ascii=False), encoding="utf-8")
    return path


def test_reads_explicit_product_name(tmp_path: Path):
    path = _write(tmp_path, {
        "name": "aero", "title": "Aero 14 Ultralight", "product_name": "Aero 14",
        "subtitle": "light", "cta": "Shop", "product_image": "p.png",
    })
    line = load_campaign(path).products[0]
    assert line.product_name == "Aero 14"


def test_product_name_defaults_to_empty(tmp_path: Path):
    path = _write(tmp_path, {
        "name": "aero", "title": "Aero 14 Ultralight", "product_image": "p.png",
    })
    line = load_campaign(path).products[0]
    assert line.product_name == ""
