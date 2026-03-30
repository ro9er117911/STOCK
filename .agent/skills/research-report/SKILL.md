---
name: research-report
user-invocable: true
description: 將深度研究結果彙總為 Markdown 報告，覆蓋所有欄位並跳過不確定值。
allowed-tools: Read, Write, Glob, Bash, AskUserQuestion
---

# Research Report - 📝 生成研究總結報告

## 觸發方式
`/research-report`

## 執行流程

### Step 1: 定位結果目錄
在當前工作目錄查找 `*/outline.yaml`，讀取研究主題 (topic) 和輸出目錄 (output_dir) 配置。

### Step 2: 掃描可選摘要欄位
讀取所有 JSON 結果，提取適合在目錄中顯示的欄位（數值型、簡短指標），例如：
- github_stars
- valuation
- release_date
- 評分 (Score)

使用 AskUserQuestion 詢問用戶：
- 目錄中除了項目名稱外，還需要顯示哪些欄位？
- 提供動態選項列表（基於實際 JSON 中存在的欄位）。

### Step 3: 生成 Python 轉換腳本
在 `{topic}/` 目錄下生成 `generate_report.py`，腳本要求：
- 讀取 output_dir 下所有 JSON。
- 讀取 fields.yaml 獲取欄位結構。
- 覆蓋每個 JSON 的所有欄位值。
- 跳過值包含 `[不確定]` 的欄位。
- 跳過 uncertain 數組中列出的欄位。
- 生成 Markdown 報告格式：目錄（帶錨點跳轉 + 用戶選擇的摘要欄位） + 詳細內容（按欄位分類）。
- 保存到 `{topic}/report.md`。

**目錄格式要求**：
- 必須包含每一個項目 (item)。
- 每個項目顯示：序號、名稱（錨點連結）、用戶選擇的摘要欄位。
- 示例：`1. [GitHub Copilot](#github-copilot) - 評分: 85%`

#### 腳本技術要點（必須遵循）

**1. JSON 結構相容**
支持兩種 JSON 結構：
- 扁平結構：欄位直接在頂層。
- 嵌套結構：欄位在分類 (category) 子字典中。

**2. 分類 (Category) 多語言映射**
建立雙向映射以兼容各種命名：
```python
CATEGORY_MAPPING = {
    "基本資訊": ["basic_info", "基本信息", "基本資訊"],
    "技術特性": ["technical_features", "技術特性", "技術特點"],
    "效能指標": ["performance_metrics", "效能指標", "性能指標"],
    "商業資訊": ["business_info", "商業信息", "商業資訊"],
    "競爭與生態": ["competition_ecosystem", "競爭與生態"],
}
```

**3. 複雜值格式化**
- 列表字典：每個字典格式化為一行，用 ` | ` 分隔鍵值。
- 普通列表：短列表用逗號連接，長列表分行顯示。
- 長文本：添加換行符 `<br>` 以提高可讀性。

**4. 額外欄位收集**
收集 JSON 中有但 fields.yaml 中沒定義的欄位，放入「其他資訊」分類。

### Step 4: 執行腳本
運行 `python {topic}/generate_report.py`

## 輸出
- `{topic}/generate_report.py` - 轉換腳本
- `{topic}/report.md` - 彙總報告
