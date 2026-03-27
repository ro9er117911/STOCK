from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import (
    CANONICAL_DIGEST_PATH,
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
from .portfolio import load_private_portfolio
from .storage import read_json, read_jsonl, write_json


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
            }
        )
    return timeline


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
        "position": position_snapshot,
        "portfolio_position": position_snapshot,
        "key_events": event_timeline[:3],
        "event_timeline": event_timeline,
        "key_action_rules": _build_action_rules(state)[:3],
        "action_rules": _build_action_rules(state),
        "changed_assumptions": changed_assumptions,
        "action_rule_delta": action_rule_delta,
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
            "thesis_statement": localize_text(state["thesis"]["statement"]),
            "core_catalyst": localize_text(state["thesis"]["core_catalyst"]),
            "market_blind_spot": localize_text(state["thesis"]["market_blind_spot"]),
            "latest_delta": [localize_text(item) for item in state.get("latest_delta", [])],
            "review_summary": localize_text(review_summary.get("review_summary", "")),
            "thesis_health": thesis_health,
            "assumptions": _build_assumptions(state),
            "risks": _build_risks(state),
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
            "current_action": state["current_action"],
            "status_label": _status_label(state),
            "priority_score": priority["score"],
            "priority_label": priority["label"],
            "next_review_at": state["next_review_at"],
            "next_checklist": next_checklist,
            "action_rules": _build_action_rules(state),
            "changed_assumptions": changed_assumptions,
        },
        "artifacts": {
            "state_path": _relative_path(ticker_dir / "state.json"),
            "current_path": _relative_path(ticker_dir / "current.md"),
            "review_summary_path": _relative_path(ticker_dir / "artifacts" / "review_summary.md"),
        },
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


def build_portfolio_digest(
    research_root: Path,
    *,
    tickers: list[str] | None = None,
    source_status_map: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    tickers = tickers or list(WATCHLIST.keys())
    cards = [
        _build_card(
            research_root,
            ticker,
            source_status=(source_status_map or {}).get(ticker),
            persist_artifacts=True,
        )
        for ticker in tickers
    ]
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "portfolio_summary": _build_portfolio_summary(cards),
        "priority_queue": _build_priority_queue(cards),
        "tickers": cards,
    }
    write_json(CANONICAL_DIGEST_PATH, payload)
    return payload


def overlay_private_positions(
    payload: dict[str, Any],
    *,
    portfolio_path: Path = PORTFOLIO_PRIVATE_PATH,
) -> dict[str, Any]:
    positions = load_private_portfolio(portfolio_path)
    if not positions:
        return payload
    copied = json.loads(json.dumps(payload))
    for card in copied["tickers"]:
        card["position"] = _position_snapshot(card["ticker"], positions.get(card["ticker"]))
        card["portfolio_position"] = card["position"]
        card["risk_level"] = card["position"]["risk_level"]
        card["risk_level_label"] = card["position"]["risk_level_label"]
        priority = compute_priority(
            current_action=card["current_action"],
            next_review_at=card["next_review_at"],
            risk_level=card["risk_level"],
            confidence_delta=card.get("confidence_delta", 0.0),
            event_timeline=card.get("event_timeline", []),
        )
        card["priority_score"] = priority["score"]
        card["priority_label"] = priority["label"]
    copied["portfolio_summary"] = _build_portfolio_summary(copied["tickers"])
    copied["priority_queue"] = _build_priority_queue(copied["tickers"])
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
