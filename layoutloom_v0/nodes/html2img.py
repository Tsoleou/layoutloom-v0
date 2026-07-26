"""Node "HTML2img": render banner HTML to a PNG.

The contract marks this deterministic, but rasterizing HTML needs a headless
browser — so the renderer sits behind a Protocol. PlaywrightRenderer is the
real one (pip install -e ".[render]" && playwright install chromium);
StubRenderer keeps tests browser-free.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .canvas import Canvas


class HtmlRenderer(Protocol):
    def render(self, html_path: Path, canvas: Canvas, scale: int) -> bytes: ...


class PlaywrightRenderer:
    def render(self, html_path: Path, canvas: Canvas, scale: int) -> bytes:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                viewport={"width": canvas.width, "height": canvas.height},
                device_scale_factor=scale,
            )
            page.goto(html_path.resolve().as_uri())
            page.wait_for_load_state("networkidle")
            png = page.screenshot(type="png")
            browser.close()
        return png


class StubRenderer:
    """Deterministic stand-in: a solid canvas-sized PNG, no browser."""

    def render(self, html_path: Path, canvas: Canvas, scale: int) -> bytes:
        import io

        from PIL import Image

        im = Image.new("RGB", (canvas.width * scale, canvas.height * scale), canvas.background)
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()
