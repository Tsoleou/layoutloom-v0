"""CLI: python -m layoutloom_v1 --campaign campaign.json [--stub] [--demo]

--demo generates a two-product demo campaign + placeholder assets first.
--stub swaps in the deterministic designer + renderer (no Ollama, no browser).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import PipelineConfig
from .driver import render_campaign


def main() -> int:
    ap = argparse.ArgumentParser(prog="layoutloom-v1")
    ap.add_argument("--campaign", default="campaign.json")
    ap.add_argument("--stub", action="store_true", help="no model, no browser")
    ap.add_argument("--demo", action="store_true", help="generate demo campaign/assets if missing")
    ap.add_argument("--mock", action="store_true",
                    help="generate the LUMOS mock campaign (4 laptop lines, drawn art) and use it")
    args = ap.parse_args()

    if args.mock:
        from .config import BrandKitConfig
        from .mockdata import MOCK_DIR, MOCK_PALETTE, ensure_mock_campaign

        campaign_path = ensure_mock_campaign()
        cfg = PipelineConfig(
            campaign_path=campaign_path,
            brand=BrandKitConfig(palette=MOCK_PALETTE, logo_path=MOCK_DIR / "logo.png"),
        )
    else:
        if args.demo:
            from .demo import ensure_demo_campaign

            ensure_demo_campaign(Path(args.campaign))
        cfg = PipelineConfig(campaign_path=Path(args.campaign))
    designer = renderer = None
    if args.stub:
        from layoutloom_v0.nodes.html2img import StubRenderer

        from .nodes.master_design import StubMasterDesigner

        designer, renderer = StubMasterDesigner(), StubRenderer()

    result = render_campaign(cfg, designer=designer, renderer=renderer)
    print(f"[banners] {len(result.manifest['generated'])} generated, "
          f"{len(result.failures)} over {cfg.max_kb}KB")
    if result.zip_path:
        print(f"[zip]     {result.zip_path}")
    if result.report_path:
        print(f"[report]  {result.report_path}")
    return 0 if not result.failures else 1


if __name__ == "__main__":
    sys.exit(main())
