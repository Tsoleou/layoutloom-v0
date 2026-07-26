from __future__ import annotations

from pathlib import Path

from layoutloom_v0.nodes.outputs import save_html, save_image, show_text


def test_save_html_creates_parent_dirs(tmp_path: Path):
    out = save_html("<html></html>", tmp_path / "deep/dir/banner.html")
    assert out.read_text(encoding="utf-8") == "<html></html>"


def test_save_image_roundtrip(tmp_path: Path):
    out = save_image(b"\x89PNG-fake", tmp_path / "out/banner.png")
    assert out.read_bytes() == b"\x89PNG-fake"


def test_show_text_formats_unicode(capsys):
    show_text({"title": {"字級": 60}})
    assert "字級" in capsys.readouterr().out
