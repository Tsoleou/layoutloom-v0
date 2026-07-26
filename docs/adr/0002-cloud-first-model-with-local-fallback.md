# Cloud-first model with automatic local fallback

The default planner model is `gpt-oss:20b-cloud` (better composition, measured
5/6 valid before the guard), but when the cloud call fails — not signed in, or
a 502 — the pipeline automatically retries once with the local `qwen2.5:7b`
instead of hard-failing. A real tool must produce *something* without making
`ollama signin` a prerequisite.

## Consequences

- Output quality is non-deterministic across the cloud/local boundary; a
  fallback render will look different from a cloud render. Acceptable because
  the alternative is a hard 502.
- Reverses the current behaviour (no model-level fallback; cloud failure → 502).
  The renderer already degrades Playwright → Stub; this extends the same
  fail-soft posture to the model.

## Considered alternatives

- **Local-first (`qwen2.5:7b`) default** — rejected: quality-first is the
  priority for a real asset tool; cloud composes better.
- **No fallback, friendlier error** — rejected: a real tool should not
  hard-fail on a missing sign-in when a local model is available.
