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
    PR_BODY_ZH_TW_PATH,
    RESEARCH_ROOT,
    RUN_SUMMARY_PATH,
    TEST_EVENTS_ROOT,
    TRANSLATION_SUMMARY_PATH,
    WATCHLIST,
)
from .llm import generate_refresh, translate_markdown
from .markdown import render_current_report, render_review_summary
from .models import Event
from .sources import SourceFailure, fetch_feed_events, fetch_price_events, fetch_sec_events
from .storage import append_jsonl, read_json, read_jsonl, sha1_digest, write_json


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
    if "force_requires_refresh" in metadata:
        return bool(metadata["force_requires_refresh"])
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
    metadata = raw_event.get("metadata", {})
    affected = metadata.get("force_assumption_ids") or _map_assumptions(raw_event["title"], state["assumptions"])
    impact = metadata.get("force_marginal_impact") or _classify_impact(raw_event["title"], state["thresholds"])
    requires_refresh = _should_refresh(
        raw_event["source_type"], raw_event["title"], metadata, state["thresholds"]
    )
    decision = metadata.get("force_decision", "ignore")
    if "force_decision" not in metadata:
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
        metadata=metadata,
    )


def _scheduled_refresh_due(
    state: dict[str, Any],
    trigger: str,
    today: date,
    fixture_name: str | None = None,
) -> bool:
    if fixture_name:
        return False
    if trigger == "manual":
        return True
    if trigger != "scheduled":
        return False
    next_review = date.fromisoformat(state["next_review_at"])
    last_review = date.fromisoformat(state["last_reviewed_at"])
    deep_refresh_days = state["thresholds"]["deep_refresh_days"]
    return today >= next_review or (today - last_review).days >= deep_refresh_days


def _load_fixture_events(fixture_name: str, fixture_root: Path = TEST_EVENTS_ROOT) -> list[dict[str, Any]]:
    fixture_path = fixture_root / f"{fixture_name}.json"
    payload = read_json(fixture_path)
    if payload is None:
        raise FileNotFoundError(f"Missing fixture file: {fixture_path}")
    events = payload.get("events", payload)
    normalized_events: list[dict[str, Any]] = []
    for event in events:
        event_copy = dict(event)
        metadata = dict(event_copy.get("metadata", {}))
        metadata["fixture_name"] = fixture_name
        event_copy["metadata"] = metadata
        event_copy.setdefault(
            "event_id",
            sha1_digest(
                event_copy["ticker"],
                "fixture",
                fixture_name,
                event_copy["occurred_at"],
                event_copy["title"],
            ),
        )
        event_copy.setdefault("source_url", f"fixture://{fixture_name}")
        normalized_events.append(event_copy)
    return normalized_events


def poll_events(
    research_root: Path = RESEARCH_ROOT,
    trigger: str = "event",
    fixture_name: str | None = None,
    fixture_root: Path = TEST_EVENTS_ROOT,
) -> dict[str, Any]:
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
        "fixture_name": fixture_name,
    }

    fixture_events = _load_fixture_events(fixture_name, fixture_root) if fixture_name else []

    for ticker, config in WATCHLIST.items():
        state = _load_state(research_root, ticker)
        ledger_path = research_root / ticker / "events.jsonl"
        seen_ids = {row["event_id"] for row in read_jsonl(ledger_path)}
        raw_events: list[dict[str, Any]] = []
        errors: list[str] = []
        cursor_updates: dict[str, str] = {}

        if fixture_name:
            raw_events.extend(event for event in fixture_events if event["ticker"] == ticker)
        else:
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

        needs_scheduled_refresh = _scheduled_refresh_due(state, trigger, today, fixture_name=fixture_name)
        refresh_events = [event.to_dict() for event in normalized if event.requires_refresh]
        if refresh_events or needs_scheduled_refresh:
            context = {
                "ticker": ticker,
                "trigger": trigger,
                "fixture_name": fixture_name,
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


def localize_refresh_outputs(
    research_root: Path,
    refreshed_tickers: list[str],
) -> dict[str, Any]:
    translated_files: list[str] = []
    for ticker in refreshed_tickers:
        ticker_dir = research_root / ticker
        current_path = ticker_dir / "current.md"
        review_summary_path = ticker_dir / "artifacts" / "review_summary.md"
        current_zh_tw_path = ticker_dir / "current.zh-tw.md"
        review_summary_zh_tw_path = ticker_dir / "artifacts" / "review_summary.zh-tw.md"

        current_zh_tw_path.write_text(
            translate_markdown(current_path.read_text(encoding="utf-8"), context_label=f"{ticker} current research note"),
            encoding="utf-8",
        )
        review_summary_zh_tw_path.write_text(
            translate_markdown(
                review_summary_path.read_text(encoding="utf-8"),
                context_label=f"{ticker} refresh review summary",
            ),
            encoding="utf-8",
        )
        translated_files.extend([str(current_zh_tw_path), str(review_summary_zh_tw_path)])

    if PR_BODY_PATH.exists():
        PR_BODY_ZH_TW_PATH.write_text(
            translate_markdown(PR_BODY_PATH.read_text(encoding="utf-8"), context_label="pull request body"),
            encoding="utf-8",
        )
        translated_files.append(str(PR_BODY_ZH_TW_PATH))

    summary = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "translated_files": translated_files,
    }
    write_json(TRANSLATION_SUMMARY_PATH, summary)
    return summary


def draft_refreshes(
    research_root: Path = RESEARCH_ROOT,
    trigger: str = "event",
    fixture_name: str | None = None,
) -> dict[str, Any]:
    summary = read_json(RUN_SUMMARY_PATH, default={"material_tickers": []})
    draft_summary: dict[str, Any] = {
        "trigger": trigger,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "refreshed_tickers": [],
        "fixture_name": fixture_name,
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
    localization_summary = localize_refresh_outputs(
        research_root,
        [item["ticker"] for item in draft_summary["refreshed_tickers"]],
    )
    draft_summary["localization"] = localization_summary
    write_json(DRAFT_SUMMARY_PATH, draft_summary)
    return draft_summary
