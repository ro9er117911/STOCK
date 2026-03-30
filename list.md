# 🚀 成長駭客專研 OS - 技能與系統快捷選單

為了解決語言不一致與辨識困難的問題，我已將全系統所有技能（Skills）與工作流（Workflows）優化為繁體中文標題，並同步 IDE 側邊欄顯示。

---

## 🎮 0. 系統控制中心 (Mission Control)
> **情境**：你不確定要用哪個工具，想讓 AI 幫你診斷並規劃整個研究/開發流程。

- 🤖 **`/pm <需求>`** 
  - **名稱**：🎮 任務調度中心 (PM)
  - **用途**：專屬 AI 參謀。他會分析你的意圖，挑選最佳工具組合。
  - **範例**：`/pm 我想重構一下 radar 模組，但我不確定會影響到誰`

---

## 📈 1. 股票與市場專研 (Domain-Specific)
> **情境**：需要進行個股分析、產業調研、市場盡職調查或投資研判時。

- 🔗 **`deep-market-research`**
  - **名稱**：🏗️ 深度市場調研工作流
  - **用途**：自動化市場研究腳本。
- 🤖 **`stock-research-operator`**
  - **名稱**：📈 專業股票投資研判
  - **用途**：原本的核心研究引擎。進行因果導因、假設驗證與情境行動。
- 🤖 **`market-research`**
  - **名稱**：📊 市場與競品分析
  - **用途**：ECC 精選調研模組。適合多維度競爭對手比較。

---

## 🔍 2. 結構化深度研究 (Deep-Research P0)
> **情境**：面對防災領域、AI 新應用等大型未知課題的知識體系建立。

- 🤖 **`research`**
  - **名稱**：🔍 領域初步研究
  - **步驟**：第一步，生成研究框架 (`outline.yaml`)。
- 🤖 **`research-add-items`**
  - **名稱**：➕ 補充研究對象
- 🤖 **`research-add-fields`**
  - **名稱**：➕ 補充研究欄位
- 🤖 **`research-deep`**
  - **名稱**：🧠 深度自動化調研
  - **步驟**：第二步，啟動多任務 Agent 背景採集細節。
- 🤖 **`research-report`**
  - **名稱**：📝 生成研究總結報告
  - **步驟**：第三步，將採集數據收斂成繁體 Markdown 報告。

---

## 🗺️ 3. 程式碼大腦地圖 (Understand-Anything P1)
> **情境**：MVP 開發需要檔案搜尋、重構代碼、或追蹤影響範圍時使用。

- 🤖 **`understand`**
  - **名稱**：🗺️ 專案架構掃描
- 🤖 **`understand-dashboard`**
  - **名稱**：📊 架構視覺化畫板
- 🤖 **`understand-chat`**
  - **名稱**：💬 架構知識對話
- 🤖 **`understand-explain`**
  - **名稱**：💡 代碼深度原理解析
- 🤖 **`understand-diff`**
  - **名稱**：🔄 Git 改動影響分析
- 🤖 **`understand-onboard`**
  - **名稱**：🆕 專案快速上手指南

---

## ⚡️ 4. 開發效率增強 (ECC P2)
> **情境**：撰寫腳本、修復 Bug、或查找技術文件時。

- 🤖 **`search-first`**
  - **名稱**：🔎 搜尋優先開發模式
- 🤖 **`documentation-lookup`**
  - **名稱**：📚 API 文檔即時查詢
- 🤖 **`search-first`**：寫任何程式碼前，先發動搜尋找最佳實踐。

---

## 🧩 5. 已掛載工具 (MCP Tools)
- `Context7`：串接 `documentation-lookup`，提供最新框架技術文件。
- `Tavily`：串接 `research`，提供強大的 Google/Bing 搜尋結果。
- `Chrome Dev Tools`：協助 Dashboard UI 調試。
- `Superpowers`：管理本地 shell 與權限。
