# 編排工作流 (Orchestration Workflow)

本文件描述了 **命令 → 代理 (具備技能) → 技能 (Command → Agent with skill → Skill)** 的編排工作流，並透過一個天氣數據獲取與 SVG 渲染系統進行展示。


## 系統概覽

天氣系統在單一編排工作流中展示了兩種截然不同的技能模式：
- **代理技能 (Agent Skills)** (預先載入)：`weather-fetcher` 在啟動時作為領域知識注入到 `weather-agent` 中。
- **技能 (Skills)** (獨立)：`weather-svg-creator` 由命令透過 Skill 工具直接調用。

這展示了 **命令 → 代理 → 技能 (Command → Agent → Skill)** 的架構模式，其中：
- 命令負責編排工作流並處理使用者交互。
- 代理使用其預載技能獲取數據。
- 技能獨立建立視覺產出。

## 組件摘要

| 組件 | 角色 | 範例 |
|-----------|------|---------|
| **命令 (Command)** | 入口點、使用者交互 | [`/weather-orchestrator`](../.claude/commands/weather-orchestrator.md) |
| **代理 (Agent)** | 使用預載技能（代理技能）獲取數據 | [`weather-agent`](../.claude/agents/weather-agent.md) 與 [`weather-fetcher`](../.claude/skills/weather-fetcher/SKILL.md) |
| **技能 (Skill)** | 獨立建立產出（技能） | [`weather-svg-creator`](../.claude/skills/weather-svg-creator/SKILL.md) |

## 流程圖

```
╔══════════════════════════════════════════════════════════════════╗
║                編排工作流 (ORCHESTRATION WORKFLOW)               ║
║           命令 (Command)  →  代理 (Agent)  →  技能 (Skill)       ║
╚══════════════════════════════════════════════════════════════════╝

                          ┌───────────────────┐
                          │    使用者交互     │
                          └─────────┬─────────┘
                                    │
                                    ▼
          ┌─────────────────────────────────────────────────────┐
          │ /weather-orchestrator — 命令 (入口點)               │
          └─────────────────────────┬───────────────────────────┘
                                    │
                                  步驟 1
                                    │
                                    ▼
                       ┌────────────────────────┐
                       │  AskUser — 攝氏或華氏?  │
                       └────────────┬───────────┘
                                    │
                           步驟 2 — Agent 工具
                                    │
                                    ▼
          ┌─────────────────────────────────────────────────────┐
          │ weather-agent — 代理 ● 技能: weather-fetcher        │
          └─────────────────────────┬───────────────────────────┘
                                    │
                           傳回: 溫度 + 單位
                                    │
                           步驟 3 — Skill 工具
                                    │
                                    ▼
          ┌─────────────────────────────────────────────────────┐
          │ weather-svg-creator — 技能 ● SVG 卡片 + 產出        │
          └─────────────────────────┬───────────────────────────┘
                                    │
                           ┌────────┴────────┐
                           │                 │
                           ▼                 ▼
                    ┌────────────┐    ┌────────────┐
                    │weather.svg │    │ output.md  │
                    └────────────┘    └────────────┘
```

## 組件細節

### 1. 命令 (Command)

#### `/weather-orchestrator` (命令)
- **位置**: `.claude/commands/weather-orchestrator.md`
- **目的**: 入口點 —— 編排工作流並處理使用者交互。
- **行動**:
  1. 詢問使用者偏好的溫度單位（攝氏/華氏）。
  2. 透過 Agent 工具調用 weather-agent。
  3. 透過 Skill 工具調用 weather-svg-creator。
- **模型**: haiku

### 2. 具備預載技能的代理 (代理技能)

#### `weather-agent` (代理)
- **位置**: `.claude/agents/weather-agent.md`
- **目的**: 使用其預載技能獲取天氣數據。
- **技能**: `weather-fetcher` (作為領域知識預先載入)。
- **可用工具**: WebFetch, Read
- **模型**: sonnet
- **代表色**: 綠色 (green)
- **記憶**: 專案 (project)

代理在啟動時已將 `weather-fetcher` 預載至其上下文。它遵循該技能的指示獲取溫度，並將數值傳回給命令。

### 3. 技能 (Skill)

#### `weather-svg-creator` (技能)
- **位置**: `.claude/skills/weather-svg-creator/SKILL.md`
- **目的**: 建立視覺化的 SVG 天氣卡片並寫入產出文件。
- **調用**: 從命令透過 Skill 工具調用（不預載至任一代理）。
- **產出**:
  - `orchestration-workflow/weather.svg` — SVG 天氣卡片。
  - `orchestration-workflow/output.md` — 天氣摘要。

### 4. 預載技能 (Preloaded Skill)

#### `weather-fetcher` (技能)
- **位置**: `.claude/skills/weather-fetcher/SKILL.md`
- **目的**: 指示如何獲取即時溫度數據。
- **數據源**: Open-Meteo API (杜拜, 阿聯酋)。
- **產出**: 溫度值與單位（攝氏或華氏）。
- **備註**: 這是一個代理技能 —— 預載至 `weather-agent` 中，而非直接調用。

## 執行流程

1. **使用者發起**: 使用者執行 `/weather-orchestrator` 命令。
2. **使用者提示**: 命令詢問使用者偏好的溫度單位（攝氏/華氏）。
3. **調用代理**: 命令透過 Agent 工具調用 `weather-agent`。
4. **技能執行** (於代理上下文中)：
   - 代理遵循 `weather-fetcher` 技能指示，從 Open-Meteo 獲取溫度。
   - 代理將溫度值與單位傳回給命令。
5. **SVG 建立**: 命令透過 Skill 工具調用 `weather-svg-creator`。
   - 技能在 `orchestration-workflow/weather.svg` 建立 SVG 天氣卡片。
   - 技能將摘要寫入 `orchestration-workflow/output.md`。
6. **結果顯示**: 向使用者顯示摘要，包含：
   - 請求的溫度單位。
   - 獲取到的溫度。
   - SVG 卡片位置。
   - 產出文件位置。

## 執行範例

```
輸入: /weather-orchestrator
├─ 步驟 1: 詢問: 攝氏或華氏?
│  └─ 使用者: 攝氏
├─ 步驟 2: Agent 工具 → weather-agent
│  ├─ 預載技能:
│  │  └─ weather-fetcher (領域知識)
│  ├─ 從 Open-Meteo 獲取 → 26°C
│  └─ 傳回: temperature=26, unit=Celsius
├─ 步驟 3: Skill 工具 → /weather-svg-creator
│  ├─ 建立: orchestration-workflow/weather.svg
│  └─ 寫入: orchestration-workflow/output.md
└─ 產出:
   ├─ 單位: 攝氏
   ├─ 溫度: 26°C
   ├─ SVG: orchestration-workflow/weather.svg
   └─ 摘要: orchestration-workflow/output.md
```

## 關鍵設計原則

1. **兩種技能模式**: 同時展示了代理技能 (預載) 與技能 (直接調用)。
2. **命令作為編排者**: 命令負責處理使用者交互並協調工作流。
3. **代理負責數據獲取**: 代理使用其預載技能獲取數據並傳回。
4. **技能負責產出**: SVG 建立器獨立執行，從命令上下文中接收數據。
5. **乾淨的職責分離**: 獲取 (代理) → 渲染 (技能) —— 每個組件各司其職。

## 架構模式

### 代理技能 (預載)

```yaml
# 在代理定義中 (.claude/agents/weather-agent.md)
---
name: weather-agent
skills:
  - weather-fetcher    # 啟動時預載至代理上下文
---
```

- **技能預先載入**: 技能的完整內容在啟動時注入到代理的上下文中。
- **代理使用技能知識**: 代理遵循預載技能的指示。
- **無動態調用**: 技能是參考資料，而非單獨調用。

### 技能 (直接調用)

```yaml
# 在技能定義中 (.claude/skills/weather-svg-creator/SKILL.md)
---
name: weather-svg-creator
description: 建立 SVG 天氣卡片...
---
```

- **透過 Skill 工具調用**: 命令呼叫 `Skill(skill: "weather-svg-creator")`。
- **獨立執行**: 在命令的上下文中執行，而非在代理內部。
- **從上下文接收數據**: 使用交談中已有的溫度數據。