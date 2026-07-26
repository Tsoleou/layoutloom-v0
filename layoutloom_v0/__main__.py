"""CLI: python -m layoutloom_v0 --title 主標題 --subtitle 副標題

--stub swaps in the deterministic planner + renderer (no Ollama, no browser)
so the wiring can be exercised offline.
"""
from __future__ import annotations

import argparse
import sys

from .config import PipelineConfig
from .demo_assets import ensure_demo_assets
from .driver import render_banner


def main() -> int:
    ap = argparse.ArgumentParser(prog="layoutloom-v0")
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", required=True)
    ap.add_argument("--stub", action="store_true", help="no model, no browser")
    ap.add_argument("--demo-assets", action="store_true", help="create placeholder assets if missing")
    ap.add_argument("--layout", default="random", help="layout archetype or 'random'")
    args = ap.parse_args()

    cfg = PipelineConfig(layout=args.layout)
    if args.demo_assets:
        ensure_demo_assets(cfg.product_path, cfg.logo_path)

    planner = renderer = None
    if args.stub:
        from .nodes.html2img import StubRenderer
        from .nodes.planner import StubBannerPlanner

        planner, renderer = StubBannerPlanner(), StubRenderer()

    result = render_banner(args.title, args.subtitle, cfg, planner=planner, renderer=renderer)
    print(f"[layout] {result.layout}")
    print(f"[html]  {result.html_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
