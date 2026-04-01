> Archived snapshot.
> Active workflow lives in `rules/orc-architecture.md`, `.agent/skills/pm/SKILL.md`, `.ai/README.md`, `.ai/scripts/bridge.sh`, and `docs/architecture/implementation_plan.md`.
> Do not treat this file as source of truth.

TL;DR
`Antigravity × OMC terminal handoff` 的核心不是雙向互控，而是「PM 產生最小工單，OMC 依工單執行」。最低成本運作原則是：短 spec、少檔案、少工具、少輪次、必要時才驗證。

## Antigravity × OMC 的 terminal handoff

### 1. 目標

讓你在終端只打一個命令，由 Antigravity 當 PM 入口，Claude OMC 當執行器，中間用檔案 handoff，而不是用長對話直接串兩個模型。

### 2. 正確資料流

```text
你在 terminal 下指令
→ Antigravity 將需求壓縮成 task.yaml
→ bridge script 呼叫 OMC
→ OMC 讀 task.yaml 後執行
→ OMC 視需要使用 Context7 / filesystem
→ OMC 輸出 result.md
```

### 3. 為什麼要用 handoff file

因為直接把 Antigravity 的長對話傳給 OMC 會造成三種浪費：

* 重複傳需求
* 重複理解上下文
* 重複消耗 token

檔案 handoff 的作用像工單系統：

* PM 只負責寫工單
* 執行器只負責讀工單
* 不共享整段會議錄音

---

## 最小實作段落

### 1. 目錄結構

```bash
mkdir -p .ai/handoff .ai/prompts .ai/scripts
```

```text
.ai/
├─ handoff/
│  ├─ request.txt
│  ├─ task.yaml
│  └─ result.md
├─ prompts/
│  ├─ pm_to_task.md
│  └─ omc_execute.md
└─ scripts/
   └─ bridge.sh
```

---

### 2. `task.yaml` 範本

這是 Antigravity 唯一要交給 OMC 的東西。

```yaml
goal: implement login flow
scope:
  - add auth api route
  - add login form
  - add minimal tests

constraints:
  - no db schema change
  - minimum file edits
  - minimum token usage
  - prefer existing patterns

acceptance:
  - valid login works
  - invalid login shows error
  - tests pass

output:
  - summary
  - changed_files
  - test_results
  - risks
```

---

### 3. Antigravity 的任務

Antigravity 不碰 repo，不碰 Context7，不碰 filesystem。
只做需求壓縮。

建議固定指令模板：

```text
將以下需求壓縮成最小 task.yaml
規則：
1. 只輸出 YAML
2. 只保留 goal, scope, constraints, acceptance, output
3. 每一欄最短化
4. 不要解釋
5. 不要重複需求

需求：
{{USER_REQUEST}}
```

---

### 4. OMC 的執行規則

OMC 只吃 `task.yaml`，不重讀 Antigravity 對話。

固定執行 prompt：

```text
Read .ai/handoff/task.yaml and execute the task with minimum token usage.

Rules:
1. Read as few files as possible.
2. Use Context7 only if framework or API docs are necessary.
3. Use filesystem only for required files.
4. Prefer surgical edits over broad refactors.
5. Run only minimal necessary tests.
6. Write result to .ai/handoff/result.md with:
   - summary
   - changed files
   - test results
   - risks
```

---

### 5. `bridge.sh` 骨架

這版是概念正確、方便你後續替換 CLI 的最小殼層。

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
AI_DIR="$ROOT/.ai"
HANDOFF="$AI_DIR/handoff"

mkdir -p "$HANDOFF"

REQ="${*:-}"
if [ -z "$REQ" ]; then
  echo 'usage: bridge.sh "your task request"'
  exit 1
fi

cat > "$HANDOFF/request.txt" <<EOF
$REQ
EOF

echo "[1/3] Build task.yaml"

cat > "$HANDOFF/task.yaml" <<EOF
goal: $REQ
scope:
  - pending
constraints:
  - minimum token usage
  - minimum file edits
acceptance:
  - task completed
output:
  - summary
  - changed_files
  - test_results
  - risks
EOF

echo "[2/3] Run OMC"
cat > "$HANDOFF/omc_prompt.txt" <<EOF
Read .ai/handoff/task.yaml and execute the task with minimum token usage.
EOF

echo "[3/3] Write placeholder result"
cat > "$HANDOFF/result.md" <<EOF
summary:
- pending

changed files:
- pending

test results:
- pending

risks:
- bridge not connected to real CLI yet
EOF

echo
echo "Generated:"
echo "  $HANDOFF/task.yaml"
echo "  $HANDOFF/result.md"
```

這個骨架的重點不是功能完整，而是先把責任邊界固定住：

* request → task
* task → omc
* omc → result

---

## 最低成本運作建議

### 1. 把 Antigravity 當「spec compiler」

不要把 Antigravity 當第二個 coder。
它的最有價值工作是：

* 把模糊需求壓短
* 把限制條件寫清楚
* 把驗收條件固定

也就是只產生最小規格，而不是產生長篇策略。

---

### 2. Context7 / filesystem 只留在 OMC 端

因為真正需要查文件、讀檔、改檔的是執行器，不是 PM。

正確配置：

* Antigravity：無工具或極少工具
* OMC：保留 Context7、filesystem
* 其他 MCP：先不要加太多

原則很簡單：工具越多，agent 越容易亂查，token 越高。

---

### 3. 先讀 3 到 5 個檔案

不要讓 OMC 一開始掃整個 repo。

建議規則：

* 第一輪只找 3 到 5 個最相關檔
* 不夠再擴到 8 到 10 個
* 沒必要不做全 repo scan

這會直接影響 token 與錯誤率。

---

### 4. 只跑最小必要測試

不要預設：

* 跑全量 test suite
* 跑 e2e
* 跑完整 build matrix

先做：

* 單一相關測試
* 單一 build 指令
* 單一路徑驗證

只有 task 明確要求時才擴大。

---

### 5. 驗證層只在 bounded chunk 後使用

Codex review 不要每次都跑。
建議只在以下情境啟動：

* 修改超過數個檔案
* 牽涉 auth / payment / state management
* 要 merge 前
* OMC 自己標記高風險

否則只會增加成本。

---

### 6. 結果只回摘要，不回完整過程

OMC 的 `result.md` 應只保留：

* summary
* changed files
* test results
* risks

不要把完整推理、完整 patch、完整中間過程再送回 PM。
因為 PM 不需要知道每個中間步驟。

---

### 7. 一個命令只做一個 bounded task

不要一次下這種需求：

* 改架構
* 補測試
* 修三個 bug
* 順便重構
* 再寫文件

成本最低的做法是每個 handoff 只處理一個明確任務，例如：

* 修 login bug
* 補 login unit test
* 加一個 auth route

這樣工單短、檔案少、驗證也便宜。

---

### 8. 固定輸入與輸出格式

永遠固定：

* 輸入：`task.yaml`
* 輸出：`result.md`

一旦格式漂移，token 很快就會浪費在重新解讀與補齊格式。

---

## 建議的極簡運作規則

```text
1. PM 只產生 task.yaml
2. OMC 只讀 task.yaml
3. Context7 只在需要 API 或框架細節時才開
4. filesystem 只讀必要檔案
5. 第一輪最多讀 5 個檔案
6. 第一輪只跑最小必要測試
7. 結果只輸出摘要
8. review 只在高風險或收斂點啟動
```

## 一句話定義

Antigravity 是需求編譯器，OMC 是帶工具的執行器；兩者之間只交換最小工單，不交換整段上下文。
