from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .research_state import (
    append_state_change_entry,
    canonical_candidate_origin,
    default_candidate_state,
    normalize_state_contract,
    rewrite_research_artifacts,
    STAGE_TO_DECISION_STATUS,
    sync_candidate_queue,
)
from .storage import read_json, write_json, write_jsonl


def upsert_candidate_dossier(
    research_root: Path,
    *,
    ticker: str,
    company_name: str,
    research_topic: str,
    candidate_origin: str,
    research_stage: str,
    radar_flags: list[str] | None = None,
    radar_summary: str = "",
    radar_risk_level: str = "none",
    note: str = "",
    current_action: str | None = None,
    invalidation_reason: str | None = None,
    decision_status: str | None = None,
) -> dict[str, Any]:
    normalized_origin = canonical_candidate_origin(candidate_origin)
    ticker = ticker.upper()
    ticker_dir = research_root / ticker
    state_path = ticker_dir / "state.json"
    existing_state = read_json(state_path)
    today = date.today().isoformat()

    if existing_state is None:
        state = default_candidate_state(
            ticker=ticker,
            company_name=company_name,
            research_topic=research_topic,
            candidate_origin=normalized_origin,
            research_stage=research_stage,
            radar_flags=radar_flags,
            radar_summary=radar_summary,
            radar_risk_level=radar_risk_level,
            note=note,
        )
        ticker_dir.mkdir(parents=True, exist_ok=True)
        if not (ticker_dir / "events.jsonl").exists():
            write_jsonl(ticker_dir / "events.jsonl", [])
        write_json(
            ticker_dir / "artifacts" / "review_summary.json",
            {
                "ticker": ticker,
                "reviewed_at": today,
                "review_summary": note or "Candidate dossier created for pre-entry research.",
                "changed_assumptions": [],
                "action_rule_delta": [],
            },
        )
        change_summary = note or "Candidate dossier created."
        previous_state: dict[str, Any] | None = None
    else:
        previous_state = normalize_state_contract(existing_state)
        state = normalize_state_contract(previous_state)
        state["company_name"] = company_name or state.get("company_name", ticker)
        state["research_topic"] = research_topic or state.get("research_topic", "")
        state["candidate_origin"] = normalized_origin
        state["research_stage"] = research_stage
        if radar_flags is not None:
            state["radar_flags"] = radar_flags
        if radar_summary:
            state["radar_summary"] = radar_summary
        if radar_risk_level:
            state["radar_risk_level"] = radar_risk_level
        change_summary = note or f"Candidate dossier updated to {research_stage}."

    if current_action:
        state["current_action"] = current_action
    if invalidation_reason is not None:
        state["invalidation_reason"] = invalidation_reason
    state["decision_status"] = decision_status or STAGE_TO_DECISION_STATUS.get(research_stage, state.get("decision_status", "pending"))
    state["decision_updated_at"] = today
    state["last_reviewed_at"] = today
    if note:
        state["latest_delta"] = [note]
    state = normalize_state_contract(state, default_stage=research_stage, default_origin=normalized_origin)
    state = append_state_change_entry(
        previous_state,
        state,
        summary=change_summary,
        change_type="candidate_stage_update",
        changed_at=today,
    )
    rewrite_research_artifacts(research_root, ticker, state)
    queue = sync_candidate_queue(research_root)
    return {
        "ticker": ticker,
        "research_stage": state["research_stage"],
        "decision_status": state["decision_status"],
        "queue_size": len(queue["items"]),
        "state_path": str(state_path),
        "current_path": str(ticker_dir / "current.md"),
    }
