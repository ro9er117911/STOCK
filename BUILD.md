# STOCK Dashboard Build & Serve (Single Source of Truth)

本文件定義本地開發唯一推薦流程，避免「重開了但還是舊資料」或「build 了但頁面抓不到」。

## 1) 先釐清兩個輸出目錄

- `site/`: 公開版 dashboard 輸出
- `automation/run/dashboard-local/`: 本地私有版 dashboard（含 private overlay）

本地開發請以 `automation/run/dashboard-local/` 為主，並由 `build-dashboard` 一次同步產生兩份輸出。

## 2) 標準開發流程（每次改資料都照這套）

在 repo root 執行：

```bash
# A. 生成分析 artifacts（price/drawdown/monthly/strategy）
./.venv/bin/python -m stock_research build-analysis

# B. 生成 dashboard 靜態頁（同時更新 site/ 與 dashboard-local/）
./.venv/bin/python -m stock_research build-dashboard
```

然後開兩個服務：

```bash
# Terminal 1: Backend API (port 8001)
./.venv/bin/python -m stock_research serve-cockpit-api --host 127.0.0.1 --port 8001

# Terminal 2: Frontend static server (port 8000)
./.venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory automation/run/dashboard-local
```

打開：

- Frontend: `http://127.0.0.1:8000/index.html`
- API: `http://127.0.0.1:8001`

## 3) 什麼情況需要重啟？什麼不需要？

- 不需要重啟 frontend server：
  - 只要你重新執行過 `build-dashboard`，靜態檔已覆蓋，瀏覽器強制重整（Cmd+Shift+R）即可。
- 需要重啟 frontend server：
  - 你改了 serve 目錄、port、或 bind host。
- 需要重啟 backend API：
  - 你改了 `serve-cockpit-api` 程式碼或 API 設定。

## 4) 快速驗證（避免「畫面有開但資料是空」）

```bash
# 應該有 strategy 檔，Sharpe tab 才不會顯示「策略指標資料不可用」
ls automation/run/dashboard-local/data/tickers/*.strategy.json

# 應該有 analysis 檔，Price/Drawdown tab 才不會是空
ls automation/run/dashboard-local/data/tickers/*.analysis.json

# 因子分析摘要（total_analyzed 不應長期是 0）
jq '.summary' automation/run/dashboard-local/data/factor_analysis.json
```

## 5) 常見問題對照

- 問題: Sharpe 顯示「策略指標資料不可用」
  - 原因: 缺少 `*.strategy.json`
  - 修正: 先跑 `build-analysis`，再跑 `build-dashboard`

- 問題: Factor Analysis 顯示 0 筆
  - 原因: build 輸出不是讀 repo `research/`（舊邏輯路徑錯誤）或外部資料源暫時不可達
  - 修正: 先重跑 `build-dashboard`；若外網不可達，沿用既有 artifacts 仍可顯示先前結果

- 問題: API 可用但前端一直是舊畫面
  - 原因: serve 目錄錯誤或瀏覽器快取
  - 修正: 確認 `--directory automation/run/dashboard-local`，再做 hard refresh

## 6) 服務連線一致性（重要）

- Frontend 固定 `127.0.0.1:8000`
- Backend 固定 `127.0.0.1:8001`
- 避免 `localhost` / `127.0.0.1` 混用造成解析差異，開發時統一使用 `127.0.0.1`
