# STOCK 專案外部模組分析：ai-trader & expert-skills

本報告基於近期對於相關開源專案的研究，評估其融入 `STOCK` 專案 Milestone 的可行性。

## 分析目標
1. **[ai-trader](https://github.com/whchien/ai-trader)**：具備 MCP 支援的 Backtrader 回測框架。
2. **[expert-skills](https://github.com/AskRoundtable/expert-skills)**：提供 Munger、Feynman 等大師級心理模型的 Agent 技能。

## 評估結論

### 1. ai-trader 
*   **技術契合度**：極高。STOCK 專案目前正需要強健的回測工具。ai-trader 不僅封裝了 Backtrader，還內建 CLI 與 MCP (Model Context Protocol) 伺服器，使我們的 Agent 能直接對策略發號施令。
*   **建議處理**：**納入 Milestone**。我們應在下一個 Alpha/Beta 版本的 Sprint 中，將其 MCP 伺服器整合進我們的 Agent 環境，並對接既有的價格資料。

### 2. expert-skills
*   **技術契合度**：中等。以不同的心理模型 (例如查理蒙格的思維模型) 來審視量化交易策略或風險控制，會有意想不到的幫助，但是需要耗費更多的對話輪次。
*   **建議處理**：**暫列 Reference**。不作為核心技術阻礙發布，可引入作為全域 Agent 技能的擴充套件，偶爾在 Maestro strategy 會議上調用，提供反向與對照思考。

## 下一步行動
1. 在 STOCK 專案的 `milestone.md` 中新增「整合 ai-trader MCP 伺服器並實作首次回測」階段。
2. 將 `expert-skills` 列為未來 Agent 進階互動技能的參考來源。
