from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import yfinance as yf

from .config import TickerConfig

logger = logging.getLogger(__name__)


def _compute_radar_metrics(
    ticker: str,
    hist: pd.DataFrame,
    info: dict[str, Any],
) -> dict[str, Any] | None:
    if hist.empty or len(hist) < 20:
        return None

    current_price = info.get("regularMarketPrice") or info.get("currentPrice")
    high_52w = info.get("fiftyTwoWeekHigh")

    if not current_price:
        current_price = float(hist["Close"].iloc[-1])

    if not high_52w:
        high_52w = float(hist["Close"].max())

    dist_pct = ((current_price / high_52w) - 1.0) * 100.0 if high_52w else 0.0

    recent_20d = hist.tail(20)
    avg_volume_20d = recent_20d["Volume"].mean()
    last_volume = float(hist["Volume"].iloc[-1])
    volume_ratio = (last_volume / avg_volume_20d) if avg_volume_20d > 0 else 0.0

    ma_10 = float(hist["Close"].tail(10).mean())
    ma_10_dev_pct = ((current_price / ma_10) - 1.0) * 100.0 if ma_10 else 0.0

    return {
        "ticker": ticker,
        "current_price": current_price,
        "high_52w": high_52w,
        "dist_to_high_pct": round(dist_pct, 2),
        "volume_ratio": round(volume_ratio, 2),
        "ma_10_dev_pct": round(ma_10_dev_pct, 2),
    }


def _evaluate_radar_flags(metrics: dict[str, Any]) -> dict[str, Any]:
    flags: list[str] = []
    risk_level = "none"
    reasons: list[str] = []

    dist_pct = metrics["dist_to_high_pct"]
    if dist_pct >= -5.0:
        flags.append("52-week breakout")
        reasons.append(f"Price is within {abs(dist_pct)}% of 52-week high.")
        risk_level = "low"
    elif dist_pct <= -20.0:
        flags.append("Max Drawdown")
        reasons.append(f"Price has drawn down {abs(dist_pct)}% from 52-week high.")
        risk_level = "high"

    vol_ratio = metrics["volume_ratio"]
    if vol_ratio >= 2.0:
        flags.append("Abnormal volume")
        reasons.append(f"Trading volume is {vol_ratio}x the 20-day average.")
        risk_level = "high" if risk_level == "high" else "medium"

    ma_10_dev = metrics["ma_10_dev_pct"]
    if ma_10_dev >= 10.0:
        flags.append("Volume Climax / Overbought")
        reasons.append(f"Price is stretched {ma_10_dev}% above the 10-day MA.")
        risk_level = "high"
    elif ma_10_dev <= -10.0:
        flags.append("Oversold")
        reasons.append(f"Price has deviated {ma_10_dev}% below the 10-day MA.")
        if risk_level == "none":
            risk_level = "medium"

    summary = " ".join(reasons) if reasons else "No significant technical deviation detected."

    return {
        "flags": flags,
        "summary": summary,
        "risk_level": risk_level,
    }


def scan_market(tickers: list[TickerConfig] | list[str]) -> dict[str, dict[str, Any]]:
    """
    Scans the provided tickers for technical deviations (Radar Flags).
    Failures per-ticker are logged and ignored to prevent pipeline disruption.
    """
    results: dict[str, dict[str, Any]] = {}
    
    ticker_symbols = [
        t.yahoo_symbol if isinstance(t, TickerConfig) else t 
        for t in tickers
    ]

    if not ticker_symbols:
        return results

    try:
        data = yf.download(
            tickers=ticker_symbols,
            period="1y",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
        )
    except Exception as exc:
        logger.warning(f"Radar mass download failed: {exc}")
        return results

    for symbol in ticker_symbols:
        try:
            if len(ticker_symbols) == 1:
                hist = data
            else:
                hist = data[symbol] if symbol in data else pd.DataFrame()
                
            if hist.empty:
                continue
                
            hist = hist.dropna(subset=["Close", "Volume"])

            # In yfinance, get basic info separately per ticker. Fallback to computing from hist if missing.
            stock = yf.Ticker(symbol)
            info = stock.info

            metrics = _compute_radar_metrics(symbol, hist, info)
            if metrics is None:
                continue

            evaluation = _evaluate_radar_flags(metrics)
            
            # Use original ticker symbol (e.g., stripping .TW if we were scanning Taiwan, but vNext is US only for now)
            # The input ticker name might be different from yahoo_symbol (e.g., BRK.B vs BRK-B), 
            # let's try to map back to the input config format if possible.
            original_ticker = next(
                (t.ticker for t in tickers if isinstance(t, TickerConfig) and t.yahoo_symbol == symbol),
                symbol
            )

            results[original_ticker] = {
                "ticker": original_ticker,
                "metrics": metrics,
                "radar_flags": evaluation["flags"],
                "radar_summary": evaluation["summary"],
                "radar_risk_level": evaluation["risk_level"],
            }
        except Exception as exc:
            logger.warning(f"Radar scan failed for {symbol}: {exc}")
            continue

    return results
