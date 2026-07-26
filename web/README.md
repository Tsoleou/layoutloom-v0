# LayoutLoom-v0 — Web (React + React Flow)

依契約 `meta.stack` 的 React Flow 前端：把 `loom/LayoutLoom-v0.json` 這張 Loom
Graph 畫成節點圖，在面板填主/副標題，按 Render 打後端 `POST /render`，顯示產生
的 banner 圖與 spec。

## 跑起來

需要兩個 terminal —— 後端 API 與前端 dev server。

```bash
# 1) 後端（專案根目錄）
cd .. && . .venv/bin/activate
uvicorn layoutloom_v0.api:app --port 8012

# 2) 前端（web/ 目錄）
npm install
npm run dev            # http://localhost:5173
```

打開 http://localhost:5173：

- 左側面板：主標題 / 副標題輸入 + **Stub 模式**勾選框。
- 勾 Stub（預設）＝ 用 `StubBannerPlanner` + `StubRenderer`，**免 Ollama、免瀏覽器**，
  可直接測整條線。
- 取消勾選＝真跑，需要 `ollama pull gemma3:4b` 與 `playwright install chromium`
  （在後端 venv：`pip install -e ".[render]"`）。
- 右側：Loom Graph 節點圖（藍＝io、紫＝model、灰＝deterministic）。

**成品預覽是 HTML iframe，不是 PNG。** `StubRenderer` 產出的 PNG 是純色佔位
（沒有真的把 HTML 畫成圖），所以預覽用 iframe 讓瀏覽器直接 render `banner.html`
—— stub 模式也看得到有字有圖的 banner。PNG 連結另附在下方（真跑 Playwright 時
才是真正的點陣輸出）。素材與字型由 API 以 HTTP 提供（`/assets`、`/fonts`），
HTML 以 HTTP URL 參照，iframe 才載得到圖。

## 設定

- `VITE_API_BASE`：後端位址，預設 `http://localhost:8012`。要改連別的 port 就
  設這個環境變數再 `npm run dev`。
- 後端 `CORSMiddleware` 只放行 `localhost:5173`；換 port 記得同步改 `api.py`。
