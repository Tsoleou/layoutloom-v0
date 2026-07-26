"""FastAPI front door: io.input (title/subtitle + configured assets) in,
io.output (banner image + HTML) out. Run: uvicorn layoutloom_v0.api:app

Also serves the Loom Graph contract (GET /graph) so the React Flow frontend
renders the same graph the pipeline is scaffolded from, and mounts the output
directory (/output) so produced banners are fetchable by URL.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .driver import render_banner
from .node_config import config_from_nodes, default_node_configs
from .nodes.html2img import HtmlRenderer, PlaywrightRenderer, StubRenderer
from .nodes.layout_pick import ARCHETYPES

app = FastAPI(title="LayoutLoom-v0")

# The Vite dev server (default :5173) is a different origin than this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_GRAPH_PATH = Path("loom/LayoutLoom-v0.json")
# Named per-node config presets, one file each: presets/<name>.json
_PRESETS_DIR = Path("presets")
for _d in ("output", "assets", "fonts", "presets"):
    Path(_d).mkdir(parents=True, exist_ok=True)

_NAME_RE = re.compile(r"^[\w一-鿿 \-]{1,40}$")


def _preset_path(name: str) -> Path:
    """Safe path for a preset name — rejects separators / traversal / odd chars."""
    name = name.strip()
    if not _NAME_RE.match(name):
        raise HTTPException(status_code=422, detail=f"invalid preset name {name!r}")
    return _PRESETS_DIR / f"{name}.json"
# Produced banner.html / banner.png at /output; asset + font files at /assets,
# /fonts so the emitted HTML can reference them over HTTP (see asset_base_url).
app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")


class RenderRequest(BaseModel):
    # Edited per-node config, keyed by Loom node id -> {config key: value}
    # (see node_config.py). Missing nodes/keys keep their defaults.
    nodes: dict[str, dict] = {}
    # stub=True swaps in the deterministic planner + renderer (no Ollama, no
    # browser) so the frontend can be exercised fully offline.
    stub: bool = False


class PresetRequest(BaseModel):
    nodes: dict[str, dict] = {}


class CampaignRequest(BaseModel):
    # stub=True swaps in the deterministic StubMasterDesigner (no Ollama); the
    # HTML renderer stays real when Playwright is available, because the v1
    # frontend previews the final PNGs (blank stubs would show nothing).
    stub: bool = False
    # optional campaign override (same shape as campaign.json); None -> the
    # LUMOS mock campaign
    campaign: dict | None = None


class RenderResponse(BaseModel):
    spec: dict
    html_path: str
    image_path: str
    image_url: str
    html_url: str
    renderer: str  # "playwright" (real PNG) or "stub" (solid placeholder PNG)
    layout: str  # the archetype actually used (resolved when "random")
    note: str | None = None


def _real_renderer() -> tuple[HtmlRenderer, str]:
    """PlaywrightRenderer if the browser stack is importable, else degrade to the
    stub. The LLM plan + HTML are produced either way — Playwright only turns the
    HTML into a real raster PNG; the frontend previews the HTML directly, so a
    missing browser must not fail the request."""
    try:
        import playwright.sync_api  # noqa: F401
    except ModuleNotFoundError:
        return StubRenderer(), "stub"
    return PlaywrightRenderer(), "playwright"


def _validate(nodes: dict[str, dict]) -> None:
    """Reject a config that wouldn't render (bad types / unknown archetype)."""
    cfg, _, _ = config_from_nodes(nodes)
    if cfg.layout != "random" and cfg.layout not in ARCHETYPES:
        raise ValueError(f"unknown layout {cfg.layout!r}; use one of {ARCHETYPES} or 'random'")


@app.get("/graph")
def graph() -> dict:
    """The Loom Graph contract with each node's `config` filled from the current
    PipelineConfig defaults — the frontend renders these as editable fields and
    layers a chosen preset on top client-side."""
    g = json.loads(_GRAPH_PATH.read_text(encoding="utf-8"))
    defaults = default_node_configs()
    for node in g["nodes"]:
        if node["id"] in defaults:
            node["config"] = defaults[node["id"]]
    return g


@app.get("/graph/v1")
def graph_v1() -> dict:
    """The LayoutLoom-v1 contract (GDN campaign pipeline), verbatim."""
    return json.loads(Path("loom/LayoutLoom-v1.json").read_text(encoding="utf-8"))


@app.post("/render-campaign")
def render_campaign_endpoint(req: CampaignRequest) -> dict:
    """Run the whole v1 campaign pipeline; banners land under /output/campaign."""
    from dataclasses import asdict

    from layoutloom_v1.config import BrandKitConfig
    from layoutloom_v1.config import PipelineConfig as V1Config
    from layoutloom_v1.driver import render_campaign
    from layoutloom_v1.mockdata import MOCK_DIR, MOCK_PALETTE, ensure_mock_campaign

    if req.campaign is not None:
        campaign_path = Path("output/campaign-web.json")
        campaign_path.parent.mkdir(parents=True, exist_ok=True)
        campaign_path.write_text(json.dumps(req.campaign, ensure_ascii=False), encoding="utf-8")
        ensure_mock_campaign()  # custom campaigns may still reference mock art/logo
    else:
        campaign_path = ensure_mock_campaign()
    cfg = V1Config(
        campaign_path=campaign_path,
        brand=BrandKitConfig(palette=MOCK_PALETTE, logo_path=MOCK_DIR / "logo.png"),
    )

    designer = None
    note = None
    if req.stub:
        from layoutloom_v1.nodes.master_design import StubMasterDesigner

        designer = StubMasterDesigner()
    renderer, renderer_name = _real_renderer()
    if renderer_name == "stub":
        note = (
            "未偵測到 Playwright,成品為純色佔位。"
            "要出真圖:pip install -e '.[render]' && playwright install chromium"
        )

    try:
        result = render_campaign(cfg, designer=designer, renderer=renderer)
    except FileNotFoundError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"連不上 Ollama:{e}")
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"master design 無法解析:{e}")

    return {
        "design": {
            name: {"layouts": d.layouts, "style": asdict(d.style), "notes": list(d.notes)}
            for name, d in result.design.products.items()
        },
        "banners": [
            {**entry, "url": f"/output/campaign/{entry['file']}"}
            for entry in result.manifest["generated"]
        ],
        "zip_url": "/output/campaign.zip" if result.zip_path else None,
        "failures": [{"file": f.file.name, "kb": f.kb} for f in result.failures],
        "renderer": renderer_name,
        "note": note,
    }


@app.get("/presets")
def list_presets() -> dict:
    """Names of the saved presets (sorted)."""
    return {"names": sorted(p.stem for p in _PRESETS_DIR.glob("*.json"))}


@app.get("/presets/{name}")
def get_preset(name: str) -> dict:
    """One saved preset's node config."""
    path = _preset_path(name)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"no preset {name!r}")
    return {"name": name, "nodes": json.loads(path.read_text(encoding="utf-8"))}


@app.put("/presets/{name}")
def save_preset(name: str, req: PresetRequest) -> dict:
    """Create or replace a named preset (validated before it is written)."""
    path = _preset_path(name)
    try:
        _validate(req.nodes)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=f"invalid preset: {e}")
    path.write_text(json.dumps(req.nodes, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True, "name": name}


@app.delete("/presets/{name}")
def delete_preset(name: str) -> dict:
    """Delete a named preset."""
    _preset_path(name).unlink(missing_ok=True)
    return {"deleted": True, "name": name}


@app.post("/render", response_model=RenderResponse)
def render(req: RenderRequest, request: Request) -> RenderResponse:
    # Emit HTML that references assets over this server's origin, so the banner
    # (and the /output/banner.html preview iframe) loads images + font over HTTP.
    base_url = str(request.base_url).rstrip("/")
    try:
        cfg, title, subtitle = config_from_nodes(req.nodes, asset_base_url=base_url)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=f"invalid node config: {e}")
    if cfg.layout != "random" and cfg.layout not in ARCHETYPES:
        raise HTTPException(
            status_code=422,
            detail=f"unknown layout {cfg.layout!r}; use one of {ARCHETYPES} or 'random'",
        )

    planner: object | None = None
    note: str | None = None
    if req.stub:
        from .demo_assets import ensure_demo_assets
        from .nodes.planner import StubBannerPlanner

        ensure_demo_assets(cfg.product_path, cfg.logo_path)
        planner = StubBannerPlanner(cfg.asset_base_url)
        renderer, renderer_name = StubRenderer(), "stub"
    else:
        # Real LLM planner (driver default); pick the renderer by availability.
        renderer, renderer_name = _real_renderer()
        if renderer_name == "stub":
            note = (
                "未偵測到 Playwright，PNG 為純色佔位；HTML 預覽仍是真實 LLM 版面。"
                "要輸出真圖：pip install -e '.[render]' && playwright install chromium"
            )

    try:
        result = render_banner(title, subtitle, cfg, planner=planner, renderer=renderer)
    except FileNotFoundError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"連不上 Ollama（是否已 `ollama serve` 並 `ollama pull {cfg.model.model}`？）：{e}",
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"模型回應無法解析成 banner plan：{e}")

    return RenderResponse(
        spec=result.spec,
        html_path=str(result.html_path),
        image_path=str(result.image_path),
        image_url=f"/output/{result.image_path.name}",
        html_url=f"/output/{result.html_path.name}",
        renderer=renderer_name,
        layout=result.layout,
        note=note,
    )
