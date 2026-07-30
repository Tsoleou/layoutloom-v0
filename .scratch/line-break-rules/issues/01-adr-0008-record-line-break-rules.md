# 01 — ADR-0008:記錄四項換行規範

**What to build:** 一份擴充 ADR-0006 的架構決策紀錄(ADR-0008),把這四項換行規範釘死,作為 Ticket 2、3 實作的依據:

1. **產品名界定**——用 campaign 的**明確欄位**(product_name),不靠模型分段或啟發式。
2. **獨立一行強度**——產品名**一律強制獨佔第一行**,不可被拆開。
3. **行首標點策略**——標題/副標換行時,行首若為標點,**預設移回上一行行尾**;只有移回會使上一行爆框時才**直接刪除**該標點。
4. **套用範圍與行數預算**——規則 3 套用**標題+副標**,並擴及 **ASCII** 標點;標題行數預算=產品名 1 行 + tagline 佔剩餘(預設總共 ≤2 行)。

**節點對照(寫進 ADR):**
- 規則 1 資料進在 **Campaign 輸入**,機制在 **Adapt Layout**(v1 專屬)。
- 規則 3 落在**共用 composer**,由 **Adapt Layout**(v1)與 **Layout Guard**(v0)共同呼叫。
- 兩者皆在確定性(code)側;**Master Design(模型)不參與**——延續 ADR-0006/0007「model designs, code guarantees」。

**Blocked by:** None — can start immediately.

**Status:** done

- [x] `docs/adr/0008-*.md` 寫出,標題即決策,含四項規範與節點對照
- [x] 明確標示擴充 ADR-0006、並與 ADR-0007「確定性保證」定位一致
- [x] 記錄被否決的替代方案(靠模型分段、純 code 啟發式、只套副標、下沉到共用 composer)
- [x] 標示綁定範圍:規則 1 為 v1-only,規則 3 v0/v1 共用
