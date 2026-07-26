"""Nodes "Show Design" / "Pack ZIP" / "Fail Report".

Show Design is the display exit for the model's decisions (which archetype per
ratio class, which style tokens — the full judgment surface). Pack ZIP is the
main product exit (PNGs + manifest). Fail Report is the compliance
short-circuit exit."""
from __future__ import annotations

import json
import zipfile
from dataclasses import asdict
from pathlib import Path

from .compliance import Failure
from .master_design import MasterDesign


def show_design(design: MasterDesign) -> str:
    payload = {
        name: {"layouts": d.layouts, "style": asdict(d.style), "notes": list(d.notes)}
        for name, d in design.products.items()
    }
    if design.notes:
        payload["_notes"] = list(design.notes)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(f"[master-design]\n{text}")
    return text


def pack_zip(files: list[Path], manifest: dict, zip_path: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=f.name)
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"[zip] {zip_path} ({len(files)} banners)")
    return zip_path


def fail_report(failures: list[Failure], max_kb: int, report_path: Path) -> Path:
    report = {
        "max_kb": max_kb,
        "failures": [{"file": str(f.file), "kb": f.kb, "over_kb": round(f.kb - max_kb, 1)} for f in failures],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[fail-report] {len(failures)} banner(s) over {max_kb}KB -> {report_path}")
    return report_path
