---
name: documentation-lookup
description: 使用來自 Context7 MCP 的最新庫與框架文檔，而非預訓練數據。適用於配置問題、API 參考、代碼示例及框架諮詢。
origin: ECC
---

# Documentation Lookup (Context7) - 📚 API 文檔即時查詢

當用戶詢問有關函式庫、框架或 API 的問題時，應透過 Context7 MCP（工具 `resolve-library-id` 與 `query-docs`）獲取最新的官方文件，而非僅依賴預訓練數據。

## 核心概念 (Core Concepts)

- **Context7**：專門提供即時官方文檔的 MCP 伺服器；請優先使用它而非預測邏輯。
- **resolve-library-id**：根據函式庫名稱與查詢內容，返回 Context7 相容的庫 ID（例如：`/vercel/next.js`）。
- **query-docs**：獲取特定庫 ID 的文檔內容與代碼片段。請務必先調用 `resolve-library-id` 以獲取有效的 ID。

## 何時使用

當用戶提出以下需求時啟動：
- 安裝或配置問題（例如：「如何配置 Next.js 中間件？」）。
- 需要依賴特定庫的代碼（例如：「寫一個 Prisma 查詢...」）。
- 需要 API 參考資訊（例如：「Supabase 的驗證方法有哪些？」）。
- 提及特定的框架或函式庫（React, Vue, Express, Tailwind, Prisma, Supabase 等）。

## 運作流程

### Step 1: 解析函式庫 ID
調用 **resolve-library-id** MCP 工具，帶入：
- **libraryName**：從問題中提取的函式庫名稱（例如：`Next.js`）。
- **query**：用戶完整的提問內容，這有助於提高結果的相關性。

### Step 2: 選擇最佳匹配
從解析結果中，根據以下標準選擇一個結果：
- **名稱匹配度**：優先選取與用戶提問最接近的名稱。
- **基準評分 (Benchmark score)**：分數越高表示文檔品質越好（100 為最高）。
- **來源信譽**：優先選取高 (High) 或中 (Medium) 信譽的來源。
- **版本資訊**：若指定版本（例如：「React 19」），優先選取特定版本的 ID。

### Step 3: 獲取官方文檔
調用 **query-docs** MCP 工具，帶入：
- **libraryId**：從第 2 步選定的庫 ID（例如：`/vercel/next.js`）。
- **query**：用戶具體的問題或任務，越精確越能獲得相關的代碼片段。

注意：針對同一個問題，請勿調用超過 3 次。若 3 次後仍無法釐清，請誠實說明不確定性，而非胡亂猜測。

### Step 4: 產出解答
- 使用最新獲取的資訊生成回答。
- 包含文檔中相關的代碼範例。
- 標註引用來源或版本（例如：「在 Next.js 15 中...」）。

## 最佳實踐
- **準確具體**：使用用戶的完整問題進行查詢，以獲得最高相關性。
- **版本意識**：當用戶提到版本時，盡量獲取版本對應的文檔。
- **優先官方來源**：在多個匹配項中，優先選取官方或原始維護者的套件。
- **隱私聲明**：在傳送給 Context7 前，請移除查詢中的所有 API 金鑰、密碼及敏感 Token。
