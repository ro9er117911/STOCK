from __future__ import annotations

from datetime import datetime, timezone

from stock_research import quick_decision
from stock_research.quick_decision import build_light_verdict, run_quick_decision
from stock_research.storage import read_json, write_json


def test_build_light_verdict_waits_on_wide_neutral_premium() -> None:
    verdict = build_light_verdict(
        ticker="2330",
        adr_premium_pct=8.5,
        local_px=950,
        trigger_description="US AI surged and TSM ADR premium widened",
        rsi_state="neutral",
        now=datetime(2026, 4, 20, tzinfo=timezone.utc),
    )

    assert verdict.status == "WAIT"
    assert verdict.confidence == 0.62
    assert len(verdict.rationale) == 2
    assert verdict.signals["adr_premium_pct"] == 8.5
    assert verdict.signals["thesis_alignment"] == "neutral"


def test_build_light_verdict_marks_buy_consistent_with_watch_thesis(tmp_path, monkeypatch) -> None:
    research_root = tmp_path / "research"
    write_json(
        research_root / "2330" / "state.json",
        {"current_action": "Watch — gather Q1 earnings evidence before entry"},
    )
    monkeypatch.setattr(quick_decision, "RESEARCH_ROOT", research_root)

    verdict = build_light_verdict(
        ticker="2330",
        adr_premium_pct=6.2,
        local_px=950,
        trigger_description="US AI surged",
        now=datetime(2026, 4, 20, tzinfo=timezone.utc),
    )

    assert verdict.status == "BUY"
    assert verdict.signals["thesis_alignment"] == "consistent"


def test_build_light_verdict_marks_buy_contradicting_exit_thesis(tmp_path, monkeypatch) -> None:
    research_root = tmp_path / "research"
    write_json(
        research_root / "2330" / "state.json",
        {"current_action": "Exit if gross margin breaks below threshold"},
    )
    monkeypatch.setattr(quick_decision, "RESEARCH_ROOT", research_root)

    verdict = build_light_verdict(
        ticker="2330",
        adr_premium_pct=6.2,
        local_px=950,
        trigger_description="US AI surged",
        now=datetime(2026, 4, 20, tzinfo=timezone.utc),
    )

    assert verdict.status == "BUY"
    assert verdict.signals["thesis_alignment"] == "contradicts"


def test_run_quick_decision_writes_only_requested_output(tmp_path) -> None:
    output_path = tmp_path / "quick-decision.json"

    payload = run_quick_decision(
        ticker="2330",
        adr_premium_pct=6.2,
        local_px=950,
        trigger_description="US AI surged",
        output_path=output_path,
        prompt=False,
    )

    assert payload["status"] == "BUY"
    assert read_json(output_path)["ticker"] == "2330"
    assert not (tmp_path / "research" / "2330" / "state.json").exists()


def test_run_quick_decision_can_calculate_manual_adr_input(tmp_path) -> None:
    output_path = tmp_path / "quick-decision.json"

    payload = run_quick_decision(
        ticker="2330",
        local_px=100,
        adr_px=3.5,
        fx_rate=32,
        adr_ratio=1,
        trigger_description="ADR premium widened",
        output_path=output_path,
        prompt=False,
    )

    assert payload["status"] == "WAIT"
    assert payload["signals"]["adr_premium_pct"] == 12.0
    assert payload["signals"]["drift_direction"] == "lagging"
