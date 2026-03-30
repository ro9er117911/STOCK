---
name: research
user-invocable: true
allowed-tools: Read, Write, Glob, WebSearch, Task, AskUserQuestion
description: 對目標話題進行初步研究，生成研究大綱 (outline)。用於學術研究、基準測試調研、技術選型等場景。
---

# Research Skill - 初步研究

## 觸發方式
`/research <topic>`

## 執行流程

### Step 1: 模型內部知識生成初步框架
基於 topic，利用模型已有知識生成：
- 該領域的主要研究對象 / items 列表
- 建議的研究欄位框架

輸出 {step1_output}，使用 AskUserQuestion 確認：
- items 列表是否需要增減？
- 欄位框架是否滿足需求？

### Step 2: Web Search 補充
使用 AskUserQuestion 詢問時間範圍（如：最近 6 個月、2024 年至今、不限）。

**參數獲取**：
- `{topic}`: 用戶輸入的研究話題
- `{YYYY-MM-DD}`: 當前日期
- `{step1_output}`: Step 1 生成的完整輸出內容
- `{time_range}`: 用戶指定的時間範圍

**硬約束**：以下 prompt 必須嚴格復述，僅替換 {xxx} 中的變量，禁止改寫結構或措辭。

啟動 1 個 web-search-agent（後台），**Prompt 模板**：
```python
prompt = f"""## 任務
研究話題: {topic}
當前日期: {YYYY-MM-DD}

基於以下初步框架，補充最新 items 和推薦研究欄位。

## 已有框架
{step1_output}

## 目標
1. 驗證已有 items 是否遺漏重要對象
2. 根據遺漏對象進行補充 items
3. 繼續搜索 {topic} 相關且 {time_range} 內的 items 並補充
4. 補充新 fields

## 輸出要求
直接返回結構化結果（不寫文件）：

### 補充 Items
- item_name: 簡要說明（為什麼應該加入）
...

### 推薦補充欄位
- field_name: 欄位描述（為什麼需要這個維度）
...

### 資訊來源
- [來源 1](url1)
- [來源 2](url2)
"""
```

### Step 3: 詢問用戶已有欄位
使用 AskUserQuestion 詢問用戶是否有已定義的欄位文件，如有則讀取並合併。

### Step 4: 生成 Outline（分離文件）
合併 {step1_output}、{step2_output} 和用戶已有欄位，生成兩個文件：

**outline.yaml**（items + 配置）：
- topic: 研究主題
- items: 研究對象列表
- execution:
  - batch_size: 並行 agent 數量（需 AskUserQuestion 確認）
  - items_per_agent: 每個 agent 研究項目數（需 AskUserQuestion 確認）
  - output_dir: 結果輸出目錄（默認 ./results）

**fields.yaml**（欄位定義）：
- 欄位分類和定義
- 每個欄位的 name、description、detail_level
- detail_level 分層：極簡 → 簡要 → 詳細
- uncertain: 不確定欄位列表（保留欄位，deep 階段自動填充）

### Step 5: 輸出並確認
- 創建目錄: `./{topic_slug}/`
- 保存: `outline.yaml` 和 `fields.yaml`
- 展示給用戶確認

## 輸出路徑
```
{當前工作目錄}/{topic_slug}/
  ├── outline.yaml    # items 列表 + execution 配置
  └── fields.yaml     # 欄位定義
```

## 後續命令
- `/research-add-items` - 補充 items
- `/research-add-fields` - 補充欄位
- `/research-deep` - 開始深度研究
