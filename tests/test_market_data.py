import pytest
import pandas as pd
import numpy as np
from stock_research.market_data import resample_monthly


def make_daily_df(n_days=60, start="2023-01-02"):
    """建立測試用 daily DataFrame"""
    dates = pd.date_range(start=start, periods=n_days, freq="B")
    prices = 100 + np.arange(n_days, dtype=float)
    volumes = np.ones(n_days) * 1000
    return pd.DataFrame({"adj_close": prices, "volume": volumes}, index=dates)


def test_resample_monthly_end_price():
    df = make_daily_df(60)
    monthly = resample_monthly(df)
    assert "adj_close" in monthly.columns
    # 月末價格應為當月最後一個交易日的價格
    assert monthly["adj_close"].iloc[0] > 100


def test_resample_monthly_sum_volume():
    df = make_daily_df(60)
    monthly = resample_monthly(df)
    assert "volume" in monthly.columns
    # 月加總 volume 應 > 單日 volume
    assert monthly["volume"].iloc[0] > 1000


def test_monthly_return_calculation():
    df = make_daily_df(60)
    monthly = resample_monthly(df)
    assert "monthly_return" in monthly.columns
    # 第一個月 return 可為 NaN（無前期）
    assert len(monthly) >= 2
