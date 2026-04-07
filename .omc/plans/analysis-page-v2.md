# 計畫：單一股票分析頁 v2 + Maximum Drawdown 頁

**來源需求**：`future_0401.md`
**新增需求**：Maximum Drawdown 獨立分頁
**建立日期**：2026-04-01
**狀態**：Ready to implement

---

## 需求摘要

在現有 thesis OS 上新增「可計算、可視覺化、可教學」的分析層。
Ticker 頁從 panel 堆疊改為 **7 + 1 個 Tab** 架構：

| # | Tab | 說明 |
|---|-----|------|
| 0 | Overview | Thesis + 快速指標整合 |
| 1 | Price | 價格走勢 + 基本 KPI |
| 2 | **Drawdown** | 最大回撤完整分析（本次新增） |
| 3 | Monthly | 月度報酬 heatmap + 趨勢 |
| 4 | Quarterly | 季度基本面 |
| 5 | CAGR | CAGR 試算器 |
| 6 | Sharpe | 策略 Sharpe 回測 |
| 7 | Glossary | 名詞解釋 registry |

---

## 驗收標準

### 功能驗收
- [ ] Ticker 頁可在 8 個 Tab 間切換，URL hash 對應（`#overview`, `#price`, `#drawdown`, ...）
- [ ] Price Tab：1M / 3M / 6M / 1Y / 3Y / 5Y / MAX 區間切換，圖表與 KPI 同步
- [ ] **Drawdown Tab**：underwater chart、drawdown periods table、rolling MDD 3 個視圖
- [ ] Monthly Tab：月報酬 heatmap 正確排序、可回推 5 年
- [ ] Quarterly Tab：最近 8 季，YoY / QoQ 公式正確，缺欄顯示 null 不消失整行
- [ ] CAGR Tab：固定區間與自訂區間一致，開始日 > 結束日要阻擋
- [ ] Sharpe Tab：至少支援 buy-and-hold，頁面標示「示意回測，非交易建議」
- [ ] Glossary Tab：至少 16 個術語（原 15 + MDD），支援頁內搜尋

### 數值驗收
- [ ] CAGR、annualized return、volatility、Sharpe、MDD 結果可由 pytest 重算驗證
- [ ] 同輸入重跑結果一致（deterministic）
- [ ] 缺資料時不報錯、不顯示錯誤數值

### UX 驗收
- [ ] 任一 Tab 載入失敗不影響其他 Tab
- [ ] 使用者可在 3 次點擊內找到任何指標定義
- [ ] 單一 ticker 頁面靜態渲染 < 2 秒

---

## 實作步驟

### TASK-001：Artifact 與資料層（P0，後端基礎）

**交付物**：
- `stock_research/market_data.py`
- `stock_research/performance.py`
- `research/<ticker>/artifacts/price_series.json`
- `research/<ticker>/artifacts/monthly_metrics.json`
- `research/<ticker>/artifacts/drawdown_analysis.json`（新增）
- `research/<ticker>/artifacts/cagr_scenarios.json`
- `research/<ticker>/artifacts/strategy_metrics.json`
- `research/<ticker>/artifacts/quarterly_fundamentals.json`
- `research/<ticker>/artifacts/glossary_refs.json`
- `site/data/tickers/<ticker>.analysis.json`（lazy load payload）

**`market_data.py` 責任**：
```python
# 關鍵函式
fetch_price_series(ticker, period="10y") -> pd.DataFrame
resample_monthly(df) -> pd.DataFrame
build_price_series_artifact(ticker) -> dict  # 輸出 price_series.json
build_monthly_metrics_artifact(ticker) -> dict  # 輸出 monthly_metrics.json
```
資料來源：`yfinance`（已在 pyproject.toml）。
預設使用 `adj_close`。

**`performance.py` 責任**：
```python
# CAGR
calc_cagr(start_price, end_price, years) -> float
build_cagr_scenarios(price_df) -> dict  # 1Y/3Y/5Y/10Y/since_inception

# MDD（新增專用函式）
calc_drawdown_series(price_df) -> pd.Series          # 每日 drawdown
calc_max_drawdown(price_df) -> float                  # 全期 MDD
calc_rolling_mdd(price_df, window=252) -> pd.Series  # 滾動年度 MDD
extract_drawdown_periods(price_df, threshold=-0.10) -> list[dict]
# 每個 period: {peak_date, trough_date, depth_pct, duration_days, recovery_date, recovery_days}
build_drawdown_artifact(ticker) -> dict  # 輸出 drawdown_analysis.json

# Sharpe / 策略
calc_annualized_return(price_df) -> float
calc_annualized_volatility(price_df) -> float
calc_sharpe(return_series, rfr=0.03) -> float
run_buy_and_hold(price_df, rfr=0.03) -> dict
build_strategy_metrics_artifact(ticker) -> dict
```

**計算口徑（寫死）**：
```
r_t = adj_close_t / adj_close_{t-1} - 1
Annualized Return = (1 + cumulative_return)^(252/trading_days) - 1
Annualized Volatility = std(daily_returns) * sqrt(252)
Sharpe = (annualized_return - rfr) / annualized_volatility
drawdown_t = price_t / rolling_max_t - 1
MDD = min(drawdown_t)
Risk-free rate default = 0.03 (3%)
```

**`drawdown_analysis.json` schema**：
```json
{
  "ticker": "NVDA",
  "as_of": "2026-04-01",
  "mdd_alltime_pct": -34.2,
  "mdd_1y_pct": -18.5,
  "mdd_3y_pct": -34.2,
  "mdd_5y_pct": -34.2,
  "daily_drawdown_series": [
    {"date": "2025-04-01", "drawdown_pct": -2.3}
  ],
  "rolling_mdd_1y_series": [
    {"date": "2025-04-01", "rolling_mdd_pct": -18.5}
  ],
  "drawdown_periods": [
    {
      "rank": 1,
      "peak_date": "2022-01-04",
      "trough_date": "2022-10-14",
      "depth_pct": -34.2,
      "duration_days": 283,
      "recovery_date": "2023-05-20",
      "recovery_days": 218
    }
  ],
  "source": {"provider": "yfinance", "adj_close": true}
}
```

**CLI 擴充**（`scripts/research_ops.py`）：
```bash
python3 scripts/research_ops.py build-analysis --ticker NVDA
python3 scripts/research_ops.py build-analysis --all
```

---

### TASK-002：Ticker 頁 Tab 化（P0，前端架構）

**修改檔案**：
- `stock_research/templates/dashboard/ticker.html`（大幅改寫）
- `stock_research/templates/dashboard/assets/dashboard.js`（新增 tab router + render 函式）
- `stock_research/templates/dashboard/assets/dashboard.css`（新增 tab 樣式）

**HTML 結構**（取代現有 detail-layout）：
```html
<section class="ticker-hero">...</section>
<nav class="tab-nav">
  <a href="#overview" class="tab-link">總覽</a>
  <a href="#price"    class="tab-link">股價</a>
  <a href="#drawdown" class="tab-link">最大回撤</a>
  <a href="#monthly"  class="tab-link">月度</a>
  <a href="#quarterly" class="tab-link">季度</a>
  <a href="#cagr"     class="tab-link">CAGR</a>
  <a href="#sharpe"   class="tab-link">Sharpe</a>
  <a href="#glossary" class="tab-link">名詞解釋</a>
</nav>
<main class="tab-content">
  <section id="tab-overview" class="tab-pane">...</section>
  <section id="tab-price"    class="tab-pane hidden">...</section>
  <section id="tab-drawdown" class="tab-pane hidden">...</section>
  <!-- ... -->
</main>
```

**JS tab router**：監聽 `hashchange`，切換 `.hidden`，無外部依賴。
**Data loading**：先 lazy load `<ticker>.json`（digest，現有），再 lazy load `<ticker>.analysis.json`（新分析 payload）。

---

### TASK-003：Drawdown Tab（P0，核心新頁）

**JS render 函式**：`renderDrawdownTab(analysis)`

**3 個子視圖**（純 SVG / Canvas，無外部圖表庫）：

**視圖 1 — Underwater Chart（水下圖）**
- X 軸：日期，Y 軸：drawdown %（負值往下）
- 負值區域填色（紅色透明漸層）
- Hover tooltip 顯示日期 + drawdown %
- 區間切換：1Y / 3Y / 5Y / MAX

**視圖 2 — Drawdown Periods Table（回撤期表格）**
- 欄位：排名 / 峰值日期 / 谷底日期 / 回撤深度 / 持續天數 / 恢復日期 / 恢復天數
- 依回撤深度排序（最深在上）
- 深度 > 20% 標紅，10-20% 標黃
- 若尚未恢復，恢復欄顯示「尚未恢復」

**視圖 3 — Rolling MDD（滾動年度 MDD）**
- 滾動 252 日 MDD 曲線
- 標記當前值

**KPI 卡片**：
- 全期 MDD
- 近 1Y MDD
- 近 3Y MDD
- 平均回撤持續天數
- 平均恢復天數
- 最近一次回撤深度

---

### TASK-004：Price Tab（P0）

`renderPriceTab(analysis)` — 調用 `price_series.json` 資料

- 折線圖：adj_close，區間 1M/3M/6M/1Y/3Y/5Y/MAX
- 指標切換：price / drawdown / cumulative return / volume
- KPI：最新收盤 / 52W 高低 / 區間報酬 / annualized volatility / MDD

---

### TASK-005：CAGR Tab（P1）

`renderCagrTab(analysis)` — 調用 `cagr_scenarios.json`

- 預設按鈕：1Y / 3Y / 5Y / 10Y / since inception
- 自訂區間：start_date + end_date picker
- 輸出：total_return / CAGR / start_price / end_price / years
- 防呆：start > end 阻擋，< 1 年顯示警告

---

### TASK-006：Quarterly Tab（P1）

`renderQuarterlyTab(analysis)` — 調用 `quarterly_fundamentals.json`

- 表格：8 季 revenue / gross margin / operating margin / EPS / FCF
- YoY / QoQ 變化率
- TTM 摘要列
- 迷你折線：revenue trend + EPS trend

---

### TASK-007：Monthly Tab（P1）

`renderMonthlyTab(analysis)` — 調用 `monthly_metrics.json`

- 月報酬 heatmap（年×月格式，顏色 green/red）
- 滾動 12 個月報酬曲線
- 月度 drawdown 條圖

---

### TASK-008：Sharpe Tab（P2）

`renderSharpeTab(analysis)` — 調用 `strategy_metrics.json`

- 策略選擇器：buy-and-hold（v1），MA rule / thesis-aligned（v2）
- 輸出：annualized return / volatility / Sharpe / MDD / win rate / exposure
- Equity curve + drawdown curve
- **頁面強制顯示**：「這是示意回測，不是交易建議」

---

### TASK-009：Glossary Tab（P1）

`renderGlossaryTab(analysis)` — 調用 `glossary_refs.json`

**16 個必備詞條**（原 15 + MDD）：
CAGR, Sharpe Ratio, Annualized Return, Volatility, **Max Drawdown (MDD)**, Adjusted Close, TTM, YoY, QoQ, Gross Margin, Operating Margin, FCF, Revenue Growth, Beta, Risk-free Rate, Underwater Chart

- 每條：term / 中文 / 定義 / 公式（code block）/ 為何重要 / 誤用警告 / 相關詞
- 頁內搜尋
- 點指標名稱開側邊 drawer

---

### TASK-010：測試（P0 + P1）

**`tests/test_performance.py`**：
```python
def test_cagr_5y()
def test_cagr_custom_range()
def test_cagr_start_after_end_raises()
def test_mdd_simple()                  # 已知序列驗算
def test_mdd_rolling()
def test_drawdown_periods_extraction() # 確認 peak/trough 正確
def test_recovery_days_calculation()
def test_sharpe_buy_and_hold()
def test_annualized_return()
def test_annualized_volatility()
```

**`tests/test_market_data.py`**：
```python
def test_resample_monthly_sum_volume()
def test_resample_monthly_end_price()
def test_monthly_return_calculation()
```

---

## 風險與緩解

| 風險 | 緩解 |
|------|------|
| yfinance API 限流或資料缺漏 | 每個 artifact 獨立 try/except，部分失敗不阻擋其他 tab |
| 前端無圖表庫（純 SVG）學習成本 | 先用最簡單的折線 SVG，heatmap 用 CSS grid + 背景色 |
| analysis.json 太大拖慢首頁 | daily_series 只放近 5 年；10Y+ 按需 lazy load |
| drawdown_periods 演算法邊界案例 | pytest 先跑 2-3 個已知序列驗算 |
| 現有 digest.json 不可污染 | analysis payload 完全獨立（`<ticker>.analysis.json`），digest 只加 summary 欄位 |

---

## 建議開發順序（MVP 優先）

```
P0（先做，奠定基礎）
  TASK-001  Artifact + 資料層
  TASK-010  測試（performance.py 部分）
  TASK-002  Ticker 頁 Tab 架構
  TASK-003  Drawdown Tab ← 新需求，P0 因為這是本次重點
  TASK-004  Price Tab

P1（核心功能完整）
  TASK-005  CAGR Tab
  TASK-006  Quarterly Tab
  TASK-007  Monthly Tab
  TASK-009  Glossary Tab

P2（進階）
  TASK-008  Sharpe Tab（策略擴展）
```

---

## 檔案異動清單

### 新增
```
stock_research/market_data.py
stock_research/performance.py
stock_research/fundamentals.py
stock_research/glossary.py
tests/test_performance.py
tests/test_market_data.py
research/<ticker>/artifacts/price_series.json        （generated）
research/<ticker>/artifacts/monthly_metrics.json     （generated）
research/<ticker>/artifacts/drawdown_analysis.json   （generated，新增）
research/<ticker>/artifacts/cagr_scenarios.json      （generated）
research/<ticker>/artifacts/strategy_metrics.json    （generated）
research/<ticker>/artifacts/quarterly_fundamentals.json （generated）
research/<ticker>/artifacts/glossary_refs.json       （generated）
site/data/tickers/<ticker>.analysis.json             （generated）
research/system/glossary.json
```

### 修改
```
stock_research/templates/dashboard/ticker.html       （tab 化重構）
stock_research/templates/dashboard/assets/dashboard.js（新增 8 個 render 函式 + tab router）
stock_research/templates/dashboard/assets/dashboard.css（新增 tab 樣式）
stock_research/dashboard.py                          （整合新 artifact 到 build pipeline）
scripts/research_ops.py                              （新增 build-analysis 命令）
```

### 不動
```
research/<ticker>/current.md    ← thesis contract 不動
research/<ticker>/state.json    ← thesis contract 不動
research/<ticker>/artifacts/digest.json  ← 只加 summary 指標欄位，不加 timeseries
```
