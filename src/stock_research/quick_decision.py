from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from .adr_premium import calculate_adr_premium
from .config import AUTOMATION_ROOT, RESEARCH_ROOT, SOURCE_REGISTRY_PATH
from .storage import read_json, write_json


QUICK_DECISION_PATH = AUTOMATION_ROOT / "quick-decision.json"
RsiState = Literal["neutral", "overbought", "oversold"]
VerdictStatus = Literal["BUY", "WAIT", "PASS"]


@dataclass
class LightVerdict:
    ticker: str
    status: VerdictStatus
    rationale: list[str]
    confidence: float
    expires_at: str
    signals: dict[str, Any]
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_light_verdict(
    ticker: str,
    adr_premium_pct: float,
    local_px: float,
    trigger_description: str,
    rsi_state: RsiState = "neutral",
    now: datetime | None = None,
) -> LightVerdict:
    ticker = ticker.upper()
    rsi_state = _normalize_rsi_state(rsi_state)
    created_at = now or datetime.now(timezone.utc)
    expires_at = (created_at + timedelta(hours=24)).isoformat()
    premium = round(float(adr_premium_pct), 2)

    if premium > 8 and rsi_state == "neutral":
        status: VerdictStatus = "WAIT"
        confidence = 0.62
        rationale = [
            f"{ticker} ADR premium is {premium:.2f}%, wide enough to imply local catch-up is still pending.",
            f"With RSI marked neutral, the setup favors waiting for a cleaner local entry instead of chasing the gap.",
        ]
    elif premium > 5 and rsi_state != "overbought":
        status = "BUY"
        confidence = 0.66
        rationale = [
            f"{ticker} ADR premium is {premium:.2f}%, above the 5% light-track momentum trigger.",
            f"The signal is not overbought, so the one-liner setup supports a tactical BUY signal tied to: {trigger_description}.",
        ]
    elif premium > 5:
        status = "WAIT"
        confidence = 0.54
        rationale = [
            f"{ticker} ADR premium is {premium:.2f}%, but the RSI state is marked overbought.",
            "The momentum trigger is present, yet the setup should wait for heat to cool before acting.",
        ]
    else:
        status = "PASS"
        confidence = 0.5
        rationale = [
            f"{ticker} ADR premium is {premium:.2f}%, below the 5% light-track momentum trigger.",
            f"The trigger is not strong enough for a BUY signal from this quick read: {trigger_description}.",
        ]

    thesis_alignment = _check_thesis_alignment(ticker, status)

    return LightVerdict(
        ticker=ticker,
        status=status,
        rationale=rationale,
        confidence=confidence,
        expires_at=expires_at,
        signals={
            "adr_premium_pct": premium,
            "local_px": float(local_px),
            "rsi_state": rsi_state,
            "trigger_description": trigger_description,
            "thesis_alignment": thesis_alignment,
        },
        disclaimer="Research automation output only; not investment advice or trade execution.",
    )


def run_quick_decision(
    ticker: str | None = None,
    adr_premium_pct: float | None = None,
    local_px: float | None = None,
    trigger_description: str | None = None,
    rsi_state: RsiState = "neutral",
    adr_px: float | None = None,
    fx_rate: float | None = None,
    adr_ratio: float | None = None,
    output_path: Path = QUICK_DECISION_PATH,
    prompt: bool = True,
) -> dict[str, Any]:
    ticker = _value_or_prompt("ticker", ticker, prompt).upper()
    trigger_description = _value_or_prompt("trigger_description", trigger_description, prompt)

    signals: dict[str, Any] = {}
    if adr_premium_pct is None and adr_px is not None and fx_rate is not None:
        # Manual prices provided — calculate directly
        ratio = adr_ratio if adr_ratio is not None else _registry_adr_ratio(ticker)
        premium = calculate_adr_premium(local_px, adr_px, fx_rate, ratio)
        adr_premium_pct = float(premium["premium_pct"])
        signals.update(
            {
                "adr_px": float(adr_px),
                "fx_rate": float(fx_rate),
                "adr_ratio": float(ratio),
                "drift_direction": premium["drift_direction"],
                "fx_wind": premium["fx_wind"],
            }
        )
    elif adr_premium_pct is None:
        # Auto-fetch live prices via yfinance
        try:
            from .adr_premium import fetch_live_adr_signal
            reg = _registry_entry(ticker)
            live = fetch_live_adr_signal(
                local_symbol=reg.get("yahoo_symbol", ticker),
                adr_symbol=reg.get("adr_symbol", ""),
                fx_symbol="TWD=X",
                adr_ratio=float(reg.get("adr_ratio", 1.0)),
            )
            adr_premium_pct = float(live["premium_pct"])
            local_px = local_px or float(live["local_px"])
            signals.update({k: live[k] for k in ("adr_px", "fx_rate", "adr_ratio", "drift_direction", "fx_wind", "local_px") if k in live})
        except Exception as exc:
            if not prompt:
                raise RuntimeError(f"Auto-fetch failed and no manual input provided: {exc}") from exc
            # Fall through to prompt
            adr_premium_pct = None

    if adr_premium_pct is None:
        adr_premium_pct = _float_or_prompt("adr_premium_pct", None, prompt)
    if local_px is None:
        local_px = _float_or_prompt("local_px", None, prompt)
    verdict = build_light_verdict(
        ticker=ticker,
        adr_premium_pct=adr_premium_pct,
        local_px=local_px,
        trigger_description=trigger_description,
        rsi_state=rsi_state,
    )
    payload = verdict.to_dict()
    payload["signals"].update(signals)

    write_json(output_path, payload)
    return payload


def _registry_entry(ticker: str) -> dict:
    registry = read_json(SOURCE_REGISTRY_PATH, default={"tickers": []})
    for row in registry.get("tickers", []):
        if row.get("ticker", "").upper() == ticker.upper():
            return row
    return {}


def _registry_adr_ratio(ticker: str) -> float:
    return float(_registry_entry(ticker).get("adr_ratio", 1.0))


def _check_thesis_alignment(ticker: str, status: VerdictStatus) -> str:
    state = read_json(RESEARCH_ROOT / ticker / "state.json", default={}) or {}
    current_action = str(state.get("current_action", "")).lower()

    if status != "BUY":
        return "neutral"
    if any(keyword in current_action for keyword in ("exit", "trim")):
        return "contradicts"
    if any(keyword in current_action for keyword in ("watch", "hold")):
        return "consistent"
    return "neutral"


def _value_or_prompt(field: str, value: str | None, prompt: bool) -> str:
    if value:
        return value.strip()
    if not prompt:
        raise ValueError(f"{field} is required")
    try:
        entered = input(f"{field}: ").strip()
    except EOFError as exc:
        raise ValueError(f"{field} is required") from exc
    if not entered:
        raise ValueError(f"{field} is required")
    return entered


def _float_or_prompt(field: str, value: float | None, prompt: bool) -> float:
    if value is not None:
        numeric = float(value)
    else:
        numeric = float(_value_or_prompt(field, None, prompt))
    if numeric <= 0 and field != "adr_premium_pct":
        raise ValueError(f"{field} must be positive")
    return numeric


def _normalize_rsi_state(rsi_state: str) -> RsiState:
    normalized = rsi_state.lower().strip()
    if normalized not in {"neutral", "overbought", "oversold"}:
        raise ValueError("rsi_state must be neutral, overbought, or oversold")
    return normalized  # type: ignore[return-value]
