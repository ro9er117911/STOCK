from __future__ import annotations

import pytest

from stock_research.adr_premium import calculate_adr_premium


def test_calculate_adr_premium_flags_local_lagging() -> None:
    result = calculate_adr_premium(local_px=100, adr_px=3.5, fx_rate=32, adr_ratio=1)

    assert result == {
        "premium_pct": 12.0,
        "drift_direction": "lagging",
        "fx_wind": "neutral",
    }


def test_calculate_adr_premium_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="local_px must be positive"):
        calculate_adr_premium(local_px=0, adr_px=3.5, fx_rate=32, adr_ratio=1)
