"""Explicit serial driver for the LayoutLoom-v1 DAG (no loops in the contract).

Topology:
  Load Campaign / Brand Kit / Size Set / Layout Catalog (+ Load Product Images)
    -> LLM Master Design  (one call for the whole campaign)
  LLM Master Design --Master Design--> Show Design                (display exit)
  LLM Master Design -> Adapt Layout -> Render HTML -> HTML2img
    -> Optimize Image -> Compliance Check --Pass--> Pack ZIP      (product exit)
                                         --Fail--> Fail Report    (short-circuit exit)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from layoutloom_v0.nodes.html2img import HtmlRenderer, PlaywrightRenderer

from .config import PipelineConfig
from .nodes.adapt_layout import adapt_layout
from .nodes.brand_kit import load_brand_kit
from .nodes.campaign_io import load_campaign
from .nodes.compliance import Failure, check_compliance
from .nodes.master_design import MasterDesign, MasterDesigner, OllamaMasterDesigner
from .nodes.optimize import optimize_png
from .nodes.outputs import fail_report, pack_zip, show_design
from .nodes.product_images import load_product_images
from .nodes.render_html import render_html
from .nodes.size_set import build_size_set


@dataclass(frozen=True)
class CampaignResult:
    """io.output: the packed banners plus everything the exits surfaced."""

    zip_path: Path | None
    manifest: dict
    design: MasterDesign
    failures: list[Failure]
    report_path: Path | None


def render_campaign(
    cfg: PipelineConfig | None = None,
    designer: MasterDesigner | None = None,
    renderer: HtmlRenderer | None = None,
) -> CampaignResult:
    cfg = cfg or PipelineConfig()
    designer = designer or OllamaMasterDesigner(cfg.model)
    renderer = renderer or PlaywrightRenderer()

    # entry nodes
    campaign = load_campaign(cfg.campaign_path)
    brand = load_brand_kit(cfg.brand)
    assets = load_product_images(campaign)
    sizes = build_size_set(cfg.sizes)

    # the single model touchpoint: one master design for the whole campaign
    design = designer.design(campaign, assets, brand, sizes)
    show_design(design)  # display exit

    # mechanical expansion: product line x size
    cfg.work_dir.mkdir(parents=True, exist_ok=True)
    generated: list[dict] = []
    files: list[Path] = []
    for line in campaign.products:
        pdesign = design.products[line.name]
        for size in sizes:
            spec, arch = adapt_layout(pdesign, line, size, assets[line.name], brand)
            html = render_html(
                spec, arch, pdesign.style, line, size, assets[line.name], brand,
                asset_base_url=cfg.asset_base_url,
            )
            stem = f"{line.name}-{size.name}"
            html_path = cfg.work_dir / f"{stem}.html"
            html_path.write_text(html, encoding="utf-8")
            png = renderer.render(html_path, size, cfg.render_scale)
            png = optimize_png(png, size)
            png_path = cfg.work_dir / f"{stem}.png"
            png_path.write_bytes(png)
            files.append(png_path)
            generated.append(
                {
                    "product": line.name,
                    "size": size.name,
                    "ratio_class": size.ratio_class,
                    "layout": arch.name,
                    "file": png_path.name,
                    "kb": round(len(png) / 1024, 1),
                }
            )

    # compliance gate -> two exits
    passed, failures = check_compliance(files, cfg.max_kb)
    manifest = {
        "campaign": campaign.name,
        "generated": generated,
        "failed": [f.file.name for f in failures],
    }
    zip_path = pack_zip(passed, manifest, cfg.zip_path) if passed else None
    report_path = (
        fail_report(failures, cfg.max_kb, cfg.work_dir / "fail_report.json") if failures else None
    )
    return CampaignResult(
        zip_path=zip_path,
        manifest=manifest,
        design=design,
        failures=failures,
        report_path=report_path,
    )
