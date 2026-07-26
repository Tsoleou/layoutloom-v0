// Thin client for the FastAPI backend. Override the base with VITE_API_BASE.
export const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8012";

// --- Loom Graph contract shapes (subset the frontend reads) ---
export type LoomKind = "deterministic" | "io" | "model";

export interface LoomNode {
  id: string;
  kind: LoomKind;
  intent: string;
  inputs: Record<string, string>;
  outputs: Record<string, string>;
  config: Record<string, unknown>;
}

export interface LoomEdge {
  from: string;
  to: string;
  from_port: string;
  to_port: string;
  when: string | null;
}

export interface LoomGraph {
  meta: { product: string; description: string; stack: string };
  io: { input: string; output: string };
  nodes: LoomNode[];
  edges: LoomEdge[];
}

export interface RenderResult {
  spec: Record<string, unknown>;
  html_path: string;
  image_path: string;
  image_url: string;
  html_url: string;
  renderer: string; // "playwright" | "stub"
  layout: string; // archetype actually used (resolved when "random")
  note?: string | null;
}

export type PipelineVersion = "v0" | "v1";

export async function fetchGraph(version: PipelineVersion = "v0"): Promise<LoomGraph> {
  const path = version === "v1" ? "/graph/v1" : "/graph";
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

// --- v1 campaign pipeline ---

export interface CampaignBanner {
  product: string;
  size: string;
  ratio_class: string;
  layout: string;
  file: string;
  kb: number;
  url: string;
}

export interface CampaignResult {
  design: Record<string, unknown>;
  banners: CampaignBanner[];
  zip_url: string | null;
  failures: { file: string; kb: number }[];
  renderer: string;
  note?: string | null;
}

export async function renderCampaign(
  stub: boolean,
  campaign?: object,
): Promise<CampaignResult> {
  const res = await fetch(`${API_BASE}/render-campaign`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ stub, campaign: campaign ?? null }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `POST /render-campaign failed: ${res.status}`);
  }
  return res.json();
}

type Configs = Record<string, Record<string, unknown>>;

export async function listPresets(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/presets`);
  if (!res.ok) throw new Error(`GET /presets failed: ${res.status}`);
  return (await res.json()).names as string[];
}

export async function getPreset(name: string): Promise<Configs> {
  const res = await fetch(`${API_BASE}/presets/${encodeURIComponent(name)}`);
  if (!res.ok) throw new Error(`GET /presets/${name} failed: ${res.status}`);
  return (await res.json()).nodes as Configs;
}

export async function savePreset(name: string, nodes: Configs): Promise<void> {
  const res = await fetch(`${API_BASE}/presets/${encodeURIComponent(name)}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ nodes }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `PUT /presets/${name} failed: ${res.status}`);
  }
}

export async function deletePreset(name: string): Promise<void> {
  const res = await fetch(`${API_BASE}/presets/${encodeURIComponent(name)}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`DELETE /presets/${name} failed: ${res.status}`);
}

export async function renderBanner(
  nodes: Record<string, Record<string, unknown>>,
  stub: boolean,
): Promise<RenderResult> {
  const res = await fetch(`${API_BASE}/render`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ nodes, stub }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `POST /render failed: ${res.status}`);
  }
  return res.json();
}
