# STOCK Workspace Rules

This file is the thin workspace entrypoint. Do not duplicate long templates,
checklists, or philosophy essays here.

## When This Framework Applies

Use this workspace research framework when the user asks for:
- US equity deep-dive research
- Thesis updates after earnings, filings, or catalysts
- Peer comparison, scenario analysis, pre-mortem, or position-sizing support

Do not force this framework onto:
- Generic macro commentary with no target stock
- Pure news summaries or transcript recap
- Day-trading TA requests with no fundamental horizon
- Administrative or coding work unrelated to equity research

## Core Rules

1. Define the holding period first.
2. Judge new information by marginal impact on the thesis, not by volume.
3. Every scenario must end in an action rule.
4. Analyze valuation regime shifts before doing point-estimate valuation.
5. Treat research as a living document that must be recalibrated over time.

6. **Mermaid Syntax Rule**: All punctuation (e.g., colons, parentheses, arrows) must be half-width (ASCII) characters.
7. **Service Connectivity Rule**: 嚴禁 Backend (8001) 與 Frontend (8000/3000) 埠號不對稱。修改 API 調用前必須核對連線設定。
8. **Visual Verification Rule**: 對於 UI 佈局調整，宣稱完成前需主動建議或使用 `webapp-testing` (Playwright) 檢查元素重疊 (Overlap)。



## Required Outputs

- Human-readable thesis: `research/<ticker>/current.md`
- Machine-readable state: `research/<ticker>/state.json`
- Explicit assumptions, risks, scenarios, peer comparison, and action rules

For new events, use this update flow before changing conclusions:
1. Does the event match the original horizon?
2. Which core assumption does it affect?
3. Is the marginal impact positive, neutral, or negative?
4. Does it breach the pre-defined threshold?
5. What action, if any, follows?

## Source Of Truth (vNext Architecture)

- **Investment Soul & Philosophy**: [rules/investment-soul.md](rules/investment-soul.md)
- **Research Methodology**: [rules/research-methodology.md](rules/research-methodology.md)
- **Workflow & Skill Contract**: [.agent/skills/stock-research-operator/SKILL.md](.agent/skills/stock-research-operator/SKILL.md)
- **Active Research Template**: [.agent/skills/stock-research-operator/template.md](.agent/skills/stock-research-operator/template.md)
- **Quality Gate Checklist**: [.agent/skills/stock-research-operator/checklist.md](.agent/skills/stock-research-operator/checklist.md)

*Note: Legacy references in `.antigravity/` are being migrated to the `rules/` directory.*

## Operating Notes

- Default peer set is `PLTR`, `MSFT`, `MAR`, unless the user names better peers.
- Propose actions and sizing; never imply trade execution.
- Keep this file short. If the rule is really a template, checklist, or worked
  example, update the referenced file instead.
