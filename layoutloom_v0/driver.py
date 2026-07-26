"""Explicit serial driver for the LayoutLoom-v0 edge DAG.

Topology (all edges unconditional):
  Canva / Load Product Image / Load Logo / Load Font / Input Text / Input
    -> LLM Banner Plan
  LLM Banner Plan --Spec--> Show Text                       (exit 1)
  LLM Banner Plan --HTML--> Save HTML -> HTML2img -> Show Image -> Save Image  (exit 2)

The two outgoing edges from the model node carry no `when`, so this is a
fan-out, not a branch: both paths always run. No loops in the contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import PipelineConfig
from .nodes.assets_io import load_font, load_image_asset
from .nodes.canvas import make_canvas
from .nodes.html2img import HtmlRenderer, PlaywrightRenderer
from .nodes.layout_guard import repair_layout
from .nodes.layout_pick import pick_layout
from .nodes.outputs import save_html, save_image, show_image, show_text
from .nodes.planner import BannerPlanner, OllamaBannerPlanner


@dataclass(frozen=True)
class BannerResult:
    """io.output: the finished banner image and its HTML (plus the spec shown)."""

    spec: dict
    html_path: Path
    image_path: Path
    layout: str


def render_banner(
    title: str,
    subtitle: str,
    cfg: PipelineConfig | None = None,
    planner: BannerPlanner | None = None,
    renderer: HtmlRenderer | None = None,
) -> BannerResult:
    cfg = cfg or PipelineConfig()
    planner = planner or OllamaBannerPlanner(cfg.model, cfg.asset_base_url)
    renderer = renderer or PlaywrightRenderer()

    # entry nodes — no interdependencies, order is arbitrary
    canvas = make_canvas(cfg.canvas)
    product = load_image_asset(cfg.product_path)
    logo = load_image_asset(cfg.logo_path)
    font = load_font(cfg.font_path)

    # Pick Layout: archetype -> pixel regions (layout diversity lives here)
    layout = pick_layout(cfg.layout, canvas)

    # the single model touchpoint
    plan = planner.plan(canvas, product, logo, font, title, subtitle, layout)

    # Layout Guard: model designs, code guarantees the geometry
    if cfg.layout_guard:
        plan, fixes = repair_layout(plan, product, logo, layout)
        for fix in fixes:
            print(f"[layout-guard] {fix}")

    # fan-out branch 1: Spec -> Show Text
    show_text(plan.spec)

    # fan-out branch 2: HTML -> Save HTML -> HTML2img -> Show Image -> Save Image
    html_path = save_html(plan.html, cfg.html_out)
    png = renderer.render(html_path, canvas, cfg.render_scale)
    image_path = save_image(png, cfg.image_out)
    show_image(image_path)

    return BannerResult(
        spec=plan.spec, html_path=html_path, image_path=image_path, layout=layout.name
    )
