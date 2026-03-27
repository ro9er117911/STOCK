# PLTR Living Thesis

| Field | Value |
| --- | --- |
| Company | Palantir Technologies |
| Research Topic | AI commercial monetization with durable government moat |
| Holding Period | 數季至一年 |
| Research Type | 事件驅動 / 中線 |
| Last Reviewed | 2026-03-25 |
| Next Review | 2026-05-05 |
| Current Action | 持有 / 逢回加碼 |
| Thesis Confidence | 0.72 |

## Delta From Previous Version

- Q4 2025 美國商業營收維持三位數成長，商業化假設被強化。
- Maven AI 升級為 Program of Record，政府訂單黏著度提升。
- 短線估值仍高，必須持續監控商業增速是否掉到 50% 以下。

## Core Thesis

- `thesis_id`: `pltr-thesis-core`
- Thesis: 市場仍低估 Palantir 在美國商業 AI 與國防軟體的雙引擎飛輪，只要商業營收維持高成長且政府專案升級為常態預算，估值雖高仍可被更高品質的成長證明支持。
- Core catalyst: 美國商業營收續強與大型政府專案正式預算化。
- Market blind spot: 市場把 PLTR 視為敘事股，但近兩季已證明商業化與政府續約可同時成立。
- Verification date: 2026-05-05
- Expiry condition: US Commercial growth 掉到 50% 以下或核心政府專案預算被削弱。

## Observation Framework

- Primary variables: US Commercial revenue growth, Government contract durability, Operating margin expansion
- Secondary variables: International commercial conversion, Federal budget cadence, Stock-based compensation discipline
- Noise filters: Insider selling headlines without demand change, Single-session tech selloff, Unverified channel checks
- Thresholds: price gap 10.0%, abnormal volume 2.2x, deep refresh every 7 days

## Assumption Status

| ID | Assumption | Status | Confidence | Invalidation |
| --- | --- | --- | --- | --- |
| pltr-a1 | US Commercial AI demand can sustain hyper-growth above 80%. | reinforced | 0.78 | US Commercial revenue growth falls below 50% for one full quarter. |
| pltr-a2 | Government contracts remain sticky and budget-backed. | reinforced | 0.74 | Program of Record gets delayed or defense funding is cut. |
| pltr-a3 | Margin expansion can accompany revenue acceleration. | watch | 0.63 | Revenue beats but operating leverage stops improving for two quarters. |

## Risk Register

| ID | Risk | Tier | Response |
| --- | --- | --- | --- |
| pltr-r1 | Commercial growth normalizes faster than narrative assumes. | thesis weakener | Pause adds and re-rate to lower EV/Sales. |
| pltr-r2 | Government procurement slows with defense budget reprioritization. | thesis breaker | Exit if budget-backed programs lose priority. |
| pltr-r3 | Valuation compresses even while fundamentals stay good. | noise | Only act if accompanied by demand deterioration. |

## Valuation Regime

- Current yardstick: High-growth AI software EV/Sales
- Better yardstick: Growth plus FCF durability premium
- Switch trigger: Commercial growth remains above 80% while margins expand.
- Re-rating logic: The market starts paying for compounding rather than story optionality.
- Associated risk: Any deceleration in commercial growth brings multiple compression first.

## Scenario Actions

| ID | Trigger | Logic | Action |
| --- | --- | --- | --- |
| pltr-s-base | US Commercial stays above 80% and government renewals remain intact. | Original thesis holds with both engines contributing. | Hold core and add on controlled pullbacks. |
| pltr-s-bull | Commercial growth remains above 100% with margin expansion. | Narrative shifts from government-heavy to enterprise platform winner. | Add if valuation expansion is backed by margin improvement. |
| pltr-s-bear | Commercial growth slows but government stays intact. | Multiple compresses before earnings catch up. | Trim tactical size, keep only high-conviction core. |
| pltr-s-break | Defense budget or flagship programs deteriorate materially. | The moat claim fails and valuation has little support. | Exit. |

## Action Rules

| ID | Kind | Condition | Action |
| --- | --- | --- | --- |
| pltr-ar-add | add | US Commercial revenue grows above 100% for two straight quarters and margin expands. | Add up to max position size. |
| pltr-ar-trim | trim | Commercial growth falls below 70% without offsetting government upside. | Trim tactical adds and revisit valuation regime. |
| pltr-ar-exit | exit | Program of Record is downgraded or core defense budget support weakens. | Exit regardless of price action. |

## Follow-Up

- Next must-check data: Q1 2026 earnings: US Commercial growth, margins, major government renewal cadence.
- Research debt: Need cleaner read on UK/FCA contribution size., Need scenario work on commercial deal concentration.

## Source Manifest

- `legacy-market-update` (local_markdown): Legacy March 2026 market update - /Users/ro9air/STOCK/research/market_update_mar2026.md
- `sec` (sec): SEC company submissions - https://data.sec.gov/submissions/CIK0001321655.json
- `investor_news` (html): Palantir investor news releases - https://investors.palantir.com/news-events/news-releases/
- `price` (market_data): Yahoo Finance chart - https://query1.finance.yahoo.com/v8/finance/chart/PLTR?range=1mo&interval=1d

## Version Log

| Version | Date | Reason | Impact |
| --- | --- | --- | --- |
| v0 | 2026-03-25 | Baseline migration from legacy March update. | Established living thesis and machine-readable state. |

## Recent Event Log

| Date | Source | Event | Impact | Decision |
| --- | --- | --- | --- | --- |
| 2026-03-25 | legacy_seed | Q4 2025 results showed 137% US commercial growth. | + | refresh |
| 2026-03-25 | legacy_seed | Maven AI became a Program of Record. | + | refresh |
