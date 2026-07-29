"""fit_chunks: chunk-aware fitting (ADR-0006).

Unlike fit_text (which sizes from an idealised char-level balanced split),
fit_chunks sizes from the *real* composed lines — respecting phrase-chunk
boundaries — so the font never assumes a split the composer can't make.
"""
from layoutloom_v0.nodes.fitting import fit_chunks


def test_sizes_down_so_chunk_boundaries_fit_in_two_lines():
    # chunks ["限時三天"(4.2u), "全館優惠特賣"(6.3u)]. The composer will not split
    # a chunk, so the widest line is the 6.3u chunk. In a 630px box that caps
    # the font at 630/6.3 = 100px (two lines fit its 250px height under 400).
    # fit_text's balanced guess (10.5u total -> 5.25u/line) would wrongly allow
    # ~120px and force the 6.3u chunk to char-break into a third line.
    fs, lines = fit_chunks(["限時三天", "全館優惠特賣"], w=630, h=400, cap=110)
    assert lines == ["限時三天", "全館優惠特賣"]
    assert abs(fs - 100.0) < 0.5


def test_returns_none_when_two_lines_stay_below_readable_size():
    # 16 CJK chars (16.8u); a balanced two-line split is ~8.4u/line. In a 60px
    # box that caps the font at 60/8.4 = 7.1px, under the 9px minimum -> None
    # (the guard reads this as "drop it").
    assert fit_chunks(["超級無敵霹靂長的標題文字沒有標點"], w=60, h=1000, cap=200) is None
