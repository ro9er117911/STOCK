---
description: 執行類似 Claude Code /insights 的歷史行為分析與系統最佳化
---
# /insights 工作流 (對話紀錄與行為分析)

這個工作流的目的是掃描你（User）與 Agent 最近的對話紀錄，幫助您分析編碼與研究習慣，找出摩擦點並提供具體改進建議。這會產出一個互動式的報告（Artifact），並在必要時為您的 `SOUL.md` 或系統級別提示詞提供「可複製貼上的」優化規則。

## 觸發條件
當使用者輸入 `/insights` 時觸發本工作流。

## 執行步驟

1. **讀取歷史對話紀錄 (Session Collection)**
   - Agent 將會檢索最近的對話內容（利用內部記憶系統 `brain/<conversation-id>/.system_generated/logs` 或近幾次的上下文對話）。
   - 從歷史記錄中提取 User 最常使用的指令、常見的工作目標（例如：優化儀表板、收集市場資料）與花費最多時間的任務類型。

2. **分析與洞察 (Analysis & Insights)**
   - **統計概覽 (Stats Dashboard)**: 評估對話長度、常用工具與高頻發送的特定請求類型。
   - **摩擦點 (Friction Points)**: 尋找溝通中的阻礙。例如有什麼指令需要 User 講第二次以上？有哪邊 Agent 經常做錯導致 User 必須去糾正（例如 Mermaid 標點符號問題、JSON 解析失敗等）？
   - **目標分類 (Workflow Patterns)**: 總結 User 最常見的幾種專案操作模式（例如：「建構新功能」、「架構重構」、「市場調研」）。

3. **產出洞察與更新建議報告 (Reporting)**
   - Agent 必須建立一個名為 `insights_report.md` 的 Artifact。內容應該包含：
     - **分析結果總結**
     - **常見摩擦與改進空間**
     - **Actionable Suggestions (具體行動建議)**: 針對發現的摩擦點提供「減少摩擦」的具體對策。
     - **規則推薦 (Rule Recommendations)**: 提供可供複製貼上加入 `AGENTS.md`、`SOUL.md` 或 `SKILL.md` 的條文。

4. **一鍵應用建議 (Apply & Optimize)**
   - 在產出 Artifact 之後，詢問使用者是否自動將這些具體規則（Quick Wins）加入相關的系統文件（如 `SOUL.md`、`AGENTS.md`）中。如果 User 允許，Agent 就自動執行 `multi_replace_file_content` 進行更新。
