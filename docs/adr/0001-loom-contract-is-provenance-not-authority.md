# The Loom contract is historical provenance, not the source of truth

LayoutLoom is a real banner-generation tool, not a demonstration of Loom-to-code
scaffolding. Given that, the running code plus `CONTEXT.md` and these ADRs are
authoritative; `loom/LayoutLoom-v0.json` and `loom/LayoutLoom-v1.json` are
frozen records of the design each surface grew from, kept for provenance but no
longer binding.

This reverses the earlier framing (CLAUDE.md said "The Loom Graph is the source
of truth"). The trigger: a real tool's authoritative spec cannot claim
capabilities that do not exist — the v0 contract's `meta.description` advertises
a "RAG pipeline / multi-layer guardrail" over "ChromaDB", none of which the
graph or code contains. As narrative in a methodology demo that is a harmless
artifact; as an authoritative spec it is misleading.

## Consequences

- The false `meta.description` / `meta.stack` fields should be corrected or
  annotated as historical, not treated as requirements.
- The `loom-check` / `loom-fill` "contract as living document" workflow is not
  adopted for this project.
- CLAUDE.md's "source of truth" line is superseded and should be updated.

## Considered alternatives

- **Keep the contract authoritative and back-fill it to match reality** —
  rejected: implies committing to the Loom methodology as part of the product,
  which the project's purpose (a real tool) does not require.
- **Split authority: contract owns node/edge topology, code owns quality** —
  rejected as unnecessary ceremony; the topology is already faithfully
  mirrored in the drivers, so nothing is gained by keeping the JSON binding.
