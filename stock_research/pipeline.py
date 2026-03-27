from __future__ import annotations

import shutil
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from .baselines import bootstrap_baselines as bootstrap_profile_files
from .config import (
    AUTOMATION_ROOT,
    CONTEXT_ROOT,
    DRAFT_SUMMARY_PATH,
    PR_BODY_PATH,
    RESEARCH_ROOT,
    RUN_SUMMARY_PATH,
    WATCHLIST,
)
from .llm import generate_refresh
from .markdown import render_current_report, render_review_summary
from .models import Event
from .sources import SourceFailure, fetch_feed_events, fetch_price_events, fetch_sec_events
from .storage import append_jsonl, read_json, read_jsonl, write_json


def bootstrap_baselines(research_root: Path = RESEARCH_ROOT, force: bool = False) -> list[str]:
    return bootstrap_profile_files(research_root=research_root, force=force)


def _load_state(research_root: Path, ticker: str) -> dict[str, Any]:
    path = research_root / ticker / "state.json"
    state = read_json(path)
    if state is None:
        raise FileNotFoundError(f"Missing state for {ticker}: {path}")
    return state


def _save_state(research_root: Path, ticker: str, state: dict[str, Any]) -> None:
    path = research_root / ticker / "state.json"
    write_json(path, state)


def _update_recent_events(research_root: Path, ticker: str) -> list[dict[str, Any]]:
    events = read_jsonl(research_root / ticker / "events.jsonl")
    return list(reversed(events[-8:]))


def _map_assumptions(title: str, assumptions: list[dict[str, Any]]) -> list[str]:
    lowered = title.lower()
    affected: list[str] = []
    for assumption in assumptions:
        keywords = assumption.get("keywords", [])
        if any(keyword.lower() in lowered for keyword in keywords):
            affected.append(assumption["assumption_id"])
    return affected


def _classify_impact(title: str, thresholds: dict[str, Any]) -> str:
    lowered = title.lower()
    if any(keyword in lowered for keyword in thresholds.get("positive_keywords", [])):
        return "+"
    if any(keyword in lowered for keyword in thresholds.get("negative_keywords", [])):
        return "-"
    return "0"


def _should_refresh(
    source_type: str,
    title: str,
    metadata: dict[str, Any],
    thresholds: dict[str, Any],
) -> bool:
    if source_type == "sec" and metadata.get("form") in thresholds["material_sec_forms"]:
        return True
    if source_type == "price":
        return (
            abs(metadata.get("change_pct", 0.0)) >= thresholds["price_gap_pct"]
            or metadata.get("volume_ratio", 0.0) >= thresholds["volume_ratio"]
        )
    lowered = title.lower()
    return any(keyword in lowered for keyword in thresholds.get("earnings_keywords", []))


def _normalize_event(raw_event: dict[str, Any], state: dict[str, Any]) -> Event:
    affected = _map_assumptions(raw_event["title"], state["assumptions"])
    impact = _classify_impact(raw_event["title"], state["thresholds"])
    requires_refresh = _should_refresh(
        raw_event["source_type"], raw_event["title"], raw_event.get("metadata", {}), state["thresholds"]
    )
    decision = "ignore"
    if requires_refresh:
        decision = "refresh"
    elif affected:
        decision = "watch"
    return Event(
        event_id=raw_event["event_id"],
        ticker=raw_event["ticker"],
        source_type=raw_event["source_type"],
        occurred_at=raw_event["occurred_at"],
        title=raw_event["title"],
        source_url=raw_event["source_url"],
        affected_assumption_ids=affected,
        marginal_impact=impact,
        threshold_breach=requires_refresh,
        requires_refresh=requires_refresh,
        decision=decision,
        metadata=raw_event.get("metadata", {}),
    )


def _scheduled_refresh_due(state: dict[str, Any], trigger: str, today: date) -> bool:
    if trigger == "manual":
        return True
    if trigger != "scheduled":
        return False
    next_review = date.fromisoformat(state["next_review_at"])
    last_review = date.fromisoformat(state["last_reviewed_at"])
    deep_refresh_days = state["thresholds"]["deep_refresh_days"]
    return today >= next_review or (today - last_review).days >= deep_refresh_days


def poll_events(research_root: Path = RESEARCH_ROOT, trigger: str = "event") -> dict[str, Any]:
    AUTOMATION_ROOT.mkdir(parents=True, exist_ok=True)
    if CONTEXT_ROOT.exists():
        shutil.rmtree(CONTEXT_ROOT)
    CONTEXT_ROOT.mkdir(parents=True, exist_ok=True)

    today = date.today()
    summary: dict[str, Any] = {
        "trigger": trigger,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "tickers": {},
        "material_tickers": [],
        "changed_files": [],
    }

    for ticker, config in WATCHLIST.items():
        state = _load_state(research_root, ticker)
        ledger_path = research_root / ticker / "events.jsonl"
        seen_ids = {row["event_id"] for row in read_jsonl(ledger_path)}
        raw_events: list[dict[str, Any]] = []
        errors: list[str] = []
        cursor_updates: dict[str, str] = {}

        try:
            sec_events, sec_cursor = fetch_sec_events(config, state)
            raw_events.extend(sec_events)
            if sec_cursor:
                cursor_updates["sec"] = sec_cursor
        except SourceFailure as exc:
            errors.append(str(exc))

        try:
            price_events, price_cursor = fetch_price_events(config, state)
            raw_events.extend(price_events)
            if price_cursor:
                cursor_updates["price"] = price_cursor
        except SourceFailure as exc:
            errors.append(str(exc))

        for feed in config.feeds:
            try:
                feed_events, feed_cursor = fetch_feed_events(feed, config, state)
                raw_events.extend(feed_events)
                if feed_cursor:
                    cursor_updates[feed.source_id] = feed_cursor
            except SourceFailure as exc:
                errors.append(str(exc))

        normalized: list[Event] = []
        run_seen: set[str] = set()
        for raw_event in raw_events:
            if raw_event["event_id"] in seen_ids or raw_event["event_id"] in run_seen:
                continue
            run_seen.add(raw_event["event_id"])
            normalized.append(_normalize_event(raw_event, state))

        if normalized:
            append_jsonl(ledger_path, [event.to_dict() for event in normalized])
            summary["changed_files"].append(str(ledger_path))

        if cursor_updates:
            state["last_seen_event_cursors"].update(cursor_updates)
            _save_state(research_root, ticker, state)
            summary["changed_files"].append(str(research_root / ticker / "state.json"))

        needs_scheduled_refresh = _scheduled_refresh_due(state, trigger, today)
        refresh_events = [event.to_dict() for event in normalized if event.requires_refresh]
        if refresh_events or needs_scheduled_refresh:
            context = {
                "ticker": ticker,
                "trigger": trigger,
                "scheduled_refresh_due": needs_scheduled_refresh,
                "new_events": [event.to_dict() for event in normalized],
                "material_events": refresh_events,
                "state_path": str(research_root / ticker / "state.json"),
                "current_path": str(research_root / ticker / "current.md"),
            }
            write_json(CONTEXT_ROOT / f"{ticker}.json", context)
            summary["material_tickers"].append(ticker)

        summary["tickers"][ticker] = {
            "new_events": len(normalized),
            "material_events": len(refresh_events),
            "scheduled_refresh_due": needs_scheduled_refresh,
            "errors": errors,
        }

    write_json(RUN_SUMMARY_PATH, summary)
    return summary


def draft_refreshes(research_root: Path = RESEARCH_ROOT, trigger: str = "event") -> dict[str, Any]:
    summary = read_json(RUN_SUMMARY_PATH, default={"material_tickers": []})
    draft_summary: dict[str, Any] = {
        "trigger": trigger,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "refreshed_tickers": [],
    }
    pr_body_lines = [
        "## Automated Research Refresh",
        "",
        f"- Trigger: `{trigger}`",
        "",
    ]

    for ticker in summary.get("material_tickers", []):
        context_path = CONTEXT_ROOT / f"{ticker}.json"
        context = read_json(context_path)
        if context is None:
            continue
        ticker_dir = research_root / ticker
        current_path = ticker_dir / "current.md"
        state_path = ticker_dir / "state.json"
        state = read_json(state_path)
        current_markdown = current_path.read_text(encoding="utf-8")
        refresh = generate_refresh(state, current_markdown, context)
        updated_state = refresh["updated_state"]
        updated_state["last_reviewed_at"] = date.today().isoformat()
        if not updated_state.get("next_review_at"):
            updated_state["next_review_at"] = (
                date.today() + timedelta(days=updated_state["thresholds"]["deep_refresh_days"])
            ).isoformat()
        if "summary_points" in refresh:
            updated_state["latest_delta"] = refresh["summary_points"]
        next_version = f"v{len(updated_state['version_log'])}"
        updated_state["version_log"].append(
            {
                "version": next_version,
                "date": date.today().isoformat(),
                "reason": f"Automated refresh triggered by {trigger}.",
                "impact": refresh["review_summary"],
            }
        )
        _save_state(research_root, ticker, updated_state)
        recent_events = _update_recent_events(research_root, ticker)
        current_path.write_text(render_current_report(updated_state, recent_events), encoding="utf-8")

        artifacts_dir = ticker_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            artifacts_dir / "review_summary.json",
            {
                "ticker": ticker,
                "reviewed_at": updated_state["last_reviewed_at"],
                "review_summary": refresh["review_summary"],
                "changed_assumptions": refresh["changed_assumptions"],
                "action_rule_delta": refresh["action_rule_delta"],
                "trigger": trigger,
                "context": context,
            },
        )
        (artifacts_dir / "review_summary.md").write_text(
            render_review_summary(
                updated_state,
                refresh["review_summary"],
                refresh["changed_assumptions"],
                refresh["action_rule_delta"],
            ),
            encoding="utf-8",
        )
        draft_summary["refreshed_tickers"].append(
            {
                "ticker": ticker,
                "review_summary": refresh["review_summary"],
                "changed_assumptions": refresh["changed_assumptions"],
            }
        )
        pr_body_lines.extend(
            [
                f"### {ticker}",
                "",
                refresh["review_summary"],
                "",
                "Changed assumptions:",
            ]
        )
        if refresh["changed_assumptions"]:
            pr_body_lines.extend(f"- `{item['assumption_id']}` {item['summary']}" for item in refresh["changed_assumptions"])
        else:
            pr_body_lines.append("- None")
        pr_body_lines.append("")

    write_json(DRAFT_SUMMARY_PATH, draft_summary)
    PR_BODY_PATH.write_text("\n".join(pr_body_lines).strip() + "\n", encoding="utf-8")
    return draft_summary
