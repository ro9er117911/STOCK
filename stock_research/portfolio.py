from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import PORTFOLIO_PRIVATE_PATH
from .storage import read_json


def load_private_portfolio(path: Path = PORTFOLIO_PRIVATE_PATH) -> dict[str, dict[str, Any]]:
    payload = read_json(path, default={}) or {}
    rows = payload.get("positions", payload if isinstance(payload, list) else [])
    positions: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return positions
    for row in rows:
        ticker = row.get("ticker")
        if not ticker:
            continue
        positions[ticker] = {
            "ticker": ticker,
            "shares": float(row.get("shares", 0) or 0),
            "avg_cost": float(row.get("avg_cost", 0) or 0),
            "target_weight_pct": float(row.get("target_weight_pct", 0) or 0),
            "max_weight_pct": float(row.get("max_weight_pct", 0) or 0),
            "risk_level": str(row.get("risk_level", "") or ""),
            "notes": str(row.get("notes", "") or ""),
        }
    return positions

