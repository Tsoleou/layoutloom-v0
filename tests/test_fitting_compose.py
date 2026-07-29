"""compose_lines: the deterministic phrase-chunk line composer (ADR-0006)."""
from layoutloom_v0.nodes.fitting import compose_lines


def test_all_chunks_fit_on_one_line():
    # Two short CJK phrases with a generous width budget: fill-first keeps
    # them on a single joined line rather than balancing into two.
    assert compose_lines(["限時三天", "全館優惠"], max_units=20) == ["限時三天全館優惠"]


def test_breaks_at_chunk_boundary_when_joined_overflows():
    # Joined width ~8.4 units exceeds the budget, but each 4-char chunk (~4.2)
    # fits alone: break at the boundary, one chunk per line, never mid-chunk.
    assert compose_lines(["限時三天", "全館優惠"], max_units=5) == ["限時三天", "全館優惠"]


def test_single_oversized_chunk_falls_back_to_char_breaking():
    # One 5-char chunk (~5.25 units) with a 3-char budget (3.15): no chunk
    # boundary to break at, so break within the chunk at characters.
    assert compose_lines(["限時三天全"], max_units=3.15) == ["限時三", "天全"]


def test_balances_line_widths_across_forced_break():
    # Greedy fill would pack line 1 full (限時三天全館 ~6.3) and orphan 優惠 (~2.1).
    # Two lines are forced either way, so balance them: 限時三天 / 全館優惠 (4.2/4.2).
    assert compose_lines(["限時三天", "全館", "優惠"], max_units=6.3) == ["限時三天", "全館優惠"]


def test_latin_breaks_at_word_boundary_not_mid_word():
    # "Aero Ultralight" (9.0 units) overflows a 6.0 budget. Character breaking
    # would orphan "light" ("Aero Ultra"/"light"); breaking at the space keeps
    # each word whole. Trailing break-point space is trimmed.
    assert compose_lines(["Aero Ultralight"], max_units=6.0) == ["Aero", "Ultralight"]


def test_hyphenated_compound_breaks_after_hyphen():
    # "Big-Screen" (6.0 units) overflows a 4.0 budget: break after the hyphen,
    # keeping the hyphen on the leading line, not mid-word.
    assert compose_lines(["Big-Screen"], max_units=4.0) == ["Big-", "Screen"]


def test_single_word_wider_than_box_still_char_breaks():
    # A single long word with no space or hyphen (3.6 units) must still fall
    # back to character breaking rather than overflow — the last resort.
    assert compose_lines(["Business"], max_units=2.4) == ["Busi", "ness"]


def test_kinsoku_pulls_line_start_punctuation_onto_previous_line():
    # A punctuation-level fallback chunk "。全館" would put the fullwidth period
    # at the start of line 2 (行頭禁則 — no punctuation may begin a line). Kinsoku
    # pulls the "。" up onto the end of line 1, accepting slight overflow
    # (限時三天。 ~5.25 > 4.2) rather than orphaning the mark at a line start.
    assert compose_lines(["限時三天", "。全館"], max_units=4.2) == ["限時三天。", "全館"]
