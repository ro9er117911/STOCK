from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from .config import RISK_POLICY_PATH, WATCHLIST
from .storage import deep_merge, read_json

DEFAULT_RISK_POLICY: dict[str, Any] = {
    "holding_period": "3-12 months",
    "vix": {
        "symbol": "^VIX",
        "regimes": [
            {
                "key": "calm",
                "label": "平穩",
                "min": 0.0,
                "max": 19.99,
                "size_multiplier": 1.0,
                "review_urgency": "normal",
                "summary": "波動正常，維持原始 target / max 倉位。",
            },
            {
                "key": "elevated",
                "label": "偏緊",
                "min": 20.0,
                "max": 29.99,
                "size_multiplier": 0.9,
                "review_urgency": "elevated",
                "summary": "波動抬升，target / max 倉位收緊 10%。",
            },
            {
                "key": "stress",
                "label": "壓力",
                "min": 30.0,
                "max": 39.99,
                "size_multiplier": 0.75,
                "review_urgency": "high",
                "summary": "風險偏高，target / max 倉位收緊 25%，暫停追價加碼。",
            },
            {
                "key": "panic",
                "label": "恐慌",
                "min": 40.0,
                "max": 1000.0,
                "size_multiplier": 0.6,
                "review_urgency": "critical",
                "summary": "市場進入恐慌區，target / max 倉位收緊 40%，優先做風險審視。",
            },
        ],
    },
    "circuit_breakers": {
        "review_loss_pct": -10.0,
        "de_risk_loss_pct": -15.0,
        "capital_preservation_loss_pct": -20.0,
        "weak_thesis_score": 0.6,
        "stress_regimes": ["stress", "panic"],
    },
    "actions": {
        "review": "觸發強制重新審視，在下一個 catalyst 前停止加碼。",
        "de_risk": "減碼到 regime-adjusted target 附近，並重新檢查 thesis。",
        "capital_preservation": "停止加碼並優先做 capital-preservation review，等待下一個 catalyst 重新驗證。",
        "over_max": "曝險高於 regime-adjusted max，先不要新增部位。",
        "healthy": "部位仍在可接受範圍，等待 thesis 驗證而不是追價。",
    },
}


def load_risk_policy(path: Path = RISK_POLICY_PATH) -> dict[str, Any]:
    payload = read_json(path, default={}) or {}
    return deep_merge(deepcopy(DEFAULT_RISK_POLICY), payload)


def _history_for_symbol(symbol: str) -> pd.DataFrame:
    history = yf.download(
        tickers=symbol,
        period="1mo",
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if history.empty:
        return history
    if isinstance(history.columns, pd.MultiIndex):
        if symbol in history.columns.get_level_values(-1):
            history = history.xs(symbol, axis=1, level=-1)
        else:
            history = history.droplevel(-1, axis=1)
    if "Close" not in history:
        return pd.DataFrame()
    return history.dropna(subset=["Close"])


def fetch_market_snapshot(
    tickers: list[str],
    *,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = policy or DEFAULT_RISK_POLICY
    snapshot: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "quotes": {},
        "vix": {
            "symbol": policy["vix"]["symbol"],
            "value": None,
            "previous_close": None,
            "change_pct": None,
            "as_of": "",
        },
    }
    yahoo_symbols = {
        ticker: WATCHLIST[ticker].yahoo_symbol if ticker in WATCHLIST else ticker
        for ticker in tickers
    }
    symbols = {policy["vix"]["symbol"], *yahoo_symbols.values()}
    symbol_rows: dict[str, dict[str, Any]] = {}

    for symbol in symbols:
        try:
            history = _history_for_symbol(symbol)
        except Exception:
            continue
        if history.empty:
            continue
        closes = history["Close"].tolist()
        price = float(closes[-1])
        previous_close = float(closes[-2]) if len(closes) >= 2 else price
        change_pct = (((price / previous_close) - 1.0) * 100.0) if previous_close else 0.0
        as_of = history.index[-1]
        if isinstance(as_of, pd.Timestamp):
            as_of_value = as_of.date().isoformat()
        else:
            as_of_value = str(as_of)
        symbol_rows[symbol] = {
            "price": round(price, 2),
            "previous_close": round(previous_close, 2),
            "change_pct": round(change_pct, 2),
            "as_of": as_of_value,
        }

    vix_symbol = policy["vix"]["symbol"]
    if vix_symbol in symbol_rows:
        snapshot["vix"] = {
            "symbol": vix_symbol,
            "value": symbol_rows[vix_symbol]["price"],
            "previous_close": symbol_rows[vix_symbol]["previous_close"],
            "change_pct": symbol_rows[vix_symbol]["change_pct"],
            "as_of": symbol_rows[vix_symbol]["as_of"],
        }

    for ticker, symbol in yahoo_symbols.items():
        row = symbol_rows.get(symbol)
        snapshot["quotes"][ticker] = {
            "symbol": symbol,
            "price": None if row is None else row["price"],
            "previous_close": None if row is None else row["previous_close"],
            "change_pct": None if row is None else row["change_pct"],
            "as_of": "" if row is None else row["as_of"],
        }
    return snapshot


def classify_vix_regime(vix_value: float | None, policy: dict[str, Any]) -> dict[str, Any]:
    regimes = policy["vix"]["regimes"]
    if vix_value is None:
        fallback = regimes[0]
        return {
            "symbol": policy["vix"]["symbol"],
            "value": None,
            "value_label": "N/A",
            "previous_close": None,
            "change_pct": None,
            "as_of": "",
            "key": fallback["key"],
            "label": "未取得",
            "size_multiplier": fallback["size_multiplier"],
            "review_urgency": fallback["review_urgency"],
            "summary": "VIX 資料暫時無法取得，先沿用原始 sizing。",
        }
    for regime in regimes:
        if regime["min"] <= vix_value <= regime["max"]:
            return {
                "symbol": policy["vix"]["symbol"],
                "value": round(float(vix_value), 2),
                "value_label": f"{float(vix_value):.2f}",
                "previous_close": None,
                "change_pct": None,
                "as_of": "",
                "key": regime["key"],
                "label": regime["label"],
                "size_multiplier": regime["size_multiplier"],
                "review_urgency": regime["review_urgency"],
                "summary": regime["summary"],
            }
    highest = regimes[-1]
    return {
        "symbol": policy["vix"]["symbol"],
        "value": round(float(vix_value), 2),
        "value_label": f"{float(vix_value):.2f}",
        "previous_close": None,
        "change_pct": None,
        "as_of": "",
        "key": highest["key"],
        "label": highest["label"],
        "size_multiplier": highest["size_multiplier"],
        "review_urgency": highest["review_urgency"],
        "summary": highest["summary"],
    }


def build_macro_regime(
    market_snapshot: dict[str, Any] | None,
    policy: dict[str, Any],
) -> dict[str, Any]:
    market_snapshot = market_snapshot or {}
    vix_row = market_snapshot.get("vix", {})
    regime = classify_vix_regime(vix_row.get("value"), policy)
    regime["previous_close"] = vix_row.get("previous_close")
    regime["change_pct"] = vix_row.get("change_pct")
    regime["as_of"] = vix_row.get("as_of", "")
    return regime


def empty_portfolio_totals() -> dict[str, Any]:
    return {
        "has_private_positions": False,
        "held_ticker_count": 0,
        "cost_basis": None,
        "cost_basis_label": "Private only",
        "market_value": None,
        "market_value_label": "Private only",
        "unrealized_pnl": None,
        "unrealized_pnl_label": "Private only",
        "unrealized_pnl_pct": None,
        "unrealized_pnl_pct_label": "Private only",
        "active_alert_count": 0,
        "largest_position_ticker": "",
        "largest_position_weight_pct": None,
        "as_of": "",
    }


def _base_alert(
    *,
    level: str,
    kind: str,
    title: str,
    message: str,
    action: str,
) -> dict[str, Any]:
    return {
        "level": level,
        "kind": kind,
        "title": title,
        "message": message,
        "action": action,
    }


def evaluate_position_snapshot(
    position: dict[str, Any],
    *,
    quote: dict[str, Any],
    macro_regime: dict[str, Any],
    thesis_health_score: float,
    key_events: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    shares = float(position.get("shares", 0) or 0)
    avg_cost = float(position.get("avg_cost", 0) or 0)
    target_weight_pct = float(position.get("target_weight_pct", 0) or 0)
    max_weight_pct = float(position.get("max_weight_pct", 0) or 0)
    cost_basis = shares * avg_cost if shares > 0 and avg_cost > 0 else 0.0
    current_price = quote.get("price")
    effective_price = float(current_price) if current_price is not None else avg_cost
    market_value = shares * effective_price if shares > 0 else 0.0
    unrealized_pnl = market_value - cost_basis if cost_basis > 0 else 0.0
    unrealized_pnl_pct = round((((effective_price / avg_cost) - 1.0) * 100.0), 2) if avg_cost > 0 else None
    multiplier = float(macro_regime.get("size_multiplier", 1.0) or 1.0)
    adjusted_target_weight_pct = round(target_weight_pct * multiplier, 2)
    adjusted_max_weight_pct = round(max_weight_pct * multiplier, 2)
    stress_regimes = set(policy["circuit_breakers"]["stress_regimes"])
    risk_alerts: list[dict[str, Any]] = []
    sizing_state = "no-position"
    sizing_label = "尚未填入"
    sizing_summary = "目前沒有部位資料。"
    recommended_next_action = policy["actions"]["healthy"]

    if macro_regime.get("key") in stress_regimes:
        risk_alerts.append(
            _base_alert(
                level="high" if macro_regime.get("key") == "stress" else "critical",
                kind="macro_regime",
                title=f"VIX {macro_regime['label']} regime",
                message=macro_regime["summary"],
                action="先收緊 sizing，暫停追價加碼。",
            )
        )

    if any(event.get("metadata", {}).get("is_exception") for event in key_events):
        exception = next(event for event in key_events if event.get("metadata", {}).get("is_exception"))
        risk_alerts.append(
            _base_alert(
                level=exception["metadata"].get("severity", "high"),
                kind="exception_event",
                title=exception["metadata"].get("exception_type", "Exception"),
                message=exception["title"],
                action="把這檔列入今日優先處理，重新檢查 thesis 與 sizing。",
            )
        )

    if unrealized_pnl_pct is not None and unrealized_pnl_pct <= policy["circuit_breakers"]["capital_preservation_loss_pct"]:
        risk_alerts.append(
            _base_alert(
                level="critical",
                kind="capital_preservation",
                title="Capital-preservation review",
                message=f"未實現損益已達 {unrealized_pnl_pct:.2f}%。",
                action=policy["actions"]["capital_preservation"],
            )
        )
        recommended_next_action = policy["actions"]["capital_preservation"]
    elif unrealized_pnl_pct is not None and unrealized_pnl_pct <= policy["circuit_breakers"]["de_risk_loss_pct"]:
        if thesis_health_score < policy["circuit_breakers"]["weak_thesis_score"] or macro_regime.get("key") in stress_regimes:
            risk_alerts.append(
                _base_alert(
                    level="high",
                    kind="de_risk",
                    title="De-risk review",
                    message=f"未實現損益 {unrealized_pnl_pct:.2f}%，且 thesis / macro 壓力同時存在。",
                    action=policy["actions"]["de_risk"],
                )
            )
            recommended_next_action = policy["actions"]["de_risk"]
    elif unrealized_pnl_pct is not None and unrealized_pnl_pct <= policy["circuit_breakers"]["review_loss_pct"]:
        risk_alerts.append(
            _base_alert(
                level="medium",
                kind="review",
                title="Forced review",
                message=f"未實現損益已達 {unrealized_pnl_pct:.2f}%。",
                action=policy["actions"]["review"],
            )
        )
        recommended_next_action = policy["actions"]["review"]

    return {
        **position,
        "has_position": shares > 0 or avg_cost > 0 or target_weight_pct > 0 or max_weight_pct > 0,
        "shares": shares,
        "avg_cost": avg_cost,
        "target_weight_pct": target_weight_pct,
        "max_weight_pct": max_weight_pct,
        "cost_basis": round(cost_basis, 2) if cost_basis else None,
        "cost_basis_label": "未填成本" if not cost_basis else f"${cost_basis:,.2f}",
        "current_price": None if current_price is None else round(float(current_price), 2),
        "current_price_label": "N/A" if current_price is None else f"${float(current_price):,.2f}",
        "market_value": round(market_value, 2) if market_value else None,
        "market_value_label": "N/A" if not market_value else f"${market_value:,.2f}",
        "unrealized_pnl": None if unrealized_pnl_pct is None else round(unrealized_pnl, 2),
        "unrealized_pnl_label": "N/A" if unrealized_pnl_pct is None else f"${unrealized_pnl:,.2f}",
        "unrealized_pnl_pct": None if unrealized_pnl_pct is None else round(unrealized_pnl_pct, 2),
        "unrealized_pnl_pct_label": "N/A" if unrealized_pnl_pct is None else f"{unrealized_pnl_pct:.2f}%",
        "portfolio_weight_pct": None,
        "portfolio_weight_label": "N/A",
        "adjusted_target_weight_pct": adjusted_target_weight_pct,
        "adjusted_target_weight_label": f"{adjusted_target_weight_pct:.1f}%",
        "adjusted_max_weight_pct": adjusted_max_weight_pct,
        "adjusted_max_weight_label": f"{adjusted_max_weight_pct:.1f}%",
        "distance_to_target_pct": None,
        "distance_to_target_label": "N/A",
        "distance_to_max_pct": None,
        "distance_to_max_label": "N/A",
        "sizing_status": {
            "state": sizing_state,
            "label": sizing_label,
            "summary": sizing_summary,
        },
        "risk_alerts": risk_alerts,
        "risk_alert_count": len(risk_alerts),
        "recommended_next_action": recommended_next_action,
        "market_data_as_of": quote.get("as_of", ""),
    }


def finalize_position_weights(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total_value = sum(
        float(position.get("market_value") or 0.0) if position.get("market_value") is not None else 0.0
        for position in positions
    )
    if total_value <= 0:
        total_value = sum(float(position.get("cost_basis") or 0.0) for position in positions)

    finalized: list[dict[str, Any]] = []
    for position in positions:
        current_value = (
            float(position.get("market_value") or 0.0)
            if position.get("market_value") is not None
            else float(position.get("cost_basis") or 0.0)
        )
        portfolio_weight_pct = round((current_value / total_value) * 100.0, 2) if total_value > 0 else 0.0
        adjusted_target_weight_pct = float(position.get("adjusted_target_weight_pct", 0.0) or 0.0)
        adjusted_max_weight_pct = float(position.get("adjusted_max_weight_pct", 0.0) or 0.0)
        distance_to_target_pct = round(adjusted_target_weight_pct - portfolio_weight_pct, 2)
        distance_to_max_pct = round(adjusted_max_weight_pct - portfolio_weight_pct, 2)

        if portfolio_weight_pct > adjusted_max_weight_pct and adjusted_max_weight_pct > 0:
            sizing_state = "over_max"
            sizing_label = "高於上限"
            sizing_summary = "目前曝險已高於 regime-adjusted max。"
        elif portfolio_weight_pct > adjusted_target_weight_pct and adjusted_target_weight_pct > 0:
            sizing_state = "above_target"
            sizing_label = "高於目標"
            sizing_summary = "目前曝險高於 regime-adjusted target。"
        elif adjusted_target_weight_pct > 0 and portfolio_weight_pct >= adjusted_target_weight_pct * 0.85:
            sizing_state = "at_target"
            sizing_label = "接近目標"
            sizing_summary = "部位大致落在 regime-adjusted target 附近。"
        else:
            sizing_state = "under_target"
            sizing_label = "低於目標"
            sizing_summary = "目前曝險仍低於 regime-adjusted target。"

        finalized.append(
            {
                **position,
                "portfolio_weight_pct": portfolio_weight_pct,
                "portfolio_weight_label": f"{portfolio_weight_pct:.2f}%",
                "distance_to_target_pct": distance_to_target_pct,
                "distance_to_target_label": f"{distance_to_target_pct:+.2f}%",
                "distance_to_max_pct": distance_to_max_pct,
                "distance_to_max_label": f"{distance_to_max_pct:+.2f}%",
                "sizing_status": {
                    "state": sizing_state,
                    "label": sizing_label,
                    "summary": sizing_summary,
                },
            }
        )
    return finalized


def build_portfolio_totals(positions: list[dict[str, Any]]) -> dict[str, Any]:
    held = [position for position in positions if position.get("has_position")]
    if not held:
        return empty_portfolio_totals()

    cost_basis = round(sum(float(position.get("cost_basis") or 0.0) for position in held), 2)
    market_value = round(
        sum(
            float(position.get("market_value") or 0.0)
            if position.get("market_value") is not None
            else float(position.get("cost_basis") or 0.0)
            for position in held
        ),
        2,
    )
    unrealized_pnl = round(market_value - cost_basis, 2)
    unrealized_pnl_pct = round((unrealized_pnl / cost_basis) * 100.0, 2) if cost_basis else None
    active_alert_count = sum(int(position.get("risk_alert_count", 0) or 0) for position in held)
    largest_position = max(held, key=lambda row: float(row.get("portfolio_weight_pct") or 0.0))
    as_of_values = [position.get("market_data_as_of", "") for position in held if position.get("market_data_as_of")]

    return {
        "has_private_positions": True,
        "held_ticker_count": len(held),
        "cost_basis": cost_basis,
        "cost_basis_label": f"${cost_basis:,.2f}",
        "market_value": market_value,
        "market_value_label": f"${market_value:,.2f}",
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_label": f"${unrealized_pnl:,.2f}",
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "unrealized_pnl_pct_label": "N/A" if unrealized_pnl_pct is None else f"{unrealized_pnl_pct:.2f}%",
        "active_alert_count": active_alert_count,
        "largest_position_ticker": largest_position["ticker"],
        "largest_position_weight_pct": largest_position.get("portfolio_weight_pct"),
        "as_of": max(as_of_values) if as_of_values else "",
    }


def project_maturity_snapshot() -> list[dict[str, str]]:
    return [
        {
            "id": "research-os",
            "label": "Research OS",
            "status": "complete",
            "status_label": "Complete",
            "summary": "研究 dossiers、state contract、digest 與 dashboard 產線已成形。",
        },
        {
            "id": "exception-monitoring",
            "label": "Exception monitoring",
            "status": "prototype",
            "status_label": "Prototype",
            "summary": "已有量價例外事件與 UI 入口，但先前資料 contract 斷裂。",
        },
        {
            "id": "post-mortem",
            "label": "Post-mortem analytics",
            "status": "basic",
            "status_label": "Basic",
            "summary": "已能回顧 assumption hit rate，但尚未結合 sizing / P&L。",
        },
        {
            "id": "risk-circuit-breaker",
            "label": "Risk circuit breaker",
            "status": "basic",
            "status_label": "Basic",
            "summary": "v1 成本基礎與 thesis/macro 雙重條件熔斷邏輯已上線，下一步是更細的例外分級。",
        },
        {
            "id": "position-sizing",
            "label": "Position sizing engine",
            "status": "prototype",
            "status_label": "Prototype",
            "summary": "已新增 regime-adjusted target / max sizing 建議，下一步是加入更完整的集中度限制。",
        },
        {
            "id": "vix-macro",
            "label": "VIX macro regime",
            "status": "basic",
            "status_label": "Basic",
            "summary": "VIX-led macro overlay 已接上，下一步是補 rates / discount-rate linkage。",
        },
    ]
