"""
Factor Analysis Page Digest Builder.
自動掃描 research/ 目錄，計算各 ticker 的因子分析 + 流動性篩選結果。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MIN_LIQUIDITY_THRESHOLD = 10_000_000  # 日均成交金額門檻（當地幣別）


def _discover_tickers(research_root: Path) -> list[str]:
    """自動掃描 research/ 找出所有 ticker 目錄（排除 system）"""
    EXCLUDED = {"system"}
    tickers = []
    if not research_root.exists():
        return tickers
    for d in sorted(research_root.iterdir()):
        if d.is_dir() and d.name not in EXCLUDED:
            tickers.append(d.name)
    return tickers


def _compute_liquidity(ticker: str) -> dict[str, Any]:
    """
    計算流動性指標（yfinance）。
    台股代碼若不含 .TW 後綴則自動加上（純數字 = 台股）。
    """
    try:
        import yfinance as yf
        # 台股代碼判斷
        yf_ticker = ticker
        if ticker.isdigit():
            yf_ticker = f"{ticker}.TW"

        end_date = datetime.today()
        start_date = end_date - timedelta(days=60)  # 足夠取得 20 交易日均量

        data = yf.download(yf_ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
        if data.empty or len(data) < 10:
            return {"avg_volume_20d": 0, "daily_dollar_vol": 0, "status": "FAIL", "error": "insufficient data"}

        import pandas as pd
        if isinstance(data.columns, pd.MultiIndex):
            close_prices = data["Close"][yf_ticker]
            volumes = data["Volume"][yf_ticker]
        else:
            close_prices = data["Close"]
            volumes = data["Volume"]

        current_price = float(close_prices.iloc[-1])
        avg_volume_20d = float(volumes.tail(20).mean())
        daily_dollar_vol = avg_volume_20d * current_price
        status = "PASS" if daily_dollar_vol > MIN_LIQUIDITY_THRESHOLD else "FAIL"

        return {
            "avg_volume_20d": int(avg_volume_20d),
            "daily_dollar_vol": int(daily_dollar_vol),
            "current_price": round(current_price, 2),
            "status": status,
        }
    except Exception as e:
        logger.warning(f"Liquidity fetch failed for {ticker}: {e}")
        return {"avg_volume_20d": 0, "daily_dollar_vol": 0, "current_price": 0.0, "status": "FAIL", "error": str(e)}


def _compute_momentum_6m(ticker: str) -> float:
    """計算 6 個月動能（約 126 個交易日）"""
    try:
        import yfinance as yf
        yf_ticker = ticker if not ticker.isdigit() else f"{ticker}.TW"
        end_date = datetime.today()
        start_date = end_date - timedelta(days=210)
        data = yf.download(yf_ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
        if data.empty or len(data) < 126:
            return 0.0
        import pandas as pd
        close = data["Close"][yf_ticker] if isinstance(data.columns, pd.MultiIndex) else data["Close"]
        momentum = float((close.iloc[-1] - close.iloc[-126]) / close.iloc[-126] * 100)
        return round(momentum, 2)
    except Exception:
        return 0.0


def build_factor_analysis_digest(research_root: Path) -> dict[str, Any]:
    """
    主函數：自動掃描 research/ 目錄，計算因子分析 + 流動性篩選結果。

    Returns:
        {
            "generated_at": str,
            "summary": {"total_analyzed", "liquidity_pass", "liquidity_fail"},
            "tickers": [...sorted by maestro_score desc...],
            "filter_criteria": {...}
        }
    """
    from .engine import FactorEngine

    tickers = _discover_tickers(research_root)
    results = []

    for ticker in tickers:
        try:
            # 判斷市場
            market = "TW" if ticker.isdigit() else "US"
            engine = FactorEngine(market=market)
            snapshot = engine.get_factor_snapshot(ticker)

            # 流動性
            liquidity = _compute_liquidity(ticker)
            momentum_6m = _compute_momentum_6m(ticker)

            results.append({
                "ticker": ticker,
                "market": market,
                "current_price": liquidity.get("current_price", 0.0),
                "factor_scores": snapshot["scores"],
                "maestro_score": snapshot["maestro_factor_score"],
                "raw_metrics": snapshot["raw_metrics"],
                "liquidity_metrics": liquidity,
                "momentum_6m_pct": momentum_6m,
            })
        except Exception as e:
            logger.error(f"Factor analysis failed for {ticker}: {e}")
            continue

    # 依照 maestro_score 降序排列
    results.sort(key=lambda x: x["maestro_score"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    liquidity_pass = sum(1 for r in results if r["liquidity_metrics"]["status"] == "PASS")
    liquidity_fail = len(results) - liquidity_pass

    return {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_analyzed": len(results),
            "liquidity_pass": liquidity_pass,
            "liquidity_fail": liquidity_fail,
            "pass_rate_pct": round(liquidity_pass / max(len(results), 1) * 100, 1),
        },
        "tickers": results,
        "filter_criteria": {
            "min_liquidity_daily_local_currency": MIN_LIQUIDITY_THRESHOLD,
            "market_coverage": list({r["market"] for r in results}),
            "momentum_window_days": 126,
            "volume_window_days": 20,
        },
    }
