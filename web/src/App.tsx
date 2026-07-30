import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import {
  API_BASE,
  deletePreset,
  fetchGraph,
  fetchMockCampaign,
  getPreset,
  listPresets,
  renderBanner,
  renderCampaign,
  savePreset,
  type CampaignResult,
  type CampaignSeed,
  type LoomGraph,
  type PipelineVersion,
  type RenderResult,
} from "./api";
import { toFlow, type LoomNodeData } from "./graph";
import { LoomNode } from "./LoomNode";
import { BannerPreview } from "./BannerPreview";
import { CampaignEditor } from "./CampaignEditor";
import { CampaignGrid } from "./CampaignGrid";
import { ConfigContext } from "./configContext";

const nodeTypes = { loom: LoomNode };
const LAST_PRESET_KEY = "layoutloom.lastPreset";

type Configs = Record<string, Record<string, unknown>>;

// Preset may hold only some keys per node — layer it over the defaults so any
// key it omits keeps the config.py value (and stray keys are dropped).
function mergeOverDefaults(defaults: Configs, preset: Configs): Configs {
  return Object.fromEntries(
    Object.entries(defaults).map(([id, def]) => [
      id,
      Object.fromEntries(Object.keys(def).map((k) => [k, preset[id]?.[k] ?? def[k]])),
    ]),
  );
}

export function App() {
  const [graph, setGraph] = useState<LoomGraph | null>(null);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<LoomNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Per-node editable config, seeded from GET /graph (config.py defaults).
  const [configs, setConfigs] = useState<Configs>({});
  const [defaults, setDefaults] = useState<Configs>({});
  const [presetNames, setPresetNames] = useState<string[]>([]);
  const [selected, setSelected] = useState(""); // "" = config.py defaults
  const [stub, setStub] = useState(true);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<RenderResult | null>(null);
  const [renderCount, setRenderCount] = useState(0);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [presetMsg, setPresetMsg] = useState<string | null>(null);

  // v1 (GDN campaign) state
  const [mode, setMode] = useState<PipelineVersion>("v0");
  const [campaignBusy, setCampaignBusy] = useState(false);
  const [campaignResult, setCampaignResult] = useState<CampaignResult | null>(null);
  const [campaignError, setCampaignError] = useState<string | null>(null);
  const [campaignCount, setCampaignCount] = useState(0);
  const [v1View, setV1View] = useState<"graph" | "grid">("graph");
  // Editable campaign, seeded from the LUMOS mock on first entry to v1 mode.
  const [seed, setSeed] = useState<CampaignSeed | null>(null);

  const setConfig = useCallback((nodeId: string, key: string, value: unknown) => {
    setConfigs((c) => ({ ...c, [nodeId]: { ...c[nodeId], [key]: value } }));
  }, []);

  // Mode switch re-fetches the matching contract for the canvas.
  useEffect(() => {
    fetchGraph(mode)
      .then((g) => {
        setGraph(g);
        const flow = toFlow(g);
        setNodes(flow.nodes);
        setEdges(flow.edges);
      })
      .catch((e) => setGraphError(String(e)));
  }, [mode, setNodes, setEdges]);

  // Seed the editor from the mock campaign the first time v1 mode is opened.
  useEffect(() => {
    if (mode !== "v1" || seed) return;
    fetchMockCampaign()
      .then(setSeed)
      .catch((e) => setCampaignError(String(e)));
  }, [mode, seed]);

  const onRenderCampaign = useCallback(async () => {
    setCampaignBusy(true);
    setCampaignError(null);
    try {
      const result = seed
        ? await renderCampaign(
            stub,
            { campaign: seed.campaign, products: seed.products },
            seed.palette,
            seed.logo_path,
          )
        : await renderCampaign(stub);
      setCampaignResult(result);
      setCampaignCount((n) => n + 1);
      setV1View("grid");
    } catch (e) {
      setCampaignError(String(e instanceof Error ? e.message : e));
    } finally {
      setCampaignBusy(false);
    }
  }, [stub, seed]);

  const onResetCampaign = useCallback(() => {
    setCampaignError(null);
    fetchMockCampaign()
      .then(setSeed)
      .catch((e) => setCampaignError(String(e)));
  }, []);

  // Load the v0 config defaults + preset list once (the canvas itself is
  // owned by the mode effect above); re-apply the last selected preset.
  useEffect(() => {
    Promise.all([fetchGraph("v0"), listPresets().catch((): string[] => [])])
      .then(async ([g, names]) => {
        const def: Configs = Object.fromEntries(
          g.nodes
            .filter((n) => n.config && Object.keys(n.config).length > 0)
            .map((n) => [n.id, { ...n.config }]),
        );
        setDefaults(def);
        setPresetNames(names);
        const last = localStorage.getItem(LAST_PRESET_KEY) ?? "";
        if (last && names.includes(last)) {
          setSelected(last);
          setConfigs(mergeOverDefaults(def, await getPreset(last)));
        } else {
          setConfigs(def);
        }
      })
      .catch((e) => setGraphError(String(e)));
  }, []);

  const onSelectPreset = useCallback(
    async (name: string) => {
      setPresetMsg(null);
      setSelected(name);
      localStorage.setItem(LAST_PRESET_KEY, name);
      try {
        setConfigs(name ? mergeOverDefaults(defaults, await getPreset(name)) : defaults);
      } catch (e) {
        setPresetMsg(String(e instanceof Error ? e.message : e));
      }
    },
    [defaults],
  );

  const onSaveAs = useCallback(async () => {
    const name = window.prompt("Preset 名稱：", selected || "")?.trim();
    if (!name) return;
    setPresetMsg(null);
    try {
      await savePreset(name, configs);
      const names = await listPresets();
      setPresetNames(names);
      setSelected(name);
      localStorage.setItem(LAST_PRESET_KEY, name);
      setPresetMsg(`已儲存「${name}」✓`);
    } catch (e) {
      setPresetMsg(String(e instanceof Error ? e.message : e));
    }
  }, [configs, selected]);

  const onDeletePreset = useCallback(async () => {
    if (!selected || !window.confirm(`刪除 preset「${selected}」？`)) return;
    setPresetMsg(null);
    try {
      await deletePreset(selected);
      setPresetNames(await listPresets());
      setSelected("");
      localStorage.removeItem(LAST_PRESET_KEY);
      setConfigs(defaults);
      setPresetMsg("已刪除 ✓");
    } catch (e) {
      setPresetMsg(String(e instanceof Error ? e.message : e));
    }
  }, [selected, defaults]);

  const onExport = useCallback(() => {
    const blob = new Blob([JSON.stringify({ nodes: configs }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selected || "layoutloom"}-preset.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [configs, selected]);

  const onRender = useCallback(async () => {
    setBusy(true);
    setRenderError(null);
    try {
      setResult(await renderBanner(configs, stub));
      setRenderCount((n) => n + 1);
    } catch (e) {
      setRenderError(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  }, [configs, stub]);

  // Cache-bust with the render count so a re-render shows the new banner
  // (the output path is always the same file).
  const previewSrc = useMemo(
    () => (result ? `${API_BASE}${result.html_url}?v=${renderCount}` : null),
    [result, renderCount],
  );

  return (
    <div className="app">
      <aside className="panel">
        <h1>LayoutLoom</h1>
        <div className="mode-tabs">
          <button
            className={mode === "v0" ? "active" : ""}
            onClick={() => setMode("v0")}
          >
            v0 單張
          </button>
          <button
            className={mode === "v1" ? "active" : ""}
            onClick={() => setMode("v1")}
          >
            v1 Campaign
          </button>
        </div>
        {graph && (
          <p className="muted">
            {graph.meta.product} · {graph.nodes.length} nodes
            {mode === "v0" ? " · 參數在節點內編輯 →" : " · GDN 批次產出"}
          </p>
        )}

        <label className="checkbox">
          <input type="checkbox" checked={stub} onChange={(e) => setStub(e.target.checked)} />
          {mode === "v0" ? "Stub 模式（免 Ollama / 瀏覽器）" : "Stub 模型（免 Ollama;圖仍真渲染）"}
        </label>

        {mode === "v1" && (
          <>
            <button onClick={onRenderCampaign} disabled={campaignBusy || !graph}>
              {campaignBusy
                ? "Rendering campaign…"
                : `Render Campaign · ${seed?.products.length ?? 0} 產品線`}
            </button>
            <p className="muted">
              {seed?.products.length ?? 0} 產品線 × 7 GDN 尺寸 ={" "}
              {(seed?.products.length ?? 0) * 7} 張。
              {!stub && "真跑每張約數秒(一次 master design + 逐張截圖)。"}
            </p>
            {seed && (
              <details className="editor-wrap" open>
                <summary>
                  編輯 Campaign
                  <button
                    className="ghost"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      onResetCampaign();
                    }}
                    disabled={campaignBusy}
                  >
                    重設為 mock
                  </button>
                </summary>
                <CampaignEditor seed={seed} onChange={setSeed} disabled={campaignBusy} />
              </details>
            )}
            {campaignError && <p className="error">⚠ {campaignError}</p>}
            {campaignResult && (
              <div className="result">
                <h2>整套成品 · {campaignResult.banners.length} 張</h2>
                {campaignResult.note && <p className="note">ℹ {campaignResult.note}</p>}
                {campaignResult.zip_url && (
                  <p className="muted">
                    <a href={`${API_BASE}${campaignResult.zip_url}?v=${campaignCount}`}>
                      下載 campaign.zip ↗
                    </a>
                  </p>
                )}
                {campaignResult.failures.length > 0 && (
                  <p className="error">
                    ⚠ {campaignResult.failures.length} 張超過 150KB:
                    {campaignResult.failures.map((f) => ` ${f.file} (${f.kb}KB)`).join(",")}
                  </p>
                )}
                <details>
                  <summary>Master Design(模型的版型選擇與風格 tokens)</summary>
                  <pre>{JSON.stringify(campaignResult.design, null, 2)}</pre>
                </details>
              </div>
            )}
          </>
        )}

        {mode === "v0" && (
          <>
        <button onClick={onRender} disabled={busy || !graph}>
          {busy ? "Rendering…" : "Render Banner"}
        </button>

        <label>
          Preset
          <select
            value={selected}
            onChange={(e) => onSelectPreset(e.target.value)}
            disabled={!graph}
          >
            <option value="">（config.py 預設）</option>
            {presetNames.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <div className="preset-bar">
          <button className="ghost" onClick={onSaveAs} disabled={!graph}>
            另存為…
          </button>
          <button className="ghost" onClick={onDeletePreset} disabled={!graph || !selected}>
            刪除
          </button>
          <button className="ghost" onClick={onExport} disabled={!graph}>
            匯出 JSON
          </button>
        </div>
        {presetMsg && <p className="muted">{presetMsg}</p>}

        {renderError && <p className="error">⚠ {renderError}</p>}

        {result && (
          <div className="result">
            <h2>成品預覽 (HTML) · {result.layout}</h2>
            {previewSrc && <BannerPreview src={previewSrc} />}
            {result.note && <p className="note">ℹ {result.note}</p>}
            <p className="muted">
              <a
                href={`${API_BASE}${result.image_url}?v=${renderCount}`}
                target="_blank"
                rel="noreferrer"
              >
                HTML2img 輸出 PNG ↗
              </a>{" "}
              (renderer: {result.renderer}
              {result.renderer === "stub" ? " — 純色佔位" : ""})
            </p>
            <details open>
              <summary>Spec</summary>
              <pre>{JSON.stringify(result.spec, null, 2)}</pre>
            </details>
          </div>
        )}
          </>
        )}
      </aside>

      <main className="canvas">
        {mode === "v1" && campaignResult && (
          <div className="view-toggle">
            <button className={v1View === "graph" ? "active" : ""} onClick={() => setV1View("graph")}>
              節點圖
            </button>
            <button className={v1View === "grid" ? "active" : ""} onClick={() => setV1View("grid")}>
              成品格
            </button>
          </div>
        )}
        {graphError ? (
          <div className="canvas-error">
            <p className="error">無法載入 Loom Graph：{graphError}</p>
            <p className="muted">後端有跑嗎？ uvicorn layoutloom_v0.api:app --port 8012</p>
          </div>
        ) : mode === "v1" && v1View === "grid" && campaignResult ? (
          <CampaignGrid result={campaignResult} version={campaignCount} />
        ) : (
          <ConfigContext.Provider value={{ configs, setConfig }}>
            <ReactFlow
              key={mode}
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              nodeTypes={nodeTypes}
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background />
              <Controls />
            </ReactFlow>
          </ConfigContext.Provider>
        )}
      </main>
    </div>
  );
}
