# Product-name and leading-punctuation line rules are deterministic guarantees

Two line-break rules join the composer, both as **code-side guarantees** rather
than model decisions — extending ADR-0006's "model designs, code guarantees"
split and ADR-0007's determinism-at-scale positioning.

## The rules

1. **Product name owns its own line.** A campaign product line carries an
   explicit `product_name` field, separate from the rest of the title (the
   tagline). When a banner's title is rendered, the product name is **always on
   its own first line and is never split**; the tagline composes into the
   remaining line budget below it. The product name is a source-of-truth input,
   **not** something the model segments or a heuristic guesses.

2. **No wrapped line may begin with punctuation.** When a title or subtitle
   wraps and a line would start with a punctuation mark (CJK *or* ASCII), the
   mark is by default **pulled onto the end of the previous line** (追い込み).
   If pulling it up would push the previous line past its width budget, the mark
   is **dropped** instead of overflowing or being orphaned at the line start.

The title line budget is **product name (1 line) + tagline within the
remaining budget**, defaulting to ≤2 lines total (tagline gets one line,
shrink-to-fit). The tagline font shrinks before the product name does; the
product name is never shrunk below the readable minimum. Because the product
name is never shrunk below that minimum and is never split, a name too long for
a narrow box at the minimum font is allowed to clip — "never split / never
below minimum" wins over "never overflow", the same trade-off the title already
makes by never being dropped.

The `product_name` is required to be a **leading substring of the title**; the
tagline is the remainder after it. When it is not a prefix the tagline cannot
be located, so the rule degrades to normal (free-wrapping) title composition
rather than guessing — a documented, deliberate fallback, not a guarantee.

## Node placement

- **Rule 1 — data** enters at the **Campaign input** node (`product_name` on the
  product line; the mock campaign splits it out). **Enforcement** lives in the
  **Adapt Layout** node (v1): it composes the title as "product-name line +
  tagline lines" and fits the font so both hold. v1-only — v0 has no product
  line. The "own line" policy stays in Adapt Layout and is **not** pushed down
  into the shared composer, so the composer gains no parameter v0 will never use.
- **Rule 2** lives in the **shared composer** (the kinsoku / line-composition
  helper) and so fires from both the **Adapt Layout** node (v1) and the
  **Layout Guard** node (v0) — one rule, both surfaces.
- Neither rule touches the **Master Design** (model) node. The model may see the
  product name as prompt context, but owns neither guarantee.

## Consequences

- The composer's leading-punctuation set widens from CJK-only to include ASCII
  marks, and its move-up becomes conditional (move up, else drop) — so it now
  needs the line's width budget to decide.
- Adapt Layout stops treating the title as a single free-wrapping field; it
  always reserves the first line for the product name.
- v0 gets Rule 2 for free through the shared composer; it does not get Rule 1.
- Existing CJK kinsoku behaviour is preserved (move-up remains the default).

## Considered alternatives

- **Identify the product name via the model's first chunk, or a code
  heuristic** — rejected: the explicit field is deterministic and reliable in
  the stub path, matching ADR-0007; a small model or a brand+model-number regex
  is fragile across naming conventions.
- **Only guarantee the product name is never split (break at its boundary when
  wrapping), without forcing its own line** — rejected: the chosen rule is the
  stronger "always its own line" for layout consistency.
- **Apply the leading-punctuation guard to the subtitle only** — rejected:
  two divergent line-break behaviours for title vs subtitle is a smell; the
  guard applies to both.
- **Push the product-name "own line" policy into the shared composer** —
  rejected: v0 has no product line, so it would be speculative generality; the
  policy stays in Adapt Layout.
