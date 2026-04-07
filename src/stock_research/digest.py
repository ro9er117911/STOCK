from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import (
    CANONICAL_DIGEST_PATH,
    COCKPIT_API_HOST,
    COCKPIT_API_PORT,
    DIGEST_FILENAME,
    NOTIFICATION_PAYLOAD_PATH,
    PORTFOLIO_PRIVATE_PATH,
    REPO_ROOT,
    SOURCE_STATUS_FILENAME,
    WATCHLIST,
)
from .copy import (
    compute_priority,
    compose_summary_blurb,
    format_currency,
    format_percent,
    localize_decision,
    localize_risk_level,
    localize_risk_tier,
    localize_source_status,
    localize_status,
    localize_text,
    public_url,
    split_checklist,
    thesis_health_snapshot,
)
from .observation import build_observation_workspace, observation_context_for_ticker
from .portfolio import load_private_portfolio
from .research_state import normalize_state_contract
from .risk import (
    build_macro_regime,
    build_portfolio_totals,
    empty_portfolio_totals,
    evaluate_position_snapshot,
    fetch_market_snapshot,
    finalize_position_weights,
    load_risk_policy,
    project_maturity_snapshot,
)
from .storage import read_json, read_jsonl, write_json
from .analytics import generate_post_mortem_report

def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _load_review_summary(ticker_dir: Path) -> dict[str, Any]:
    return read_json(ticker_dir / "artifacts" / "review_summary.json", default={})


def _load_source_status(ticker_dir: Path, ticker: str) -> list[dict[str, Any]]:
    payload = read_json(ticker_dir / "artifacts" / SOURCE_STATUS_FILENAME, default={})
    sources = payload.get("sources")
    if sources:
        return sources
    if ticker not in WATCHLIST:
        return []
    config = WATCHLIST[ticker]
    return [
        {
            "source_id": source.source_id,
            "source_type": source.source_type,
            "kind": source.kind,
            "url": source.url,
            "status": source.status,
            "priority": source.priority,
            "new_events": 0,
            "cursor": "",
            "error": "",
            "notes": source.notes,
        }
        for source in config.sources
    ]


def _status_label(state: dict[str, Any]) -> str:
    stage = state.get("research_stage")
    if stage == "candidate":
        return "候選觀察"
    if stage == "in_research":
        return "研究進行中"
    if stage == "ready_to_decide":
        return "待決策"
    if stage == "rejected":
        return "已拒絕"
    if stage == "archived":
        return "已封存"
    action = state["current_action"]
    confidence = state["confidence"]
    lowered = action.lower()
    if "exit" in lowered or "退出" in action:
        return "需要退出"
    if "trim" in lowered or "減碼" in action:
        return "保守應對"
    if "add" in lowered or "加碼" in action or "偏多" in action:
        return "偏多"
    if confidence >= 0.7:
        return "穩定持有"
    return "持有觀察"


def _confidence_delta(review_summary: dict[str, Any]) -> float:
    raw = review_summary.get("confidence_delta", 0.0)
    try:
        return round(float(raw or 0.0), 2)
    except (TypeError, ValueError):
        return 0.0


def _logical_paths(ticker: str) -> dict[str, str]:
    return {
        "detail_path": f"tickers/{ticker}.html",
        "research_path": f"research/{ticker}.html",
    }


def _position_placeholder(ticker: str) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "has_position": False,
        "shares": 0.0,
        "avg_cost": 0.0,
        "target_weight_pct": 0.0,
        "max_weight_pct": 0.0,
        "risk_level": "",
        "risk_level_label": "尚未設定",
        "notes": "",
        "summary": "尚未填入部位",
        "shares_label": "尚未填入",
        "avg_cost_label": "未填成本",
        "target_weight_label": "未填目標倉位",
        "max_weight_label": "未填上限倉位",
        "cost_basis": None,
        "cost_basis_label": "Private only",
        "current_price": None,
        "current_price_label": "N/A",
        "market_value": None,
        "market_value_label": "Private only",
        "unrealized_pnl": None,
        "unrealized_pnl_label": "Private only",
        "unrealized_pnl_pct": None,
        "unrealized_pnl_pct_label": "Private only",
        "portfolio_weight_pct": None,
        "portfolio_weight_label": "Private only",
        "adjusted_target_weight_pct": None,
        "adjusted_target_weight_label": "Private only",
        "adjusted_max_weight_pct": None,
        "adjusted_max_weight_label": "Private only",
        "distance_to_target_pct": None,
        "distance_to_target_label": "Private only",
        "distance_to_max_pct": None,
        "distance_to_max_label": "Private only",
        "sizing_status": {
            "state": "private-only",
            "label": "Private only",
            "summary": "需要本機 private portfolio 才會顯示 sizing 狀態。",
        },
        "risk_alerts": [],
        "risk_alert_count": 0,
        "recommended_next_action": "需要本機 private portfolio 才會顯示風控建議。",
        "market_data_as_of": "",
    }


def _position_snapshot(ticker: str, position: dict[str, Any] | None) -> dict[str, Any]:
    if not position:
        return _position_placeholder(ticker)
    shares = float(position.get("shares", 0) or 0)
    avg_cost = float(position.get("avg_cost", 0) or 0)
    target_weight_pct = float(position.get("target_weight_pct", 0) or 0)
    max_weight_pct = float(position.get("max_weight_pct", 0) or 0)
    risk_level = str(position.get("risk_level", "") or "")
    return {
        "ticker": ticker,
        "has_position": shares > 0 or avg_cost > 0 or target_weight_pct > 0 or max_weight_pct > 0,
        "shares": shares,
        "avg_cost": avg_cost,
        "target_weight_pct": target_weight_pct,
        "max_weight_pct": max_weight_pct,
        "risk_level": risk_level,
        "risk_level_label": localize_risk_level(risk_level),
        "notes": position.get("notes", ""),
        "summary": f"{shares:g} 股 @ {format_currency(avg_cost)}" if shares > 0 else "尚未填入部位",
        "shares_label": f"{shares:g} 股" if shares > 0 else "尚未填入",
        "avg_cost_label": format_currency(avg_cost) if avg_cost > 0 else "未填成本",
        "target_weight_label": format_percent(target_weight_pct) if target_weight_pct > 0 else "未填目標倉位",
        "max_weight_label": format_percent(max_weight_pct) if max_weight_pct > 0 else "未填上限倉位",
        "cost_basis": round(shares * avg_cost, 2) if shares > 0 and avg_cost > 0 else None,
        "cost_basis_label": format_currency(shares * avg_cost) if shares > 0 and avg_cost > 0 else "Private only",
        "current_price": None,
        "current_price_label": "N/A",
        "market_value": None,
        "market_value_label": "Private only",
        "unrealized_pnl": None,
        "unrealized_pnl_label": "Private only",
        "unrealized_pnl_pct": None,
        "unrealized_pnl_pct_label": "Private only",
        "portfolio_weight_pct": None,
        "portfolio_weight_label": "Private only",
        "adjusted_target_weight_pct": None,
        "adjusted_target_weight_label": "Private only",
        "adjusted_max_weight_pct": None,
        "adjusted_max_weight_label": "Private only",
        "distance_to_target_pct": None,
        "distance_to_target_label": "Private only",
        "distance_to_max_pct": None,
        "distance_to_max_label": "Private only",
        "sizing_status": {
            "state": "private-only",
            "label": "Private only",
            "summary": "需要本機 private portfolio 才會顯示 sizing 狀態。",
        },
        "risk_alerts": [],
        "risk_alert_count": 0,
        "recommended_next_action": "需要本機 private portfolio 才會顯示風控建議。",
        "market_data_as_of": "",
    }


def _localize_changed_items(items: list[dict[str, Any]], *, key_name: str) -> list[dict[str, Any]]:
    localized: list[dict[str, Any]] = []
    for item in items:
        localized.append(
            {
                **item,
                "summary": localize_text(item.get("summary", "")),
                key_name: item.get(key_name, ""),
            }
        )
    return localized


def _build_source_status_items(source_status: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for source in source_status:
        items.append(
            {
                **source,
                "status_label": localize_source_status(source.get("status", "")),
                "notes": localize_text(source.get("notes", "")),
                "is_clickable": public_url(source.get("url", "")),
            }
        )
    return items


def _build_citations(
    ticker: str,
    state: dict[str, Any],
    events: list[dict[str, Any]],
    source_status: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    paths = _logical_paths(ticker)
    citations: list[dict[str, Any]] = [
        {
            "citation_id": f"{ticker.lower()}-research-page",
            "kind": "internal",
            "label": "研究內頁",
            "href": paths["research_path"],
            "source_type": localize_text("research page"),
            "is_clickable": True,
            "occurred_at": state["last_reviewed_at"],
        },
        {
            "citation_id": f"{ticker.lower()}-review-summary",
            "kind": "internal",
            "label": "本輪更新摘要",
            "href": f"{paths['research_path']}#review-summary",
            "source_type": localize_text("review summary"),
            "is_clickable": True,
            "occurred_at": state["last_reviewed_at"],
        },
    ]

    for source in state.get("source_manifest", []):
        url = source.get("url", "")
        if not public_url(url):
            continue
        citations.append(
            {
                "citation_id": f"{ticker.lower()}-manifest-{source['source_id']}",
                "kind": "external",
                "label": localize_text(source.get("label", source["source_id"])),
                "href": url,
                "source_type": localize_text(source.get("type", source["source_id"])),
                "is_clickable": True,
                "occurred_at": state["last_reviewed_at"],
            }
        )

    for event in events[:8]:
        source_url = event.get("source_url", "")
        if public_url(source_url):
            citations.append(
                {
                    "citation_id": event["event_id"],
                    "kind": "external",
                    "label": event["title"],
                    "href": source_url,
                    "source_type": localize_text(event["source_type"].replace("_", " ")),
                    "is_clickable": True,
                    "occurred_at": event["occurred_at"],
                }
            )
        else:
            citations.append(
                {
                    "citation_id": f"{event['event_id']}-internal",
                    "kind": "internal",
                    "label": f"內部研究節點：{Path(source_url).name or 'seed note'}",
                    "href": f"{paths['research_path']}#event-timeline",
                    "source_type": localize_text("research note"),
                    "is_clickable": True,
                    "occurred_at": event["occurred_at"],
                }
            )

    for source in source_status:
        url = source.get("url", "")
        if not public_url(url):
            continue
        citations.append(
            {
                "citation_id": f"{ticker.lower()}-source-{source['source_id']}",
                "kind": "external",
                "label": localize_text(source.get("notes", source["source_id"])),
                "href": url,
                "source_type": localize_text(source.get("source_type", source["source_id"]).replace("_", " ")),
                "is_clickable": True,
                "occurred_at": state["last_reviewed_at"],
            }
        )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in citations:
        key = (item["kind"], item["label"], item["href"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _build_event_timeline(events: list[dict[str, Any]], ticker: str) -> list[dict[str, Any]]:
    logical_paths = _logical_paths(ticker)
    timeline: list[dict[str, Any]] = []
    for event in events[:8]:
        source_url = event.get("source_url", "")
        is_public = public_url(source_url)
        timeline.append(
            {
                "event_id": event["event_id"],
                "occurred_at": event["occurred_at"],
                "source_type": event["source_type"],
                "source_label": localize_text(event["source_type"].replace("_", " ")),
                "title": event["title"],
                "impact": event["marginal_impact"],
                "impact_label": {
                    "+": "偏正向",
                    "0": "中性",
                    "-": "偏負向",
                }.get(event.get("marginal_impact", "0"), "中性"),
                "decision": event["decision"],
                "decision_label": localize_decision(event["decision"]),
                "link_kind": "external" if is_public else "internal",
                "link_label": "原始公告" if is_public else "內部研究節點",
                "href": source_url if is_public else f"{logical_paths['research_path']}#event-timeline",
                "is_clickable": True,
                "metadata": event.get("metadata", {}),
            }
        )
    return timeline


def _build_recent_progress(
    summary: dict[str, Any],
    analytics: dict[str, Any],
    project_maturity: list[dict[str, Any]],
) -> list[dict[str, str]]:
    complete_count = sum(1 for item in project_maturity if item["status"] == "complete")
    return [
        {
            "label": "Tracked names",
            "value": str(summary["tracked_ticker_count"]),
            "detail": "Living dossiers currently covered by the research OS.",
        },
        {
            "label": "Pending events",
            "value": str(summary["pending_event_count"]),
            "detail": "Recent watch / refresh items already flowing through the digest.",
        },
        {
            "label": "Due this week",
            "value": str(summary["review_due_count"]),
            "detail": "Names that need near-term review attention.",
        },
        {
            "label": "Post-mortem",
            "value": f"{analytics['hit_rate_pct']}%",
            "detail": "Current assumption hit rate from the existing post-mortem layer.",
        },
        {
            "label": "Complete modules",
            "value": str(complete_count),
            "detail": "Institutional-capability map showing what is finished versus missing.",
        },
    ]


def _build_assumptions(state: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for assumption in state.get("assumptions", []):
        items.append(
            {
                "assumption_id": assumption["assumption_id"],
                "type": localize_text(assumption.get("type", "")),
                "statement": localize_text(assumption["statement"]),
                "status": assumption["status"],
                "status_label": localize_status(assumption["status"]),
                "confidence": round(float(assumption.get("confidence", 0.0) or 0.0), 2),
                "verification_method": localize_text(assumption.get("verification_method", "")),
                "invalidation_condition": localize_text(assumption.get("invalidation_condition", "")),
                "update_frequency": localize_text(assumption.get("update_frequency", "")),
            }
        )
    return items


def _build_action_rules(state: dict[str, Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for rule in state.get("action_rules", []):
        rules.append(
            {
                "action_rule_id": rule["action_rule_id"],
                "kind": rule["kind"],
                "kind_label": {
                    "add": "加碼條件",
                    "trim": "減碼條件",
                    "exit": "退出條件",
                }.get(rule["kind"], localize_text(rule["kind"])),
                "condition": localize_text(rule["condition"]),
                "action": localize_text(rule["action"]),
            }
        )
    return rules


def _build_risks(state: dict[str, Any]) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    for risk in state.get("risks", []):
        risks.append(
            {
                "risk_id": risk["risk_id"],
                "statement": localize_text(risk["statement"]),
                "tier": risk["tier"],
                "tier_label": localize_risk_tier(risk["tier"]),
                "response": localize_text(risk["response"]),
            }
        )
    return risks


def _build_card(
    research_root: Path,
    ticker: str,
    *,
    source_status: list[dict[str, Any]] | None = None,
    position: dict[str, Any] | None = None,
    persist_artifacts: bool = True,
) -> dict[str, Any]:
    ticker_dir = research_root / ticker
    state = read_json(ticker_dir / "state.json")
    if state is None:
        raise FileNotFoundError(f"Missing state for {ticker}")
    state = normalize_state_contract(state)

    review_summary = _load_review_summary(ticker_dir)
    source_status_rows = source_status if source_status is not None else _load_source_status(ticker_dir, ticker)
    recent_events = list(reversed(read_jsonl(ticker_dir / "events.jsonl")[-8:]))
    event_timeline = _build_event_timeline(recent_events, ticker)
    next_checklist = split_checklist(state.get("next_must_check_data", ""))
    summary_blurb = compose_summary_blurb(
        ticker=ticker,
        current_action=state["current_action"],
        changed_assumptions=review_summary.get("changed_assumptions", []),
        event_timeline=event_timeline,
        next_checklist=next_checklist,
    )
    confidence_delta = _confidence_delta(review_summary)
    position_snapshot = _position_snapshot(ticker, position)
    priority = compute_priority(
        current_action=state["current_action"],
        next_review_at=state["next_review_at"],
        risk_level=position_snapshot["risk_level"],
        confidence_delta=confidence_delta,
        event_timeline=event_timeline,
    )
    source_status_items = _build_source_status_items(source_status_rows)
    citations = _build_citations(ticker, state, recent_events, source_status_rows)
    thesis_health = thesis_health_snapshot(state)
    changed_assumptions = _localize_changed_items(review_summary.get("changed_assumptions", []), key_name="assumption_id")
    action_rule_delta = _localize_changed_items(review_summary.get("action_rule_delta", []), key_name="action_rule_id")
    paths = _logical_paths(ticker)

    digest = {
        "ticker": ticker,
        "company_name": state["company_name"],
        "research_stage": state["research_stage"],
        "candidate_origin": state["candidate_origin"],
        "decision_status": state["decision_status"],
        "decision_updated_at": state["decision_updated_at"],
        "status_label": _status_label(state),
        "current_action": state["current_action"],
        "thesis_confidence": round(float(state["confidence"]), 2),
        "confidence_delta": confidence_delta,
        "summary_blurb": summary_blurb,
        "next_review_at": state["next_review_at"],
        "next_must_check_data": localize_text(state["next_must_check_data"]),
        "next_checklist": next_checklist,
        "last_reviewed_at": state["last_reviewed_at"],
        "risk_level": position_snapshot["risk_level"],
        "risk_level_label": position_snapshot["risk_level_label"],
        "priority_score": priority["score"],
        "priority_label": priority["label"],
        "last_event_status": event_timeline[0]["decision_label"] if event_timeline else "例行更新",
        "detail_path": paths["detail_path"],
        "internal_research_path": paths["research_path"],
        "recommended_next_action": state["current_action"],
        "position": position_snapshot,
        "portfolio_position": position_snapshot,
        "key_events": event_timeline[:3],
        "event_timeline": event_timeline,
        "key_action_rules": _build_action_rules(state)[:3],
        "action_rules": _build_action_rules(state),
        "changed_assumptions": changed_assumptions,
        "action_rule_delta": action_rule_delta,
        "radar": {
            "flags": [localize_text(item) for item in state.get("radar_flags", [])],
            "summary": localize_text(state.get("radar_summary", "")),
            "risk_level": state.get("radar_risk_level", "none"),
        },
        "outcome_markers": state.get("outcome_markers", []),
        "thesis_change_log": state.get("thesis_change_log", []),
        "invalidation_reason": localize_text(state.get("invalidation_reason", "")),
        "consistency_notes": [localize_text(item) for item in state.get("consistency_notes", [])],
        "source_status": source_status_items,
        "citations": citations,
        "citation_links": {
            "external": [item for item in citations if item["kind"] == "external"],
            "internal": [item for item in citations if item["kind"] == "internal"],
            "all": citations,
        },
        "assumptions": _build_assumptions(state),
        "risks": _build_risks(state),
        "thesis_health": thesis_health,
        "review_summary": localize_text(review_summary.get("review_summary", "")),
        "research_state": {
            "research_topic": localize_text(state["research_topic"]),
            "holding_period": state["holding_period"],
            "research_stage": state["research_stage"],
            "candidate_origin": state["candidate_origin"],
            "decision_status": state["decision_status"],
            "decision_updated_at": state["decision_updated_at"],
            "thesis_statement": localize_text(state["thesis"]["statement"]),
            "core_catalyst": localize_text(state["thesis"]["core_catalyst"]),
            "market_blind_spot": localize_text(state["thesis"]["market_blind_spot"]),
            "latest_delta": [localize_text(item) for item in state.get("latest_delta", [])],
            "radar_summary": localize_text(state.get("radar_summary", "")),
            "radar_flags": [localize_text(item) for item in state.get("radar_flags", [])],
            "review_summary": localize_text(review_summary.get("review_summary", "")),
            "thesis_health": thesis_health,
            "assumptions": _build_assumptions(state),
            "risks": _build_risks(state),
            "outcome_markers": state.get("outcome_markers", []),
            "thesis_change_log": state.get("thesis_change_log", []),
            "event_timeline": event_timeline,
            "source_manifest": [
                {
                    "source_id": source["source_id"],
                    "label": localize_text(source["label"]),
                    "type": localize_text(source["type"]),
                    "url": source["url"],
                    "is_clickable": public_url(source["url"]),
                }
                for source in state.get("source_manifest", [])
            ],
        },
        "decision_state": {
            "research_stage": state["research_stage"],
            "decision_status": state["decision_status"],
            "decision_updated_at": state["decision_updated_at"],
            "current_action": state["current_action"],
            "status_label": _status_label(state),
            "priority_score": priority["score"],
            "priority_label": priority["label"],
            "next_review_at": state["next_review_at"],
            "next_checklist": next_checklist,
            "action_rules": _build_action_rules(state),
            "changed_assumptions": changed_assumptions,
            "invalidation_reason": localize_text(state.get("invalidation_reason", "")),
        },
        "artifacts": {
            "state_path": _relative_path(ticker_dir / "state.json"),
            "current_path": _relative_path(ticker_dir / "current.md"),
            "review_summary_path": _relative_path(ticker_dir / "artifacts" / "review_summary.md"),
        },
        "observation_actions_enabled": False,
        "observation_context": None,
    }

    if persist_artifacts:
        write_json(ticker_dir / "artifacts" / DIGEST_FILENAME, digest)
        write_json(ticker_dir / "artifacts" / "citations.json", citations)
    return digest


def build_ticker_digest(
    research_root: Path,
    ticker: str,
    *,
    source_status: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return _build_card(research_root, ticker, source_status=source_status, persist_artifacts=True)


def _build_portfolio_summary(cards: list[dict[str, Any]]) -> dict[str, Any]:
    avg_confidence = round(sum(item["thesis_confidence"] for item in cards) / len(cards), 2) if cards else 0.0
    avg_health = round(sum(item["thesis_health"]["score"] for item in cards) / len(cards), 2) if cards else 0.0
    due_within_week = [item for item in cards if date.fromisoformat(item["next_review_at"]) <= date.today() + timedelta(days=7)]
    if avg_health >= 0.75:
        health_label = "整體健康"
    elif avg_health >= 0.6:
        health_label = "整體穩定"
    elif avg_health >= 0.45:
        health_label = "需要留意"
    else:
        health_label = "風險偏高"
    return {
        "tracked_ticker_count": len(cards),
        "positioned_ticker_count": sum(1 for item in cards if item["position"]["has_position"]),
        "average_confidence": avg_confidence,
        "thesis_health_score": avg_health,
        "thesis_health_label": health_label,
        "pending_event_count": sum(
            1 for item in cards for event in item["event_timeline"][:3] if event["decision"] in {"watch", "refresh"}
        ),
        "review_due_count": len(due_within_week),
        "upcoming_tickers": [item["ticker"] for item in sorted(due_within_week, key=lambda row: row["next_review_at"])[:3]],
    }


def _build_priority_queue(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(cards, key=lambda item: (-item["priority_score"], item["next_review_at"], item["ticker"]))
    queue: list[dict[str, Any]] = []
    for item in ordered[:5]:
        next_focus = item["next_checklist"][0] if item["next_checklist"] else "下一次例行複盤"
        queue.append(
            {
                "ticker": item["ticker"],
                "company_name": item["company_name"],
                "priority_label": item["priority_label"],
                "priority_score": item["priority_score"],
                "reason": f"{item['current_action']}；下一步先看 {next_focus}",
                "detail_path": item["detail_path"],
                "research_path": item["internal_research_path"],
            }
        )
    return queue


def _discover_research_tickers(research_root: Path) -> list[str]:
    discovered = sorted(
        state_path.parent.name
        for state_path in research_root.glob("*/state.json")
        if state_path.parent.name != "system"
    )
    return discovered or list(WATCHLIST.keys())


def build_portfolio_digest(
    research_root: Path,
    *,
    tickers: list[str] | None = None,
    source_status_map: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    tickers = tickers or _discover_research_tickers(research_root)
    risk_policy = load_risk_policy(research_root / "system" / "risk_policy.json")
    market_snapshot = fetch_market_snapshot(tickers, policy=risk_policy)
    macro_regime = build_macro_regime(market_snapshot, risk_policy)
    cards = [
        _build_card(
            research_root,
            ticker,
            source_status=(source_status_map or {}).get(ticker),
            persist_artifacts=True,
        )
        for ticker in tickers
    ]
    analytics = generate_post_mortem_report(research_root)
    project_maturity = project_maturity_snapshot()
    portfolio_summary = _build_portfolio_summary(cards)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "portfolio_summary": portfolio_summary,
        "priority_queue": _build_priority_queue(cards),
        "tickers": cards,
        "post_mortem_analytics": analytics,
        "market_snapshot": market_snapshot,
        "macro_regime": macro_regime,
        "portfolio_totals": empty_portfolio_totals(),
        "project_maturity": project_maturity,
        "recent_progress": _build_recent_progress(portfolio_summary, analytics, project_maturity),
        "risk_policy": {
            "holding_period": risk_policy["holding_period"],
            "vix": {
                "symbol": risk_policy["vix"]["symbol"],
                "regimes": [
                    {
                        "key": regime["key"],
                        "label": regime["label"],
                        "size_multiplier": regime["size_multiplier"],
                    }
                    for regime in risk_policy["vix"]["regimes"]
                ],
            },
            "circuit_breakers": risk_policy["circuit_breakers"],
        },
        "observation_summary": {
            "total_count": 0,
            "open_count": 0,
            "ready_count": 0,
            "promoted_count": 0,
            "dismissed_count": 0,
            "average_score": 0.0,
        },
        "observation_items": [],
        "watchlist_recommendations": [],
        "observation_actions_enabled": False,
        "api_base_url": None,
    }
    write_json(CANONICAL_DIGEST_PATH, payload)
    return payload


def overlay_private_positions(
    payload: dict[str, Any],
    *,
    research_root: Path | None = None,
    portfolio_path: Path = PORTFOLIO_PRIVATE_PATH,
    risk_policy_path: Path | None = None,
    market_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    positions = load_private_portfolio(portfolio_path)
    risk_policy = load_risk_policy(risk_policy_path or portfolio_path.parent / "risk_policy.json")
    copied = json.loads(json.dumps(payload))
    market_snapshot = market_snapshot or copied.get("market_snapshot") or fetch_market_snapshot(
        [card["ticker"] for card in copied["tickers"]],
        policy=risk_policy,
    )
    macro_regime = build_macro_regime(market_snapshot, risk_policy)
    enriched_positions: list[dict[str, Any]] = []
    for card in copied["tickers"]:
        base_position = _position_snapshot(card["ticker"], positions.get(card["ticker"]))
        evaluated_position = evaluate_position_snapshot(
            base_position,
            quote=market_snapshot.get("quotes", {}).get(card["ticker"], {}),
            macro_regime=macro_regime,
            thesis_health_score=card["thesis_health"]["score"],
            key_events=card.get("key_events", []),
            policy=risk_policy,
        )
        enriched_positions.append(evaluated_position)
    finalized_positions = {
        position["ticker"]: position
        for position in finalize_position_weights(enriched_positions)
    }

    for card in copied["tickers"]:
        card["position"] = finalized_positions.get(card["ticker"], _position_snapshot(card["ticker"], positions.get(card["ticker"])))
        if (
            card["position"]["sizing_status"]["state"] == "over_max"
            and not any(alert["kind"] == "capital_preservation" for alert in card["position"]["risk_alerts"])
        ):
            card["position"]["risk_alerts"].append(
                {
                    "level": "medium",
                    "kind": "over_max",
                    "title": "Size above regime-adjusted max",
                    "message": "目前曝險高於依 VIX regime 調整後的 max 倉位。",
                    "action": risk_policy["actions"]["over_max"],
                }
            )
            card["position"]["risk_alert_count"] = len(card["position"]["risk_alerts"])
            if card["position"]["recommended_next_action"] == risk_policy["actions"]["healthy"]:
                card["position"]["recommended_next_action"] = risk_policy["actions"]["over_max"]
        card["portfolio_position"] = card["position"]
        card["risk_level"] = card["position"]["risk_level"]
        card["risk_level_label"] = card["position"]["risk_level_label"]
        card["recommended_next_action"] = card["position"]["recommended_next_action"]
        priority = compute_priority(
            current_action=card["current_action"],
            next_review_at=card["next_review_at"],
            risk_level=card["risk_level"],
            confidence_delta=card.get("confidence_delta", 0.0),
            event_timeline=card.get("event_timeline", []),
            risk_alert_count=card["position"].get("risk_alert_count", 0),
            macro_regime=macro_regime.get("key", ""),
        )
        card["priority_score"] = priority["score"]
        card["priority_label"] = priority["label"]
    copied["market_snapshot"] = market_snapshot
    copied["macro_regime"] = macro_regime
    copied["portfolio_summary"] = _build_portfolio_summary(copied["tickers"])
    copied["portfolio_totals"] = build_portfolio_totals([card["position"] for card in copied["tickers"]])
    copied["priority_queue"] = _build_priority_queue(copied["tickers"])
    observation_workspace = build_observation_workspace(
        research_root=research_root or portfolio_path.parent.parent,
        cards=copied["tickers"],
    )
    copied["observation_summary"] = observation_workspace["summary"]
    copied["observation_items"] = observation_workspace["items"]
    copied["watchlist_recommendations"] = observation_workspace["watchlist_recommendations"]
    copied["observation_actions_enabled"] = True
    copied["api_base_url"] = f"http://{COCKPIT_API_HOST}:{COCKPIT_API_PORT}"
    for card in copied["tickers"]:
        card["observation_actions_enabled"] = True
        card["observation_context"] = observation_context_for_ticker(
            card["ticker"],
            graph=observation_workspace["graph"],
        )
    return copied


def localize_digest_payload(payload: dict[str, Any], *, context_label: str) -> dict[str, Any]:
    _ = context_label
    return payload


def render_pr_body_from_digest(payload: dict[str, Any]) -> str:
    lines = [
        "## 自動研究更新",
        "",
        f"- 產生時間：`{payload['generated_at']}`",
        "",
    ]
    for card in payload["tickers"]:
        lines.extend(
            [
                f"### {card['ticker']}",
                "",
                card["summary_blurb"],
                "",
                f"- 目前操作：{card['current_action']}",
                f"- 下次檢查：{card['next_review_at']}",
                f"- 必查資料：{card['next_must_check_data']}",
                "",
                "假設變更：",
            ]
        )
        if card["changed_assumptions"]:
            lines.extend(f"- `{item['assumption_id']}` {item['summary']}" for item in card["changed_assumptions"])
        else:
            lines.append("- 本輪沒有新增假設變更。")
        lines.extend(["", "關鍵事件："])
        if card["key_events"]:
            lines.extend(
                f"- {item['occurred_at']} | {item['source_label']} | {item['title']}"
                for item in card["key_events"]
            )
        else:
            lines.append("- 本輪沒有新的關鍵事件。")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_notification_payload(
    payload: dict[str, Any],
    *,
    run_type: str,
    dashboard_url: str,
    pr_url: str,
) -> dict[str, Any]:
    notification_payload = {
        "run_type": run_type,
        "material_tickers": [item["ticker"] for item in payload["tickers"]],
        "dashboard_url": dashboard_url,
        "pr_url": pr_url,
        "digest_cards": payload["tickers"],
    }
    write_json(NOTIFICATION_PAYLOAD_PATH, notification_payload)
    return notification_payload
