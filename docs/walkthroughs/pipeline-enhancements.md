# Feature Implementation Walkthrough: Pipeline Enhancements

我們已經成功將 [future-roadmap.md](../architecture/future-roadmap.md) 中規劃的三項核心功能推進到現有架構中。

## 1. Radar 預警掃描 (#7)
我們用標準化的 Python 模組 [stock_research/radar.py](file:///Users/ro9air/STOCK/stock_research/radar.py) 取代了原本的單純命令列雛形。
- **What Changed**: 
  - 實作 [scan_market(tickers)](file:///Users/ro9air/STOCK/stock_research/radar.py#92-161) 透過 `yfinance` 自動批次下載歷史價格與交易量。
  - 精準判斷三大技術警訊：**52週相對高低點 (52-week distance)**、**異常交易量 (Volume Ratio)**、**均線乖離 (10-MA Deviation)**。
  - 將 Radar 整合進 [pipeline.py](file:///Users/ro9air/STOCK/tests/test_pipeline.py) 的 [run_radar_scan()](file:///Users/ro9air/STOCK/stock_research/pipeline.py#518-562) 流程。
- **Validation**:
  - 當標的觸發技術警示時，系統將呼叫 [upsert_candidate_dossier()](file:///Users/ro9air/STOCK/stock_research/candidates.py#19-111)，將該標的以 [candidate](file:///Users/ro9air/STOCK/stock_research/candidates.py#19-111) 狀態直接自動寫入到 [research/system/candidates.json](file:///Users/ro9air/STOCK/research/system/candidates.json) 的候選清單中，實現從「手動觀察」到「自動進件」的推進。

## 2. 決策回測 / 驗屍資料庫 (#11)
你已經在 `state.json` 中加入了非常完備的 `outcome_markers` 與 `thesis_change_log`。我們現在可以把這些沉靜的檔案變為決策量表。
- **What Changed**:
  - 新增 [stock_research/analytics.py](file:///Users/ro9air/STOCK/stock_research/analytics.py)，裡面包含 [generate_post_mortem_report()](file:///Users/ro9air/STOCK/stock_research/analytics.py#9-82)。
  - 它會遞迴讀取所有標的的狀態檔，計算 `assumptions_resolved` vs `assumptions_correct`，得出你的**假設命中率 (Assumption Hit Rate)**。
  - 另外，它利用關鍵字萃取（"regime", "drift", "gap", "priced"）來量化發現【投資典範轉移 Regime Drift】或【預期差 Expectation Gap】的頻率。
- **Validation**:
  - 此數據已被接入到 [digest.py](file:///Users/ro9air/STOCK/stock_research/digest.py) 生成的 `portfolio.json`，並在 **Dashboard** 首頁右方區塊正式視覺化為 "Review Performance"。

## 3. 例外管理量化儀表板 (#9)
原本 [sources.py](file:///Users/ro9air/STOCK/stock_research/sources.py) 裡的 [fetch_price_events](file:///Users/ro9air/STOCK/stock_research/sources.py#98-165) 只會像新聞一樣紀錄價格跳動，現在它具備了「定性」的能力。
- **What Changed**:
  - 更新 [fetch_price_events](file:///Users/ro9air/STOCK/stock_research/sources.py#98-165)：
    - 當 `Volume Ratio >= 3.0` 且 `Price Change >= 5.0%`，標記例外為 **妖股爆發結構 (Volume Climax Breakout)** (Severity: High)。
    - 當 `Volume Ratio >= 2.0` 且 `Price Change <= -5.0%`，標記為 **籌碼崩解 (High-Volume Selloff)** (Severity: Critical)。
  - 更新 Dashboard 前端 UI ([index.html](file:///Users/ro9air/STOCK/site/index.html) + `dashboard.js` + `dashboard.css`)，加入了隱形的 `Exception Alerts` 區塊。
- **Validation**:
  - 如果發生了上述「籌碼崩解」或「妖股結構」的例外事件，Dashboard 首頁將會**直接置頂顯示紅色的優先處理佇列 (Risk Alert)**，強制使用者優先介入處理該標的。

---

### 下階段階段建議 
我們已經完成了此次的特徵縫合，所有單元測試皆通過。如果要實際投入每天的日常運作，下一步就是到 `.github/workflows` 將 Radar 排程設定為每週定時掃描，或者是設定每天盤後背景執行。
