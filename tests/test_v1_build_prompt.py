"""v1 build_prompt asks the model for per-product phrase segmentation
(ADR-0006), taught by a worked example — mirroring v0's planner prompt."""
from __future__ import annotations

from pathlib import Path

from layoutloom_v0.nodes.assets_io import FontAsset, ImageAsset
from layoutloom_v1.nodes.brand_kit import BrandKit
from layoutloom_v1.nodes.campaign_io import Campaign, ProductLine
from layoutloom_v1.nodes.master_design import build_prompt
from layoutloom_v1.nodes.size_set import Size

BRAND = BrandKit(
    palette=("#0f4c81", "#ffffff"),
    font=FontAsset(path=None, family="sans-serif"),
    logo=ImageAsset(path=Path("assets/logo.png"), width=300, height=100),
    cta_radius_px=6,
)


def test_prompt_requests_chunks_with_a_worked_example():
    campaign = Campaign(
        name="t",
        products=(ProductLine("swift", "限時三天，全館優惠", "現貨供應", "立即選購", Path("a.png")),),
    )
    assets = {"swift": ImageAsset(path=Path("a.png"), width=600, height=600)}
    prompt = build_prompt(campaign, assets, BRAND, (Size(300, 250),))
    assert '"chunks"' in prompt
    assert '["限時三天，", "全館優惠"]' in prompt
