# 02 — 產品名獨佔一行(v1)

**What to build:** campaign 的每個產品線帶一個明確的**產品名**(product_name),與其餘標題文案(tagline)分離。渲染標題時,產品名**永遠獨佔第一行、絕不被拆開**,tagline 排在其下並在行數預算內組行(預設標題總共 ≤2 行:產品名 1 行 + tagline 1 行,字級 shrink-to-fit)。以 LUMOS mock 在 300×600 驗收:`Aero 14` / `Ultralight`、`Vista 16` / `Big-Screen at Home` 等,產品名都乾淨地獨佔首行。

**節點對照:**
- **資料進在 Campaign 輸入節點**——campaign 檔 / 產品線資料結構新增 product_name 欄位;mock 資料同步拆出產品名。
- **機制在 Adapt Layout 節點**——展開 design×size 時,把標題組成「產品名一行 + tagline 組行」,字級擬合需同時讓產品名與 tagline 都容納。
- v1 專屬(v0 無產品線概念);**Master Design 模型不負責此規則**,頂多在 prompt 得知產品名當上下文。
- 「產品名獨佔一行」的策略留在 Adapt Layout,**不下沉到共用 composer**(避免 v0 用不到的參數 / speculative generality)。

**Blocked by:** 01(ADR-0008 定案後開始)。

**Status:** done

- [x] campaign 資料模型新增 product_name(選填,預設空);mock campaign 同步拆出產品名(與 tagline 分離)
- [x] 標題渲染時產品名永遠獨佔第一行,任何尺寸都不被拆開(含 728×90 banner 亦強制)
- [x] tagline 在剩餘行數預算內組行,沿用既有詞邊界 / chunk 邊界規則
- [x] 字級擬合讓產品名與 tagline 同時容納;放不下時 clamp 到 MIN_FS,產品名不縮到不可讀、標題不 drop
- [x] 300×600 + 728×90 mock 驗收樣本產品名獨佔首行、無中斷
- [x] 現有 v1 測試全綠(144),新增 campaign_io/adapt/mockdata 測試;`--stub` 端到端驗證
