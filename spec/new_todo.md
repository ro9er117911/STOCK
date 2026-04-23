TL;DR：把你許願的功能收斂成一個可落地的「單一股票分析頁 v2」需求說明書，核心是新增 5 個分頁：股價、月度資料、季度資料、CAGR 試算、策略 Sharpe、名詞解釋；這件事本質上是在現有 thesis OS 上加一層「可計算、可視覺化、可教學」的分析層，而不是再做一套新的量化平台。

3 個關鍵檢核

1. 先確認產品邊界：這次是「單一標的分析頁增強」，不是把整個 repo 改造成全市場量化平台。
2. 先確認資料定義：月度資料預設為月 K / 月報酬 / 月成交量彙總；季度資料預設為財報季度指標。
3. 先確認計算口徑：CAGR、Sharpe 的公式、基準、無風險利率、再平衡頻率必須先寫死，不然後面數字會亂。

你現在 repo 的現況是：vNext 明確把產品定義成 personal-first 的美股研究決策 OS，量化資料只扮演研究前雷達與風險提醒，不是核心決策引擎 。目前 dashboard 會產出 ticker digest、portfolio digest、研究頁與 ticker 頁，但 digest 內容仍以 thesis、assumption、action rules、event timeline、source status、post-mortem 與 quote snapshot 為主，還沒有歷史價格序列、月度/季度財務面板、CAGR 試算器、Sharpe 分析或 glossary registry 。現有 ticker 頁面也只有部位、health、alerts、assumptions、timeline、rules、sources 等 panel，沒有 tab-based 的分析分頁 。另外目前 market snapshot 只抓約 1 個月的日線與即時 quote／VIX 狀態，並不足以支撐長期 CAGR 或策略 Sharpe 計算 。功能缺口審計也指出目前量價雷達、exception monitoring、post-mortem 都還在 prototype/basic 階段，代表這類分析功能還沒有完整工程化 。

以下直接給你可實作的需求說明書。

# 單一股票分析頁 v2 需求說明書

## 1. 文件目的

在既有 `Stock Research Operator` 基礎上，新增一個「單一股票分析頁 v2」，讓使用者在同一頁面內完成以下任務：

* 看一檔股票的歷史股價與區間表現
* 看月度資料與季度資料
* 試算不同持有期間的 CAGR
* 檢視某策略或持有邏輯的 Sharpe ratio
* 查閱頁面中所有專有名詞的定義與公式

本功能是對既有研究 OS 的增強層，不改變 `current.md + state.json` 作為核心 thesis contract 的定位 。

## 2. 產品定位

這不是新的量化研究平台。
這是「研究 thesis + 可計算分析面板」的整合頁。

定位分成兩層：

第一層是既有 thesis OS。
用途是記錄研究狀態、假設、風險、事件與決策變化。

第二層是這次新增的單檔分析頁。
用途是回答兩個高頻問題：

* 這檔股票過去到底怎麼走
* 我現在看到的 thesis，配上價格/財報/策略表現，值不值得進一步研究或決策

## 3. 使用者與核心情境

### 3.1 使用者角色

1. 使用者本人
   負責做標的研究、決定是否進場、複盤 thesis。

2. TA / 研究助理
   負責協助整理數據、檢查口徑、驗證計算結果、維護 glossary。

### 3.2 核心情境

情境 A：第一次研究一檔股票
使用者打開 ticker 頁後，希望先看：

* 最近 1 年 / 3 年 / 5 年價格走勢
* 最大回撤
* 近 8 季營收、EPS、FCF
* 若 3 年前買入到現在，CAGR 大概多少

情境 B：已有 thesis，要驗證是否還站得住
使用者希望在 thesis 與價格/財報視圖之間切換，不要分散在多個檔案或網站。

情境 C：看到術語但不想跳出頁面查
例如 CAGR、Sharpe、MDD、TTM、EV/Sales，頁面內就能直接展開解釋。

## 4. 範圍定義

## 4.1 本次納入

* 單檔股票價格分頁
* 月度資料分頁
* 季度資料分頁
* CAGR 試算分頁
* 策略 Sharpe 分頁
* 名詞解釋分頁
* 後端 artifact 與前端 tab 導航
* 測試與錯誤處理

## 4.2 本次不納入

* 全市場掃描
* 自動選股
* 台股月營收資料
* 跨市場供應鏈映射
* 情緒指數 / 社群熱度
* 即時交易下單

這樣的切法符合 repo 目前的 vNext 邊界，避免直接把 repo 拉成另一種產品 。

## 5. 關鍵名詞定義

這份需求書先把最容易歧義的資料定義寫死。

### 5.1 月度資料

預設定義為「市場月度資料」，不是月度財報。包含：

* 月末收盤價
* 當月報酬率
* 月成交量彙總
* 月波動度
* 月最大回撤摘要
* 可選：月度估值快照

原因是美股多數公司沒有台股式月營收制度化資料。若你把「月度資料」解讀成「月營收」，那會變成台股功能，已超出當前 repo 邊界。

### 5.2 季度資料

預設定義為「季度基本面資料」，包含：

* Revenue
* Gross Profit / Gross Margin
* Operating Income / Operating Margin
* Net Income
* EPS
* Free Cash Flow
* YoY / QoQ 變化率
* TTM 滾動值

### 5.3 CAGR

用來衡量某段期間的年化複合報酬率。
預設公式：

```text
CAGR = (Ending Value / Beginning Value) ^ (1 / Years) - 1
```

### 5.4 Sharpe Ratio

用來衡量每承擔一單位波動風險可獲得多少超額報酬。
預設公式：

```text
Sharpe = (Annualized Return - Risk Free Rate) / Annualized Volatility
```

## 6. 功能需求總表

這次建議做成 ticker 頁內的 6 個 tab。

1. 總覽 Overview
2. 股價 Price
3. 月度資料 Monthly
4. 季度資料 Quarterly
5. CAGR 試算 CAGR
6. 策略 Sharpe Sharpe
7. 名詞解釋 Glossary

你原本列了 5 類需求，但實作上最好保留一個總覽 tab，不然頁面入口太碎。

## 7. 詳細功能需求

## 7.1 總覽分頁 Overview

### 目的

把 thesis 與新分析層串起來。

### 顯示內容

* ticker、company name
* thesis 一句話摘要
* current action
* thesis confidence
* 最新價格
* 52 週高低區間位置
* 近 1Y / 3Y / 5Y 總報酬
* 近 8 季 revenue / EPS 迷你趨勢
* 常用指標快照：CAGR、volatility、Sharpe、MDD

### 需求

* 使用者在不切 tab 的情況下，先判斷這檔值不值得深入看
* 必須顯示資料日期 `as_of`
* 若資料缺漏，顯示「待補」而不是空白

## 7.2 股價分頁 Price

### 目的

提供可視化價格脈絡，而不是只有當前 quote。

### 顯示內容

* 價格走勢圖：1M / 3M / 6M / 1Y / 3Y / 5Y / MAX
* 指標切換：

  * price
  * drawdown
  * cumulative return
  * volume
* 關鍵數字：

  * 最新收盤價
  * 52 週高低
  * 區間報酬
  * annualized volatility
  * max drawdown

### 計算口徑

* 預設使用 adjusted close
* 圖表 interval：

  * 1Y 以下可用日線
  * 3Y / 5Y 可改週線
  * MAX 可視資料量切換週線/月線

### 驗收標準

* 切換區間時，圖表與 KPI 同步更新
* 所有百分比顯示統一到小數點後 2 位
* 若歷史資料不足，頁面顯示「資料不足，無法計算」

## 7.3 月度資料分頁 Monthly

### 目的

讓使用者從月度節奏觀察報酬與波動，不只看日線噪音。

### 顯示內容

* 月度表格：

  * month
  * month_end_price
  * monthly_return_pct
  * monthly_volume_sum
  * monthly_volatility
  * rolling_12m_return
* 視覺化：

  * 月報酬 heatmap
  * 滾動 12 個月報酬曲線
  * 月度 drawdown 條圖

### 特別規則

* 月度資料一律由日線 resample 產生
* 不可混用外部不同頻率資料，避免口徑不一

### 驗收標準

* 至少可回推 5 年月資料
* heatmap 的月份排序正確
* 與原始日線聚合後結果可抽樣驗算

## 7.4 季度資料分頁 Quarterly

### 目的

把 thesis 與財報節奏對齊。

### 顯示內容

* 季度表格：

  * fiscal_quarter
  * revenue
  * revenue_yoy_pct
  * revenue_qoq_pct
  * gross_margin_pct
  * operating_margin_pct
  * eps
  * eps_yoy_pct
  * fcf
  * shares_outstanding
* 視覺化：

  * revenue trend
  * EPS trend
  * margin trend
  * FCF trend
* 補充：

  * TTM revenue
  * TTM EPS
  * TTM FCF

### 資料來源規則

* 優先 official / structured source
* source_url 與 as_of 必須保留
* 若某欄位來源不同，需在 metadata 標記

### 驗收標準

* 至少呈現最近 8 季
* YoY / QoQ 公式正確
* 若某季缺資料，不可整行消失，需顯示 null / 待補

## 7.5 CAGR 試算分頁 CAGR

### 目的

讓使用者快速回答「這檔歷史上長期持有的年化表現如何」。

### 顯示內容

* 預設按鈕：

  * since inception
  * 1Y
  * 3Y
  * 5Y
  * 10Y
* 自訂區間：

  * start_date
  * end_date
* 輸出：

  * total_return_pct
  * CAGR_pct
  * start_price
  * end_price
  * years
* 可選：

  * 是否含股息 total return
  * 與 benchmark 比較

### 計算規則

* 預設先做「price CAGR」
* 若資料源支援，再做「total return CAGR」
* 自訂區間若不足 1 年：

  * 不顯示 CAGR
  * 改顯示 annualized return 或直接標註「不建議以 CAGR 解讀」

### 驗收標準

* 固定區間與自訂區間一致
* 同一區間 repeated run 結果一致
* 開始日大於結束日要阻擋

## 7.6 策略 Sharpe 分頁 Sharpe

### 目的

把「這檔股票很好」和「這個持有/交易規則有效」分開。

### 先決策：策略定義

這一頁不能直接算「股票本身的 Sharpe」然後假裝是策略 Sharpe。
必須明確定義 strategy return series。

### v1 建議支援 3 種策略模式

1. Buy and Hold
2. Moving Average Rule

   * 例如 price > MA200 才持有，否則空倉
3. Thesis-aligned Event Hold

   * 例如只有在 `research_stage in {ready_to_decide, active}` 且 action = add/hold 才視為持有

### 顯示內容

* 策略選擇器
* 回測期間
* 再平衡頻率
* risk-free rate
* 輸出：

  * annualized return
  * annualized volatility
  * Sharpe
  * max drawdown
  * win rate
  * exposure ratio
* 視覺化：

  * equity curve
  * drawdown curve
  * strategy vs buy-and-hold 比較

### 計算規則

* 日報酬序列作為基礎
* 無風險利率預設寫入 config
* 一律先不做交易成本與滑價
* v1 不做 short strategy

### 驗收標準

* 每個策略都有可重現的 return series
* 同一參數重跑結果一致
* 頁面明確顯示：這是示意回測，不是交易建議

## 7.7 名詞解釋分頁 Glossary

### 目的

降低頁面認知摩擦，讓 TA 與使用者都能對齊語言。

### 顯示內容

每個名詞要有 5 個欄位：

* term
* 中文名稱
* 定義
* 公式
* 為什麼這個指標重要
* 注意誤用
* related_terms

### v1 必備詞條

* CAGR
* Sharpe Ratio
* Annualized Return
* Volatility
* Max Drawdown
* Adjusted Close
* TTM
* YoY
* QoQ
* Gross Margin
* Operating Margin
* FCF
* Revenue Growth
* Beta
* Risk-free Rate

### 互動需求

* 頁內搜尋
* 點指標名稱可開側邊說明
* 公式支援 code block 顯示

### 驗收標準

* 頁面所有出現的專有名詞，都可以從 glossary 找到
* glossary 條目可版本化管理
* 新增術語不需要改 JS 核心邏輯

## 8. 非功能需求

## 8.1 可維護性

* 新分析功能不可直接污染 `state.json` thesis contract
* 建議新增獨立 artifacts，而不是把所有欄位硬塞進現有 digest

## 8.2 可解釋性

* 每一個數字都要可追溯資料來源與計算口徑
* 每個 tab 顯示 `as_of` 與 `source`

## 8.3 效能

* 單一 ticker 頁面載入應在 2 秒內完成靜態渲染
* 大型圖表資料先預聚合，避免前端即時計算過重

## 8.4 失敗容忍

* 單一資料源失敗不可讓整頁崩潰
* 每個分頁都要支援 partial render

## 9. 建議資料架構

現有 repo 是 static dashboard + digest 輸出模式，因此最穩的做法不是先擴 API，而是先擴 artifact。

### 建議新增 artifacts

```text
research/<ticker>/artifacts/
  price_series.json
  monthly_metrics.json
  quarterly_fundamentals.json
  cagr_scenarios.json
  strategy_metrics.json
  glossary_refs.json
```

### 建議新增 site data

```text
site/data/tickers/<ticker>.analysis.json
```

這個檔案專門給前端分頁讀取，不要把所有歷史序列混進原本 `digest.json`。

## 10. 建議 JSON contract

### 10.1 price_series.json

```json
{
  "ticker": "NVDA",
  "as_of": "2026-04-01",
  "currency": "USD",
  "series": [
    {
      "date": "2025-04-01",
      "adj_close": 123.45,
      "close": 124.01,
      "volume": 123456789
    }
  ],
  "derived": {
    "return_1y_pct": 25.31,
    "volatility_1y_pct": 32.44,
    "max_drawdown_3y_pct": -28.77,
    "high_52w": 140.00,
    "low_52w": 88.10
  },
  "source": {
    "provider": "yfinance",
    "url": "待補"
  }
}
```

### 10.2 quarterly_fundamentals.json

```json
{
  "ticker": "NVDA",
  "as_of": "2026-04-01",
  "quarters": [
    {
      "fiscal_quarter": "2025Q4",
      "revenue": 1000000000,
      "revenue_yoy_pct": 35.2,
      "revenue_qoq_pct": 8.4,
      "gross_margin_pct": 72.1,
      "operating_margin_pct": 41.8,
      "eps": 2.31,
      "eps_yoy_pct": 44.0,
      "fcf": 320000000
    }
  ],
  "ttm": {
    "revenue": 3900000000,
    "eps": 8.75,
    "fcf": 1200000000
  },
  "source": {
    "provider": "待補",
    "url": "待補"
  }
}
```

### 10.3 strategy_metrics.json

```json
{
  "ticker": "NVDA",
  "as_of": "2026-04-01",
  "strategies": [
    {
      "strategy_id": "buy_and_hold",
      "label": "Buy and Hold",
      "period": {
        "start": "2021-04-01",
        "end": "2026-04-01"
      },
      "risk_free_rate_pct": 3.0,
      "annualized_return_pct": 28.4,
      "annualized_volatility_pct": 35.1,
      "sharpe": 0.72,
      "max_drawdown_pct": -34.2,
      "win_rate_pct": 54.1,
      "exposure_ratio_pct": 100.0
    }
  ]
}
```

## 11. 後端實作需求

## 11.1 新增模組

建議新增以下檔案：

```text
stock_research/market_data.py
stock_research/fundamentals.py
stock_research/performance.py
stock_research/glossary.py
```

### market_data.py

責任：

* 拉歷史股價
* 產生日線 / 週線 / 月線聚合
* 輸出 `price_series.json` 與 `monthly_metrics.json`

### fundamentals.py

責任：

* 拉季度基本面
* 計算 YoY / QoQ / TTM
* 輸出 `quarterly_fundamentals.json`

### performance.py

責任：

* CAGR 計算
* strategy return series 計算
* Sharpe / volatility / MDD 計算
* 輸出 `cagr_scenarios.json` 與 `strategy_metrics.json`

### glossary.py

責任：

* 管理 glossary registry
* 提供 term lookup
* 讓前端 tooltip / drawer 直接使用

## 11.2 CLI 擴充

在 `stock_research/cli.py` 目前已有 `build-dashboard`、`poll`、`draft-refresh` 等命令 。建議新增：

```bash
python3 scripts/research_ops.py build-analysis --ticker NVDA
python3 scripts/research_ops.py build-analysis --ticker NVDA --with-fundamentals
python3 scripts/research_ops.py build-analysis --all
```

## 11.3 Digest 整合策略

目前 `build_ticker_digest()` 主要負責 thesis card 的組裝 。
建議不要直接把所有 timeseries 塞進 digest，而是：

* digest 保留 summary 指標
* 大型序列放 `analysis.json`
* 前端 ticker page 先讀 digest，再 lazy load analysis payload

這樣不會把首頁與 portfolio digest 變太重。

## 12. 前端實作需求

目前 ticker 頁是 panel layout，不是 tab layout 。
建議重構為：

```text
上方：hero + quick metrics
中段：tab navigation
下段：tab content
右側：decision rail 保留
```

### 12.1 tab 規格

* 預設 tab：Overview
* URL 支援 hash，例如：

  * `#price`
  * `#monthly`
  * `#quarterly`
  * `#cagr`
  * `#sharpe`
  * `#glossary`

### 12.2 元件需求

* Line chart
* Bar chart
* Heatmap
* KPI cards
* Table with sort
* Glossary drawer / modal

### 12.3 前端容錯

* 若 analysis payload 缺一部分資料，該 tab 顯示待補
* 其他 tab 不受影響

## 13. 計算口徑需求

這一段最重要，因為如果不先寫死，後面會一直吵數字。

### 13.1 Return

* 預設用 adjusted close 計算日報酬
* return series：

```text
r_t = P_t / P_{t-1} - 1
```

### 13.2 Annualized Return

```text
(1 + cumulative_return) ^ (252 / trading_days) - 1
```

### 13.3 Annualized Volatility

```text
std(daily_returns) * sqrt(252)
```

### 13.4 Sharpe

```text
(annualized_return - risk_free_rate) / annualized_volatility
```

### 13.5 Max Drawdown

```text
drawdown_t = price_t / running_max_t - 1
MDD = min(drawdown_t)
```

### 13.6 QoQ / YoY

```text
QoQ = current_quarter / previous_quarter - 1
YoY = current_quarter / same_quarter_last_year - 1
```

## 14. 未解決痛點，這次需求要一併補掉

這一段是你上一輪要我「多說一點」的重點。

### 痛點 1：目前是 thesis OS，不是 analysis OS

repo 的核心是 thesis、事件與決策流，不是用來看長期價格與策略表現。你現在想要的功能，等於是在 thesis 旁邊補一個 analysis layer。這不是小改版，是資訊架構升級。

### 痛點 2：目前只有快照，沒有長序列

現有 risk snapshot 只抓短期日線與當前 quote，足夠做風險提醒，但不足以支持 CAGR、月度 heatmap、Sharpe 回測 。

### 痛點 3：月度資料容易定義錯

如果不先寫清楚，美股的「月度資料」很容易被誤解成台股月營收。但 vNext 明確鎖美股且排除台股資料源，這次只能先把月度資料定義成市場月度彙總，而不是月營收模組 。

### 痛點 4：Sharpe 沒有策略定義就毫無意義

Sharpe 不是一個股票欄位，而是 return series 的函數。你若沒有 strategy rule、持有期間、risk-free rate、rebalance 邏輯，Sharpe 數字只是裝飾。

### 痛點 5：專有名詞目前沒有治理層

現在 repo 有很多研究與風控術語，但沒有 glossary registry。這會導致 TA、你自己、未來協作者對相同術語的理解漂移。

### 痛點 6：前端目前不是分頁結構

現有 ticker 頁仍是 panel 堆疊，若硬塞更多模組，頁面會失控。必須先做 tab 化，不然使用成本會越改越高 。

## 15. 驗收標準

### 功能驗收

* 使用者可在單一 ticker 頁切換 6 個 tab
* 價格資料至少支援 1Y / 3Y / 5Y / MAX
* 月度 heatmap 可正確顯示最近 5 年
* 季度資料至少顯示最近 8 季
* CAGR 支援固定區間與自訂區間
* Sharpe 至少支援 buy-and-hold
* glossary 至少有 15 個術語

### 數值驗收

* CAGR、annualized return、volatility、Sharpe 的結果可由測試重算驗證
* 同輸入重跑結果一致
* 缺資料時不報錯、不顯示錯誤數值

### UX 驗收

* 使用者可在 3 次點擊內找到任何一個指標定義
* 不需要跳出 repo 外查公式
* 任一 tab 載入失敗不影響其他 tab

## 16. 建議開發順序

### P0

先做資料層與 tab 架構

* `market_data.py`
* `performance.py`
* ticker page tab 化
* `analysis.json`

### P1

補季度資料與 glossary

* `fundamentals.py`
* `glossary.py`
* tooltip / drawer

### P2

補 Sharpe 策略模式擴展

* moving average strategy
* thesis-aligned strategy
* benchmark compare

## 17. 最小可行版本 MVP

如果你想先做一版最小可用，建議只做這 4 個：

1. Price tab
2. Quarterly tab
3. CAGR tab
4. Glossary tab

先不要做：

* 月度 heatmap
* 多策略 Sharpe
* total return CAGR
* benchmark compare

原因很直接：
Price + Quarterly + CAGR + Glossary 已經能把「研究 thesis」和「價格/財報/指標解釋」串起來，且工程風險最低。

## 18. 直接可開工的 TASK 切分

### TASK-001：Ticker 頁 tab 化

交付物：

* 新版 `ticker.html`
* `dashboard.js` tab router
* `dashboard.css` tab style

### TASK-002：歷史價格與 CAGR

交付物：

* `market_data.py`
* `performance.py`
* `price_series.json`
* `cagr_scenarios.json`
* 測試：CAGR、MDD、volatility

### TASK-003：季度基本面

交付物：

* `fundamentals.py`
* `quarterly_fundamentals.json`
* 測試：YoY、QoQ、TTM

### TASK-004：Glossary Registry

交付物：

* `research/system/glossary.json`
* glossary loader
* UI drawer

### TASK-005：Sharpe v1

交付物：

* `strategy_metrics.json`
* buy-and-hold strategy engine
* 測試：annualized return / Sharpe

如果你下一步要，我可以直接把這份需求說明書拆成 `TASK.md + 檔案結構 + API/JSON schema + pytest 驗收案例`。
