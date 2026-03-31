from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .markdown import render_current_report, render_review_summary
from .storage import read_json, read_jsonl, write_json


RESEARCH_STAGES = (
    "candidate",
    "in_research",
    "ready_to_decide",
    "active",
    "rejected",
    "archived",
)

STAGE_TO_DECISION_STATUS = {
    "candidate": "pending",
    "in_research": "needs_more_research",
    "ready_to_decide": "ready_to_decide",
    "active": "active",
    "rejected": "rejected",
    "archived": "archived",
}

ORIGIN_ALIASES = {
    "manual": "manual_watchlist",
    "watchlist": "manual_watchlist",
    "manual_watchlist": "manual_watchlist",
    "idea": "ad_hoc_idea",
    "ad_hoc": "ad_hoc_idea",
    "ad_hoc_idea": "ad_hoc_idea",
    "quant": "quant_radar",
    "radar_scan": "quant_radar",
    "quant_radar": "quant_radar",
    "observation": "observation_lake",
    "observation_lake": "observation_lake",
}


def canonical_candidate_origin(value: str | None, *, default: str = "manual_watchlist") -> str:
    if not value:
        return default
    return ORIGIN_ALIASES.get(str(value).strip().lower(), str(value).strip())


def _today() -> str:
    return date.today().isoformat()


def _stage_is_valid(value: str | None) -> bool:
    return bool(value) and value in RESEARCH_STAGES


def _decision_status_for_stage(stage: str) -> str:
    return STAGE_TO_DECISION_STATUS.get(stage, "pending")


def infer_research_stage(state: dict[str, Any]) -> str:
    explicit = state.get("research_stage")
    if _stage_is_valid(explicit):
        return explicit

    current_action = str(state.get("current_action", "") or "").lower()
    if "reject" in current_action or "不買" in current_action or "放棄" in current_action:
        return "rejected"
    if "archive" in current_action or "封存" in current_action:
        return "archived"
    if state.get("assumptions") and state.get("action_rules"):
        return "active"
    if state.get("assumptions"):
        return "ready_to_decide"
    if str(state.get("thesis", {}).get("statement", "")).strip():
        return "in_research"
    return "candidate"


def normalize_state_contract(
    state: dict[str, Any],
    *,
    default_stage: str | None = None,
    default_origin: str = "manual_watchlist",
) -> dict[str, Any]:
    normalized = deepcopy(state)
    stage = default_stage if _stage_is_valid(default_stage) else infer_research_stage(normalized)
    origin = canonical_candidate_origin(normalized.get("candidate_origin"), default=default_origin)
    decision_status = str(normalized.get("decision_status") or "").strip() or _decision_status_for_stage(stage)
    decision_updated_at = str(
        normalized.get("decision_updated_at")
        or normalized.get("last_reviewed_at")
        or normalized.get("next_review_at")
        or _today()
    )

    normalized["research_stage"] = stage
    normalized["candidate_origin"] = origin
    normalized["decision_status"] = decision_status
    normalized["decision_updated_at"] = decision_updated_at
    normalized["radar_flags"] = [str(item) for item in normalized.get("radar_flags", []) if str(item).strip()]
    normalized["radar_summary"] = str(
        normalized.get("radar_summary")
        or "No radar flags logged yet; use this field for pre-research prioritization only."
    )
    normalized["radar_risk_level"] = str(normalized.get("radar_risk_level") or "none")
    normalized["outcome_markers"] = list(normalized.get("outcome_markers", []))
    normalized["thesis_change_log"] = list(normalized.get("thesis_change_log", []))
    normalized["invalidation_reason"] = str(normalized.get("invalidation_reason") or "")
    normalized["consistency_notes"] = list(normalized.get("consistency_notes", []))

    if not normalized["thesis_change_log"]:
        normalized["thesis_change_log"].append(
            {
                "changed_at": str(normalized.get("last_reviewed_at") or _today()),
                "change_type": "baseline",
                "research_stage": stage,
                "decision_status": decision_status,
                "current_action": str(normalized.get("current_action", "")),
                "confidence": round(float(normalized.get("confidence", 0.0) or 0.0), 2),
                "summary": "Established the living research state under the vNext decision workflow contract.",
            }
        )

    return normalized


def default_candidate_state(
    *,
    ticker: str,
    company_name: str,
    research_topic: str,
    candidate_origin: str,
    research_stage: str = "candidate",
    radar_flags: list[str] | None = None,
    radar_summary: str = "",
    radar_risk_level: str = "none",
    note: str = "",
) -> dict[str, Any]:
    today = _today()
    stage = research_stage if _stage_is_valid(research_stage) else "candidate"
    default_note = note or "Candidate added to the research queue for pre-entry thesis work."
    state = {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "research_topic": research_topic,
        "research_type": "候選研究 / 進場前",
        "holding_period": "待定義",
        "last_reviewed_at": today,
        "next_review_at": (date.today() + timedelta(days=14)).isoformat(),
        "current_action": "No decision yet; gather evidence and build a falsifiable thesis.",
        "confidence": 0.0,
        "latest_delta": [default_note],
        "primary_observation_variables": [],
        "secondary_observation_variables": [],
        "noise_filters": [
            "Single-session price moves without thesis evidence",
            "Headline-only narrative spikes without primary-source confirmation",
        ],
        "thresholds": {
            "price_gap_pct": 8.0,
            "volume_ratio": 2.0,
            "deep_refresh_days": 14,
            "material_sec_forms": ["8-K", "10-Q", "10-K"],
            "earnings_keywords": ["earnings", "results", "guidance", "quarter", "outlook"],
            "positive_keywords": ["record", "raises", "expands", "beats", "wins"],
            "negative_keywords": ["cuts", "miss", "delay", "probe", "lawsuit"],
        },
        "thesis": {
            "thesis_id": f"{ticker.lower()}-thesis-core",
            "statement": "Research in progress. The thesis is not decision-ready yet.",
            "core_catalyst": "Define the catalyst that would close the market-expectation gap.",
            "market_blind_spot": "State the specific change the market may be underpricing.",
            "verification_date": (date.today() + timedelta(days=30)).isoformat(),
            "expiry_condition": "Reject the candidate if the core thesis cannot be verified or falsified with primary sources.",
        },
        "assumptions": [],
        "risks": [],
        "valuation_regime": {
            "current_yardstick": "Not assessed yet.",
            "better_yardstick": "Define during research.",
            "switch_trigger": "Define during research.",
            "re_rating_logic": "Define during research.",
            "associated_risk": "Incomplete regime analysis can create false conviction.",
        },
        "scenarios": [],
        "action_rules": [],
        "next_must_check_data": "Define the must-check data before promoting this candidate to ready_to_decide.",
        "research_debt": [
            "Write the first falsifiable thesis sentence.",
            "Add at least three core assumptions and three risks.",
            "Define explicit buy, defer, and reject conditions.",
        ],
        "source_manifest": [],
        "last_seen_event_cursors": {},
        "version_log": [
            {
                "version": "v0",
                "date": today,
                "reason": "Candidate research dossier created.",
                "impact": default_note,
            }
        ],
        "seed_events": [],
        "radar_flags": radar_flags or [],
        "radar_summary": radar_summary or "No radar flags logged yet; this candidate entered manually.",
        "radar_risk_level": radar_risk_level,
        "outcome_markers": [],
        "thesis_change_log": [],
        "invalidation_reason": "",
        "consistency_notes": [],
        "candidate_origin": candidate_origin,
        "research_stage": stage,
        "decision_status": _decision_status_for_stage(stage),
        "decision_updated_at": today,
    }
    return normalize_state_contract(state, default_stage=stage, default_origin=candidate_origin)


def append_state_change_entry(
    previous_state: dict[str, Any] | None,
    updated_state: dict[str, Any],
    *,
    summary: str,
    change_type: str,
    changed_at: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_state_contract(updated_state)
    when = changed_at or normalized.get("decision_updated_at") or normalized.get("last_reviewed_at") or _today()
    previous_log = list((previous_state or {}).get("thesis_change_log", normalized.get("thesis_change_log", [])))
    if previous_state is None:
        previous_log = []
    entry = {
        "changed_at": when,
        "change_type": change_type,
        "research_stage": normalized["research_stage"],
        "decision_status": normalized["decision_status"],
        "current_action": normalized.get("current_action", ""),
        "confidence": round(float(normalized.get("confidence", 0.0) or 0.0), 2),
        "summary": summary.strip(),
    }
    if previous_log and previous_log[-1] == entry:
        normalized["thesis_change_log"] = previous_log
        return normalized
    previous_log.append(entry)
    normalized["thesis_change_log"] = previous_log
    return normalized


def record_outcome_marker(
    state: dict[str, Any],
    *,
    kind: str,
    summary: str,
    marked_at: str | None = None,
    affected_assumption_ids: list[str] | None = None,
) -> dict[str, Any]:
    normalized = normalize_state_contract(state)
    marker = {
        "marked_at": marked_at or normalized.get("last_reviewed_at") or _today(),
        "kind": kind,
        "summary": summary,
        "affected_assumption_ids": sorted(set(affected_assumption_ids or [])),
    }
    markers = list(normalized.get("outcome_markers", []))
    if not markers or markers[-1] != marker:
        markers.append(marker)
    normalized["outcome_markers"] = markers
    return normalized


def candidate_entry_from_state(state: dict[str, Any], research_root: Path) -> dict[str, Any]:
    normalized = normalize_state_contract(state)
    ticker = normalized["ticker"]
    ticker_dir = research_root / ticker
    latest_change = normalized["thesis_change_log"][-1] if normalized.get("thesis_change_log") else {}
    return {
        "ticker": ticker,
        "company_name": normalized.get("company_name", ""),
        "research_stage": normalized["research_stage"],
        "candidate_origin": normalized["candidate_origin"],
        "decision_status": normalized["decision_status"],
        "decision_updated_at": normalized["decision_updated_at"],
        "current_action": normalized.get("current_action", ""),
        "research_topic": normalized.get("research_topic", ""),
        "radar_flags": normalized.get("radar_flags", []),
        "radar_summary": normalized.get("radar_summary", ""),
        "radar_risk_level": normalized.get("radar_risk_level", "none"),
        "invalidation_reason": normalized.get("invalidation_reason", ""),
        "latest_change": latest_change,
        "artifacts": {
            "state_path": str(ticker_dir / "state.json"),
            "current_path": str(ticker_dir / "current.md"),
        },
    }


def sync_candidate_queue(research_root: Path) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for state_path in sorted(research_root.glob("*/state.json")):
        state = read_json(state_path)
        if state is None:
            continue
        candidates.append(candidate_entry_from_state(state, research_root))

    payload = {
        "generated_at": _today(),
        "items": sorted(
            candidates,
            key=lambda item: (item["research_stage"], item["decision_updated_at"], item["ticker"]),
        ),
    }
    write_json(research_root / "system" / "candidates.json", payload)
    return payload


def rewrite_research_artifacts(research_root: Path, ticker: str, state: dict[str, Any]) -> None:
    normalized = normalize_state_contract(state)
    ticker_dir = research_root / ticker
    ticker_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = ticker_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    recent_events = list(reversed(read_jsonl(ticker_dir / "events.jsonl")[-8:]))
    write_json(ticker_dir / "state.json", normalized)
    (ticker_dir / "current.md").write_text(render_current_report(normalized, recent_events), encoding="utf-8")
    if (ticker_dir / "current.zh-tw.md").exists():
        (ticker_dir / "current.zh-tw.md").write_text(
            render_current_report(normalized, recent_events),
            encoding="utf-8",
        )

    review_summary_payload = read_json(artifacts_dir / "review_summary.json", default={})
    if review_summary_payload:
        review_summary_markdown = render_review_summary(
            normalized,
            review_summary_payload.get("review_summary", ""),
            review_summary_payload.get("changed_assumptions", []),
            review_summary_payload.get("action_rule_delta", []),
        )
        (artifacts_dir / "review_summary.md").write_text(review_summary_markdown, encoding="utf-8")
        if (artifacts_dir / "review_summary.zh-tw.md").exists():
            (artifacts_dir / "review_summary.zh-tw.md").write_text(review_summary_markdown, encoding="utf-8")
