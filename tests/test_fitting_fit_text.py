"""fit_text: two-line font sizing uses the real composed longest line (ADR-0006).

The two-line branch must size from the actual balanced split's longest line,
not the old ``units * 0.55`` guess, so the fitting math agrees with the render.
"""
from layoutloom_v0.nodes.fitting import fit_text


def test_two_line_fs_uses_balanced_longest_line_not_055_guess():
    # "限時三天全館優惠" = 8 CJK chars (8.4 units). A balanced 2-line split is
    # 4/4, so the longest line is 4.2 units — not 8.4*0.55 = 4.62. In a 42-wide,
    # 30-tall box the two-line branch is width-limited: 42/4.2 = 10.0 (the old
    # 0.55 guess gave 42/4.62 = 9.09). One line would be 42/8.4 = 5.0, so the
    # larger two-line font wins.
    assert fit_text("限時三天全館優惠", 42, 30) == (10.0, 2)
