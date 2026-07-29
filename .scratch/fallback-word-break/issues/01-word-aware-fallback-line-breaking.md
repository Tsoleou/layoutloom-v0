# 01 — 詞邊界感知的 fallback 斷行

**What to build:** 在無模型的確定性斷行路徑(stub designer / `segment_text` fallback)下,有空格的拉丁/英文文案要在**詞邊界**折行,不再切在單字中間;連字號複合詞(如 `Big-Screen`)可在**連字號後**折行,連字號留在前一行;只有當單一個詞本身就比框寬還寬時,才退化成逐字元硬斷(最後手段)。折行後的每一行不留多餘的頭尾空格。此行為由 v0(Layout Guard)與 v1(Adapt Layout)共用的 `fitting.py` composer 提供,兩條 stub 路徑一致生效。

實際觸發場景:300×600 skyscraper 的 mock 標題目前被硬斷在字中間(`Aero 14 Ultra`/`light`、`Vista 16 Big-S`/`creen at Home`、`Strike 17 Gam`/`ing Beast`)。修好後應在空格 / 連字號處乾淨折行。

設計取向(擇一,不動 `segment_text` 語意與 LLM prompt 範例為佳):讓 composer 的**溢出斷行**依「連字號 / 空格 > 字元」的優先序選最佳斷點——先在詞邊界切,單一超寬詞才逐字元切。真實模型的語意分詞路徑不受影響(它本來就給好 chunks)。

**Blocked by:** None — can start immediately.

**Status:** done

- [x] 有空格的英文標題在詞邊界折行,不切在單字中間(以 300×600 的三個 mock 標題為驗收樣本)
- [x] 連字號複合詞可在連字號後折行,連字號保留在前一行(`Big-Screen` → `Big-`/`Screen`)
- [x] 單一超寬詞(無空格、無連字號)仍能逐字元硬斷,不會溢出或無限迴圈
- [x] 折行後的每一行沒有多餘的頭尾空格
- [x] 中文含標點的既有行為不變(`限時三天,全館優惠` 仍在標點邊界折)
- [x] v0 與 v1 的 stub / fallback 路徑都套用同一套 composer;現有測試全綠,並新增涵蓋上述情境的測試
- [x] 端到端在 `--stub` 下驗證 300×600 產出的 HTML `<br>` 折點正確(composer + render_html `<br>` 皆有測試涵蓋)
