from __future__ import annotations

import json
from pathlib import Path

import pytest

_V0_CONTRACT = Path(__file__).resolve().parents[1] / "loom" / "LayoutLoom-v0.json"

# Capabilities ADR-0001 records as advertised by the frozen contract but absent
# from the graph and the code. The contract is provenance, not an authoritative
# spec, so it must not claim a tool it does not contain.
_ABSENT_CAPABILITIES = ["rag", "chromadb", "guardrail", "gemma"]


@pytest.fixture
def v0_meta() -> dict:
    return json.loads(_V0_CONTRACT.read_text(encoding="utf-8"))["meta"]


def test_v0_meta_does_not_advertise_absent_capabilities(v0_meta: dict):
    advertised = f"{v0_meta['description']} {v0_meta['stack']}".lower()
    named = [cap for cap in _ABSENT_CAPABILITIES if cap in advertised]
    assert not named, f"v0 contract meta still claims absent capabilities: {named}"
