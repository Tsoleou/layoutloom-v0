# v1 is compliance-grade production infrastructure, not a design tool

v1 is positioned as a **deterministic, compliance-gated mass-production layer**
for programmatic display advertising — not a tool that competes on the aesthetic
quality of a single banner. Its defensible value is the "model designs, code
guarantees" split (ADR-0006's principle, generalized): the model commits to a
design once per campaign, and deterministic code guarantees every produced
artifact is overlap-free, in-region, on-palette, contrast-safe, pixel-exact per
slot, and under the platform's file-size cap (`nodes/compliance.py`). That
guarantee is worth little for one hero image and decisive for a thousand
variants.

The trigger is a positioning question: a frontier model asked to generate a
banner directly will out-design v1's archetype catalog on any single artifact,
and the gap widens as models gain vision, self-checking, and image generation.
Competing there is a losing bet. But "generate one beautiful banner" is not the
job GDN / retail-media / marketplace advertising actually has. That job is
**dozens-to-hundreds of pixel-precise, brand-locked, spec-compliant size
variants, reproducibly** — where one-off chat generation is unreliable on
pixel precision, file-size compliance, and cross-size consistency, and where
`notes`-logged mechanical corrections (palette snap, contrast fix, archetype
fallback, dropped subtitle) give the auditability volume production needs.

Crucially, the model is a swappable seam (`MasterDesigner` Protocol), so a
frontier model — including Claude — is the **best designer to plug in, not the
competitor**. The moat is the constraint-enforcement + size-expansion layer
below the seam, and it only grows more valuable as the plugged-in model improves:
a better designer raises quality without weakening any guarantee.

This binds v1 only. v0 stays the human-in-the-loop single-banner surface
(ADR-0003) — a different job.

## Consequences

- **Roadmap leans toward guarantees and scale, not flair.** Prioritize:
  broader compliance coverage (more sizes / ratio classes / ad platforms, and
  animation once static is solid per ADR-0004); a pluggable frontier designer
  behind the existing seam (cloud model per ADR-0002); campaign + asset
  ingestion at volume (#7 editor + upload); and surfacing the audit trail
  (`notes`, compliance fail reports) as a first-class output.
- **De-prioritize** single-banner visual sophistication as a headline feature,
  per-element aesthetic knobs, and anything that trades determinism or
  reproducibility for one-off flair.
- **The deterministic path stays model-agnostic.** No model-specific behavior
  leaks below the `MasterDesigner` seam; parsing keeps enforcing constraints
  mechanically regardless of which model produced the design (the no-rework
  principle).
- **Positioning language** is "deterministic execution / guarantee layer for
  ad production", not "AI banner designer". Marketing must not claim aesthetic
  parity with frontier generative design; it claims guarantees, scale, and
  reproducibility those tools do not offer.

## Considered alternatives

- **Position v1 as an AI design tool competing on aesthetics** — rejected: it
  loses to frontier models on any single artifact, the small local model caps
  quality, and it abandons the guarantee/scale value that is actually
  defensible.
- **Treat frontier models as the competitor to beat** — rejected: they are the
  ideal designer for the swappable seam; competing means fighting your best
  complement instead of adopting it.
- **Stay generic ("banners for anyone")** — rejected: no wedge. The
  compliance-and-scale pain is specific to programmatic display / retail media;
  a generic single-banner generator has no reason to exist beside a frontier
  model.
