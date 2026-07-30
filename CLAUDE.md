# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A banner-generator pipeline **scaffolded from a Loom Graph design contract**
(`loom/LayoutLoom-v0.json`, schema 0.4.0). An LLM (Ollama / `gemma3:4b`) plans
the layout and emits a self-contained HTML document; deterministic code handles
saving, HTML→PNG rendering, and display. This is the **v0 contract design**
(LLM directly produces HTML) and is deliberately separate from
`~/Projects/LayoutLoom` (the rebuilt deterministic engine).

## Commands

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

pytest                          # full offline suite (stub planner + stub renderer, no net/browser)
pytest tests/test_driver.py     # one file
pytest tests/test_planner_parse.py::test_parses_clean_json   # one test

# Offline smoke test of the wiring (no Ollama, no browser):
python -m layoutloom_v0 --title "Big Sale" --subtitle "Three Days Only" --stub --demo-assets

# Real run (needs `ollama pull gemma3:4b` + a headless browser):
pip install -e ".[render]" && playwright install chromium
python -m layoutloom_v0 --title "Big Sale" --subtitle "Three Days Only" --demo-assets

# API:
uvicorn layoutloom_v0.api:app --port 8012
# POST /render {"title","subtitle","stub"?} -> {spec, html_path, image_path, image_url}
# GET  /graph  -> the Loom contract JSON;  /output/<name> serves produced files
# stub:true swaps in StubBannerPlanner+StubRenderer (offline, no Ollama/browser)

# Frontend (React + React Flow) — needs the API running:
cd web && npm install && npm run dev   # http://localhost:5173
```

## Architecture

The Loom Graph is the source of truth. Each node in the contract maps to code,
and `config.py` mirrors every node's `config` block — anything the contract left
unstated is an **explicit default in `config.py`**, never a value buried in the
pipeline.

Graph → code:

| Loom node | kind | Code |
|---|---|---|
| Canva | deterministic | `nodes/canvas.py::make_canvas` |
| Load Product Image / Load Logo / Load Font | io | `nodes/assets_io.py` |
| Input Text / Input | deterministic | the `title` / `subtitle` args (API/CLI) |
| Pick Layout | deterministic | `nodes/layout_pick.py` — archetype → pixel regions; **layout diversity lives here** (`cfg.layout`: name or `"random"`) |
| LLM Banner Plan | model | `nodes/planner.py` — the **only** model touchpoint; receives the Layout |
| Layout Guard | deterministic | `nodes/layout_guard.py` — clamps the plan into the Layout's regions (`cfg.layout_guard`) |
| Show Text | deterministic | `nodes/outputs.py::show_text` (exit 1: the Spec) |
| Save HTML → HTML2img → Show Image → Save Image | deterministic | `nodes/outputs.py` + `nodes/html2img.py` (exit 2: the finished image) |

`web/` is a Vite + React + React Flow frontend (per `meta.stack`): it reads
`GET /graph` and renders the Loom contract as a node diagram whose nodes carry
**editable config fields** — every configurable parameter lives on the node
that owns it (Canva → width/height, LLM Banner Plan → model/temperature/…,
Pick Layout → layout, …). Editing is per-node (`LoomNode` + `configContext`),
and `POST /render` sends `{nodes: {id: config}}`. `node_config.py` is the single
bridge between those node config blocks and `PipelineConfig`
(`config_from_nodes` / `default_node_configs`) — the graph→config mapping that
otherwise only lived in this doc's table. `GET /graph` fills each node's
`config` with the current `config.py` defaults so the UI shows real values.
Edits can be saved as **named presets** (`presets/<name>.json`): the frontend
has a preset dropdown and the API is a small CRUD (`GET /presets`,
`GET|PUT|DELETE /presets/{name}`; PUT validates before writing, names are
sanitized against path traversal). The last-selected preset is remembered in
`localStorage` and re-applied on load; a preset is layered over the defaults
client-side, so a key it omits keeps its `config.py` value. Config can also be
exported as a downloadable JSON. The
preview is an **iframe of the produced `banner.html`** (rendered by the real
browser), not the PNG — because `StubRenderer` emits a blank solid-fill
placeholder, so in stub mode only the HTML shows a true banner. `api.py` adds
CORS for the Vite origin, a `stub` request flag (offline planner/renderer), and
mounts `/output`, `/assets`, `/fonts` as static. A non-stub `/render` runs the real LLM planner but
**degrades the renderer to `StubRenderer` (placeholder PNG + a `note`) when
Playwright isn't installed** — the browser only rasterizes the PNG, and the
frontend previews the HTML directly, so a real LLM layout is testable without a
browser. Ollama/parse failures surface as 502s, not 500 tracebacks. For the iframe to load images/font over HTTP, `/render`
sets `cfg.asset_base_url` to the request origin so the emitted HTML references
assets by HTTP URL instead of `file://`. The graph layout is computed
client-side in `web/src/graph.ts` (longest-path layering; the contract carries
no node positions).

**`driver.py::render_banner` is the whole pipeline.** The graph is linear plus a
single unconditional fan-out from the model node (both `Spec` and `HTML` edges
have `when: null`, so both paths always run — it is a fan-out, not a branch) and
has no loops, so it is written as one explicit serial function rather than a
graph executor. This is the entry point to understand before anything else.

### Seams for testing (the key design idea)

Two nodes need the outside world; both sit behind a `typing.Protocol` with a
real impl + an offline stub, injected into `render_banner`:

- `BannerPlanner` (`nodes/planner.py`): `OllamaBannerPlanner` (HTTP to Ollama)
  vs. `StubBannerPlanner` (deterministic fixed layout). Prompt building
  (`build_prompt`) and response parsing (`parse_plan_response`) are **pure
  functions**, unit-tested independently of the network. `parse_plan_response`
  is deliberately tolerant — it slices to the outermost `{...}` to survive
  markdown fences and surrounding prose.
- `HtmlRenderer` (`nodes/html2img.py`): `PlaywrightRenderer` (headless Chromium)
  vs. `StubRenderer` (solid canvas-sized PNG via Pillow). HTML2img is marked
  deterministic in the contract but needs a browser, so it is isolated here.

`--stub` (CLI) / passing stub instances (tests) swaps both, making the entire
pipeline runnable with no model, no browser, and no network.

## LayoutLoom-v1 (GDN batch pipeline)

`layoutloom_v1/` implements the second contract, `loom/LayoutLoom-v1.json`
(drafted via loom-draft in-session): campaign file (product lines) x GDN size
set -> ZIP of static PNGs. Run: `python -m layoutloom_v1 --demo [--stub]`, or
`--mock` for the LUMOS mock campaign (`mockdata.py`: 4 laptop lines with
PIL-drawn transparent cutouts + wordmark logo + matching palette — the
realistic fixture for eyeballing output quality).
Key semantics, deliberately different from v0:

- **The LLM emits no HTML and no geometry.** `nodes/master_design.py` makes
  ONE call per campaign: it sees every product line's copy lengths + product
  image aspect ratios + brand palette + size classes + archetype catalog, and
  commits to a layout per ratio class plus style tokens per product line.
  `parse_master_design` enforces constraints mechanically (snap off-palette
  colours, fix <3:1 contrast, fall back on unknown archetype names) and logs
  to `notes` — the model is never re-asked. There is no Layout Guard in v1:
  nothing downstream can produce bad geometry.
- `nodes/layout_catalog.py`: archetypes are per-element **fractional rects,
  disjoint by construction** (tests verify), two per ratio class
  (rectangle / banner / skyscraper — classified in `nodes/size_set.py`).
  `nodes/adapt_layout.py` expands design x size mechanically: shrink-to-fit
  text with a 2-line budget (larger-font option wins), aspect-preserving image
  fit, CTA pill sizing; an unfittable subtitle is dropped, never squeezed.
- Screenshots at 2x, then `nodes/optimize.py` downscales to the **exact slot
  size** (GDN assets must match pixel-for-pixel) + palette-quantizes;
  `nodes/compliance.py` gates at 150KB -> Pack ZIP (pass) / fail report exit.
- Reuses v0's `HtmlRenderer/PlaywrightRenderer/StubRenderer` and asset
  loaders; `StubMasterDesigner` + `StubRenderer` keep the whole campaign
  pipeline offline-testable. v0 stays fully runnable and untouched.
- Web: the frontend has a **v0 單張 / v1 Campaign mode switch**. v1
  integration: `GET /graph/v1` (contract for the node canvas), `GET
  /campaign/mock` (the LUMOS campaign as an editable seed), `POST /upload`
  (multipart product-image / logo upload → `assets/uploads/`, served over
  `/assets`), and `POST /render-campaign`
  (`{stub, campaign?, palette?, logo_path?}`; all-None -> LUMOS mock).
  The canvas toggles between the node graph and a **full-set grid** (banners
  grouped per product across all sizes). v1's `stub` only stubs the
  *designer* — the renderer stays Playwright when available, because the grid
  shows final PNGs (a stubbed renderer would show blank fills).
- **Campaign editor** (`web/src/CampaignEditor.tsx`, ticket #2): the v1 panel
  seeds from `GET /campaign/mock` and lets you edit the campaign name, brand
  palette, and per-product-line copy, add/remove lines, and upload logo +
  product images (`POST /upload` → path stored on the campaign). Render sends
  the edited campaign + palette + logo to `/render-campaign`. `api.py`'s
  `_resolve_brand` threads the palette/logo into `BrandKitConfig` (mock brand
  when unset); `_safe_upload_name` sanitizes upload filenames. The LUMOS mock
  is **retained** as the offline test fixture — the editor is additive.
  No named-campaign save/load yet (a follow-up, like v0 presets).
- Out of scope by decision: GIF/animation, i18n. Not yet built: v1 node-config
  editing in the web UI, named-campaign persistence, rembg cutouts.

## Deliberate contract deviations (documented assumptions)

These are choices made where the contract was silent or self-contradictory —
all adjustable:

1. `meta.description` says "RAG pipeline / multi-layer guardrail" and
   `meta.stack` lists ChromaDB, but the graph has **no retrieval node and no
   guardrail branch**. The graph wins; that description and ChromaDB are ignored.
2. The LLM receives asset **metadata** (path + pixel size), not pixels; the HTML
   references asset files by URL. `cfg.asset_base_url` selects the scheme:
   `None` → `file://` (offline CLI/Playwright load from disk); an HTTP origin
   (set by the API) → HTTP URLs served from `/assets` + `/fonts`.
3. A missing font file degrades to a system sans-serif stack (no `@font-face`
   emitted) rather than failing the render.
4. No critic/validation *loop* — the contract has no loop, so there is no
   re-prompting. But the **Layout Guard node** is a deterministic post-pass
   over the model's plan (on by default, `cfg.layout_guard=False` for raw
   output): the model owns the design (colours, font sizes, proportions), code
   guarantees the geometry (region bounds, stacking gaps, no overlap, no
   clipping, aspect ratio, absolute positioning + text-align even when the
   model mangles them). It only repairs template-shaped HTML; anything else
   passes through untouched. Echoes the guardrail idea in `meta.description`.
   Layout diversity is the **Pick Layout node**: archetypes
   (`text-left` / `text-right` / `text-top`) are data in
   `nodes/layout_pick.py`; `"random"` draws one per render. The archetype's
   regions parameterize the prompt, the stub planner's `reference_spec`, and
   the guard — one source of truth per layout, so every archetype carries the
   same geometric guarantees. **v0 is canvas-size-aware** (the web UI lets you
   edit Canva width/height): margins/gutters scale with the canvas, archetypes
   unsuitable for the canvas's ratio class are coerced (banner -> side-by-side
   only, skyscraper -> text-top only), and the guard fits fonts to the actual
   copy width (two-line budget, real wrapped heights in the stack, subtitle
   dropped when it can't reach 9px). The shared helpers live in
   `nodes/fitting.py` (`classify`/`fit_text`) and are the same ones v1's
   Size Set / Adapt Layout use — one source of truth for geometry math.
5. The contract names `gemma3:4b`, but the `config.py` default is
   `gpt-oss:20b-cloud` (via Ollama Cloud, needs `ollama signin`). gemma3:4b
   produced malformed JSON and overlaps; `qwen2.5:7b` runs fully local and is
   the offline fallback (measured 5/5 valid layouts *with the guard*); the
   cloud model is 5/6 valid *before* the guard and composes better. The prompt
   carries no-overlap + design-system rules, a worked spec example, and a
   mandatory HTML template — models follow a concrete example far better than
   prose. Reasoning models need `cfg.model.reasoning_effort` (Ollama `think`):
   gpt-oss defaults to `"low"`, or it burns the whole token budget thinking and
   returns an empty response; set it to `None` for non-thinking models like
   qwen2.5:7b, which reject the field.
