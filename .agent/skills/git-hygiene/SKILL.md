---
name: git-hygiene
user-invocable: true
description: Git 狀態清理與事故回報工作流。先盤點、再切片提交、最後驗證與安全推送。
allowed-tools: Read, Write, Glob
origin: STOCK
---

# Git Hygiene - 🧹 Git 清理與事故回報工作流

當任務涉及「整理整個專案 Git 狀態」時，使用此 Skill。

## 適用情境
- 分支顯示 `ahead/behind`，且工作樹同時有已追蹤修改與未追蹤檔案。
- 需要把「發生過的 Git 問題」整理成可重複執行的修復流程。
- 需要讓 PM 能快速路由到標準 Git 清理流程。

## 本次 Incident 回報（可觀測）
1. Working tree 為 dirty：同時存在 tracked modifications 與 untracked files。
2. `main` 上直接累積未推送 commits（`origin/main...main` 顯示 `ahead`）。
3. untracked 功能檔未先分類就混在工作樹中，增加誤提交風險。
4. stash 有歷史項目但未治理（命名、用途、清理策略未定義）。
5. PM Step 1 依賴 `list.md`，但 repo 已無此檔，造成路由依據失效。

## 正確 Workflow
固定流程：`Preflight -> 變更分類 -> 分批 staging -> commit slicing -> 驗證 -> push`

1. Preflight
- `git status -sb`
- `git rev-list --left-right --count origin/main...HEAD`
- `git stash list`

2. 變更分類
- 先分成「功能檔 / 規範檔 / 既有未提交檔」三類，不混批處理。
- 任何不確定檔案先 `git diff` 查明，不要直接 `git add -A`。

3. 分批 staging
- 僅把本批需要的檔案加入 staging。
- 有混雜風險時使用 `git add -p` 做 hunk 級切片。

4. Commit slicing
- 每個 commit 只承載單一意圖（例如：測試基線、技能路由、文件治理）。
- commit message 要能直接說明「為什麼這一批一起提交」。

5. 驗證
- 跑對應測試（至少覆蓋本批核心變更）。
- 用 `git diff --cached --name-only` 檢查 staged 範圍。

6. Push
- 預設禁止改寫歷史與 force push。
- 僅在檢查通過後執行 `git push origin <branch>`。

## 反模式清單
- 在 dirty `main` 上把多種意圖一次混提。
- 使用 `git add -A` 無差別納管所有變更。
- 未驗證測試就直接 push。
- stash 無上下文（沒有用途說明、沒有清理時機）。

## 行動版 SOP（命令 + 完成條件 + 回滾點）

### Step 0: Baseline Snapshot
```bash
git status -sb
git rev-list --left-right --count origin/main...HEAD
git stash list
```
完成條件：確認 ahead/behind、dirty 範圍、stash 基線。  
回滾點：無（純讀取）。

### Step 1: Scope Verification
```bash
git diff -- <path>
git ls-files --others --exclude-standard
```
完成條件：每個變更檔已歸類，未歸類檔案為 0。  
回滾點：無（純讀取）。

### Step 2: Stage Current Slice
```bash
git add <file-a> <file-b> ...
git diff --cached --name-only
```
完成條件：staged 清單與本批意圖一致。  
回滾點：`git restore --staged <file>` 或 `git reset HEAD <file>`。

### Step 3: Commit Current Slice
```bash
git commit -m "<type>: <scope>"
```
完成條件：`git log -n 1 --oneline` 顯示預期訊息。  
回滾點：若尚未 push，可用 `git reset --soft HEAD~1` 重新切片。

### Step 4: Validation
```bash
pytest <relevant-tests>
```
完成條件：測試通過，且 `git status --short` 只剩預期待提交內容。  
回滾點：修正後重新測試；必要時新增一個修復 commit。

### Step 5: Push
```bash
git push origin main
```
完成條件：`git rev-list --left-right --count origin/main...main` 返回 `0 0`。  
回滾點：禁止 force push；若發現問題，新增修復 commit 再 push。

## Stash 治理規範
- 不隨意 drop 既有 stash；先保留，直到內容已被 commit 或明確淘汰。
- 新增 stash 必須寫用途，例如：`git stash push -m "wip/dashboard-copy-tuning-2026-03-31"`。
- 需要長期保留的 stash，應優先還原到備援分支而非永遠留在 stash stack。
