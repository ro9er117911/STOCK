---
name: stock-research-operator
description: >
  Conducts professional US equity research producing actionable investment theses,
  verifiable assumptions, scenario-based action plans, and peer comparisons.
  Monitors PLTR, MSFT, MAR as core watchlist.
  Use this skill whenever the user mentions: stock research, investment thesis,
  thesis update, earnings review, position sizing, scenario analysis, pre-mortem,
  valuation regime, PLTR, MSFT, MAR, or asks for buy/sell/hold recommendations.
metadata:
  author: ro9air
  version: "1.0"
  watchlist: "PLTR, MSFT, MAR"
---

# Investment Research Operator

## Purpose

Transform investment research from "information aggregation" into an **executable, iterable, calibratable** decision process.

The deliverable is NOT a pretty report. It is:
1. A clear investment    thesis (one verifiable sentence)
2. Core assumptions that can be tracked and falsified
3. Scenario-conditioned action rules
4. A living document that evolves with new data
5. A machine-readable state that automation can refresh safely

---

## Core Principles

### 1. Time-Horizon First
Before any vanálysis, define the holding period. The horizon determines:
- Which variables matter
- How to weight information
- What counts as noise
- Which events trigger action

### 2. Marginal Change Over Information Volume
Value comes not from more data, but from answering:
- Does this new event change the thesis?
- By how much?
- Does it breach my alarm threshold?

### 3. Scenarios Must Produce Actions
Every conclusion must be written as:
- If A happens → do X
- If B happens → do Y
- If C happens → exit or switch

### 4. Valuation Regime > Point Estimate
Don't just ask "is it cheap?" Ask:
- What yardstick is the market using to price this?
- Could that yardstick change?
- What event would trigger a regime shift?

### 5. Research Is Continuous Calibration
A good study is never "done." Each update must re-check:
- Are original assumptions still valid?
- Which risks have materialized?
- Which signals turned out to be noise?
- Do action rules need adjustment?

---

## Research Workflow (9 Steps)

### Step 1. Define Time-Horizon

Answer before anything else:
- Intended holding period (weeks / months / years)
- Top 3 variables for this horizon
- Items to de-noise
- Events that directly impact the thesis

**Horizon-Variable Mapping**
| Horizon | Priority Variables |
|---|---|
| Short-term (weeks) | Newsflow, event catalysts, expectation gaps, crowding |
| Medium-term (quarters) | Orders, inventory, margin trends, consensus revisions |
| Long-term (years) | Market share, industry structure, capital allocation, moat |

**Output fields:**
- Holding period
- Primary observation variables (3)
- Secondary observation variables (3)
- Noise filters
- Alarm thresholds

---

### Step 2. Build the Thesis

Compress the investment view into one verifiable sentence:

> I am long/short [ticker] because [causal logic]. The market has not fully priced [key change], which I expect [catalyst] to surface within [timeframe].

The thesis MUST contain: causal chain, key variable, timeframe, catalyst source, and invalidation condition.

**Output fields:** Thesis, Core catalyst, Market blind spot, Verification date, Expiry condition

---

### Step 3. List Core Assumptions

Decompose the thesis into ≥3 testable assumptions.

| Assumption | Type | Verification Method | Update Frequency | Invalidation Condition |
|---|---|---|---|---|
| A | Demand / Supply / Pricing / Valuation / Mgmt | Data source | W / M / Q | When X happens |

**Good assumption traits:** observable, verifiable, falsifiable, linked to stock-price driver.
**Bad assumptions:** "company is great," "industry has potential," "market will understand eventually."

---

### Step 4. List Top Risks That Could Kill the Thesis

≥3 risks. Generic macro or black-swan-only lists are not acceptable.

| Risk | Type | Leading Indicator | Thesis Impact | Response |
|---|---|---|---|---|
| A | Structural / Execution / Competition / Demand / Regulatory | What moves first | +/0/-/thesis-breaker | Watch / Trim / Exit |

**Risk tiers:**
- **Thesis breaker** — logic collapses, exit immediately
- **Thesis weakener** — lower conviction, don't necessarily exit
- **Noise** — short-term disruption, ignore per threshold rules

---

### Step 5. Analyze the Valuation Regime

Do NOT jump into a DCF. First answer:
1. What yardstick is the market using now?
2. Is that yardstick appropriate?
3. Under what conditions would the market switch yardsticks?
4. If the regime shifts, where does the re-rating come from?

**Common regime drifts:** P/B→P/E, P/E→EV/EBITDA, mature→growth, single-metric→narrative, asset-value→earnings-value, legacy→optionality/platform.

**Output fields:** Current yardstick, Better yardstick, Switch trigger, Re-rating logic, Associated risk

---

### Step 6. Scenario Analysis

Do NOT produce optimistic / neutral / pessimistic number tweaks. Build **causal-switch scenarios**.

| Scenario | Trigger | Causal Logic | Winner / Loser | Action |
|---|---|---|---|---|
| Base | Condition A | Original thesis holds | Target / Peers | Hold / small add |
| Bull | Condition B | Assumptions accelerate | Higher-beta plays | Add / rotate up |
| Bear | Condition C | Key variable deteriorates | Weak-B/S firms first | Trim / exit |
| Break | Condition D | Thesis invalid | All hurt | Full exit |

Each scenario MUST specify: trigger condition, change chain, profit redistribution, beneficiaries (first & lagged), and action.

---

### Step 7. Pre-Mortem

Assume one year from now this investment lost 50%. Work backward:
- Most likely failure scenario
- Which assumption failed
- What signal was ignored
- Earliest point to have corrected
- How to avoid next time

Purpose: surface blind spots, find the weakest assumption, build early-exit rules.

---

### Step 8. Peer Comparison

Research must answer not just "should I buy this?" but "is this the **best** choice?"

**Comparison dimensions:**
- Upside elasticity
- Downside protection
- Catalyst visibility
- Assumption difficulty
- Valuation-regime improvement potential
- Balance-sheet resilience
- "If wrong, who survives?"

**Standard table (pre-filled for watchlist):**

| Ticker | Upside Source | Downside Protection | Key Catalyst | Core Risk | Best-Fit Scenario |
|---|---|---|---|---|---|
| PLTR | | | | | |
| MSFT | | | | | |
| MAR | | | | | |

**Must answer:**
- Why this and not the others?
- If thesis holds, which has most upside?
- If thesis partially holds, which has best risk/reward?
- If thesis fails, which drops least?

---

### Step 9. Write Executable Actions

Every study MUST end with action rules.

- Current action:
- Suggested position size:
- Add condition:
- Trim condition:
- Exit condition:
- Switch condition:
- Next update date:
- Next must-check data:

**Action rule examples:**
- If gross margin declines non-seasonally for 2 consecutive quarters → trim
- If capacity expansion beats expectations AND ASP holds → add
- If market shifts from P/B to P/E pricing → re-rate target price
- If thesis breaker fires → unconditional exit

---

## Event Update Protocol

When new information appears, do NOT change conclusions directly. Follow this flow:

1. Does this info match my time-horizon?
2. Which core assumption does it affect?
3. Marginal contribution: + / 0 / −?
4. Does it breach the alarm threshold?
5. Is an action required?

**Event Log Table:**

| Date | Event | Affected Assumption | Marginal Impact | Threshold Breach? | Action |
|---|---|---|---|---|---|

## Automation Output Contract

Every research cycle should maintain both:

- `research/<ticker>/current.md`: the human-readable living thesis
- `research/<ticker>/state.json`: the machine-readable state for automation

Minimum machine state fields:

- `thesis_id`
- `assumptions[].assumption_id`
- `action_rules[].action_rule_id`
- `thresholds`
- `last_reviewed_at`
- `next_review_at`
- `confidence`
- `research_debt`
- `source_manifest`

---

## Signal vs. Noise Rules

**Treat as signal when:**
- Multiple indicators move together
- Change hits a core assumption directly
- Change is persistent (not one-off)
- Change affects the valuation regime
- Change alters profit distribution

**Treat as noise when:**
- Single month / single week / single source / unverified
- Affects sentiment only, not fundamentals
- Does not touch the thesis causal chain
- Below alarm threshold

---

## Iteration Mechanism

This skill produces living documents, not one-shot reports.

**Version convention:**
- v0: Initial thesis
- v1: + comparison & scenarios
- v2: + event tracking & thresholds
- v3: + pre-mortem & counter-evidence
- v4+: Ongoing thesis revision

**Each iteration must:**
1. Log new events
2. Re-check all core assumptions
3. Re-check valuation regime
4. Re-check whether a better alternative exists
5. Update action rules

**Version Log:**

| Version | Date | Reason | Changes | Impact on Conclusion |
|---|---|---|---|---|

---

## Common Errors to Avoid

1. Starting research without defining time-horizon
2. Mixing all sources (news, transcripts, revenue, rumors) without weighting
3. Obsessing over valuation math while ignoring regime drift
4. Producing info-rich reports with zero action rules
5. Analyzing only one company without peer comparison
6. Scenario analysis that only changes numbers, not causal logic
7. Emotionally revising thesis on new events without checking thresholds

---

## Success Criteria

A compliant research output must satisfy all five:
1. Reader knows the long/short thesis, rationale, and verification timeline within 3 minutes
2. Every major conclusion traces to a verifiable assumption
3. New information can be quickly triaged: ignore / watch / add / trim / exit
4. Clearly answers "why this and not the alternatives?"
5. When the thesis breaks, enables fast pivot instead of post-hoc rationalization

---

## Bundled Resources

- Read `template.md` at the start of every new research to get the blank fill-in structure.
- Read `checklist.md` before delivering any research to run the QA gate.
