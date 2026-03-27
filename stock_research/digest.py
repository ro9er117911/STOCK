from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import (
    CANONICAL_DIGEST_PATH,
    DIGEST_FILENAME,
    NOTIFICATION_PAYLOAD_PATH,
    REPO_ROOT,
    SOURCE_STATUS_FILENAME,
    WATCHLIST,
)
from .llm import translate_structured_payload
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
        return "需退出"
    if "trim" in lowered or "減碼" in action:
        return "偏保守"
    if "add" in lowered or "加碼" in action or "偏多" in action:
        return "偏多"
    if confidence >= 0.7:
        return "穩定持有"
    return "持有觀察"


def build_ticker_digest(
    research_root: Path,
    ticker: str,
    *,
    source_status: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ticker_dir = research_root / ticker
    state = read_json(ticker_dir / "state.json")
    if state is None:
        raise FileNotFoundError(f"Missing state for {ticker}")

    review_summary = _load_review_summary(ticker_dir)
    recent_events = list(reversed(read_jsonl(ticker_dir / "events.jsonl")[-5:]))
    changed_assumptions = review_summary.get("changed_assumptions", [])
    action_rule_delta = review_summary.get("action_rule_delta", [])
    summary_blurb = review_summary.get("review_summary") or "No review summary has been generated yet."
    source_status = source_status if source_status is not None else _load_source_status(ticker_dir, ticker)

    digest = {
        "ticker": ticker,
        "company_name": state["company_name"],
        "status_label": _status_label(state),
        "current_action": state["current_action"],
        "thesis_confidence": round(state["confidence"], 2),
        "summary_blurb": summary_blurb,
        "next_review_at": state["next_review_at"],
        "next_must_check_data": state["next_must_check_data"],
        "last_reviewed_at": state["last_reviewed_at"],
        "key_events": [
            {
                "occurred_at": event["occurred_at"],
                "source_type": event["source_type"],
                "title": event["title"],
                "impact": event["marginal_impact"],
                "decision": event["decision"],
                "source_url": event["source_url"],
            }
            for event in recent_events[:3]
        ],
        "key_action_rules": [
            {
                "action_rule_id": item["action_rule_id"],
                "kind": item["kind"],
                "condition": item["condition"],
                "action": item["action"],
            }
            for item in state["action_rules"][:3]
        ],
        "changed_assumptions": changed_assumptions,
        "action_rule_delta": action_rule_delta,
        "source_status": source_status,
        "artifacts": {
            "state_path": _relative_path(ticker_dir / "state.json"),
            "current_path": _relative_path(ticker_dir / "current.md"),
            "review_summary_path": _relative_path(ticker_dir / "artifacts" / "review_summary.md"),
        },
    }
    write_json(ticker_dir / "artifacts" / DIGEST_FILENAME, digest)
    return digest


def build_portfolio_digest(
    research_root: Path,
    *,
    tickers: list[str] | None = None,
    source_status_map: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    tickers = tickers or list(WATCHLIST.keys())
    cards = [
        build_ticker_digest(
            research_root,
            ticker,
            source_status=(source_status_map or {}).get(ticker),
        )
        for ticker in tickers
    ]
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "tickers": cards,
    }
    write_json(CANONICAL_DIGEST_PATH, payload)
    return payload


def localize_digest_payload(payload: dict[str, Any], *, context_label: str) -> dict[str, Any]:
    return translate_structured_payload(payload, context_label=context_label)


def render_pr_body_from_digest(payload: dict[str, Any]) -> str:
    lines = [
        "## Automated Research Refresh",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        "",
    ]
    for card in payload["tickers"]:
        lines.extend(
            [
                f"### {card['ticker']}",
                "",
                card["summary_blurb"],
                "",
                f"- Current action: {card['current_action']}",
                f"- Next review: {card['next_review_at']}",
                f"- Next must-check data: {card['next_must_check_data']}",
                "",
                "Changed assumptions:",
            ]
        )
        if card["changed_assumptions"]:
            lines.extend(
                f"- `{item['assumption_id']}` {item['summary']}" for item in card["changed_assumptions"]
            )
        else:
            lines.append("- None")
        lines.extend(["", "Key events:"])
        if card["key_events"]:
            lines.extend(
                f"- {item['occurred_at']} | {item['source_type']} | {item['title']}"
                for item in card["key_events"]
            )
        else:
            lines.append("- None")
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
    localized_payload = localize_digest_payload(
        notification_payload,
        context_label="material update notification payload",
    )
    write_json(NOTIFICATION_PAYLOAD_PATH, localized_payload)
    return localized_payload
