"""Bridge between the Loom graph's per-node `config` blocks and PipelineConfig.

The graph is the source of truth: every editable parameter belongs to the node
whose `config` block declares it (Canva owns width/height, LLM Banner Plan owns
model/temperature, ...). This module is the single place that maps each
(node id, config key) to its PipelineConfig field — the translation that used
to live only in CLAUDE.md's node→code table. The frontend renders each node's
config as editable fields; on render it posts them back keyed by node id, and
config_from_nodes() reassembles a PipelineConfig.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

from .config import CanvasConfig, ModelConfig, PipelineConfig

DEFAULT_TITLE = "大促銷"
DEFAULT_SUBTITLE = "限時三天"


def _reasoning(v: Any) -> str | None:
    return None if v in (None, "", "none", "None") else str(v)


@dataclass(frozen=True)
class Param:
    node: str  # Loom node id
    key: str  # config key on that node
    group: str  # "canvas" | "model" | "title" | "subtitle" | "top"
    field: str  # PipelineConfig (or nested) attribute name
    cast: Callable[[Any], Any]  # JSON value -> typed value


# One row per editable parameter. Order here is the display order in a node.
PARAMS: list[Param] = [
    Param("Canva", "width", "canvas", "width", int),
    Param("Canva", "height", "canvas", "height", int),
    Param("Canva", "background", "canvas", "background", str),
    Param("Load Product Image", "path", "top", "product_path", Path),
    Param("Load Logo", "path", "top", "logo_path", Path),
    Param("Load Font", "path", "top", "font_path", Path),
    Param("Input Text", "value", "title", "", str),
    Param("Input", "value", "subtitle", "", str),
    Param("Pick Layout", "layout", "top", "layout", str),
    Param("LLM Banner Plan", "model", "model", "model", str),
    Param("LLM Banner Plan", "temperature", "model", "temperature", float),
    Param("LLM Banner Plan", "max_tokens", "model", "max_tokens", int),
    Param("LLM Banner Plan", "reasoning_effort", "model", "reasoning_effort", _reasoning),
    Param("Layout Guard", "enabled", "top", "layout_guard", bool),
    Param("Save HTML", "path", "top", "html_out", Path),
    Param("HTML2img", "format", "top", "image_format", str),
    Param("HTML2img", "scale", "top", "render_scale", int),
    Param("Save Image", "path", "top", "image_out", Path),
]

_BY_NODE_KEY = {(p.node, p.key): p for p in PARAMS}


def _current(cfg: PipelineConfig, p: Param) -> Any:
    if p.group == "canvas":
        return getattr(cfg.canvas, p.field)
    if p.group == "model":
        return getattr(cfg.model, p.field)
    if p.group == "title":
        return DEFAULT_TITLE
    if p.group == "subtitle":
        return DEFAULT_SUBTITLE
    return getattr(cfg, p.field)


def _display(value: Any) -> Any:
    """JSON-serializable form for the graph endpoint (Path->str, None->'')."""
    if isinstance(value, Path):
        return str(value)
    if value is None:
        return ""
    return value


def default_node_configs(cfg: PipelineConfig | None = None) -> dict[str, dict]:
    """Current defaults, keyed by node id -> {config key: value}, so GET /graph
    can present config.py's real values as the editable node fields."""
    cfg = cfg or PipelineConfig()
    out: dict[str, dict] = {}
    for p in PARAMS:
        out.setdefault(p.node, {})[p.key] = _display(_current(cfg, p))
    return out


def config_from_nodes(
    nodes: dict[str, dict], asset_base_url: str | None = None
) -> tuple[PipelineConfig, str, str]:
    """Reassemble a PipelineConfig (plus title/subtitle) from edited node configs.
    Unknown node/key pairs are ignored; missing ones keep their defaults."""
    canvas_kw: dict[str, Any] = {}
    model_kw: dict[str, Any] = {}
    top_kw: dict[str, Any] = {}
    title, subtitle = DEFAULT_TITLE, DEFAULT_SUBTITLE

    for node_id, conf in (nodes or {}).items():
        for key, value in conf.items():
            p = _BY_NODE_KEY.get((node_id, key))
            if p is None:
                continue
            v = p.cast(value)
            if p.group == "canvas":
                canvas_kw[p.field] = v
            elif p.group == "model":
                model_kw[p.field] = v
            elif p.group == "title":
                title = v
            elif p.group == "subtitle":
                subtitle = v
            else:
                top_kw[p.field] = v

    cfg = PipelineConfig(
        canvas=replace(CanvasConfig(), **canvas_kw),
        model=replace(ModelConfig(), **model_kw),
        asset_base_url=asset_base_url,
        **top_kw,
    )
    return cfg, title, subtitle
