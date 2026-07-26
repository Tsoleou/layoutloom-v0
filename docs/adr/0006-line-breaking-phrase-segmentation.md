# Line-breaking: LLM segments phrases, code composes lines

Line-break quality (especially for CJK copy with no spaces) is owned by a
hybrid seam that mirrors the project's "model designs, code guarantees"
principle: the LLM emits **phrase segmentation** — a size-independent list of
atomic semantic chunks per text field, e.g. `["限時三天", "全館優惠"]` — and
deterministic code composes lines per box (never splitting a chunk unless it
alone overflows, balancing line widths, applying kinsoku and orphan rules,
fitting to width).

The segmentation is *linguistic, not geometric*, so it survives v1's one-call
constraint: v1's master design makes a single campaign-level call and never
sees individual sizes, yet the same chunks drive wrapping correctly at every
size. Chunks that don't fit fall back to in-chunk breaking; no LLM / stub
paths degrade to punctuation- or character-level chunks with the same
code-side composer.

## Consequences

- Replaces the browser's greedy auto-wrap, which broke CJK phrases at arbitrary
  characters and mismatched the fitting math.
- Lets `fit_text` measure the actual longest composed line instead of the
  `units * 0.55` two-line guess — fitting and render finally agree.
- The composer (balance + kinsoku + orphan) is pure and deterministic, so it is
  unit-testable and identical across both surfaces and the stub paths.

## Considered alternatives

- **Per-size pre-split lines from the LLM** — rejected: wrapping is
  size-dependent, so a fixed split cannot serve v1's one-call model.
- **Two mechanisms (v0 `<br>`, v1 chunks)** — rejected: two line-break paths to
  maintain for no gain; phrase segmentation serves the single fixed v0 box too.
- **Pure-code (no LLM)** — rejected as the primary path: cannot tell that
  `限時三天` is one semantic unit; retained only as the stub/fallback composer.
