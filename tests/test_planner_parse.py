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


def test_extracts_model_supplied_chunks():
    payload = json.dumps(
        {
            "spec": {"title": {}},
            "html": "<html></html>",
            "chunks": {"title": ["限時三天，", "全館優惠"]},
        }
    )
    assert parse_plan_response(payload).chunks == {"title": ["限時三天，", "全館優惠"]}


def test_absent_chunks_default_to_empty_for_guard_fallback():
    # No "chunks" key: parse leaves it empty; the guard segments the HTML text.
    assert parse_plan_response(_payload()).chunks == {}
