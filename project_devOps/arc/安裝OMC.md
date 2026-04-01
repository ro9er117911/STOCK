**TL;DR**：在 Antigravity 裡最穩的做法不是把這套東西硬塞進 Antigravity 原生 agent 面板，而是把 Antigravity 當 IDE 與 PM 對話前台，實際執行面放在 Antigravity 的整合終端機內跑 Claude Code CLI，再在 Claude Code 裡同時安裝 `oh-my-claudecode`、`oh-my-codex` 與 `codex-plugin-cc`。這樣可同時保留 Antigravity 的 Claude Opus 4.6 / MCP 能力、Claude Code 的 team workflow，以及 Codex CLI 的平行執行與 review 工作流。Antigravity 官方文件可見 Claude Opus 4.6 / Sonnet 4.6 與 MCP；Claude Code 官方 IDE 文件則重點支援 VS Code/Cursor，且明確說 CLI 可在 IDE 整合終端機中使用。([Google Antigravity][1])

> Archived snapshot.
> Active workflow lives in `rules/orc-architecture.md`, `.agent/skills/pm/SKILL.md`, `.ai/README.md`, `.ai/scripts/bridge.sh`, and `docs/architecture/implementation_plan.md`.
> Do not treat this file as source of truth.

**3 個關鍵檢核**

1. `claude --version`、`codex --version`、`omx --version`、`tmux -V` 都能正常輸出。`oh-my-codex` 需要 Node.js 20+，`codex-plugin-cc` 也會透過本機 Codex CLI 運作。([GitHub][2])
2. `~/.claude/settings.json` 已啟用 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`，否則 OMC 的 Team 模式只會警告或退回非 Team 模式。([GitHub][3])
3. `omx doctor` 通過，且專案根目錄的 `.codex/` overlay 與 `.omx/` state 被視為本機 runtime state，不進 repo。([GitHub][9])
4. 專案根目錄至少存在 `init.sh`、`claude-progress.txt`、`feature_list.json` 三類交接 artifact，否則不符合 Anthropic 的 long-running harness 最小契約。([Anthropic][4])

# Antigravity + Claude Code + OMC + Codex Plugin 安裝文件

## 0. 系統定位

本文件採用以下分層：

* **Antigravity 原生對話面板**：做 PM 討論、需求釐清、規格拆解。Antigravity 官方文件列出可用 `Claude Opus 4.6 (thinking)`、`Claude Sonnet 4.6 (thinking)`，並支援 MCP。([Google Antigravity][1])
* **Antigravity 整合終端機內的 Claude Code CLI**：做實際開發、插件安裝、team orchestration。Claude Code 官方文件明確說 CLI 可在 IDE 整合終端機中執行，且 extension/CLI 共用 `~/.claude/settings.json`。([Claude][5])
* **oh-my-claudecode**：負責 Claude Code 內部多 agent 編排，標準 Team 流程為 `team-plan → team-prd → team-exec → team-verify → team-fix`。([GitHub][3])
* **oh-my-codex**：負責 Codex CLI 的工作流層，常用在 read-heavy、parallelizable、長輸出整理與持久化 state；project scope 會落 `.codex/` overlay 與 `.omx/` state。([GitHub][9])
* **codex-plugin-cc**：負責獨立 code review、adversarial review、rescue。它透過本機 Codex CLI 與 app server 工作，不是另一個遠端黑盒。([GitHub][2])

待補：我沒有查到「Antigravity 直接安裝 Claude Code 擴充」的官方專頁，因此以下文件以 **CLI 路徑** 為主，不假設 Antigravity 原生支援 Claude Code extension。這是目前最穩定、最少相容性風險的方案。([Claude][5])

## 1. 先決條件

以下為最小依賴：

* Antigravity IDE 已安裝。([Google Antigravity][6])
* Claude Code 已安裝並可登入。官方安裝方式包含 macOS/Linux 的 `curl ... install.sh | bash`，Windows 則有 PowerShell/CMD 與 WinGet。([Claude API Docs][7])
* Node.js 20+，可同時滿足 `oh-my-codex` 與 `codex-plugin-cc`。([GitHub][9])
* tmux，因 OMC 的 `omc-teams` 會在 tmux pane 裡啟動真實 CLI worker；tmux 可用 Homebrew 安裝。([GitHub][3])
* ChatGPT 帳號或 OpenAI API key，因 `codex-plugin-cc` 透過本機 Codex CLI 工作，並需要登入。([GitHub][2])
* `oh-my-codex` 已安裝，並能通過 `omx doctor`。([GitHub][9])

## 2. macOS 安裝命令

以下命令以 macOS 為主，直接在 Antigravity 的整合終端機執行。

```bash
# 0) Homebrew（若尚未安裝）
command -v brew >/dev/null 2>&1 || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 1) 基礎工具
brew install git tmux node jq

# 2) Claude Code
curl -fsSL https://claude.ai/install.sh | bash

# 3) Codex CLI
npm install -g @openai/codex

# 4) oh-my-codex
npm install -g oh-my-codex

# 5) 驗證版本
git --version
node --version
npm --version
tmux -V
claude --version
codex --version
omx --version
omx doctor
```

其中 `tmux` 可用 Homebrew 安裝；Claude Code 官方 quickstart 使用原生安裝腳本；Codex plugin 則要求本機有可用的 Codex CLI；OMX 則把 Codex CLI 包成更省 token 的工作流層。([GitHub][9])

## 3. 登入與第一次啟動

```bash
# Claude Code 首次登入
claude
# 依畫面完成登入；之後也可在 REPL 內使用 /login

# Codex CLI 首次登入
codex login
```

Claude Code 官方文件說第一次執行 `claude` 會要求登入；`codex-plugin-cc` README 則明說若 Codex 尚未登入，可用 `!codex login`，本質上就是登入本機 Codex CLI。([Claude API Docs][7])

## 4. 啟用 Claude Code Team 模式

OMC 的 Team 模式要依賴 Claude Code 原生 teams 開關。官方 README 要求把 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 放到 `~/.claude/settings.json`。([GitHub][3])

安全更新寫法如下，不會直接覆蓋你現有設定：

```bash
python3 - <<'PY'
import json
from pathlib import Path

p = Path.home() / ".claude" / "settings.json"
p.parent.mkdir(parents=True, exist_ok=True)

data = {}
if p.exists():
    try:
        data = json.loads(p.read_text())
    except Exception:
        data = {}

data.setdefault("env", {})
data["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"

p.write_text(json.dumps(data, ensure_ascii=False, indent=2))
print(f"updated: {p}")
PY
```

更新後可檢查：

```bash
cat ~/.claude/settings.json
```

## 5. 在 Claude Code 內安裝 OMC 與 Codex Plugin

進入任一 repo 目錄後，啟動 Claude Code：

```bash
cd /path/to/your/repo
claude
```

進入 Claude Code 後，依序執行：

```text
/plugin marketplace add https://github.com/Yeachan-Heo/oh-my-claudecode
/plugin install oh-my-claudecode

/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex

/reload-plugins
/omc-setup
/codex:setup
```

這些命令都來自各自官方 README。OMC 的 quickstart 是 marketplace add → install → `/omc-setup`；Codex plugin 的 quickstart 是 marketplace add → install → `/reload-plugins` → `/codex:setup`。([GitHub][3])

補充：

* `codex-plugin-cc` 安裝完成後，應會看到 `/codex:review`、`/codex:adversarial-review`、`/codex:rescue` 等指令，以及 `codex:codex-rescue` subagent。([GitHub][2])
* OMC v4.4.0+ 已移除舊的 Codex/Gemini MCP provider，改成用 `/omc-teams` 在 tmux 裡啟動真實 CLI worker。若你要用 OMC 的外部 worker，必須有 active tmux session，且本機已裝好對應 CLI。([GitHub][3])

## 6. 建立 Anthropic harness 最小骨架

Anthropic 的 long-running harness 核心不是「多加幾個 agent」，而是 **可交接的 artifact 契約**。官方文章明確列出 initializer session 應建立 `init.sh`、`claude-progress.txt`、初始 git commit；後續 session 應先讀 progress / git log / feature list，再做增量工作，並以 clean state 收尾。官方也建議 feature list 用 JSON，並只改 `passes` 欄位，避免 agent 任意改測試說明。([Anthropic][4])

在 repo 根目錄執行：

```bash
mkdir -p .harness

cat > .harness/init.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

echo "[pwd]"
pwd

echo "[git status]"
git status --short || true

echo "[git log]"
git log --oneline -10 || true

if [ -f package.json ]; then
  echo "[npm install]"
  npm install || true
fi

if [ -f package.json ] && jq -e '.scripts.test' package.json >/dev/null 2>&1; then
  echo "[npm test]"
  npm test || true
fi

echo "[done]"
SH
chmod +x .harness/init.sh

cat > claude-progress.txt <<'TXT'
# Claude Progress

## Current state
- branch: 待補
- last verified state: 待補
- current owner/session: 待補

## What was done last
- 待補

## What is broken / risky
- 待補

## Next highest-priority task
- 待補

## Verification notes
- 待補
TXT

cat > feature_list.json <<'JSON'
[
  {
    "category": "functional",
    "description": "待補：第一個端到端功能",
    "steps": [
      "待補：步驟 1",
      "待補：步驟 2",
      "待補：步驟 3"
    ],
    "passes": false
  },
  {
    "category": "non_functional",
    "description": "待補：基本 lint/test/build 可通過",
    "steps": [
      "執行 lint",
      "執行 test",
      "執行 build"
    ],
    "passes": false
  }
]
JSON

cat > CLAUDE.md <<'MD'
# Working Contract

## Initializer session
1. Ensure .harness/init.sh, claude-progress.txt, feature_list.json exist.
2. Expand the user spec into concrete end-to-end features.
3. Make an initial git commit if repo has no baseline commit.

## Every later session
1. Run pwd.
2. Read claude-progress.txt and feature_list.json.
3. Read git log --oneline -10.
4. Run ./.harness/init.sh.
5. Pick exactly one highest-priority feature where passes=false.
6. Implement incrementally.
7. Self-verify end-to-end before marking passes=true.
8. Append progress notes to claude-progress.txt.
9. Commit with a descriptive message.
10. Never declare the project complete while any passes=false remains.
MD
```

這份骨架是依 Anthropic 提出的 initializer / coding agent 契約轉成可直接落地的 repo scaffold。([Anthropic][4])

## 7. 建議的角色分工

這一段是架構決策，不是工具硬性要求。

### A. Antigravity 原生面板：PM/規格層

使用 `Claude Opus 4.6 (thinking)` 做需求訪談、風險拆解、PRD 草案。Antigravity 官方模型頁可見 Opus / Sonnet 4.6；MCP 也可在此層接外部資料。([Google Antigravity][1])

### B. Claude Code + OMC：執行層

讓 OMC 的 Team 模式負責規劃與實作，優先用 Claude team，不急著讓 OMC 再開 tmux 的 Codex worker，避免 reviewer lane 重複。OMC 官方 README 已把 Team 定成標準模式。([GitHub][3])

### C. codex-plugin-cc：獨立驗證層

用 `/codex:review`、`/codex:adversarial-review`、`/codex:rescue` 做第二意見，保持 reviewer 與 implementer 分離。這正是該 plugin 的官方設計目標。([GitHub][2])

## 8. 第一次實跑流程

### 8.1 在 Antigravity 的 PM 對話面板先產出規格

把需求整理成一份 PRD 或 task brief，再貼到 repo 的 `docs/brief.md`。

### 8.2 在 Antigravity 的整合終端機開 Claude Code

```bash
cd /path/to/your/repo
claude
```

### 8.3 第一次初始化 prompt

在 Claude Code 中貼這段：

```text
請作為 initializer agent 執行：
1. 讀取 CLAUDE.md。
2. 檢查 .harness/init.sh、claude-progress.txt、feature_list.json 是否存在，不存在就建立。
3. 依 docs/brief.md 把需求擴展成端到端 feature_list.json。
4. 執行 ./.harness/init.sh。
5. 驗證目前專案是否可正常啟動/測試。
6. 只整理基礎環境，不要一次實作太多功能。
7. 最後更新 claude-progress.txt 並建立一個描述清楚的 git commit。
```

這段 prompt 的設計直接對應 Anthropic 的 initializer agent 做法：先建環境、先留 artifact、先做 baseline 驗證，而不是一開始就 one-shot 實作。([Anthropic][4])

### 8.4 後續開發 prompt

```text
請作為 coding agent 執行：
1. 先讀 claude-progress.txt、feature_list.json、git log --oneline -10。
2. 執行 ./.harness/init.sh。
3. 挑選一個 passes=false 的最高優先 feature。
4. 只做這一個 feature，完成後自我驗證。
5. 驗證通過才把該 feature 的 passes 改為 true。
6. 更新 claude-progress.txt。
7. 建立一個清楚的 git commit。
```

### 8.5 OMC 命令

需求還模糊時：

```text
/deep-interview "我要做一個待補專案"
```

已明確要開始做時：

```text
/team 3:executor "根據 docs/brief.md 與 feature_list.json，實作下一個最高優先功能"
```

OMC README 的 quickstart、`/deep-interview`、`/team` 與 Team pipeline 都對應這種用法。([GitHub][3])

### 8.6 Codex 驗證命令

```text
/codex:review --base main --background
/codex:status
/codex:result
```

要做壓力測試式審查時：

```text
/codex:adversarial-review --base main
```

要交給 Codex 調查 bug 或做 rescue 時：

```text
/codex:rescue
```

這些都是官方 README 直接列出的主命令。([GitHub][2])

## 9. 建議的日常操作紀律

這一段屬於架構建議，但完全貼合 Anthropic 的方法論。

1. **每次 session 開始先驗證，不先寫碼。** 官方文章明講要先讀 progress / git log / feature list，再跑 `init.sh` 與基本端到端驗證。([Anthropic][4])
2. **一次只做一個 feature。** 這是避免 one-shot 與半成品 context 崩壞的核心做法。([Anthropic][4])
3. **只有驗證通過才把 `passes=false` 改成 `true`。** Anthropic 特別強調 feature 不可提早標記完成。([Anthropic][4])
4. **每輪都 commit。** 官方文章指出 descriptive commits + progress file 能讓 agent 回到 working state。([Anthropic][4])
5. **Claude 負責寫碼，Codex 負責反證。** 這是你這套架構最有價值的分工，不要讓同一條 lane 自評自過。這一點是基於工具能力設計的架構建議。([GitHub][2])

## 10. 常見故障排除

### 10.1 `/plugin install` 找不到 marketplace

先重開 Claude Code，再執行：

```text
/plugin marketplace add https://github.com/Yeachan-Heo/oh-my-claudecode
/plugin marketplace add openai/codex-plugin-cc
/reload-plugins
```

### 10.2 OMC Team 沒啟動

檢查：

```bash
cat ~/.claude/settings.json | jq '.env'
```

確認包含：

```json
{
  "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
}
```

若沒開啟，OMC 官方說會警告並在可能時回退到非 Team 執行模式。([GitHub][3])

### 10.3 `/codex:setup` 失敗

依官方 README，逐項檢查：

```bash
node --version
codex --version
codex login
```

`codex-plugin-cc` 的運作依賴本機 Codex CLI 與本機登入狀態。([GitHub][2])

### 10.4 `/omc-teams` 失敗

檢查：

```bash
tmux -V
tmux new -s omc-test
```

OMC README 明寫 `omc-teams` 需要 active tmux session，且需要已裝 `codex` / `gemini` CLI。([GitHub][3])

### 10.5 更新 OMC 後異常

官方建議：

```text
/plugin marketplace update omc
/omc-setup
/omc-doctor
```

([GitHub][3])

## 11. 最小驗收標準

```bash
claude --version
codex --version
tmux -V
test -f .harness/init.sh && echo OK:init
test -f claude-progress.txt && echo OK:progress
test -f feature_list.json && echo OK:features
```

進入 Claude Code 後：

```text
/omc-setup
/codex:setup
/team 3:executor "read the repo and propose the next single feature"
/codex:review --background
/codex:status
/codex:result
```

若上述都可執行，代表：

* Antigravity 作為 IDE 可正常承載這套工作流；
* Claude Code plugin 層已就緒；
* OMC Team 層可用；
* Codex 獨立驗證層可用；
* Anthropic harness 的最小 artifact 契約已落地。([GitHub][2])

**一句話總結**：這套安裝不是把所有模型塞進同一個面板，而是把 Antigravity 當前台、Claude Code 當執行器、OMC 當協作排程器、Codex 當獨立審查器，再用 `init.sh + claude-progress.txt + feature_list.json` 把長時代理變成可交接、可驗證、可恢復的工程系統。([Google Antigravity][1])

[1]: https://antigravity.google/docs/models?utm_source=chatgpt.com "Reasoning Model"
[2]: https://github.com/openai/codex-plugin-cc "GitHub - openai/codex-plugin-cc: Use Codex from Claude Code to review code or delegate tasks. · GitHub"
[3]: https://github.com/Yeachan-Heo/oh-my-claudecode/blob/main/README.zh.md "oh-my-claudecode/README.zh.md at main · Yeachan-Heo/oh-my-claudecode · GitHub"
[4]: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents "Effective harnesses for long-running agents \ Anthropic"
[5]: https://code.claude.com/docs/en/vs-code "Use Claude Code in VS Code - Claude Code Docs"
[6]: https://antigravity.google/download?utm_source=chatgpt.com "Google Antigravity Download"
[7]: https://docs.anthropic.com/en/docs/claude-code/quickstart "Quickstart - Claude Code Docs"
[8]: https://github.com/tmux/tmux/wiki/Installing?utm_source=chatgpt.com "Installing · tmux/tmux Wiki"
[9]: https://github.com/Yeachan-Heo/oh-my-codex "GitHub - Yeachan-Heo/oh-my-codex: OmX - Oh My codeX"
