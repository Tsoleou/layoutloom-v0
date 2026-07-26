# v0 is a human-in-the-loop surface; the Layout Guard gap is accepted

v0's Layout Guard repairs only template-shaped HTML and passes anything else
through untouched, so the model can in principle emit a banner the guard cannot
fix. This is accepted, not a bug: v0 is an interactive single-banner surface
with a live HTML preview, so a bad layout is visible on screen and the user
regenerates. A deterministic safety net is deliberately *not* built.

## Consequences

- v0 must not be relied on for **unattended / batch** rendering — there is no
  guarantee of geometric correctness without a human looking at the preview.
  Batch, geometry-safe generation is v1's job.
- If v0 ever gains an unattended code path, this decision must be revisited
  (the likely fix: render the Spec deterministically into the archetype's
  regions as a fallback, mirroring v1).
