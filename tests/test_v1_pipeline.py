"""End-to-end v1 wiring with the deterministic stubs: demo campaign -> ZIP of
exact-size PNGs + manifest; tiny max_kb forces the fail-report exit."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from PIL import Image

from layoutloom_v0.nodes.html2img import StubRenderer
from layoutloom_v1.config import BrandKitConfig, PipelineConfig
from layoutloom_v1.demo import ensure_demo_campaign
from layoutloom_v1.driver import render_campaign
from layoutloom_v1.nodes.master_design import StubMasterDesigner

SIZES = ((300, 250), (728, 90), (160, 600))


def _cfg(tmp_path: Path, **over) -> PipelineConfig:
    import os

    os.chdir(tmp_path)  # demo assets + campaign paths are relative
    ensure_demo_campaign(tmp_path / "campaign.json")
    return PipelineConfig(
        campaign_path=tmp_path / "campaign.json",
        brand=BrandKitConfig(font_path=tmp_path / "missing.ttf"),
        sizes=SIZES,
        zip_path=tmp_path / "out/campaign.zip",
        work_dir=tmp_path / "out/campaign",
        **over,
    )


def test_stub_campaign_produces_zip_with_all_banners(tmp_path: Path):
    cfg = _cfg(tmp_path)
    result = render_campaign(cfg, designer=StubMasterDesigner(), renderer=StubRenderer())

    assert result.zip_path and result.zip_path.is_file()
    assert not result.failures and result.report_path is None
    # 2 products x 3 sizes
    assert len(result.manifest["generated"]) == 6

    with zipfile.ZipFile(result.zip_path) as zf:
        names = set(zf.namelist())
        assert "manifest.json" in names
        assert len(names) == 7  # 6 banners + manifest
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["campaign"] == "demo-laptops"
        # every PNG is exactly its slot size (GDN requirement)
        for entry in manifest["generated"]:
            w, h = map(int, entry["size"].split("x"))
            im = Image.open(io.BytesIO(zf.read(entry["file"])))
            assert im.size == (w, h), entry["file"]


def test_master_design_is_shown_and_recorded(tmp_path: Path):
    cfg = _cfg(tmp_path)
    result = render_campaign(cfg, designer=StubMasterDesigner(), renderer=StubRenderer())
    assert set(result.design.products) == {"swift", "nitro"}
    for entry in result.manifest["generated"]:
        assert entry["layout"]  # the chosen archetype is traceable per banner


def test_oversize_banners_take_fail_exit(tmp_path: Path):
    cfg = _cfg(tmp_path, max_kb=0)  # everything fails
    result = render_campaign(cfg, designer=StubMasterDesigner(), renderer=StubRenderer())
    assert result.zip_path is None
    assert len(result.failures) == 6
    assert result.report_path and result.report_path.is_file()
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert len(report["failures"]) == 6
