from __future__ import annotations

from pathlib import Path
from typing import Any

from .storage import read_json


def generate_post_mortem_report(research_root: Path) -> dict[str, Any]:
    """
    Generates analytics reviewing past outcome markers and thesis changes
    to identify the user's decision quality (hit rate, regime drift recognition, etc).
    """
    report = {
        "total_tickers_analyzed": 0,
        "assumptions_resolved": 0,
        "assumptions_correct": 0,
        "hit_rate_pct": 0.0,
        "thesis_changes": 0,
        "regime_drift_events": 0,
        "expectation_gap_events": 0,
        "ticker_breakdown": {},
    }

    for state_path in sorted(research_root.glob("*/state.json")):
        if state_path.parent.name == "system":
            continue

        state = read_json(state_path)
        if not state:
            continue

        ticker = state.get("ticker", state_path.parent.name)
        report["total_tickers_analyzed"] += 1

        ticker_stats = {
            "outcomes_resolved": 0,
            "outcomes_correct": 0,
            "thesis_changes": len(state.get("thesis_change_log", [])),
            "regime_drifts": 0,
            "expectation_gaps": 0,
        }

        markers = state.get("outcome_markers", [])
        for marker in markers:
            if marker.get("resolution") in ("validated", "invalidated"):
                ticker_stats["outcomes_resolved"] += 1
                report["assumptions_resolved"] += 1
                if marker.get("resolution") == "validated":
                    ticker_stats["outcomes_correct"] += 1
                    report["assumptions_correct"] += 1

                # We roughly identify structural changes through notes referencing specific concepts
                note = (marker.get("actual_outcome") or "").lower()
                if "regime" in note or "drift" in note or "yardstick" in note:
                    ticker_stats["regime_drifts"] += 1
                    report["regime_drift_events"] += 1
                if "gap" in note or "priced" in note:
                    ticker_stats["expectation_gaps"] += 1
                    report["expectation_gap_events"] += 1

        
        changes = state.get("thesis_change_log", [])
        report["thesis_changes"] += len(changes)
        for change in changes:
            reason = (change.get("reason") or "").lower()
            if "regime" in reason or "drift" in reason or "yardstick" in reason:
                ticker_stats["regime_drifts"] += 1
                report["regime_drift_events"] += 1
            if "gap" in reason or "priced" in reason:
                ticker_stats["expectation_gaps"] += 1
                report["expectation_gap_events"] += 1

        report["ticker_breakdown"][ticker] = ticker_stats

    if report["assumptions_resolved"] > 0:
        report["hit_rate_pct"] = round(
            (report["assumptions_correct"] / report["assumptions_resolved"]) * 100.0, 2
        )

    return report
