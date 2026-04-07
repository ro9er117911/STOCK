# Factor Logic V1: Quantitative Scoring Specification

## 1. Quality Factors (Weight: 40% of Factor Score)
Focus on financial health and profitability sustainability.
- **ROE (Return on Equity)**: 
    - *Metric*: (Net Income / Total Equity)
    - *Logic*: Z-score vs. Sector Average. 
    - *Threshold*: > 15% is strong; < 8% is a red flag.
- **FCF Yield**: 
    - *Metric*: Free Cash Flow / Market Cap.
    - *Logic*: Measures cash generation relative to price.

## 2. Value Factors (Weight: 30% of Factor Score)
Focus on finding "fair" or "cheap" entries relative to historical norms.
- **Forward P/E**:
    - *Metric*: Current Price / Estimated Next 12m Earnings.
    - *Logic*: Compare to 5-year historical mean. 
- **P/B (Price to Book)**:
    - *Metric*: Current Price / Book Value per Share.
    - *Logic*: Secondary check for capital-intensive industries.

## 3. Momentum Factors (Weight: 30% of Factor Score)
Focus on relative strength to avoid "value traps."
- **12m Relative Strength**:
    - *Metric*: (Ticker 12m Return) - (Benchmark 12m Return).
    - *Logic*: Measures if the ticker is outperforming the S&P 500 (US) or TAIEX (TW).

---

## 4. Normalization & Scoring
1. **Raw Score**: Calculate the raw metric for each ticker.
2. **Z-Score**: (Raw - Universe Mean) / Universe StdDev.
3. **Mapped Score (0-100)**: Convert Z-score to a percentile-based 0-100 score.

## 5. Final Hybrid Integration (Maestro Score)
`Final Score = (Factor Score * 0.6) + (Qualitative Conviction * 0.4)`

*Qualitative Conviction is a manual 0-100 input derived from the Research Thesis health.*
