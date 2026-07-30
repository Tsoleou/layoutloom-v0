import { useState } from "react";
import {
  API_BASE,
  uploadAsset,
  type CampaignProduct,
  type CampaignSeed,
} from "./api";

// Editable form for a v1 campaign: name, brand palette + logo, and the list of
// product lines. Product images / logo are uploaded via POST /upload; the
// returned path is stored on the campaign so the render references the file.
// Seeded from the LUMOS mock (GET /campaign/mock) — editing is additive, the
// mock stays the offline test fixture.
export function CampaignEditor({
  seed,
  onChange,
  disabled,
}: {
  seed: CampaignSeed;
  onChange: (seed: CampaignSeed) => void;
  disabled?: boolean;
}) {
  const [uploadError, setUploadError] = useState<string | null>(null);

  const src = (path: string) => `${API_BASE}/${path}`;

  const setProduct = (i: number, patch: Partial<CampaignProduct>) =>
    onChange({
      ...seed,
      products: seed.products.map((p, j) => (j === i ? { ...p, ...patch } : p)),
    });

  const addProduct = () => {
    const n = seed.products.length + 1;
    onChange({
      ...seed,
      products: [
        ...seed.products,
        {
          name: `product-${n}`,
          product_name: "",
          title: "",
          subtitle: "",
          cta: "Learn More",
          product_image: "",
        },
      ],
    });
  };

  const removeProduct = (i: number) =>
    onChange({ ...seed, products: seed.products.filter((_, j) => j !== i) });

  const upload = async (file: File, apply: (path: string) => void) => {
    setUploadError(null);
    try {
      apply((await uploadAsset(file)).path);
    } catch (e) {
      setUploadError(String(e instanceof Error ? e.message : e));
    }
  };

  return (
    <div className="campaign-editor">
      <label>
        Campaign 名稱
        <input
          value={seed.campaign}
          disabled={disabled}
          onChange={(e) => onChange({ ...seed, campaign: e.target.value })}
        />
      </label>

      <label>品牌色 palette</label>
      <div className="palette-row">
        {seed.palette.map((c, i) => (
          <input
            key={i}
            type="color"
            className="swatch"
            value={c}
            disabled={disabled}
            title={c}
            onChange={(e) =>
              onChange({
                ...seed,
                palette: seed.palette.map((x, j) => (j === i ? e.target.value : x)),
              })
            }
          />
        ))}
      </div>

      <label>Logo</label>
      <div className="asset-row">
        {seed.logo_path && <img className="thumb" src={src(seed.logo_path)} alt="logo" />}
        <input
          type="file"
          accept="image/*"
          disabled={disabled}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) upload(f, (path) => onChange({ ...seed, logo_path: path }));
          }}
        />
      </div>

      {uploadError && <p className="error">⚠ {uploadError}</p>}

      <div className="products-head">
        <label>產品線 · {seed.products.length}</label>
        <button className="ghost" onClick={addProduct} disabled={disabled}>
          ＋ 新增
        </button>
      </div>

      {seed.products.map((p, i) => (
        <div className="product-card" key={i}>
          <div className="product-card__head">
            <span className="muted">#{i + 1}</span>
            <button className="ghost" onClick={() => removeProduct(i)} disabled={disabled}>
              刪除
            </button>
          </div>
          <div className="asset-row">
            {p.product_image && (
              <img className="thumb" src={src(p.product_image)} alt={p.name} />
            )}
            <input
              type="file"
              accept="image/*"
              disabled={disabled}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) upload(f, (path) => setProduct(i, { product_image: path }));
              }}
            />
          </div>
          <label>
            產品名（獨佔標題行）
            <input
              value={p.product_name}
              disabled={disabled}
              onChange={(e) => setProduct(i, { product_name: e.target.value })}
            />
          </label>
          <label>
            標題 title
            <input
              value={p.title}
              disabled={disabled}
              onChange={(e) => setProduct(i, { title: e.target.value })}
            />
          </label>
          <label>
            副標 subtitle
            <input
              value={p.subtitle}
              disabled={disabled}
              onChange={(e) => setProduct(i, { subtitle: e.target.value })}
            />
          </label>
          <label>
            CTA
            <input
              value={p.cta}
              disabled={disabled}
              onChange={(e) => setProduct(i, { cta: e.target.value })}
            />
          </label>
        </div>
      ))}
    </div>
  );
}
