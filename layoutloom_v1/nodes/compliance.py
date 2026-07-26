"""Node "Compliance Check" (deterministic): every banner must be <= max_kb
(GDN's 150KB asset cap). Splits the set into a pass list and a fail list —
the driver ships the passes and short-circuits the fails to the report exit."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Failure:
    file: Path
    kb: float


def check_compliance(files: list[Path], max_kb: int) -> tuple[list[Path], list[Failure]]:
    passed: list[Path] = []
    failed: list[Failure] = []
    for f in files:
        kb = f.stat().st_size / 1024
        if kb <= max_kb:
            passed.append(f)
        else:
            failed.append(Failure(file=f, kb=round(kb, 1)))
    return passed, failed
