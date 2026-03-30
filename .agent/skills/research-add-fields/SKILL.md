---
name: research-add-fields
user-invocable: true
description: 向現有研究 outline 補充欄位定義。
allowed-tools: Bash, Read, Write, Glob, WebSearch, Task, AskUserQuestion
---

# Research Add Fields - ➕ 補充研究欄位

## 觸發方式
`/research-add-fields`

## 執行流程

### Step 1: 自動定位 Fields 文件
在當前工作目錄查找 `*/fields.yaml` 文件，自動讀取現有 fields 定義。

### Step 2: 獲取補充來源
詢問用戶選擇：
- **A. 用戶直接輸入**：用戶提供欄位名稱和描述。
- **B. Web Search 搜尋**：啟動 web-search-agent 搜尋該領域常用欄位。

### Step 3: 展示並確認
- 展示建議的新欄位列表。
- 用戶確認哪些欄位需要添加。
- 用戶指定欄位分類和 detail_level。

### Step 4: 保存更新
將確認的欄位追加到 fields.yaml，保存文件。

## 輸出
更新後的 `{topic}/fields.yaml` 文件（原地修改，需用戶確認）。
