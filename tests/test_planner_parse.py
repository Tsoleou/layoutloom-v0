from __future__ import annotations

import json

import pytest

from layoutloom_v0.nodes.planner import parse_plan_response


def _payload() -> str:
    return json.dumps({"spec": {"title": {"font_size_px": 60}}, "html": "<html></html>"})


def test_parses_clean_json():
    plan = parse_plan_response(_payload())
    assert plan.spec["title"]["font_size_px"] == 60
    assert plan.html == "<html></html>"


def test_tolerates_fences_and_prose():
    plan = parse_plan_response("Here you go:\n```json\n" + _payload() + "\n```\nDone.")
    assert plan.html == "<html></html>"


@pytest.mark.parametrize("bad", ["no json here", '{"spec": {}}', '{"html": "<p>"}', '{"spec": {}, "html": ""}'])
def test_rejects_missing_fields(bad: str):
    with pytest.raises(ValueError):
        parse_plan_response(bad)
