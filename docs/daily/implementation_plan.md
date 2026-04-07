# Implementation Plan - Stock Analysis Dashboard v2 Completion

OMC has established a solid foundation with `performance.py`, `market_data.py`, and the HTML structure for tabs. However, the frontend rendering logic and the back-end persistence for the analysis artifacts are missing.

## User Review Required

> [!IMPORTANT]
> **No External Libraries**: I will implement the charts using pure SVG as per the plan, reducing dependency bloat and ensuring fast load times.

## Proposed Changes

### [Backend] Artifact Persistence & CLI

#### [MODIFY] [cli.py](file:///Users/ro9air/STOCK/stock_research/cli.py)
- Update the `build-analysis` command to:
    - Save individual artifacts to `research/<ticker>/artifacts/`.
    - Create a consolidated `site/data/tickers/<ticker>.analysis.json` for the frontend.
    - Support both `site/` and `_site/` (local cockpit) output paths.

### [Frontend] Tab Implementation

#### [MODIFY] [dashboard.js](file:///Users/ro9air/STOCK/stock_research/templates/dashboard/assets/dashboard.js)
- Implement `renderOverviewTab`, `renderPriceTab`, `renderDrawdownTab`, `renderMonthlyTab`, `renderQuarterlyTab`, `renderCagrTab`, `renderSharpeTab`, `renderGlossaryTab`.
- **[NEW] SVG Charting Utility**: A lightweight internal engine for:
    - Underwater charts (Drawdown).
    - Price line charts with volume.
    - Monthly Heatmaps.
    - Rolling metrics.

#### [MODIFY] [dashboard.css](file:///Users/ro9air/STOCK/stock_research/templates/dashboard/assets/dashboard.css)
- Add CSS for:
    - Tab switching animations.
    - Heatmap grid styling.
    - SVG tooltip and interactive states.
    - KPI card layouts within tabs.

## Verification Plan

### Automated Tests
- Run `pytest tests/test_performance.py` to ensure calculation logic is solid.
- Run `python3 scripts/research_ops.py build-analysis --ticker PLTR` to verify file generation.
- Use `webapp-testing` (Playwright) to verify:
    - Tab switching works.
    - Charts are rendered in SVG.
    - KPI cards are populated correctly.

### Manual Verification
- Open the dashboard in the browser via `/webapp-testing` and navigate to a ticker (e.g., PLTR).
- Verify the Drawdown Tab (Underwater chart) feels responsive.
