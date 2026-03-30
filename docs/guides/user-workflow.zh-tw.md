# 使用者操作流程介紹

## 目錄

- [這份文件在講什麼](#這份文件在講什麼)
- [整體流程總覽](#整體流程總覽)
- [情境 1：新增一檔候選標的](#情境-1新增一檔候選標的)
- [情境 2：把候選標的推進到可決策](#情境-2把候選標的推進到可決策)
- [情境 3：追蹤既有研究與事件更新](#情境-3追蹤既有研究與事件更新)
- [平常要看哪些檔案](#平常要看哪些檔案)
- [常用指令](#常用指令)
- [簡單操作原則](#簡單操作原則)

## 這份文件在講什麼

這個 repo 現在不是單純的研究筆記庫，而是一套 personal-first 的美股研究決策 OS。

核心流程是：

`候選標的進件 -> 基本面研究 -> 可執行 thesis -> 後續事件校準`

你可以把它理解成一套「先決定要不要研究，再決定要不要買，之後持續驗證」的工作流。

## 整體流程總覽

研究狀態固定分成 6 個階段：

- `candidate`：剛進候選名單，還沒開始完整研究
- `in_research`：正在蒐集資料、整理 thesis
- `ready_to_decide`：研究已成形，可以決定買 / 不買 / 延後
- `active`：已成為正式追蹤 thesis
- `rejected`：研究後決定先不買，但保留理由
- `archived`：舊 thesis 封存，不再當前追蹤

量化雷達在這套流程中只做兩件事：

- 幫你把候選標的排優先順序
- 提醒風險，不直接替你做交易決定

## 情境 1：新增一檔候選標的

如果你今天想把一檔股票放進研究流程，先用 `upsert-candidate` 建立 dossier。

```bash
python3 scripts/research_ops.py upsert-candidate \
  --ticker NVDA \
  --company-name "NVIDIA" \
  --research-topic "AI capex beneficiary with valuation discipline" \
  --origin manual_watchlist \
  --stage candidate \
  --radar-flag "52-week breakout" \
  --radar-summary "價格強，但估值也不便宜。" \
  --radar-risk-level medium \
  --note "先放入候選名單，等待進一步研究。"
```

做完之後，系統會同步更新：

- `research/NVDA/state.json`
- `research/NVDA/current.md`
- `research/system/candidates.json`

這一步的目標不是下結論，而是先留下「為什麼值得研究」。

## 情境 2：把候選標的推進到可決策

當你開始做基本面研究，就把狀態從 `candidate` 推到 `in_research`。

```bash
python3 scripts/research_ops.py upsert-candidate \
  --ticker NVDA \
  --company-name "NVIDIA" \
  --research-topic "AI capex beneficiary with valuation discipline" \
  --origin manual_watchlist \
  --stage in_research \
  --note "已開始整理 primary sources 與 thesis。"
```

等你已經有：

- 一句話 thesis
- 核心假設
- 主要風險
- 情境分析
- action rules

就可以把狀態推到 `ready_to_decide`。

如果研究後覺得先不買，也不要刪掉，改成 `rejected`，並留下原因：

```bash
python3 scripts/research_ops.py upsert-candidate \
  --ticker NVDA \
  --company-name "NVIDIA" \
  --research-topic "AI capex beneficiary with valuation discipline" \
  --origin manual_watchlist \
  --stage rejected \
  --current-action "Do not buy; keep only as a comparison anchor." \
  --invalidation-reason "預期報酬已不夠補償當前估值風險。" \
  --note "研究完成，但目前 reward/risk 不合格。"
```

這樣之後你回頭看，會知道自己當初不是「忘了買」，而是「有理由地不買」。

## 情境 3：追蹤既有研究與事件更新

對已經在正式追蹤的標的，例如 `MSFT`、`PLTR`、`MAR`，平常主要是跑事件更新流程：

```bash
python3 scripts/research_ops.py poll --trigger event
python3 scripts/research_ops.py draft-refresh --trigger event
```

這條流程會做幾件事：

- 抓新事件
- 判斷哪些事件需要刷新 thesis
- 更新 `state.json`、`current.md`、`review_summary.json`
- 保留 `thesis_change_log` 與 `outcome_markers`

如果你只是要把既有 dossier 全部補到最新 vNext 契約，可用：

```bash
python3 scripts/research_ops.py sync-research-contracts
```

如果只是重建候選清單索引，可用：

```bash
python3 scripts/research_ops.py sync-candidates
```

## 平常要看哪些檔案

最常用的檔案有這幾個：

- `research/system/candidates.json`
  看目前有哪些候選、研究到哪一階段
- `research/<ticker>/current.md`
  看單一標的目前的完整 thesis
- `research/<ticker>/state.json`
  看 machine-readable 狀態，適合給 automation 用
- `research/<ticker>/artifacts/review_summary.json`
  看最近一次更新到底改了什麼
- `site/data/portfolio.json`
  看 dashboard 背後的聚合資料

如果你只想快速掌握整體狀況，先看 `research/system/candidates.json` 就夠了。

## 常用指令

初始化 baseline：

```bash
python3 scripts/research_ops.py bootstrap-baselines --force
```

建立或更新候選標的：

```bash
python3 scripts/research_ops.py upsert-candidate ...
```

重建候選索引：

```bash
python3 scripts/research_ops.py sync-candidates
```

同步所有研究檔到 vNext 契約：

```bash
python3 scripts/research_ops.py sync-research-contracts
```

抓事件：

```bash
python3 scripts/research_ops.py poll --trigger event
```

生成研究更新草稿：

```bash
python3 scripts/research_ops.py draft-refresh --trigger event
```

重建 dashboard：

```bash
python3 scripts/research_ops.py build-dashboard
```

## 簡單操作原則

- 先決定研究階段，再補內容，不要一開始就想把 thesis 寫到完美
- `radar_*` 只是提醒，不要把它當成自動交易訊號
- 不買也要留下理由，`rejected` 比刪掉更有價值
- 重大事件後要更新 thesis，不要只更新情緒
- 如果同一檔股票的結論常反覆改變，就去看 `thesis_change_log` 和 `outcome_markers`

