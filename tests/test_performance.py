import pytest
import pandas as pd
import numpy as np
from stock_research.performance import (
    calc_cagr, calc_drawdown_series, calc_max_drawdown,
    calc_rolling_mdd, extract_drawdown_periods,
    calc_annualized_return, calc_annualized_volatility, calc_sharpe,
    run_buy_and_hold
)


def make_price_df(prices, start="2020-01-02"):
    """建立測試用 price DataFrame"""
    dates = pd.date_range(start=start, periods=len(prices), freq="B")
    return pd.DataFrame({"adj_close": prices}, index=dates)


def test_cagr_5y():
    # 100 -> 161.05 in 5 years = 10% CAGR
    result = calc_cagr(100, 161.05, 5)
    assert abs(result - 0.10) < 0.001


def test_cagr_custom_range():
    # 100 -> 121 in 2 years = 10% CAGR
    result = calc_cagr(100, 121, 2)
    assert abs(result - 0.10) < 0.001


def test_cagr_zero_years_returns_nan():
    # years=0 時回傳 nan（不 raise）
    result = calc_cagr(100, 80, 0)
    assert np.isnan(result)


def test_mdd_simple():
    # 100 -> 200 -> 100：MDD = -50%
    prices = [100, 150, 200, 150, 100]
    df = make_price_df(prices)
    mdd = calc_max_drawdown(df)
    assert abs(mdd - (-0.50)) < 0.001


def test_mdd_rolling():
    prices = [100, 90, 80, 100, 90, 80, 100]
    df = make_price_df(prices)
    rolling = calc_rolling_mdd(df, window=3)
    assert isinstance(rolling, pd.Series)
    assert len(rolling) == len(df)


def test_drawdown_periods_extraction():
    # peak=100@t0, trough=70@t2, recovery=100@t4
    prices = [100, 85, 70, 85, 100, 105]
    df = make_price_df(prices)
    periods = extract_drawdown_periods(df, threshold=-0.10)
    assert len(periods) >= 1
    p = periods[0]
    assert p["depth_pct"] <= -0.10
    assert "peak_date" in p
    assert "trough_date" in p


def test_recovery_days_calculation():
    prices = [100, 85, 70, 85, 100, 105]
    df = make_price_df(prices)
    periods = extract_drawdown_periods(df, threshold=-0.10)
    if periods and periods[0].get("recovery_date"):
        assert periods[0]["recovery_days"] > 0


def test_sharpe_buy_and_hold():
    # 單調上漲序列：Sharpe 應為正
    prices = list(range(100, 600, 10))  # 50 個點
    df = make_price_df(prices)
    result = run_buy_and_hold(df, rfr=0.03)
    assert "sharpe_ratio" in result
    assert result["sharpe_ratio"] > 0


def test_annualized_return():
    # 252 個交易日，價格從 100 翻倍 -> annualized ~= 100%
    prices = [100 * (2 ** (i/252)) for i in range(253)]
    df = make_price_df(prices)
    ann_ret = calc_annualized_return(df)
    assert abs(ann_ret - 1.0) < 0.05


def test_annualized_volatility():
    # 常數價格 -> volatility = 0
    prices = [100.0] * 50
    df = make_price_df(prices)
    vol = calc_annualized_volatility(df)
    assert abs(vol) < 1e-9
