# LayoutLoom-v0

依 Loom Graph 設計契約（`loom/LayoutLoom-v0.json`，schema 0.4.0）scaffold 的
banner 產生 pipeline：LLM（Ollama / gemma3:4b）規劃版面並產出 HTML，程式碼
負責存檔、轉圖與展示。

> 注意：這是契約的 v0 設計（LLM 直接產 HTML），與
> `~/Projects/LayoutLoom`（rebuild 後的確定性引擎）刻意分開。

## 圖 → 程式碼對照

| Loom 節點 | kind | 實作 |
|---|---|---|
| Canva | deterministic | `nodes/canvas.py::make_canvas` |
| Load Product Image / Load Logo / Load Font | io | `nodes/assets_io.py` |
| Input Text / Input | deterministic | API/CLI 的 `title` / `subtitle` 欄位 |
| LLM Banner Plan | model | `nodes/planner.py::OllamaBannerPlanner`（唯一模型觸點；`StubBannerPlanner` 為離線 stub） |
| Show Text | deterministic | `nodes/outputs.py::show_text`（出口一：Spec） |
| Save HTML → HTML2img → Show Image → Save Image | deterministic | `nodes/outputs.py` + `nodes/html2img.py`（出口二：成品圖） |

驅動器：`driver.py::render_banner` — 圖是線性加一個無條件扇出、無 loop，
所以是一個顯式串行函式，不需要 graph executor。

## 使用

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest                                    # 全離線：stub planner + stub renderer

# 離線試跑接線（不需要 Ollama / 瀏覽器）
python -m layoutloom_v0 --title 大促銷 --subtitle 限時三天 --stub --demo-assets

# 真跑（需要 ollama pull gemma3:4b，以及 headless 瀏覽器）
pip install -e ".[render]" && playwright install chromium
python -m layoutloom_v0 --title 大促銷 --subtitle 限時三天 --demo-assets

# API（io.input → io.output）
uvicorn layoutloom_v0.api:app --port 8012
# POST /render {"title": "...", "subtitle": "..."} → {spec, html_path, image_path}
```

## 實作假設（契約沒說、由此處決定，皆可調）

1. `meta.description` 寫「RAG pipeline / 多層 guardrail」但圖中無檢索節點、無
   guardrail 分支——以圖為準，忽略該描述；`meta.stack` 的 ChromaDB 未使用。
2. LLM 收到的是素材**中繼資料**（路徑 + 像素尺寸），不是像素本身；HTML 以
   `file://` URL 引用素材檔。
3. `HTML2img` 契約標 deterministic，但轉圖需要 headless 瀏覽器，故以
   `HtmlRenderer` Protocol 隔離（Playwright 實作 + 無瀏覽器 stub）。
4. Ollama endpoint 預設 `http://localhost:11434`，request 帶 `format: "json"`，
   回應以容錯 parser（`parse_plan_response`）取出 `{spec, html}`。
5. 字型檔缺失時降級為系統 sans-serif 並照常出圖，不視為失敗。
6. 契約無 loop：LLM 輸出不經 critic 驗證，一次過（v0 語意）。
