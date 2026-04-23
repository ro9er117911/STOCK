from __future__ import annotations


def fetch_live_adr_signal(
    local_symbol: str = "2330.TW",
    adr_symbol: str = "TSM",
    fx_symbol: str = "TWD=X",
    adr_ratio: float = 5.0,
) -> dict:
    """Fetch live prices from yfinance and calculate ADR premium.

    Args:
        local_symbol: Taiwan exchange symbol (e.g. '2330.TW')
        adr_symbol: US ADR symbol (e.g. 'TSM')
        fx_symbol: Yahoo FX symbol for USD/TWD (e.g. 'TWD=X')
        adr_ratio: Local shares per ADR unit

    Returns:
        dict with local_px, adr_px, fx_rate, premium_pct, drift_direction, fx_wind
        or raises RuntimeError if prices unavailable
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance not installed; run: pip install yfinance") from exc

    tickers = yf.download(
        [local_symbol, adr_symbol, fx_symbol],
        period="2d",
        interval="1d",
        auto_adjust=True,
        progress=False,
    )

    def _last_close(sym: str) -> float:
        try:
            col = ("Close", sym)
            series = tickers[col].dropna()
            if series.empty:
                raise ValueError(f"No data for {sym}")
            return float(series.iloc[-1])
        except KeyError:
            # Single-ticker fallback (shouldn't happen with multi-download)
            raise ValueError(f"Symbol {sym} not found in downloaded data")

    local_px = _last_close(local_symbol)
    adr_px = _last_close(adr_symbol)
    # TWD=X quotes as TWD per USD (inverse); yfinance returns price of 1 USD in TWD
    fx_rate = _last_close(fx_symbol)

    result = calculate_adr_premium(local_px, adr_px, fx_rate, adr_ratio)
    result.update({
        "local_px": round(local_px, 2),
        "adr_px": round(adr_px, 4),
        "fx_rate": round(fx_rate, 4),
        "local_symbol": local_symbol,
        "adr_symbol": adr_symbol,
    })
    return result


def calculate_adr_premium(local_px: float, adr_px: float, fx_rate: float, adr_ratio: float) -> dict[str, float | str]:
    if local_px <= 0:
        raise ValueError("local_px must be positive")
    if adr_px <= 0:
        raise ValueError("adr_px must be positive")
    if fx_rate <= 0:
        raise ValueError("fx_rate must be positive")
    if adr_ratio <= 0:
        raise ValueError("adr_ratio must be positive")

    implied_local_px = adr_px * fx_rate / adr_ratio
    premium_pct = (implied_local_px / local_px - 1) * 100

    if premium_pct > 1:
        drift_direction = "lagging"
    elif premium_pct < -1:
        drift_direction = "leading"
    else:
        drift_direction = "neutral"

    return {
        "premium_pct": round(premium_pct, 4),
        "drift_direction": drift_direction,
        "fx_wind": "neutral",
    }
