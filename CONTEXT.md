# LayoutLoom

A banner-generation tool with two product surfaces — v0 (single banner, LLM
composes HTML) and v1 (batch GDN campaign, LLM commits design tokens only).
This glossary pins the project's canonical vocabulary; it is a glossary, not a
spec.

## Language

### Shared

**Loom contract**:
The frozen JSON design record a surface was scaffolded from
(`loom/LayoutLoom-v0.json`, `loom/LayoutLoom-v1.json`). Historical provenance,
**not** the source of truth — the running code plus this glossary and the ADRs
are authoritative. See ADR-0001.
_Avoid_: spec, contract-as-authority.

**Surface**:
One of the two products in this repo — v0 or v1. They coexist long-term as
distinct products, not iterations of one another.
_Avoid_: version, mode.

**Archetype**:
A named layout template expressed as geometry (regions/rects), chosen before
the model plans. v0 archetypes are pixel regions per canvas; v1 archetypes are
fractional rects per ratio class.
_Avoid_: template, layout preset.

**Phrase chunk**:
An atomic, size-independent semantic unit of a text field (e.g. `限時三天`)
that line-breaking must not split. The LLM emits the chunk list; deterministic
code composes chunks into balanced, kinsoku-clean lines per box. See ADR-0006.
_Avoid_: token, word (Latin-centric), line (a chunk is not a line).

**LUMOS mock**:
The synthetic campaign fixture (`mockdata.py`: laptop lines + cutouts + wordmark
+ palette) used to exercise v1 offline without real customer data. Retained
permanently as the test fixture — the campaign editor is additive, not a
replacement.
_Avoid_: demo, sample (reserve those for v0's `--demo-assets`).

### v0 — single-banner surface

**LayoutLoom v0**:
The single-banner surface: one title + subtitle → one banner. The model
composes a self-contained HTML document directly; geometry is repaired
afterward by the Layout Guard.
_Avoid_: the old pipeline, legacy.

**Spec**:
v0's structured plan object (exit 1, shown as text), distinct from the **HTML**
(exit 2, rendered to PNG). Both come from the same model call as an
unconditional fan-out.

**Layout Guard**:
v0's deterministic post-pass that clamps the model's plan into the archetype's
regions (bounds, stacking gaps, no overlap/clipping, font fitting). Repairs
only template-shaped HTML; anything else passes through untouched.
_Avoid_: validator, critic (there is no re-prompting loop).

### v1 — batch-campaign surface

**LayoutLoom v1**:
The batch surface: a campaign (product lines) × a GDN size set → a ZIP of
pixel-exact static PNGs. One model call per campaign; deterministic nodes do
all geometry.

**Master Design**:
v1's single LLM output for a whole campaign — a layout choice per ratio class
plus style tokens per product line. The model emits **no HTML and no
geometry**; constraints are enforced mechanically and the model is never
re-asked.
_Avoid_: plan, layout (those are v0 terms).

**Adapt Layout**:
v1's mechanical expansion of one Master Design across every concrete size
(shrink-to-fit text, aspect-preserving image fit, CTA pill sizing). Cannot
produce bad geometry by construction.

**Compliance**:
v1's 150KB-per-asset gate after optimize. Pass → Pack ZIP; fail → fail report
exit. GDN assets must match slot pixel dimensions exactly.
