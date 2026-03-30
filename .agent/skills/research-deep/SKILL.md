---
name: research-deep
user-invocable: true
description: 讀取研究 outline，為每個 item 啟動獨立 agent 進行深度研究。禁用 Task Output。
allowed-tools: Bash, Read, Write, Glob, WebSearch, Task
---

# Research Deep - 深度研究

## 觸發方式
`/research-deep`

## 執行流程

### Step 1: 自動定位 Outline
在當前工作目錄查找 `*/outline.yaml` 文件，讀取 items 列表、execution 配置（含 items_per_agent）。

### Step 2: 斷點續傳檢查
- 檢查 output_dir 下已完成的 JSON 文件
- 跳過已完成的 items

### Step 3: 分批執行
- 按 batch_size 分批（完成一批需要得到用戶同意才可進行下一批）
- 每個 agent 負責 items_per_agent 個項目
- 啟動 web-search-agent（後台並行，禁用 Task Output）

**參數獲取**：
- `{topic}`: outline.yaml 中的 topic 欄位
- `{item_name}`: item 的 name 欄位
- `{item_related_info}`: item 的完整 yaml 內容（name + category + description 等）
- `{output_dir}`: outline.yaml 中 execution.output_dir（默認 ./results）
- `{fields_path}`: {topic}/fields.yaml 的絕對路徑
- `{output_path}`: {output_dir}/{item_name_slug}.json 的絕對路徑（slugify 處理 item_name：空格替換為 _，移除特殊字符）

**硬約束**：以下 prompt 必須嚴格復述，僅替換 {xxx} 中的變量，禁止改寫結構或措辭。

**Prompt 模板**：
```python
prompt = f"""## 任務
研究 {item_related_info}，輸出結構化 JSON 到 {output_path}

## 欄位定義
讀取 {fields_path} 獲取所有欄位定義

## 輸出要求
1. 按 fields.yaml 定義的欄位輸出 JSON
2. 不確定的欄位值標註 [不確定]
3. JSON 末尾添加 uncertain 數組，列出所有不確定的欄位名
4. 所有欄位值必須使用繁體中文輸出（研究過程可用英文，但最終 JSON 值為繁體中文）

## 輸出路徑
{output_path}

## 驗證
完成 JSON 輸出後，運行驗證腳本確保欄位完整覆蓋：
python .agent/skills/research/validate_json.py -f {fields_path} -j {output_path}
驗證通過後才算完成任務。
"""
```

### Step 4: 等待與監控
- 等待當前批次完成
- 啟動下一批
- 顯示進度

### Step 5: 彙總報告
全部完成後輸出：
- 完成數量
- 失敗 / 不確定標記的 items
- 輸出目錄

## Agent 配置
- 後台執行: 是
- Task Output: 禁用（agent 完成時有明確輸出文件）
- 斷點續傳: 是
