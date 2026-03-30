# Stock Research Operator — 功能缺口審計報告

> **日期**：2026-03-27 ｜ **範圍**：[figureout.md](file:///Users/ro9air/STOCK/figureout.md) 五大藍圖、[vNext.md](file:///Users/ro9air/STOCK/vNext.md)、[PLAN.md](file:///Users/ro9air/STOCK/PLAN.md) 對比目前已實作的程式碼

---

## 一覽表：規劃 vs. 實作狀態

| # | 功能區域 | 規劃文件 | 實作狀態 | 有無 TASK.md / 開發規劃書 |
|---|---|---|---|---|
| 1 | **vNext：候選研究層** | [vNext.md](file:///Users/ro9air/STOCK/vNext.md) | ✅ 已實作 | ❌ 無 |
| 2 | **PLAN.md：語氣後處理** | [PLAN.md](file:///Users/ro9air/STOCK/PLAN.md) | ✅ 已實作 | ❌ 無 |
| 3 | **PLAN.md：來源白名單** | PLAN.md | ✅ 已實作 | ❌ 無 |
| 4 | **PLAN.md：Canonical Digest 層** | PLAN.md | ✅ 已實作 | ❌ 無 |
| 5 | **PLAN.md：Email 通知 (Resend)** | PLAN.md | ✅ 已實作 | ❌ 無 |
| 6 | **PLAN.md：Dashboard 靜態站** | PLAN.md | ✅ 已實作 | ❌ 無 |
| 7 | **Radar 量價篩選** | vNext.md + [radar.py](file:///Users/ro9air/STOCK/scripts/radar.py) | ⚠️ 原型階段 | ❌ 無 |
| 8 | **跨市場產業鏈共振追蹤器** | [figureout.md](file:///Users/ro9air/STOCK/figureout.md) #1 | ❌ 未開始 | ❌ 無 |
| 9 | **例外管理量化儀表板** | figureout.md #2 | ❌ 未開始 | ❌ 無 |
| 10 | **預期差量化計分板** | figureout.md #3 | ❌ 未開始 | ❌ 無 |
| 11 | **決策回測「驗屍」資料庫** | figureout.md #4 | 🟡 基礎存在 | ❌ 無 |
| 12 | **敘事熱度/擁擠度指數** | figureout.md #5 | ❌ 未開始 | ❌ 無 |

---

## 分項詳細分析

### ✅ 已完成功能（#1–6）

這些功能在 [PLAN.md](file:///Users/ro9air/STOCK/PLAN.md) 和 [vNext.md](file:///Users/ro9air/STOCK/vNext.md) 中有規劃，且已完整實作並有測試覆蓋：

- **候選研究層**：[candidates.py](file:///Users/ro9air/STOCK/stock_research/candidates.py) + [research_state.py](file:///Users/ro9air/STOCK/stock_research/research_state.py) 實作了 `candidate → in_research → ready_to_decide → active / rejected / archived` 完整狀態機，包含 [upsert_candidate_dossier()](file:///Users/ro9air/STOCK/stock_research/candidates.py#19-111)、`sync_candidate_queue()`
- **語氣後處理**：[postprocess.py](file:///Users/ro9air/STOCK/stock_research/postprocess.py) 實作了 [post_process_refresh_output()](file:///Users/ro9air/STOCK/stock_research/postprocess.py#201-237)，能正確改寫「reinforced → reinforced」為研究語言
- **來源白名單**：`source_registry.json` + [config.py](file:///Users/ro9air/STOCK/stock_research/config.py) ([load_source_registry()](file:///Users/ro9air/STOCK/stock_research/config.py#72-100)) 已完整拆離，不再混用 WATCHLIST
- **Canonical Digest**：[digest.py](file:///Users/ro9air/STOCK/stock_research/digest.py) (684 行) 實作了完整的 [build_ticker_digest()](file:///Users/ro9air/STOCK/stock_research/digest.py#518-525) / [build_portfolio_digest()](file:///Users/ro9air/STOCK/stock_research/digest.py#572-596)
- **Email**：[notify.py](file:///Users/ro9air/STOCK/stock_research/notify.py) 實作了 Resend 寄送、HTML/Text 雙格式
- **Dashboard**：[dashboard.py](file:///Users/ro9air/STOCK/stock_research/dashboard.py) + `templates/dashboard/` 實作了公開站 + 本機私有 cockpit

---

### ⚠️ #7 — Radar 量價篩選（原型階段，需補齊規劃）

**目前狀態**：

| 項目 | 狀態 |
|---|---|
| [scripts/radar.py](file:///Users/ro9air/STOCK/scripts/radar.py) | 存在，只有 40 行的 yfinance 腳本，只做 52 週新高距離計算 |
| vNext.md 規劃 | 「少量量價篩選結果」作為候選進件的第三種來源 |
| `state.json` 欄位 | `radar_flags[]`、`radar_summary`、`radar_risk_level` 已在 contract 中 |
| 與 pipeline 的整合 | ❌ [radar.py](file:///Users/ro9air/STOCK/scripts/radar.py) 結果未自動進入候選研究流程 |

**缺失清單**：
- [ ] [radar.py](file:///Users/ro9air/STOCK/scripts/radar.py) 需要升級：增加更多量化指標（均線乖離、爆量偵測、動能指標）
- [ ] 需要一個 `pipeline.radar_scan()` 函數，把掃描結果自動寫入 `candidates.json`
- [ ] 缺少排程整合（手動跑 vs. CI cron vs. launchd）
- [ ] 缺少 radar → candidate 的自動進件邏輯
- [ ] 無測試覆蓋

---

### ❌ #8 — 跨市場產業鏈共振追蹤器（figureout.md #1）

**figureout 描述**：定義 `US-MSFT → TW-Server-SupplyChain` 關聯樹，當美股龍頭打破 Threshold 時，預判資金轉向台股的「時間差紅利」。

**目前資產**：完全沒有任何程式碼或設定。[vNext.md](file:///Users/ro9air/STOCK/vNext.md) 明確排除：「台股資料源、跨市場供應鏈映射」不進核心目標。

**如果未來要做**：
- 需要台股資料源的選型與 API 串接（TEJ / Goodinfo / 證交所公開資料）
- 需要定義「關聯樹」的資料結構（ticker → supply_chain_tickers[]）
- 需要 threshold breach → alert 的事件流

> [!NOTE]
> vNext 已明確將此功能排除出核心範圍，列為 roadmap。除非你決定推進，否則不需要現在開發。

---

### ❌ #9 — 例外管理量化儀表板（figureout.md #2）

**figureout 描述**：背景運行量化指標（價格動能、均線乖離、爆量偵測），只在持股出現「妖股爆發結構」或「籌碼崩解」時跳 Alert。

**目前資產**：
- [sources.py](file:///Users/ro9air/STOCK/stock_research/sources.py) → [fetch_price_events()](file:///Users/ro9air/STOCK/stock_research/sources.py#98-143) 已有基本的 `change_pct` 和 `volume_ratio` 偵測
- `state.json` → `thresholds.price_gap_pct` + `thresholds.volume_ratio` 已存在
- **但**：只在 pipeline polling 時被動觸發，不是「背景持續監控」

**缺失清單**：
- [ ] 均線乖離、動能指標（RSI、MACD）的計算模組
- [ ] 「爆發結構 / 籌碼崩解」的特徵偵測邏輯
- [ ] 獨立於 pipeline 的背景監控 scheduler
- [ ] Alert → Action Rule 自動執行建議的橋接
- [ ] Dashboard 上的「例外儀表板」UI

---

### ❌ #10 — 預期差量化計分板（figureout.md #3）

**figureout 描述**：針對台股，把基本面事件（月營收月增 30%）與隔天量價反應做對比。營收大好卻開高走低 → 標記「高預期計價區 (Priced-in)」。

**目前資產**：概念上與 SOUL.md 的「Expectation Gap」一致，但：
- 完全沒有程式碼
- 無台股資料源
- [vNext.md](file:///Users/ro9air/STOCK/vNext.md) 已排除台股

**與現有架構的關係**：
- `state.json` 的 `outcome_markers[]` 和 `thesis_change_log[]` 可以作為事後記錄的基礎
- 但「即時比對基本面事件 vs. 隔天量價反應」的自動化流程完全不存在

---

### 🟡 #11 — 決策回測「驗屍」資料庫（figureout.md #4）

**figureout 描述**：把每份 thesis 的 Assumption 與實際財報數據比對，每季自動生成「個人投資季報」。

**目前資產（基礎存在但不完整）**：

| 功能 | 狀態 |
|---|---|
| `outcome_markers[]` 欄位 | ✅ 已在 `state.json` contract 中 |
| `thesis_change_log[]` 欄位 | ✅ 已在 `state.json` contract 中 |
| `record_outcome_marker()` 函數 | ✅ 在 [research_state.py](file:///Users/ro9air/STOCK/stock_research/research_state.py) 中 |
| `append_state_change_entry()` 函數 | ✅ 在 [research_state.py](file:///Users/ro9air/STOCK/stock_research/research_state.py) 中 |
| `version_log[]` 追蹤 | ✅ 自動寫入每次 refresh |
| Post-mortem 步驟（SKILL.md Step 7） | ✅ 在 SKILL.md 研究流程中 |
| 自動季度彙整報告生成 | ❌ 完全沒有 |
| Assumption 預測 vs. 實際比對邏輯 | ❌ 完全沒有 |
| 個人決策勝率統計 | ❌ 完全沒有 |

**缺失清單**：
- [ ] `analytics.py` 或類似模組：讀取所有 ticker 的 `outcome_markers` 和 `thesis_change_log`，生成彙整
- [ ] 與外部財報數據源的比對邏輯（e.g. 預測 EPS vs. 實際 EPS）
- [ ] 季度報告的 markdown/HTML render
- [ ] Dashboard 的「歷史績效」頁面

---

### ❌ #12 — 敘事熱度與擁擠度指數（figureout.md #5）

**figureout 描述**：接入新聞標題或社群（Reddit, PTT）的關鍵字頻率，量化情緒，當故事 + 機構持倉極度擁擠時自動調降 Confidence。

**目前資產**：完全沒有任何程式碼。

**預備條件**：
- 需要社群 / 新聞資料源 API
- 需要「擁擠度」的量化模型（NLP 關鍵字頻率 + 13F 持倉集中度）
- 需要與 `state.json` confidence 的自動調整機制

---

## 總結：哪些功能需要「規劃 → 準備開發 → 開發規劃書」？

### 建議立即規劃（與現有架構契合度高）

| 優先級 | 功能 | 理由 |
|---|---|---|
| 🔴 P0 | **Radar 量價篩選完善** (#7) | 原型已存在，vNext 已承諾，只差與 pipeline 的整合 |
| 🟠 P1 | **決策回測「驗屍」** (#11) | 資料基礎 (`outcome_markers`, `thesis_change_log`) 已在 state contract 中，只差彙整邏輯 |

### 建議中期規劃（需要新模組但技術可行）

| 優先級 | 功能 | 理由 |
|---|---|---|
| 🟡 P2 | **例外管理量化儀表板** (#9) | [fetch_price_events](file:///Users/ro9air/STOCK/stock_research/sources.py#98-143) 已有基礎，需要擴充指標 + 背景排程 |

### 建議長期 Roadmap（範圍大、依賴外部資料源）

| 優先級 | 功能 | 理由 |
|---|---|---|
| 🔵 P3 | 跨市場產業鏈共振 (#8) | vNext 明確排除，需台股資料源 |
| 🔵 P3 | 預期差量化計分板 (#10) | 依賴台股資料，vNext 排除 |
| 🔵 P3 | 敘事熱度/擁擠度指數 (#12) | 需 NLP + 社群 API，複雜度最高 |

---

## 下一步建議

如果你想推進，我建議按照以下順序為每個功能建立正式的開發規劃書（TASK.md）：

1. **先做 #7 Radar**：升級 [radar.py](file:///Users/ro9air/STOCK/scripts/radar.py) → `stock_research/radar.py`，接入 [pipeline.py](file:///Users/ro9air/STOCK/tests/test_pipeline.py) 的候選進件流程
2. **再做 #11 Post-Mortem Analytics**：新增 `stock_research/analytics.py`，讀取 outcome/change log 生成季度報告
3. **接著才考慮 #9 Exception Dashboard**：擴充量化指標 + 背景 scheduler

**要我幫你針對其中某一個（或多個）功能寫正式的開發規劃書嗎？**
