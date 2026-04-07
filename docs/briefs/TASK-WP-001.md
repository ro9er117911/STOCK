# Task Brief: TASK-WP-001 — DCA Analysis Web App

## 1. 任務說明
將 `docs/daily/teacher.md` 中的 R 語言回測邏輯轉換為一個獨立的 HTML/JS 網頁應用。

## 2. 核心功能
- **資料抓取**: 使用 Yahoo Finance API (透過 Cloudflare Worker CORS Proxy)。
- **邏輯實現**: 用 Vanilla JS 實作 XTS/PerformanceAnalytics 的核心邏輯 (Wealth calculation, CAGR, MDD, Volatility)。
- **UI/UX**: 
    - 輸入欄位: Ticker, StartDate, EndDate, InitialAmount, PeriodicAmount, Frequency (Monthly/Weekly).
    - 視覺化: 使用 Chart.js 或 D3.js 繪製 Wealth 曲線。
    - 指標面板: 顯示 CAGR, MaxDrawdown, Sharpe, TotalProfit 等。

## 3. 技術契約
- **Frontend**: Single HTML file or simple HTML/JS structure.
- **Proxy**: 提供一個可配置的 Cloudflare Worker URL 欄位 (或預設使用的 proxy 邏輯)。
- **No external R dependencies**: 代碼必須完全在 JS 中執行。

## 4. 驗收標準
- [ ] 可正確抓取 `SPY` 資料。
- [ ] 計算出的 `Wealth(T)` 與 R 腳本邏輯一致。
- [ ] 曲線渲染正確且具有互動性。
- [ ] 支援從指定日期開始到當前的定期定額試算。
