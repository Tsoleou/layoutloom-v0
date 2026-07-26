import { API_BASE, type CampaignResult } from "./api";

// Behance-style full-set view: every product line's banners across all GDN
// sizes, grouped per product, at (down-scaled) natural proportions.
export function CampaignGrid({ result, version }: { result: CampaignResult; version: number }) {
  const byProduct = new Map<string, typeof result.banners>();
  for (const b of result.banners) {
    byProduct.set(b.product, [...(byProduct.get(b.product) ?? []), b]);
  }
  return (
    <div className="campaign-grid">
      {[...byProduct.entries()].map(([product, banners]) => (
        <section key={product}>
          <h3>{product}</h3>
          <div className="campaign-grid__row">
            {banners.map((b) => (
              <figure key={b.file}>
                <img src={`${API_BASE}${b.url}?v=${version}`} alt={`${product} ${b.size}`} />
                <figcaption>
                  {b.size} · {b.layout} · {b.kb}KB
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
