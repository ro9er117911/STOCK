# CI/CD 與 GitHub Actions 失效檢查報告 (2026-04-28)

## 1) 目的與範圍
本報告針對目前 repo 的 CI/CD 與 GitHub Actions 狀態進行靜態檢查 + 本地測試重現，聚焦回答三件事：
1. 最近為什麼看起來「CI/CD 或 Actions 失效」。
2. 哪些是根因、哪些是症狀。
3. 下一步如何改善，並給出可執行修正順序。

## 2) 本次檢查方式
- 檢視 workflows：
  - `.github/workflows/ci.yml`
  - `.github/workflows/research-refresh.yml`
  - `.github/workflows/dashboard-site.yml`
- 本地執行測試：`python -m pytest -q`
- 對照失敗堆疊與程式碼關聯：
  - `src/stock_research/notify_line.py`
  - `src/stock_research/llm.py`
  - `src/stock_research/pipeline.py`
  - `tests/test_notify_line.py`
  - `tests/test_pipeline.py`

## 3) 主要發現 (Executive Summary)
目前「失效」不是單一問題，而是三類問題疊加：

### A. 單元測試契約漂移 (Contract Drift)
`tests/test_notify_line.py` 期待舊介面：
- `send_message(...)` 函式存在
- 訊息 payload 為 `type=text`

但目前 `src/stock_research/notify_line.py` 已切換為：
- 以 `send_messages(...)` 為主要 API
- `send_verdict(...)` 傳的是 Flex Message (`type=flex`)

=> 結果：至少 3 個測試必然失敗。這是「程式與測試不同步」造成的 deterministic failure。

### B. 測試流程中存在外部依賴，導致非決定性失敗
`tests/test_pipeline.py` 內的流程測試會走到 `draft_refreshes(...)` -> `generate_refresh(...)`，
而 `generate_refresh(...)` 在偵測到 `OPENAI_API_KEY` 存在時，會直接呼叫 OpenAI API。若 CI/執行環境網路策略、proxy、或金鑰可用性有問題，就會失敗。

本次重現出現：`Tunnel connection failed: 403 Forbidden`。

=> 這類失敗代表測試不夠 hermetic (封閉可重現)，對外部網路過度敏感。

### C. Workflow 對 Secrets / 外部服務耦合偏高，缺乏 fail-safe
`research-refresh.yml` 與 `dashboard-site.yml` 都把 `OPENAI_API_KEY` 放入執行環境。只要 API 發生短暫不可用、配額或網路問題，就可能讓 action 的關鍵步驟中止。

目前程式雖有某些 fallback，但行為不一致：
- 有些路徑會 graceful fallback
- 有些路徑 (尤其測試路徑) 仍可能硬失敗

## 4) 根因拆解

### 根因 1: API 演進後，測試沒有同步更新
- 程式端已升級到 Flex Message 與 `send_messages(...)`。
- 測試仍以舊的 text message / `send_message(...)` 假設驗證。

這是典型 refactor 後 contract 沒共同演進。

### 根因 2: Pipeline 測試沒有完全 mock LLM 邊界
雖然部分翻譯步驟有 mock，但核心 `generate_refresh(...)` 仍可能觸發真實網路請求。

測試應該驗證「流程協調」而不是「真實 OpenAI 可連線」，故目前測試邊界切分不正確。

### 根因 3: CI workflow 缺少外部依賴保護機制
目前 workflow 沒有明確分層：
- PR 必跑：純離線、可重現測試
- Nightly/Manual：允許線上模型與外部服務

導致當外部服務不穩時，看起來像「整體 CI 壞掉」。

## 5) 改進方案 (由快到慢)

### Phase 1 (立即，可在下一步開始改)
1. **修正 notify_line 測試契約**
   - 讓 `tests/test_notify_line.py` 改測 `send_messages(...)` 與 Flex payload。
   - 或補一層相容 wrapper `send_message(...)`（若要向後相容）。
2. **讓 pipeline 測試完全離線**
   - 在 `tests/test_pipeline.py` 針對 `generate_refresh` 或 `_request_openai_*` 做 mock。
   - 明確確保測試不依賴 `OPENAI_API_KEY` 是否存在。

### Phase 2 (短期，提升 CI 穩定度)
3. **切分 workflow 測試層級**
   - `ci.yml` 僅跑 deterministic tests (unit + mocked integration)。
   - 新增/保留一條 `integration-online` workflow，僅手動或排程執行。
4. **加入外部服務容錯策略**
   - 針對 OpenAI 呼叫加入 retry + backoff + timeout 分級。
   - 對可降級路徑改為 warning 並產生 artifact，不直接 fail 全流程。

### Phase 3 (中期，治理與可觀測性)
5. **建立 CI 失敗分類標籤**
   - `test_contract_drift` / `network_dependency` / `secrets_missing`。
   - 在 job summary 中輸出可讀診斷，減少排障時間。
6. **導入 pre-merge 守門**
   - 在 PR 檢查加入「測試與 public function 對齊」掃描（例如 API symbol smoke test）。

## 6) 建議的「下一步就來改」實作順序
1. 先修 `tests/test_notify_line.py` 與對應 API 相容層策略。
2. 再修 `tests/test_pipeline.py`，把 LLM 呼叫全部 mock 化。
3. 跑 `python -m pytest -q` 確認綠燈。
4. 接著調整 `ci.yml`，把線上依賴測試移出主 CI。

## 7) 風險與注意事項
- 若保留「主 CI 直接打 OpenAI」，即使修好當前 bug，仍會持續出現間歇性紅燈。
- 若直接把所有失敗都改成 warning，可能掩蓋真實退化；建議僅對可降級步驟使用。
- notify_line 若要向後相容舊 API，需明確註記 deprecation 期限，避免長期雙軌。

## 8) 結論
目前「最近 CI/CD 或 actions 失效」的核心不是 GitHub Actions 平台本身，而是：
- 程式與測試契約不同步
- 測試混入外部網路依賴
- workflow 未明確區分離線驗證與線上整合

只要先完成「測試契約同步 + 測試離線化」，主 CI 穩定度會立刻大幅提升；
再做 workflow 分層與容錯，就能把 action 失效率降到可控範圍。
