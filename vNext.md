# vNext 專案目標重定義

## Summary

- 專案主目標：把這個 repo 明確定義為「personal-first 的美股研究決策 OS」，核心任務是讓你在進場前，能更一致地形成可執行 thesis，而不是擴成跨市場量化平台。
- vNext 服務的核心流程：`候選標的進件 -> 基本面研究 -> 可執行 thesis -> 後續事件校準`。
- 量化的正式角色：只做研究前雷達與風險提醒，用來排序與聚焦，不具否決權，也不直接產生交易指令。
- 正式輸出仍以 `current.md` + `state.json` 為核心，但要從「持有後更新」擴成同時支援「進場前研究與決策紀錄」。
- vNext 不納入：台股資料源、跨市場供應鏈映射、全市場自動掃描、情緒/擁擠度指數、硬性量化 veto。

## Implementation Changes

- 新增一個候選研究層，接受三種最初版進件：手動 watchlist、臨時研究想法、少量量價篩選結果；這一層只負責把候選送進研究流程，不直接下判斷。
- 把研究流程明確分成固定狀態：`candidate`、`in_research`、`ready_to_decide`、`active`、`rejected`、`archived`；每個狀態都要可回溯原因。
- 對新標的的標準交付物固定為：一句話 thesis、可驗證假設、主要風險、情境分析、peer comparison、action rules、以及明確的「先不買/延後研究」理由。
- 保留現有事件更新能力，但要讓事件更新能回寫到「研究中的候選案」與「已建 thesis 的標的」，而不只服務既有持股研究。
- 把「一致性」做成正式能力：系統需保留決策前提、後續事件、結論變化與失效原因，讓之後可以自動回看哪些判斷最常漂移。

## Public APIs / Interfaces / Types

- 在 machine-readable 狀態中新增候選研究欄位：`research_stage`、`candidate_origin`、`decision_status`、`decision_updated_at`。
- 新增量化雷達欄位：`radar_flags[]`、`radar_summary`、`radar_risk_level`；這些欄位只能標記提醒，不能直接等同 `exit` 或 `do_not_buy`。
- 新增校準欄位：`outcome_markers[]`、`thesis_change_log[]`、`invalidation_reason`、`consistency_notes`。
- 若新增候選入口檔或佇列，介面預設為簡單、手動可編輯的資料格式，不引入複雜外部資料庫或全市場 universe schema。

## Test Plan

- 候選標的可從手動清單進件，並成功進入 `candidate -> in_research -> ready_to_decide` 流程。
- 一檔標的即使有量化風險旗標，仍可產出完整 thesis，但輸出中必須保留風險提醒與優先級訊號。
- 一檔最終不值得買的標的，系統也要留下可回看的拒絕理由，而不是直接消失。
- 後續重大事件進來時，系統能指出它改變了哪個假設、是否改變 thesis、以及是否造成決策狀態改寫。
- 既有 `PLTR`、`MSFT`、`MAR` 的更新流程不能因新增候選研究層而退化或破壞原本 artifact contract。

## Assumptions

- 主要使用者就是你自己，因此允許流程偏個人化，不以通用產品化為 vNext 目標。
- 正式市場範圍先鎖美股；台股與跨市場聯動只保留為 roadmap，不進核心目標。
- 成功標準以「研究與決策結論更一致」為第一優先；研究速度提升是次要收益。
- 校準機制以「盡量自動化」為原則，人工回填只保留在高訊號節點，不要求高頻手動評分。
