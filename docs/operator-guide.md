# Stock Research Operator Guide

## 事件來源 Input 在哪裡

正式來源白名單在 [`research/system/source_registry.json`](/Users/ro9air/STOCK/research/system/source_registry.json)。

每筆來源至少定義：

- `ticker`
- `source_id`
- `source_type`
- `kind`
- `url`
- `status`
- `priority`
- `title_keywords`
- `allow_patterns`
- `notes`

如果來源不在這份 registry 裡，或 `status != active`，pipeline 就不會輪詢它。

## 最終輸出有哪些

正式研究輸出：

- `research/<ticker>/current.md`
- `research/<ticker>/state.json`
- `research/system/candidates.json`
- `research/<ticker>/events.jsonl`
- `research/<ticker>/artifacts/review_summary.json`
- `research/<ticker>/artifacts/digest.json`
- `research/<ticker>/artifacts/citations.json`

Delivery surfaces：

- GitHub PR：顯示本輪 material refresh 的 reviewable diff
- Email：只在 material refresh PR create/update 時寄出摘要
- Dashboard：從 merged `main` 生成的 summary-first 靜態站
- Local cockpit：如果有 `research/system/portfolio.private.json`，會額外生成本機私有 dashboard

執行期中間產物：

- `automation/run/poll-summary.json`
- `automation/run/draft-summary.json`
- `automation/run/canonical-digest.json`
- `automation/run/notification-payload.json`
- `automation/run/pr-body*.md`
- `automation/run/email-preview.*`
- `automation/run/dashboard-local/`

## 各 surface 代表什麼狀態

- PR：最新 automation draft，可能尚未合併
- Email：material refresh 的精簡摘要，附 PR 與 dashboard 連結
- Dashboard：只顯示 merged `main` 的正式狀態，不顯示未審稿 preview
- Local cockpit：包含你的私有部位資料，不應 commit

## vNext workflow 怎麼看

- `research_stage`：`candidate`、`in_research`、`ready_to_decide`、`active`、`rejected`、`archived`
- `candidate_origin`：目前預設來源為 `manual_watchlist`、`ad_hoc_idea`、`quant_radar`
- `decision_status`：補充你此刻對該 dossier 的決策狀態，不等同交易執行
- `radar_*`：研究前雷達，只做排序與提醒，不是硬性 veto
- `outcome_markers` / `thesis_change_log`：用來回看 thesis 怎麼被事件改寫，以及哪些判斷最常漂移

`research/system/candidates.json` 是目前候選與正式 dossier 的工作流索引。它可以手動編修，但最穩妥的做法仍是透過 CLI 生成，避免漏掉 `state.json` / `current.md` 的同步更新。

## 你通常要看哪裡

- 想知道事件來源有沒有成功輪詢：看 `poll-summary.json` 和各 ticker 的 `artifacts/source_status.json`
- 想知道這次到底改了什麼：看 PR 與 `review_summary.json`
- 想快速掌握目前持股狀態：看 dashboard
- 想整理候選研究與下一步：看 `research/system/candidates.json`
- 想確認 email 會寄什麼：看 `automation/run/email-preview.html` 與 `automation/run/email-preview.txt`
- 想把成本、持股數、目標倉位放進 cockpit：從 `research/system/portfolio.private.json.example` 複製成 `research/system/portfolio.private.json`
