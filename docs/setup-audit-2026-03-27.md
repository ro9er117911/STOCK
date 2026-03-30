# Setup Audit Report

日期：2026-03-27

## 範圍

本次實際閱讀並納入審查的文字型設定/指令檔共 51 份，包含：

- 工作區主設定：`CLAUDE.md`
- 工作區本地 skills：`.agent/skills/*`、`.antigravity/skills/*`
- 全域 Codex system skills：`/Users/ro9air/.codex/skills/.system/*`
- 全域 prompt library：`/Users/ro9air/.codex/prompts/*.md`
- context / constitution：`/Users/ro9air/.specify/context/*`、`/Users/ro9air/.specify/memory/constitution.md`
- 其他核心規則檔：`/Users/ro9air/.codex/rules/default.rules`
- 補充確認：`/Users/ro9air/Library/Application Support/Claude/claude_desktop_config.json`

備註：

- `claude_desktop_config.json` 只有 MCP server 設定，幾乎不含自然語言規則。
- `README.md`、`PLAN.md` 已掃描，但我將它們視為專案文件，不列入「常駐指令」主表。

## 判斷原則

對每個規則群，我都用同一套五題審查：

1. 這是不是模型本來就傾向做到的預設行為
2. 是否和其他設定衝突
3. 是否和其他地方重複
4. 是否像是為了修補單次糟糕輸出而加上的補丁
5. 是否模糊到每次解讀都可能不同

表格欄位說明：

- `預設`：`是` / `否` / `部分`
- `衝突`、`重複`、`事故補丁`、`模糊`：`是` / `否` / `部分`
- `建議`：`保留` / `精簡` / `對齊` / `刪除` / `條件保留`

## 規則群審查

| ID | 規則群 | 主要來源 | 預設 | 衝突 | 重複 | 事故補丁 | 模糊 | 建議 |
|---|---|---|---|---|---|---|---|---|
| R01 | 全域允許清單：大量專案特定 `prefix_rule` | `.codex/rules/default.rules` | 否 | 是 | 否 | 是 | 否 | 刪除 |
| R02 | Claude Desktop 只啟用 `pencil` MCP | `claude_desktop_config.json` | 否 | 否 | 否 | 否 | 否 | 保留 |
| R03 | 舊專案 session resume 指南 | `.specify/context/session-status.md` | 否 | 是 | 否 | 是 | 否 | 刪除 |
| R04 | 空白 constitution placeholder | `.specify/memory/constitution.md` | 否 | 否 | 部分 | 否 | 是 | 條件保留 |
| R05 | STOCK 根設定的適用/不適用邊界 | 原 `CLAUDE.md` | 否 | 部分 | 是 | 否 | 部分 | 精簡 |
| R06 | 投資研究五大核心原則 | `CLAUDE.md`、兩套 stock skill、`research_methodology.md`、`SOUL.md` | 否 | 否 | 是 | 否 | 否 | 保留 |
| R07 | 完整 9 步研究流程內嵌在 `CLAUDE.md` | 原 `CLAUDE.md` | 否 | 部分 | 是 | 否 | 否 | 刪除 |
| R08 | 完整研究模板內嵌在 `CLAUDE.md` | 原 `CLAUDE.md` | 否 | 是 | 是 | 否 | 否 | 刪除 |
| R09 | 完整 QA checklist 內嵌在 `CLAUDE.md` | 原 `CLAUDE.md` | 否 | 否 | 是 | 否 | 否 | 刪除 |
| R10 | `stock-research-operator` 的觸發邊界 | `.agent/.../SKILL.md`、`.antigravity/.../SKILL.md` | 否 | 部分 | 是 | 否 | 低 | 保留 |
| R11 | `current.md` + `state.json` 為雙輸出契約 | `.agent/.../SKILL.md`、`README.md` | 否 | 部分 | 部分 | 否 | 否 | 保留 |
| R12 | Automation mirror 欄位必填 | `.agent/.../template.md` | 否 | 是 | 否 | 否 | 否 | 保留為主模板 |
| R13 | 研究交付前 QA gate | `.agent/.../checklist.md`、`.antigravity/.../quality_checklist.md` | 否 | 否 | 是 | 否 | 否 | 保留單一主版本 |
| R14 | `ALWAYS output exact structure` 且模板不同 | `.antigravity/.../SKILL.md` + `assets/template.md` | 否 | 是 | 是 | 否 | 否 | 對齊 |
| R15 | SOUL 哲學：Expectation Gap / Regime Drift | `.antigravity/.../references/SOUL.md` | 否 | 否 | 部分 | 否 | 部分 | 保留 |
| R16 | 噪音過濾與事件分流方法論 | `.antigravity/.../research_methodology.md` | 否 | 否 | 是 | 否 | 否 | 保留 |
| R17 | `deep-market-research` 四階段 workflow | `.agent/workflows/deep-market-research.md` | 否 | 否 | 部分 | 部分 | 否 | 條件保留 |
| R18 | 固定 watchlist 為 `PLTR/MSFT/MAR` | 兩套 stock skill | 否 | 部分 | 部分 | 部分 | 否 | 保留但降為預設值 |
| R19 | `description` 是主要 trigger；frontmatter 只允許 `name`、`description` | `.codex/skills/.system/skill-creator/SKILL.md` | 否 | 是 | 部分 | 否 | 否 | 保留，但需處理衝突 |
| R20 | Progressive disclosure / SKILL 要瘦身 | system `skill-creator`、local `skill-creator-advanced` | 否 | 否 | 是 | 否 | 否 | 保留 |
| R21 | 一個 skill 只做一件主要工作 | local `skill-creator-advanced` | 否 | 否 | 是 | 否 | 否 | 保留 |
| R22 | workflow 每步都要有 I/O / validation / output contract | local `skill-creator-advanced` | 否 | 否 | 是 | 否 | 否 | 保留 |
| R23 | scripts / baseline / ROI / regression gates | local `skill-creator-advanced` refs | 否 | 否 | 是 | 否 | 否 | 保留 |
| R24 | `references/quality_checklist.md` 同時放「已填 audit」和「空白模板」 | `.antigravity/skills/skill-creator-advanced/references/quality_checklist.md` | 否 | 是 | 是 | 是 | 部分 | 精簡 |
| R25 | Speckit 核心 prompt：`specify/clarify/plan/tasks/checklist/analyze` | `.codex/prompts/*` | 否 | 否 | 部分 | 否 | 低 | 條件保留 |
| R26 | Speckit Bank Profile prompt 家族：`meta/business/process/infosec/law/audit/nfr/review` | `.codex/prompts/*` | 否 | 部分 | 是 | 部分 | 部分 | 條件保留 |

## 我建議刪除的條目

下列清單是「建議刪除或移出常駐層」；不是每一條都已自動執行。

1. `CLAUDE.md` 內嵌的 9 步流程
   刪除理由：和兩套 `stock-research-operator` skill 重複，且會讓三個地方的 workflow 漂移。
2. `CLAUDE.md` 內嵌的完整研究模板
   刪除理由：模板本來就該住在 `template.md`，常駐層重複只會增加維護成本。
3. `CLAUDE.md` 內嵌的完整 QA checklist
   刪除理由：`checklist.md` 已是專責文件，重貼一份只會造成雙重維護。
4. `CLAUDE.md` 內嵌的 iteration/common errors/success criteria 長段
   刪除理由：和 `.agent/.../SKILL.md` 已高度重複，常駐層沒有新增資訊。
5. `/Users/ro9air/.codex/rules/default.rules` 中與 STOCK 無關的專案專用 `prefix_rule`
   刪除理由：明顯是歷史操作白名單，既不通用，也會和其他專案安全邊界混在一起。
6. `/Users/ro9air/.specify/context/session-status.md`
   刪除理由：內容指向另一個 repo/branch，若被當作當前 context 讀入會直接污染判斷。
7. `.antigravity/skills/skill-creator-advanced/references/quality_checklist.md` 的「已填 audit header」
   刪除理由：和同檔底部的空白模板混在一起，讓文件同時像紀錄檔又像規格模板。
8. Speckit Bank Profile prompt 家族（若此 repo 已不再跑 Speckit）
   刪除理由：七成以上是重複骨架與檢查表，若已停用，保留只會增加搜尋噪音。

## 各檔案之間的衝突

1. `skill-creator` system skill 要求 YAML frontmatter 只含 `name`、`description`，但本地 `skill-creator-advanced` 與本地 stock skills 都用了 `version`、`metadata`、`homepage`、`license`。
2. `.agent/skills/stock-research-operator/template.md` 要求 `thesis_id` / `assumption_id` / `action_rule_id` 等 automation mirror 欄位，`.antigravity/skills/stock-research-operator/assets/template.md` 沒有這些欄位，兩個 output contract 不一致。
3. `.antigravity/skills/stock-research-operator/SKILL.md` 要求「永遠使用 `assets/template.md` 的 exact structure」，但 `.agent/skills/stock-research-operator/SKILL.md` 同時又要求 machine-readable state 與更完整欄位，若兩者同時載入會拉扯輸出格式。
4. 原 `CLAUDE.md` 內嵌完整 workflow/template/checklist，而兩套 stock skills 也各自定義；三處一旦不同步，就會出現同一任務有三份規格。
5. `.specify/context/session-status.md` 指向 `001-spec-bot-sdd-integration` 分支與 speckit 工作流，和目前 `STOCK` repo 的上下文直接衝突。
6. `.codex/rules/default.rules` 允許多個與本 repo 無關的 `git push` / `rm -f` 前綴，和「設定應反映當前工作」的原則衝突。

## Step 2：本次實際採取的刪除

我沒有全盤照單全收，只做了我有把握、不會誤傷其他 runtime 的一批刪除：

- 已把根目錄 `CLAUDE.md` 改成薄入口檔。
- 保留真正改變行為的核心原則與事件分流規則。
- 刪除所有重複模板、重複 checklist、重複 workflow 長文。
- 把細節改成參照本地 skill / template / checklist / methodology。

我沒有直接刪除以下內容，因為風險太高：

- 兩套 `stock-research-operator` skill 本體
- 全域 `.codex/prompts` 整包
- 全域 `.codex/rules/default.rules`
- `.specify/*`

理由很簡單：這些檔案跨 repo / 跨 runtime 共用的可能性太高，現在直接刪，風險大於收益。

## Step 2：三種常見任務的回歸檢查

這裡做的是「靜態回歸檢查」，不是另一個模型的即時 A/B generation。原因是同一回合內無法熱重載新的常駐設定再跑公平對照。

| 任務 | 檢查點 | 結果 |
|---|---|---|
| 新建個股深度研究 | `CLAUDE.md` 仍保留適用邊界、五大原則，並直接指向 `SKILL.md`、`template.md`、`checklist.md` | 通過 |
| 財報/事件後 thesis update | `CLAUDE.md` 保留 5 步事件分流規則，且明指 `research_methodology.md` 與 `current.md/state.json` 契約 | 通過 |
| 同業比較 / 部位調整 | `CLAUDE.md` 保留 peer/action/sizing 邊界，並保留 `PLTR/MSFT/MAR` 僅作預設 peers | 通過 |

判讀：

- 常見任務沒有失去核心能力。
- 刪掉的多半是「重複描述」，不是「獨有能力」。
- 目前沒有看到需要把刪掉的 `CLAUDE.md` 內容加回來的項目。

## Step 3：每週排程

我沒有直接替你在「Claude Cowork」裡建立排程，因為本機找不到可安全編輯的 Cowork 排程設定檔或 CLI，不能假裝已完成外部產品操作。

若你要手動貼到 Claude Cowork，下面這段就是可直接使用的任務內容：

```text
建立一個名為「setup-audit」的每週排程任務，於每週一早上 9 點執行。

任務內容：完整讀取我的所有設定（核心md、所有 skills、所有 context 檔案，以及一切相關檔案），
接著對每一條規則套用以下 5 個篩選條件進行審查：

1. 這是你不需要被告知就會預設執行的行為嗎？
2. 這條規則與我設定中其他地方的規則有衝突或矛盾嗎？
3. 這條規則與另一條規則或另一個檔案中的內容重複了嗎？
4. 這條規則看起來像是為了修正某一次特定的糟糕輸出而加入的，而不是為了整體改善輸出品質？
5. 這條規則模糊到每次你的解讀都可能不同嗎？

最後請提供：
- 建議刪除的條目清單，每條附上一行理由
- 各檔案之間發現的衝突清單
- 規則總數中通過審查與被標記的數量摘要

不要修改任何檔案，僅輸出報告。
```

## 精簡版 CLAUDE.md

精簡版已直接套用到 repo root 的 `CLAUDE.md`。設計原則是：

- 根檔只保留「何時用、核心原則、必要輸出、事件分流」。
- 詳細流程交給 `.agent/skills/stock-research-operator/SKILL.md`。
- 模板交給 `.agent/skills/stock-research-operator/template.md`。
- QA 交給 `.agent/skills/stock-research-operator/checklist.md`。
- 投資哲學與噪音過濾交給 `.antigravity/.../SOUL.md`、`research_methodology.md`。

這樣做的好處是：

- 常駐上下文更短
- 只剩一層入口，不再有三份長文互相打架
- 真正會改變輸出的規則仍然完整保留
