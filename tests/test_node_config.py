"""The node-config bridge: graph defaults reflect PipelineConfig, and edited
node values round-trip back into a typed PipelineConfig."""
from __future__ import annotations

from pathlib import Path

from layoutloom_v0.config import PipelineConfig
from layoutloom_v0.node_config import (
    DEFAULT_SUBTITLE,
    DEFAULT_TITLE,
    config_from_nodes,
    default_node_configs,
)


def test_defaults_mirror_pipeline_config():
    cfg = PipelineConfig()
    d = default_node_configs(cfg)
    assert d["Canva"]["width"] == cfg.canvas.width
    assert d["LLM Banner Plan"]["model"] == cfg.model.model
    assert d["Pick Layout"]["layout"] == cfg.layout
    assert d["Layout Guard"]["enabled"] is cfg.layout_guard
    # Paths are stringified, None -> "" for JSON
    assert d["Load Product Image"]["path"] == str(cfg.product_path)
    assert d["Input Text"]["value"] == DEFAULT_TITLE


def test_none_reasoning_effort_round_trips():
    d = default_node_configs(PipelineConfig(model=__import__("layoutloom_v0.config", fromlist=["ModelConfig"]).ModelConfig(reasoning_effort=None)))
    assert d["LLM Banner Plan"]["reasoning_effort"] == ""  # None -> "" for display
    cfg, _, _ = config_from_nodes({"LLM Banner Plan": {"reasoning_effort": ""}})
    assert cfg.model.reasoning_effort is None


def test_edits_round_trip_into_typed_config():
    nodes = {
        "Canva": {"width": 800, "height": 400, "background": "#111111"},
        "Pick Layout": {"layout": "text-top"},
        "LLM Banner Plan": {"model": "qwen2.5:7b", "temperature": 0.2, "max_tokens": 999},
        "Layout Guard": {"enabled": False},
        "HTML2img": {"scale": 3, "format": "png"},
        "Load Logo": {"path": "assets/mylogo.png"},
        "Input Text": {"value": "新標題"},
        "Input": {"value": "新副標"},
    }
    cfg, title, subtitle = config_from_nodes(nodes, asset_base_url="http://x")
    assert (cfg.canvas.width, cfg.canvas.height, cfg.canvas.background) == (800, 400, "#111111")
    assert cfg.layout == "text-top"
    assert cfg.model.model == "qwen2.5:7b"
    assert cfg.model.temperature == 0.2 and cfg.model.max_tokens == 999
    assert cfg.layout_guard is False
    assert cfg.render_scale == 3
    assert cfg.logo_path == Path("assets/mylogo.png")
    assert cfg.asset_base_url == "http://x"
    assert (title, subtitle) == ("新標題", "新副標")


def test_empty_nodes_yields_defaults():
    cfg, title, subtitle = config_from_nodes({})
    assert cfg.canvas.width == PipelineConfig().canvas.width
    assert (title, subtitle) == (DEFAULT_TITLE, DEFAULT_SUBTITLE)


def test_unknown_keys_ignored():
    cfg, _, _ = config_from_nodes({"Canva": {"bogus": 1}, "Nope": {"x": 2}})
    assert cfg.canvas.width == PipelineConfig().canvas.width
