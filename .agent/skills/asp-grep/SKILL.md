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

---
*註：此工具主要依賴 `ast-grep` 引擎。在處理中文語境或配置時，請確保遵從全域定義的半形標點符號規則。*
