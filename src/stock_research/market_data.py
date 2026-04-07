from __future__ import annotations

import datetime
from typing import Any

import pandas as pd
import yfinance as yf


def fetch_price_series(ticker: str, period: str = "10y") -> pd.DataFrame:
    """從 yfinance 取得調整後收盤價與成交量。

    回傳 DataFrame，columns: adj_close, volume，index 為日期。
    """
    raw = yf.download(ticker, period=period, auto_adjust=False, progress=False)
    if raw.empty:
        raise ValueError(f"No data returned for ticker: {ticker}")

    # yfinance 多層 column 時取第一層
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    df = pd.DataFrame(
        {
            "adj_close": raw["Adj Close"],
            "volume": raw["Volume"],
        }
    )
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    return df.dropna(subset=["adj_close"])


def resample_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """將日線資料重採樣為月線。

    price 取月末，volume 取月加總，計算 monthly_return。
    """
    monthly_price = df["adj_close"].resample("ME").last()
    monthly_volume = df["volume"].resample("ME").sum()
    monthly_return = monthly_price.pct_change()

    result = pd.DataFrame(
        {
            "adj_close": monthly_price,
            "volume": monthly_volume,
            "monthly_return": monthly_return,
        }
    )
    return result.dropna(subset=["adj_close"])


def build_price_series_artifact(ticker: str) -> dict[str, Any]:
    """建立價格序列 artifact。

    輸出 dict：ticker, as_of, series: [{date, adj_close, volume, cumulative_return}]
    """
    df = fetch_price_series(ticker)
    first_price = df["adj_close"].iloc[0]
    cumulative_return = df["adj_close"] / first_price - 1

    series = [
        {
            "date": idx.strftime("%Y-%m-%d"),
            "adj_close": round(float(row["adj_close"]), 4),
            "volume": int(row["volume"]),
            "cumulative_return": round(float(cumulative_return[idx]), 6),
        }
        for idx, row in df.iterrows()
    ]

    return {
        "ticker": ticker.upper(),
        "as_of": datetime.date.today().isoformat(),
        "series": series,
    }


def build_monthly_metrics_artifact(ticker: str) -> dict[str, Any]:
    """建立月度指標 artifact。

    輸出 dict：ticker, as_of, monthly: [{year, month, return_pct, adj_close}]
    """
    df = fetch_price_series(ticker)
    monthly = resample_monthly(df)

    monthly_list = [
        {
            "year": idx.year,
            "month": idx.month,
            "return_pct": round(float(row["monthly_return"]) * 100, 4) if pd.notna(row["monthly_return"]) else None,
            "adj_close": round(float(row["adj_close"]), 4),
        }
        for idx, row in monthly.iterrows()
    ]

    return {
        "ticker": ticker.upper(),
        "as_of": datetime.date.today().isoformat(),
        "monthly": monthly_list,
    }
