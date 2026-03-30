# 投資研究模板 — Research Template

> 每次啟動新研究時，複製此模板並填入內容。
> 所有欄位皆需填寫，不可留空或填寫泛泛之辭。

---

## 研究基本資訊

| 欄位 | 內容 |
|---|---|
| 標的名稱 | |
| Ticker | PLTR / MSFT / MAR（圈選或填入） |
| 研究主題 | |
| 研究日期 | YYYY-MM-DD |
| 研究版本 | v0 |
| 持有期 | 週 / 月 / 年 |
| 研究類型 | 短線 / 中線 / 長線 / 主題 / 事件驅動 |
| 初始主張一句話 | |
| 預期 Alpha 來源 | |
| 主要比較對象 | |
| research_stage | candidate / in_research / ready_to_decide / active / rejected / archived |
| candidate_origin | manual_watchlist / ad_hoc_idea / quant_radar |
| decision_status | pending / needs_more_research / ready_to_decide / active / rejected / archived |
| decision_updated_at | YYYY-MM-DD |
| 信心評分 | 0.00 - 1.00 |
| last_reviewed_at | YYYY-MM-DD |
| next_review_at | YYYY-MM-DD |
| thesis_id | `ticker-thesis-core` |

### Automation Mirror

> 每份 `current.md` 都必須有對應的 `state.json`，以下欄位不可缺。

| 欄位 | 說明 |
|---|---|
| assumption_id | 每條核心假設的穩定 ID，例如 `msft-a1` |
| action_rule_id | 每條動作規則的穩定 ID，例如 `msft-ar-add` |
| thresholds | 至少含 `price_gap_pct`、`volume_ratio`、`deep_refresh_days`、`material_sec_forms` |
| research_debt | 目前尚未補齊、但會影響判讀品質的資料缺口 |
| source_manifest | 目前倚賴的主要來源清單 |
| radar_flags / radar_summary / radar_risk_level | 候選雷達訊號，只做提醒，不做硬性 veto |
| outcome_markers | 關鍵事件後留下的結果標記 |
| thesis_change_log | thesis / decision 狀態改寫記錄 |
| invalidation_reason | 明確不買、拒絕或撤銷 thesis 的原因 |
| consistency_notes | 事後校準用的簡短紀錄 |

### 限制條件

| 條件 | 設定 |
|---|---|
| 可承受最大回撤 | % |
| 最大部位上限 | % of portfolio |
| 主要退出條件 | |
| 研究資料缺口 | |

---

## 0. 決策紀錄 (Decision Log — Pre-entry)

> 紀錄標的如何進入候選名單，以及決定啟動深研的初衷。

- **進件來源：** (例如：52週新高雷達 / 13F 追蹤 / 產業鏈推導)
- **初篩亮點：**
- **深研啟動動機：**
- **是否跳過深研直接觀察？** 是/否 (理由)
- **決策者自評：** (進場前的直覺或擔憂)

---


## 1. 一句話結論

> 我看多/看空 [標的]，因為 [核心因果邏輯]，市場尚未充分反映 [關鍵變化]，預計在 [時間範圍] 內由 [催化事件] 反映。

---

## 2. 持有期與研究框架

- **持有期：**
- **研究類型：**
- **核心觀察變數（3項）：**
  1.
  2.
  3.
- **次要觀察變數（3項）：**
  1.
  2.
  3.
- **預設降噪項目：**
- **警鈴閾值：**

## 2A. Workflow 與 Radar

- **research_stage：**
- **candidate_origin：**
- **decision_status：**
- **decision_updated_at：**
- **radar_flags：**
- **radar_summary：**
- **radar_risk_level：**

---

## 3. 核心 Thesis

- **Thesis：**
- **核心催化：**
- **市場未反映之處：**
- **何時驗證：**
- **何時失效：**

---

## 4. 核心假設

| assumption_id | 假設 | 類型 | 驗證方式 | 更新頻率 | 失效條件 |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |

---

## 5. 主要風險

| # | 風險 | 類型 | 先行訊號 | 對 Thesis 影響 | 應對動作 |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

風險層級標記：🔴 thesis breaker / 🟡 thesis weakener / ⚪ noise

---

## 6. 評價體系分析

- **市場目前使用的尺：**
- **更合理的尺：**
- **可能切換的觸發條件：**
- **切換後的重估邏輯：**
- **對應風險：**

---

## 7. 情境分析

| 情境 | 觸發條件 | 因果邏輯變化 | 最受益/最受損 | 動作 |
|---|---|---|---|---|
| Base | | | | |
| Bull | | | | |
| Bear | | | | |
| Break | | | | |

---

## 8. Pre-mortem

- **失敗情境（假設一年後虧損 50%）：**
- **最可能出錯的假設：**
- **當時忽略的訊號：**
- **若重來一次，最早該在哪個點修正：**
- **未來如何避免：**

---

## 9. 橫向比較

| 維度 | PLTR | MSFT | MAR |
|---|---|---|---|
| 上行來源 | | | |
| 下行保護 | | | |
| 催化可見度 | | | |
| 假設難度 | | | |
| 評價改善空間 | | | |
| 資產負債表韌性 | | | |
| 判斷錯誤時存活力 | | | |

### 比較結論

- **為什麼選它不是別家：**
- **若主假設成立，彈性最大者：**
- **若主假設部分成立，風報比最佳者：**
- **若主假設失敗，跌幅最小者：**

---

## 10. 行動建議

| action_rule_id | 類型 | 內容 |
|---|---|---|
| | 現在動作 | |
| | 建議部位 | |
| | 加碼條件 | |
| | 減碼條件 | |
| | 撤退條件 | |
| | 換股條件 | |

---

## 11. 後續追蹤

| 項目 | 內容 |
|---|---|
| 下次更新日期 | |
| 必追資料 | |
| 待補資料 | |
| 目前最大不確定性 | |
| research_debt | |

## 12. Calibration Log

| 類型 | 日期 | 內容 |
|---|---|---|
| outcome_marker | | |
| thesis_change_log | | |
| consistency_note | | |

## Source Manifest

| source_id | 類型 | 說明 | URL |
|---|---|---|---|
| sec | SEC filings | | |
| investor_news | IR / 公司新聞 | | |
| price | 價格 / 成交量 | | |

---

## 事件紀錄

| 日期 | 新事件 | 對應假設 | 邊際貢獻 (+/0/−) | 是否超過閾值 | 動作 |
|---|---|---|---|---|---|

---

## 版本紀錄

| 版本 | 日期 | 變更原因 | 修改內容 | 對結論影響 |
|---|---|---|---|---|
| v0 | | 初始研究 | — | — |
