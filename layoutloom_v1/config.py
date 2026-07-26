"""Node configs from the LayoutLoom-v1 contract, surfaced as overridable
settings. Each field mirrors a node's `config` block in
loom/LayoutLoom-v1.json; anything the contract left unsaid is an explicit
default here, never a value buried in the pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BrandKitConfig:
    # node "Brand Kit"
    palette: tuple[str, ...] = ("#0f4c81", "#83c5be", "#111111", "#ffffff")
    font_path: Path = Path("fonts/NotoSansTC-Bold.ttf")
    logo_path: Path = Path("assets/logo.png")
    cta_radius_px: int = 6


@dataclass(frozen=True)
class ModelConfig:
    # node "LLM Master Design"
    model: str = "gpt-oss:20b-cloud"
    temperature: float = 0.7
    max_tokens: int = 4096
    base_url: str = "http://localhost:11434"
    # Ollama `think` level for reasoning models; None for models without it.
    reasoning_effort: str | None = "low"


@dataclass(frozen=True)
class PipelineConfig:
    # node "Load Campaign"
    campaign_path: Path = Path("campaign.json")
    brand: BrandKitConfig = field(default_factory=BrandKitConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    # node "Size Set" — GDN sizes to produce
    sizes: tuple[tuple[int, int], ...] = (
        (300, 250),
        (336, 280),
        (728, 90),
        (300, 600),
        (160, 600),
        (320, 100),
        (970, 250),
    )
    # node "HTML2img" — screenshot at 2x for crisp text, Optimize downscales
    # back to the exact slot size (GDN assets must match the slot pixel-for-pixel)
    image_format: str = "png"
    render_scale: int = 2
    # node "Compliance Check"
    max_kb: int = 150
    # node "Pack ZIP"
    zip_path: Path = Path("output/campaign.zip")
    # working dir for per-banner html/png
    work_dir: Path = Path("output/campaign")
    # None -> file:// asset URIs; an HTTP origin -> served URLs (like v0)
    asset_base_url: str | None = None
