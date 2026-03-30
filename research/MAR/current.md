# MAR Living Thesis

| Field | Value |
| --- | --- |
| Company | Marriott International |
| Research Topic | Light-asset travel compounder with business travel recovery optionality |
| Holding Period | 數季至一年 |
| Research Type | 中線 / 防禦配置 |
| Research Stage | active |
| Candidate Origin | manual_watchlist |
| Decision Status | active |
| Decision Updated | 2026-03-27 |
| Last Reviewed | 2026-03-27 |
| Next Review | 2026-05-07 |
| Current Action | 穩健持有 |
| Thesis Confidence | 0.67 |

## Delta From Previous Version

- No material evidence delta versus the prior state; thesis, assumptions, and action remain intact.
- Maintained the defensive quality / business-travel-recovery framing without changing confidence.
- Advanced last_reviewed_at to today and set a sensible next_review_at on the prior review cadence.

## Core Thesis

- `thesis_id`: `mar-thesis-core`
- Thesis: Marriott 受惠於輕資產模式、高端與國際旅遊韌性，以及企業差旅回溫，因此在景氣不確定環境下仍能維持穩定現金流與較佳下行保護。
- Core catalyst: Business travel recovery and stable international/high-end RevPAR.
- Market blind spot: 市場容易把 MAR 當純週期股，但其資本輕、品牌強與回購能力提供了更好的防禦質地。
- Verification date: 2026-05-05
- Expiry condition: High-end and business travel demand crack together in a deeper macro slowdown.

## Observation Framework

- Primary variables: RevPAR by segment and geography, Business travel recovery, Capital-light cash return profile
- Secondary variables: Forward bookings, High-end leisure mix, Macro slowdown risk
- Noise filters: Single-quarter EPS miss without RevPAR weakness, Short-lived consumer sentiment noise, Headline volatility in lower-end domestic travel
- Thresholds: price gap 8.0%, abnormal volume 2.0x, deep refresh every 10 days

## Research Workflow

- Stage: active
- Candidate origin: manual_watchlist
- Decision status: active
- Decision updated at: 2026-03-27
- Invalidation reason: None logged

## Radar Summary

- Risk level: none
- Summary: No radar flags logged yet; use this field for pre-research prioritization only.
- Flags: None logged

## Assumption Status

| ID | Assumption | Status | Confidence | Invalidation |
| --- | --- | --- | --- | --- |
| mar-a1 | High-end and international travel remain resilient enough to offset weaker low-end domestic demand. | reinforced | 0.70 | High-end and international RevPAR both roll over materially. |
| mar-a2 | Business travel improves through 2026 and supports occupancy and pricing. | watch | 0.61 | Corporate travel recovery stalls for another full cycle. |
| mar-a3 | The asset-light model preserves downside protection and cash return flexibility. | reinforced | 0.69 | Fee earnings weaken materially and leverage rises without demand support. |

## Risk Register

| ID | Risk | Tier | Response |
| --- | --- | --- | --- |
| mar-r1 | Macro recession broadens from budget travel to high-end and business travel. | thesis breaker | Exit if premium segments crack together. |
| mar-r2 | International travel momentum fades as FX or geopolitics worsen. | thesis weakener | Trim and lower the valuation range. |
| mar-r3 | Market rotates away from quality defensives even if fundamentals hold. | noise | Ignore unless fundamentals deteriorate. |

## Valuation Regime

- Current yardstick: Hotel-cycle P/E plus RevPAR outlook
- Better yardstick: Quality fee-based travel compounder
- Switch trigger: Business travel recovery becomes visible while premium segments stay resilient.
- Re-rating logic: The market pays for durable fee earnings and cash returns rather than pure cycle recovery.
- Associated risk: If the cycle weakens across all segments, the quality premium disappears.

## Scenario Actions

| ID | Trigger | Logic | Action |
| --- | --- | --- | --- |
| mar-s-base | Premium and international demand remain healthy and business travel improves gradually. | MAR compounds through a quality earnings profile rather than a hot cycle. | Hold as defensive quality exposure. |
| mar-s-bull | Corporate travel snaps back and forward bookings beat expectations. | The market re-rates MAR from cycle recovery to durable compounding. | Add on confirmation from RevPAR and bookings. |
| mar-s-bear | Budget weakness starts leaking into premium segments. | The thesis weakens but cash-return quality still matters. | Trim, but do not exit until premium demand clearly breaks. |
| mar-s-break | Deep recession hits business and premium travel together. | Downside protection is no longer enough to support the valuation. | Exit. |

## Action Rules

| ID | Kind | Condition | Action |
| --- | --- | --- | --- |
| mar-ar-add | add | Corporate travel and forward bookings improve while international RevPAR remains strong. | Add selectively after management confirms trend persistence. |
| mar-ar-trim | trim | Premium segment demand softens without offsetting business-travel recovery. | Trim and keep only defensive core size. |
| mar-ar-exit | exit | High-end and business travel weaken together in a deeper recession. | Exit the active thesis. |

## Follow-Up

- Next must-check data: Next earnings: RevPAR mix, corporate travel commentary, forward bookings, and cash return guidance.
- Research debt: Need a cleaner framework for group and convention demand sensitivity., Need cross-check on Europe and Asia RevPAR versus US softness.
- Consistency notes: None logged

## Source Manifest

- `legacy-market-update` (local_markdown): Legacy March 2026 market update - /Users/ro9air/STOCK/research/market_update_mar2026.md
- `sec` (sec): SEC company submissions - https://data.sec.gov/submissions/CIK0001048286.json
- `investor_news` (html): Marriott investor news releases - https://news.marriott.com/news/
- `price` (market_data): Yahoo Finance chart - https://query1.finance.yahoo.com/v8/finance/chart/MAR?range=1mo&interval=1d

## Version Log

| Version | Date | Reason | Impact |
| --- | --- | --- | --- |
| v0 | 2026-03-25 | Baseline migration from legacy March update. | Established living thesis and machine-readable state. |
| v1 | 2026-03-27 | Automated refresh triggered by manual. | No new events were provided in the refresh bundle, so the MAR thesis remains unchanged. Confidence and action stay stable; only the review timestamps are advanced to today with the next check pushed out on the existing cadence. |

## Thesis Change Log

| Date | Type | Stage | Decision | Summary |
| --- | --- | --- | --- | --- |
| 2026-03-27 | baseline | active | active | Established the living research state under the vNext decision workflow contract. |

## Recent Event Log

| Date | Source | Event | Impact | Decision |
| --- | --- | --- | --- | --- |
| 2026-03-25 | legacy_seed | High-end and international travel stayed firm while lower-end US demand softened. | 0 | watch |
| 2026-03-25 | legacy_seed | 2026 guidance stayed intact despite a small EPS miss. | + | watch |
