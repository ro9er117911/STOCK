# Agent 協作協議 (Agent Coordination Rules)

本文件定義了多 Agent 協作模式下的訊息傳遞、責任邊界與任務接棒機制。

---

## 1. 職能矩陣 (Role Matrix)

| 角色 | 入口/出口 | 核心工具 | 職責 |
| --- | --- | --- | --- |
| **PM (Antigravity)** | 入口 | ASK/SPEC | 需求解構、draft 工單編譯、freeze gate、任務編排、最終驗收。 |
| **OMC Executor** | 執行 | Context7/FS | 深度推理、外科手術式代碼修改、自我迭代。 |
| **OMX Executor** | 探索 | ParallelWorker | Repo 掃描、長輸出摘要、平行驗證、持久化 State。 |
| **Codex Plugin** | 驗證 | adversarial-review | 獨立代碼審查、壓力測試、Bug 修復委派。 |

---

## 2. 協作傳遞機制 (The Handoff)

### 2.1 工單化協議 (Tasking)
- **傳遞路徑**：PM → `./.ai/scripts/brief.sh` → draft `task.yaml` → `./.ai/scripts/freeze.sh` → frozen `task.yaml` → `./.ai/scripts/bridge.sh` → Executor。
- **原則**：Executor 只讀 frozen `task.yaml`，不與 PM 共享對話歷史（減少上下文污染與 Token 浪費）。
- **補充**：`request.txt` 只作為原始需求紀錄，不是執行契約。

### 2.2 多 Agent Teams 配置
當開啟 `AGENT_TEAMS` 時，應遵循以下預設配置：
- **Executor**: 通用程式實作。
- **Debugger**: 專攻 Build 與型別錯誤。
- **Designer**: 負責前端樣式與 UI 任務。

---

## 3. 分層執行原則 (Layered Execution)

1. **優先讀取 5 檔**：不要一開始就進行全 Repo 掃描。
2. **surgical edit**：優先修改受影響的最小區塊，而不是重寫整份檔案。
3. **測試優先**：在代碼修改完畢後，必須優先執行與修改路徑相關的最小單元測試。
4. **freeze-first**：draft 可以重寫，frozen task 只能執行或退回新 draft。

---

## 4. 全域狀態管理

- **`.codex/` 與 `.omx/`** 僅保存本機 Runtime State，不可視為 Repo Source of Truth。
- **`state.json`**：針對特定股票研究（Research Domain），應維護其研究進度與假設驗證狀態。
