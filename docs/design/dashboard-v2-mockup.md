# Design Mockup: Stock Research Dashboard V2 (Progressive Disclosure)

## 1. Design Philosophy: The "3-Click" Rule
The user should never feel overwhelmed. Information is disclosed only as needed.
- **Click 0 (The Overview)**: Everything at a glance. Single score, trend arrow.
- **Click 1 (The Analytics)**: Why is the score high/low? Factor Radar.
- **Click 2 (The Proof)**: Where did this come from? Event Ledger & Raw Data.

## 2. Visual Layout (L1: The Cockpit)
Minimalist Dark Mode. Each Ticker is a slim card.
```text
+-------------------------------------------------------------+
| [2330.TW] TSMC | Maestro Score: 78 | [BULLISH] | 📈 +2.4% |
+-------------------------------------------------------------+
| [AAPL] Apple   | Maestro Score: 42 | [NEUTRAL] | 📉 -0.5% |
+-------------------------------------------------------------+
```

## 3. Visual Layout (L2: The Deep-Dive Overlay)
When a card is clicked, it expands or opens a modal.
```text
+-------------------------------------------------------------+
| [2330.TW] TSMC                                              |
|-------------------------------------------------------------|
| QUANT FACTORS (60%) | QUALITATIVE THESIS (40%)              |
|                     |                                       |
| Quality:  [####--]  | Conviction: [#######-]                |
| Value:    [##----]  | Health:     [######--]                |
| Momentum: [######]  | Catalyst:   2nm Margin Expansion      |
|-------------------------------------------------------------|
| [View Detailed Ledger] | [Edit Research Thesis]             |
+-------------------------------------------------------------+
```

## 4. Visual Elements
- **Factor Radar Chart**: A clean web-chart showing Quality, Value, Momentum, Growth, and Risk.
- **Sentiment Icons**: Minimalist indicators for management guidance (Up/Down/Stable).
- **Time-Series Chart**: Focus on "Price vs. Decision Points" (not just OHLC).

## 5. Technology Stack
- **Frontend**: Clean Tailwind CSS + Headless UI.
- **Charts**: Chart.js or ECharts (for Radar and Decision plots).
- **State**: Alpine.js or Vue.js for fast, interactive layering without page reloads.
