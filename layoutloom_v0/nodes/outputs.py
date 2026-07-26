"""Nodes "Show Text" / "Save HTML" / "Show Image" / "Save Image".

Show Text and Show Image are display exits — in this scaffold they format for
stdout and pass data through; the API surfaces the same values in its response.
The save nodes are the file side effects.
"""
from __future__ import annotations

import json
from pathlib import Path


def show_text(spec: dict) -> str:
    text = json.dumps(spec, ensure_ascii=False, indent=2)
    print(f"[spec]\n{text}")
    return text


def save_html(html: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def show_image(image_path: Path) -> Path:
    print(f"[image] {image_path}")
    return image_path


def save_image(png: bytes, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return path
