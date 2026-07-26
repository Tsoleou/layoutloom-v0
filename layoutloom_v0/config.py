"""Node configs from the Loom contract, surfaced as overridable settings.

Each field mirrors a node's `config` block in loom/LayoutLoom-v0.json.
Anything the contract left unsaid is an explicit default here, not a value
buried in the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CanvasConfig:
    # node "Canva"
    width: int = 1200
    height: int = 628
    background: str = "#ffffff"


@dataclass(frozen=True)
class ModelConfig:
    # node "LLM Banner Plan" — contract says gemma3:4b, but its JSON output is
    # flaky and its spatial reasoning is weak. Deliberate deviation for reliable
    # structured output: qwen2.5:7b runs fully local; gpt-oss:20b-cloud routes
    # through Ollama Cloud (needs `ollama signin`) for higher fidelity + nicer
    # design, at near-zero code change (same API, same format:"json").
    model: str = "gpt-oss:20b-cloud"
    temperature: float = 0.7
    max_tokens: int = 2048
    # assumption: contract names the Ollama stack but not the endpoint
    base_url: str = "http://localhost:11434"
    # Reasoning-model effort (Ollama `think`): "low"/"medium"/"high", or None.
    # gpt-oss reasons before answering; without a low cap it burns the whole
    # token budget on thinking and emits an empty response. Set None for
    # non-thinking models (e.g. qwen2.5:7b), which reject the `think` field.
    reasoning_effort: str | None = "low"


@dataclass(frozen=True)
class PipelineConfig:
    canvas: CanvasConfig = field(default_factory=CanvasConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    # io nodes "Load Product Image" / "Load Logo" / "Load Font"
    product_path: Path = Path("assets/product.png")
    logo_path: Path = Path("assets/logo.png")
    font_path: Path = Path("fonts/NotoSansTC-Bold.ttf")
    # How the emitted HTML references asset files:
    #   None      -> file:// URIs (offline: CLI + Playwright load from disk)
    #   "http://…" -> HTTP URLs under that origin (so the banner is viewable
    #                 over HTTP, e.g. the web preview iframe). Set by the API.
    asset_base_url: str | None = None
    # nodes "Save HTML" / "Save Image"
    html_out: Path = Path("output/banner.html")
    image_out: Path = Path("output/banner.png")
    # node "HTML2img"
    image_format: str = "png"
    render_scale: int = 2
    # Deterministic geometry guardrail over the model's plan (layout_guard.py):
    # the model owns the design, code guarantees no overlap / no clipping.
    # Set False for raw, unrepaired LLM output (original v0 semantics).
    layout_guard: bool = True
    # node "Pick Layout": archetype name from nodes/layout_pick.py::ARCHETYPES,
    # or "random" to draw one per render (the layout-diversity knob).
    layout: str = "random"
