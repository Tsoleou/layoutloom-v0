# API renders are isolated per request

Each API render writes to a unique output path (per-request subdirectory) and
returns that URL, instead of the fixed `output/banner.*` / `output/campaign.*`
paths. The fixed paths silently clobber under any concurrency and can hand one
caller another caller's asset — a correctness bug for a tool that leaves the
door open to being shared or deployed. The CLI keeps its stable default paths.

## Consequences

- Produced files accumulate on disk; a cleanup / TTL policy is a required
  follow-up before any real deployment.
- The web preview can no longer assume a fixed filename; it uses the URL
  returned by the render response.
