# Static-only output is a deliberate, revisitable product boundary

Both surfaces emit static images only; animated HTML5 / GIF banners are out of
scope for now. This is a conscious boundary to keep the rendering path simple
(no timeline, per-frame rasterization, or animation-specific file-size
budgets), **not** a permanent product decision — animation is a large slice of
real GDN inventory and may be reconsidered once static output is solid.

## Consequences

- This is a real capability gap for GDN specifically; positioning should not
  claim full GDN coverage.
- The v1 contract's "no animation" note is now framed as "not yet", superseding
  the earlier "out of scope by decision" language.
