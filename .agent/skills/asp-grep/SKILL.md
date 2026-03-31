---
name: asp-grep
description: 協助使用 ast-grep (asp-grep) 進行語法結構分析、程式碼搜尋與自動重構
---

# asp-grep (ast-grep) Skill

此 Skill 授權 Agent 使用 `ast-grep` (在此專案中稱為 `asp-grep`) 進行基於抽象語法樹 (AST) 的結構化搜尋與修改。

## 🎯 使用場景

1. **結構化搜尋**: 當傳統的 `grep` (如 `ripgrep`) 無法區分語法上下文時（例如：分辨 function 定義與 function 調用）。
2. **語法感知過濾**: 搜尋特定類型的節點（如：所有的 `async` 函數、未處理 Error 的 `try-catch` 塊）。
3. **大規模重構**: 自動化地將舊 API 更換為新 API，同時保持參數結構一致。
4. **提示詞修復**: 分析代碼結構並根據其 AST 節點推薦最佳的提示詞插入點或錯誤修復方案。

## 🛠️ 核心工作流

1. **定義模式 (Pattern)**: 使用符號 `$VAR` 來匹配任意節點。例如 `console.log($ARGS)`。
2. **編寫規則 (Rule)**: 在 YAML 中定義搜尋邏輯，可以使用 `inside`, `has`, `precedes`, `follows` 等關鍵字。
3. **執行掃描 (Scan)**: 使用 `ast-grep scan --inline-rules` 進行快速、即時的驗證與搜尋。
4. **驗證與校正**: 在大規模應用前，先針對目標文件的小片段進行測試。

## 📝 範例使用

如果要搜尋所有沒帶 `try-catch` 的 `await` 表達式：
```bash
ast-grep scan --inline-rules "
id: await-no-catch
language: TypeScript
rule:
  pattern: await $_
  not:
    inside:
      kind: try_statement
"
```

## 🛡️ Core Rules (全域規範)

在使用此 Skill 或產生任何代碼/圖表時，必須嚴格遵守以下規範：

1.  **Mermaid 語法規範**: 當產生任何 Mermaid 語法或相關圖例時，所有標點符號（如冒號 `:`、括弧 `()` `[]` `{}`、箭頭 `-->` 等）**必須使用半形 (ASCII) 字元**。不得使用中文輸入法產生的全形字元，以確保語法有效性。
2.  **連線埠對稱規範**: 嚴禁出現 Backend (8001) 與 Frontend (8000/3000) 埠號不對稱的情形。在修改任何 API 調用邏輯前，必須先核對連線設定。
3.  **視覺驗證規範**: 進行 UI 佈局調整後，在宣稱完成前必須主動建議或使用 `webapp-testing` (Playwright) 檢查元素重疊 (Overlap) 狀況。
4.  **索引建立規範**: 若 Code Search 失效 (is_code_search_indexed=false)，必須向 `main` 分支提交實際的程式碼檔案（如 `src/index_probe.py`）以觸發 GitHub Indexing Pipeline。

---
*註：此文件定義的規範位階高於一般實作建議。*
