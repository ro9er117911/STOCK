from __future__ import annotations

import datetime
from typing import Any

import numpy as np
import pandas as pd

from .market_data import fetch_price_series


def calc_cagr(start_price: float, end_price: float, years: float) -> float:
    """計算年複合成長率（CAGR）。"""
    if years <= 0 or start_price <= 0:
        return float("nan")
    return (end_price / start_price) ** (1 / years) - 1


def build_cagr_scenarios(price_df: pd.DataFrame) -> dict[str, Any]:
    """建立 1Y/3Y/5Y/10Y/since_inception 的 CAGR 情境。"""
    end_price = price_df["adj_close"].iloc[-1]
    end_date = price_df.index[-1]
    start_date = price_df.index[0]

    scenarios: dict[str, float | None] = {}
    for label, years in [("1y", 1), ("3y", 3), ("5y", 5), ("10y", 10)]:
        cutoff = end_date - pd.DateOffset(years=years)
        subset = price_df[price_df.index >= cutoff]
        if len(subset) < 2:
            scenarios[label] = None
        else:
            actual_years = (end_date - subset.index[0]).days / 365.25
            scenarios[label] = round(calc_cagr(subset["adj_close"].iloc[0], end_price, actual_years), 6)

    inception_years = (end_date - start_date).days / 365.25
    scenarios["since_inception"] = round(
        calc_cagr(price_df["adj_close"].iloc[0], end_price, inception_years), 6
    )
    return scenarios


def calc_drawdown_series(price_df: pd.DataFrame) -> pd.Series:
    """計算每日 drawdown：price_t / rolling_max_t - 1。"""
    rolling_max = price_df["adj_close"].cummax()
    drawdown = price_df["adj_close"] / rolling_max - 1
    drawdown.name = "drawdown"
    return drawdown


def calc_max_drawdown(price_df: pd.DataFrame) -> float:
    """計算全期最大回撤（MDD）。"""
    return float(calc_drawdown_series(price_df).min())


def calc_rolling_mdd(price_df: pd.DataFrame, window: int = 252) -> pd.Series:
    """計算滾動窗口內的最大回撤序列。"""
    drawdown = calc_drawdown_series(price_df)
    rolling_mdd = drawdown.rolling(window=window, min_periods=1).min()
    rolling_mdd.name = "rolling_mdd"
    return rolling_mdd


def extract_drawdown_periods(
    price_df: pd.DataFrame, threshold: float = -0.10
) -> list[dict[str, Any]]:
    """找出所有超過 threshold 的回撤區間。

    每個 period dict 格式：
    {peak_date, trough_date, depth_pct, duration_days, recovery_date, recovery_days}
    """
    prices = price_df["adj_close"]
    drawdown = calc_drawdown_series(price_df)

    periods: list[dict[str, Any]] = []
    in_drawdown = False
    peak_date = None
    peak_price = None
    trough_date = None
    trough_depth = 0.0

    dates = prices.index.tolist()

    for date in dates:
        dd = drawdown[date]
        price = prices[date]

        if not in_drawdown:
            if dd >= 0:
                peak_date = date
                peak_price = price
            elif dd < threshold:
                in_drawdown = True
                trough_date = date
                trough_depth = float(dd)
        else:
            if dd < trough_depth:
                trough_depth = float(dd)
                trough_date = date
            if dd >= 0:
                # 已回復
                recovery_date = date
                recovery_days = (recovery_date - trough_date).days
                duration_days = (trough_date - peak_date).days
                periods.append(
                    {
                        "peak_date": peak_date.strftime("%Y-%m-%d"),
                        "trough_date": trough_date.strftime("%Y-%m-%d"),
                        "depth_pct": round(trough_depth * 100, 4),
                        "duration_days": duration_days,
                        "recovery_date": recovery_date.strftime("%Y-%m-%d"),
                        "recovery_days": recovery_days,
                    }
                )
                in_drawdown = False
                peak_date = date
                peak_price = price
                trough_date = None
                trough_depth = 0.0

    # 尚未回復的回撤
    if in_drawdown and trough_date is not None:
        duration_days = (trough_date - peak_date).days
        periods.append(
            {
                "peak_date": peak_date.strftime("%Y-%m-%d"),
                "trough_date": trough_date.strftime("%Y-%m-%d"),
                "depth_pct": round(trough_depth * 100, 4),
                "duration_days": duration_days,
                "recovery_date": None,
                "recovery_days": None,
            }
        )

    # 按深度排序（最深在前）
    periods.sort(key=lambda x: x["depth_pct"])
    for rank, period in enumerate(periods, start=1):
        period["rank"] = rank
    return periods


def build_drawdown_artifact(ticker: str) -> dict[str, Any]:
    """建立完整 drawdown artifact，符合指定 schema。"""
    price_df = fetch_price_series(ticker)
    drawdown_series = calc_drawdown_series(price_df)
    rolling_mdd_series = calc_rolling_mdd(price_df, window=252)

    # 全期 MDD
    mdd_alltime = calc_max_drawdown(price_df)

    # 1Y MDD
    cutoff_1y = price_df.index[-1] - pd.DateOffset(years=1)
    df_1y = price_df[price_df.index >= cutoff_1y]
    mdd_1y = calc_max_drawdown(df_1y) if len(df_1y) >= 2 else float("nan")

    # 3Y MDD
    cutoff_3y = price_df.index[-1] - pd.DateOffset(years=3)
    df_3y = price_df[price_df.index >= cutoff_3y]
    mdd_3y = calc_max_drawdown(df_3y) if len(df_3y) >= 2 else float("nan")

    # 5Y MDD
    cutoff_5y = price_df.index[-1] - pd.DateOffset(years=5)
    df_5y = price_df[price_df.index >= cutoff_5y]
    mdd_5y = calc_max_drawdown(df_5y) if len(df_5y) >= 2 else float("nan")

    daily_dd_series = [
        {
            "date": idx.strftime("%Y-%m-%d"),
            "drawdown_pct": round(float(val) * 100, 4),
        }
        for idx, val in drawdown_series.items()
    ]

    rolling_mdd_1y = [
        {
            "date": idx.strftime("%Y-%m-%d"),
            "rolling_mdd_pct": round(float(val) * 100, 4),
        }
        for idx, val in rolling_mdd_series.items()
    ]

    periods = extract_drawdown_periods(price_df, threshold=-0.10)

    return {
        "ticker": ticker.upper(),
        "as_of": datetime.date.today().isoformat(),
        "mdd_alltime_pct": round(mdd_alltime * 100, 4),
        "mdd_1y_pct": round(mdd_1y * 100, 4) if not np.isnan(mdd_1y) else None,
        "mdd_3y_pct": round(mdd_3y * 100, 4) if not np.isnan(mdd_3y) else None,
        "mdd_5y_pct": round(mdd_5y * 100, 4) if not np.isnan(mdd_5y) else None,
        "daily_drawdown_series": daily_dd_series,
        "rolling_mdd_1y_series": rolling_mdd_1y,
        "drawdown_periods": periods,
        "source": {"provider": "yfinance", "adj_close": True},
    }


def calc_annualized_return(price_df: pd.DataFrame) -> float:
    """計算年化報酬率。

    Annualized Return = (1 + cumulative_return)^(252/trading_days) - 1
    """
    daily_returns = price_df["adj_close"].pct_change().dropna()
    if len(daily_returns) == 0:
        return float("nan")
    trading_days = len(daily_returns)
    cumulative_return = (1 + daily_returns).prod() - 1
    return float((1 + cumulative_return) ** (252 / trading_days) - 1)


def calc_annualized_volatility(price_df: pd.DataFrame) -> float:
    """計算年化波動率。

    Annualized Volatility = std(daily_returns) * sqrt(252)
    """
    daily_returns = price_df["adj_close"].pct_change().dropna()
    if len(daily_returns) == 0:
        return float("nan")
    return float(daily_returns.std() * np.sqrt(252))


def calc_sharpe(return_series: pd.Series, rfr: float = 0.03) -> float:
    """計算 Sharpe Ratio。

    Sharpe = (annualized_return - rfr) / annualized_volatility
    """
    if len(return_series) == 0:
        return float("nan")
    trading_days = len(return_series)
    cumulative_return = (1 + return_series).prod() - 1
    ann_return = float((1 + cumulative_return) ** (252 / trading_days) - 1)
    ann_vol = float(return_series.std() * np.sqrt(252))
    if ann_vol == 0:
        return float("nan")
    return (ann_return - rfr) / ann_vol


def run_buy_and_hold(price_df: pd.DataFrame, rfr: float = 0.03) -> dict[str, Any]:
    """執行買入持有策略分析。"""
    daily_returns = price_df["adj_close"].pct_change().dropna()
    ann_return = calc_annualized_return(price_df)
    ann_vol = calc_annualized_volatility(price_df)
    sharpe = calc_sharpe(daily_returns, rfr=rfr)
    mdd = calc_max_drawdown(price_df)
    cagr_scenarios = build_cagr_scenarios(price_df)

    start_price = float(price_df["adj_close"].iloc[0])
    end_price = float(price_df["adj_close"].iloc[-1])
    total_return = end_price / start_price - 1

    return {
        "start_date": price_df.index[0].strftime("%Y-%m-%d"),
        "end_date": price_df.index[-1].strftime("%Y-%m-%d"),
        "start_price": round(start_price, 4),
        "end_price": round(end_price, 4),
        "total_return_pct": round(total_return * 100, 4),
        "annualized_return_pct": round(ann_return * 100, 4),
        "annualized_volatility_pct": round(ann_vol * 100, 4),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown_pct": round(mdd * 100, 4),
        "rfr_used": rfr,
        "cagr_scenarios": cagr_scenarios,
    }


def build_strategy_metrics_artifact(ticker: str) -> dict[str, Any]:
    """建立完整策略指標 artifact。"""
    price_df = fetch_price_series(ticker)
    bah = run_buy_and_hold(price_df)
    drawdown_artifact = build_drawdown_artifact(ticker)

    return {
        "ticker": ticker.upper(),
        "as_of": datetime.date.today().isoformat(),
        "buy_and_hold": bah,
        "drawdown_summary": {
            "mdd_alltime_pct": drawdown_artifact["mdd_alltime_pct"],
            "mdd_1y_pct": drawdown_artifact["mdd_1y_pct"],
            "mdd_3y_pct": drawdown_artifact["mdd_3y_pct"],
            "mdd_5y_pct": drawdown_artifact["mdd_5y_pct"],
        },
        "source": {"provider": "yfinance", "adj_close": True},
    }
