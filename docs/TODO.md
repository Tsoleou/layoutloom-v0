# TODO

Implementation to-dos agreed in the 2026-07-26 `grill-with-docs` session
(commit `bab3b20`). Every item has an ADR or grilling-question backing it; none
is coded yet. Listed in recommended build order.

Workflow: already-decided items (e.g. #6) go straight to `/tdd`. Genuinely new,
undecided features get `/grill-with-docs` first, then `/tdd`. `/tdd` auto-reads
`CONTEXT.md` + the ADRs, so it picks up the design context on its own.

| # | To-do | Backing | Notes |
|---|---|---|---|
| 1 | **Line-breaking composer** — LLM phrase segmentation + deterministic code composer | [ADR-0006](adr/0006-line-breaking-phrase-segmentation.md) | Recommended first. Pure function `fitting.py::compose_lines`, offline-TDD-friendly. Also replaces `fit_text`'s `units*0.55` guess with the real longest composed line. |
| 2 | **Campaign editor + asset upload** — unblocks v1 real use | Q8 | LUMOS mock is **retained** as the offline test fixture; the editor is additive, not a replacement. |
| 3 | **Model fallback** — cloud-first `gpt-oss:20b-cloud`, auto-retry once on local `qwen2.5:7b` | [ADR-0002](adr/0002-cloud-first-model-with-local-fallback.md) | Triggers on a 502 / not-signed-in cloud failure. |
| 4 | **Subtitle-drop logging** — v1 `adapt_layout` records dropped subtitles | Q6 | Append a note per (product line × size); never drop silently. |
| 5 | **API per-request output isolation** — unique output path per request | [ADR-0005](adr/0005-api-renders-are-isolated-per-request.md) | Fixed `output/banner.*` clobbers under concurrency. CLI keeps stable paths; disk cleanup/TTL is a follow-up. |
| 6 | **Fix contract lies** — correct/annotate `loom/*.json` `meta.description` | [ADR-0001](adr/0001-loom-contract-is-provenance-not-authority.md) | Claims RAG / ChromaDB / guardrail that don't exist. Doc-only. |
| 7 | **Update CLAUDE.md** — drop the "Loom Graph is the source of truth" line | [ADR-0001](adr/0001-loom-contract-is-provenance-not-authority.md) | Superseded by ADR-0001. Doc-only. |

For #1, the TDD seam and tracer order are already agreed — see
[ADR-0006](adr/0006-line-breaking-phrase-segmentation.md).
