# Institutional Growth Cockpit Upgrade

**Summary**
- Treat the current repo as a solid phase-1 research OS, not a rewrite target: 3 tracked names, working dossier/state contracts, static dashboard generation, private position overlay hooks, and prototype exception/post-mortem surfaces already exist.
- Upgrade the product into a local-first, institution-style cockpit for your real holdings: actual cost basis, VIX-led macro regime, circuit-breaker alerts, sizing discipline, and a clean dark dashboard.
- Keep privacy boundaries intact: the public site stays sanitized; the full cost/P/L/risk cockpit lives only in the local private dashboard output.

**Implementation Changes**
- Replace the current stale private position source with your actual holdings as the single source of truth: `MAR 10 @ 350.3`, `MSFT 5 @ 536.98`, `PLTR 6 @ 173.86`.
- Add a portfolio risk-policy layer for global rules instead of hiding them in ticker notes. This layer should define VIX regimes, regime multipliers, and circuit-breaker defaults for a `3-12 month` holding period.
- Build a VIX-led macro regime engine using daily `^VIX` data with four states: `calm < 20`, `elevated 20-29.99`, `stress 30-39.99`, `panic >= 40`.
- Implement regime-adjusted sizing as recommendation output only: use your manual `target_weight_pct` and `max_weight_pct` as the base, then apply VIX multipliers `1.0 / 0.9 / 0.75 / 0.6` for `calm / elevated / stress / panic`.
- Implement three circuit-breaker states tied to your cost basis and thesis discipline:
  - `review` at `-10%` unrealized loss vs cost.
  - `de-risk` at `-15%` when combined with weak thesis health or VIX `stress/panic`.
  - `capital-preservation review` at `-20%`, with add-freeze until the next catalyst re-validates the thesis.
- Extend the local digest so each held name shows current price, market value, unrealized P/L, unrealized P/L %, portfolio weight, distance to target/max, triggered alerts, and recommended next action.
- Redesign the landing page into a Bloomberg-inspired dark cockpit: charcoal base, restrained amber/orange/cyan accents, denser metric-first layout, and one-screen-first prioritization. Replace the current light sand palette entirely.
- Make the homepage dual-purpose:
  - Top layer: real portfolio state, VIX regime, risk alerts, and sizing pressure.
  - Second layer: recent project progress and explicit institutional gaps.
- Add an “Institutional Gap Map” section that explicitly labels current maturity:
  - `Research OS`: complete
  - `Exception monitoring`: prototype
  - `Post-mortem analytics`: basic
  - `Risk circuit breaker`: missing
  - `Position sizing engine`: missing
  - `VIX macro regime`: missing
- Use existing digest stats to populate the “recent progress” strip so the page shows recent成果, not just design polish.
- Fold analytics and exceptions into the main dashboard boot path and fix the current dashboard correctness issues as part of the same scope:
  - remove the broken `initDashboard` override pattern,
  - fix the template-string syntax error around ``portfolio.private.json``,
  - preserve event `metadata` through the digest so exception cards can actually render.

**Interfaces / Types**
- Extend `research/system/portfolio.private.json` from “static position notes” into the authoritative private holdings input, but keep manual weights user-controlled.
- Add a new global risk-policy contract for:
  - VIX thresholds,
  - regime multipliers,
  - circuit-breaker defaults,
  - alert copy/action mapping.
- Extend the local dashboard payload with:
  - `macro_regime`
  - `portfolio_totals`
  - `position.market_value`
  - `position.unrealized_pnl`
  - `position.unrealized_pnl_pct`
  - `position.portfolio_weight_pct`
  - `position.sizing_status`
  - `position.risk_alerts[]`
  - `project_maturity[]`
- Keep the public payload compatible by emitting placeholders or `null` for private-only fields rather than exposing cost basis, share counts, or P/L.

**Test Plan**
- Unit-test VIX regime classification and multiplier selection at boundary values `19.99`, `20`, `29.99`, `30`, `39.99`, and `40`.
- Unit-test the sizing and circuit-breaker engine with your actual `10/5/6` holdings to verify `review`, `de-risk`, and `capital-preservation review` states trigger as designed.
- Unit-test private overlay generation so public output remains sanitized while local output includes full position metrics.
- Add a digest test confirming exception-event `metadata` survives into `key_events` and `event_timeline`.
- Add a frontend smoke test or browser check confirming the portfolio page loads without console syntax errors and renders analytics/exceptions from one unified boot path.

**Assumptions**
- The working horizon is `3-12 months`.
- Your latest message overrides the existing stale `100/100/100` private file entries.
- VIX is a regime valve, not a standalone sell signal.
- End-of-day data is sufficient for v1; intraday monitoring is out of scope.
- The first deliverable is a static local private cockpit plus sanitized public parity, not a framework rewrite.

## Phase 2: Hybrid Factor-Decision System (HFD)
**Objective**: Balanced decision engine merging quantitative factors with qualitative narratives.
- **Factor Logic**: Quality (ROE), Value (P/E), Momentum (RS).
- **Data Source**: Integrated FinMind (Taiwan) + yfinance (Global).
- **UI/UX Strategy**: Progressive Disclosure (L1: Cockpit, L2: Analytics, L3: Evidence).
- **Final Score**: 60% Factor / 40% Qualitative conviction.
