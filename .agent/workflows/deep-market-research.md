---
description: 深度市場調研與投資研判工作流 (Deep Market Research Workflow)
---

# 深度市場調研與投資研判工作流 (Deep Market Research Workflow)

此工作流融合了 GitHub `deep-research-skills` 的「分階段深度檢索」方法論，與 `stock-research-operator` 的「市場判斷與變數追蹤」邏輯。適用於面對複雜商業動態（如微軟與 OpenAI/Anthropic 的戰略博弈）時，進行有結構的資訊挖掘與投資決策。

## 階段一：構建調研提綱 (Phase 1: Outline Generation)

在進行任何分析前，先定義研究的邊界與需要收集的核心字段。

**執行指令 / 動作：**
1. 定義研究主題（例如："微軟 2026 AI 戰略佈局與模型合作夥伴"）。
2. 列出待調研對象 (Items)，例如：`[OpenAI, Anthropic, MSFT Azure, Copilot]`。
3. 為每個對象定義必須收集的欄位 (Fields)，包括：
   - 近期股權變動 / 合作協議條款
   - 算力消費承諾 (CapEx impact)
   - 產品整合進度 (e.g., Copilot 採用率)
   - 公司層面的潛在摩擦或利益衝突

## 階段二：並發深度檢索 (Phase 2: Deep Investigation)

針對提綱中的每一個 Item 與 Field，進行獨立且深度的 Web Search。

**執行指令 / 動作：**
1. 針對 `Item 1` 執行精確搜索（需組合時間限定詞如 2025/2026，以及特定關鍵字如 "friction", "investment", "exclusive"）。
2. 針對 `Item 2` 執行搜索，並交叉比對 `Item 1` 的結果（例如：Anthropic 獲得注資是否與 OpenAI 開放第三方算力發生在同一時期）。
3. 確保每個 Field 都有具體的數據支撐（例如：投資金額、合約規模、股權佔比）。若資訊缺失，需進行二次追問搜索。

## 階段三：市場痛點與機遇剖析 (Phase 3: Market Judgment Synthesis)

將收集到的原始數據，透過「市場判斷」濾鏡進行轉譯。

**執行分析步驟：**
1. **痛點分析 (Pain Points)：**
   - 從主角公司（如微軟）的視角，找出商業模式中的脆弱點（單點依賴、毛利侵蝕、合約漏洞）。
2. **投資機遇 (Investment Opportunities)：**
   - 尋找對沖策略（Hedging）：企業如何透過新投資（如 Anthropic）來降低現有風險。
   - 基礎設施紅利：識別誰是「賣鏟子的人」（如 Azure 算力消耗）。
   - 找出市場尚未完全反映 (underpriced) 的戰略轉換價值。
3. **制定觀測指標與觸發條件：**
   - 設定未來一至兩個季度的觀測指標（如 CapEx 增速變化、企業端續約率）。
   - 定義失效條件（Thesis Breaker）與觸發行動（加碼/減碼）。

## 階段四：生成投資策略報告 (Phase 4: Output Final Report)

將上述成果整理為結構化的 Markdown 報告，交由使用者審閱。

**報告必備章節：**
- **核心動態掃描** (Executive Summary of Events)
- **痛點分析** (Structural Risks & Pain Points)
- **投資機遇** (Strategic Shifts & Opportunities)
- **總結與操作啟示** (Actionable Rules & Triggers)

---
> **提示：** 本工作流強迫 AI 在給出結論前，必須先經歷「列提綱 -> 深度填空」的窮舉過程，避免針對複雜三角關係產生幻覺或以偏概全的推論。
