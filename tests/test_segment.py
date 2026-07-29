"""segment_text: the deterministic fallback phrase segmenter (ADR-0006).

The LLM emits phrase chunks; when it doesn't (stub, or a response missing the
key), this splits on trailing punctuation so the composer still has semantic
boundaries to break at instead of arbitrary characters.
"""
from layoutloom_v0.nodes.fitting import segment_text


def test_splits_on_trailing_punctuation_keeping_the_mark():
    # A fullwidth comma ends a clause: break after it, keeping the mark on the
    # preceding chunk (so the composer never orphans it at a line start).
    assert segment_text("限時三天，全館優惠") == ["限時三天，", "全館優惠"]
