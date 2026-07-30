"""Mock data generator: produces a loadable campaign whose art actually loads."""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image

from layoutloom_v1.mockdata import MOCK_DIR, ensure_mock_campaign
from layoutloom_v1.nodes.campaign_io import load_campaign
from layoutloom_v1.nodes.product_images import load_product_images


def test_mock_campaign_generates_and_loads(tmp_path: Path):
    os.chdir(tmp_path)  # generator writes relative paths
    path = ensure_mock_campaign(tmp_path / "campaign-mock.json", font_path=tmp_path / "missing.ttf")

    campaign = load_campaign(path)
    assert len(campaign.products) == 4
    assets = load_product_images(campaign)
    assert set(assets) == {"aero", "travelpro", "vista", "strike"}
    for asset in assets.values():
        assert asset.width > 0 and asset.height > 0
        with Image.open(asset.path) as im:
            assert im.mode == "RGBA"  # transparent cutouts
    assert (MOCK_DIR / "logo.png").is_file()


def test_mock_products_carry_product_name(tmp_path: Path):
    os.chdir(tmp_path)
    path = ensure_mock_campaign(tmp_path / "campaign-mock.json", font_path=tmp_path / "missing.ttf")
    campaign = load_campaign(path)
    names = {p.name: p.product_name for p in campaign.products}
    # each product name is the leading, own-line portion of its title
    assert names["aero"] == "Aero 14"
    assert names["vista"] == "Vista 16"
    for line in campaign.products:
        assert line.title.startswith(line.product_name)  # a clean prefix so the tagline splits


def test_mock_generation_is_idempotent(tmp_path: Path):
    os.chdir(tmp_path)
    p1 = ensure_mock_campaign(tmp_path / "c.json", font_path=tmp_path / "missing.ttf")
    before = (MOCK_DIR / "aero.png").stat().st_mtime_ns
    p2 = ensure_mock_campaign(tmp_path / "c.json", font_path=tmp_path / "missing.ttf")
    assert p1 == p2
    assert (MOCK_DIR / "aero.png").stat().st_mtime_ns == before  # not rewritten
