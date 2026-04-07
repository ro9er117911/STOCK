from __future__ import annotations

import shutil
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from .baselines import bootstrap_baselines as bootstrap_profile_files
from .config import (
    AUTOMATION_ROOT,
    CANONICAL_DIGEST_PATH,
    CONTEXT_ROOT,
    DRAFT_SUMMARY_PATH,
    DIGEST_FILENAME,
    PR_BODY_PATH,
    PR_BODY_ZH_TW_PATH,
    RESEARCH_ROOT,
    RUN_SUMMARY_PATH,
    SOURCE_STATUS_FILENAME,
    TEST_EVENTS_ROOT,
    TRANSLATION_SUMMARY_PATH,
    WATCHLIST,
)
from .dashboard import build_dashboard_bundle
from .digest import build_portfolio_digest, render_pr_body_from_digest
from .llm import generate_refresh, translate_markdown
from .radar import scan_market
from .markdown import render_current_report, render_review_summary
from .models import Event
from .observation import ensure_observation_system_files
from .postprocess import post_process_refresh_output
from .research_state import (
    append_state_change_entry,
    normalize_state_contract,
    record_outcome_marker,
    rewrite_research_artifacts,
    sync_candidate_queue,
)
from .sources import SourceFailure, fetch_feed_events, fetch_price_events, fetch_sec_events
from .storage import append_jsonl, read_json, read_jsonl, sha1_digest, write_json


def bootstrap_baselines(research_root: Path = RESEARCH_ROOT, force: bool = False) -> list[str]:
    return bootstrap_profile_files(research_root=research_root, force=force)


def _load_state(research_root: Path, ticker: str) -> dict[str, Any]:
    path = research_root / ticker / "state.json"
    state = read_json(path)
    if state is None:
        raise FileNotFoundError(f"Missing state for {ticker}: {path}")
    return normalize_state_contract(state)


def _save_state(research_root: Path, ticker: str, state: dict[str, Any]) -> None:
    path = research_root / ticker / "state.json"
    write_json(path, normalize_state_contract(state))


def _update_recent_events(research_root: Path, ticker: str) -> list[dict[str, Any]]:
    events = read_jsonl(research_root / ticker / "events.jsonl")
    return list(reversed(events[-8:]))


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path(".").resolve()))
    except ValueError:
        return str(path)


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


def _source_status_row(
    source,
    *,
    status: str,
    new_events: int = 0,
    cursor: str = "",
    error: str = "",
    notes: str | None = None,
) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "source_type": source.source_type,
        "kind": source.kind,
        "url": source.url,
        "status": status,
        "priority": source.priority,
        "new_events": new_events,
        "cursor": cursor,
        "error": error,
        "notes": notes if notes is not None else source.notes,
    }


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
        artifacts_dir = research_root / ticker / "artifacts"
        seen_ids = {row["event_id"] for row in read_jsonl(ledger_path)}
        raw_events: list[dict[str, Any]] = []
        errors: list[str] = []
        cursor_updates: dict[str, str] = {}
        source_status_rows: list[dict[str, Any]] = []

        if fixture_name:
            for source in config.sources:
                source_status_rows.append(
                    _source_status_row(
                        source,
                        status="fixture_override",
                        notes=f"Skipped because fixture {fixture_name} overrides live polling.",
                    )
                )
            raw_events.extend(event for event in fixture_events if event["ticker"] == ticker)
            if any(event["ticker"] == ticker for event in fixture_events):
                source_status_rows.append(
                    {
                        "source_id": f"fixture:{fixture_name}",
                        "source_type": "fixture",
                        "kind": "fixture",
                        "url": f"fixture://{fixture_name}",
                        "status": "polled",
                        "priority": 0,
                        "new_events": len([event for event in fixture_events if event["ticker"] == ticker]),
                        "cursor": fixture_name,
                        "error": "",
                        "notes": "Deterministic fixture input for test refresh validation.",
                    }
                )
        else:
            for source in config.sources:
                if source.status != "active":
                    source_status_rows.append(_source_status_row(source, status="disabled"))
                    continue
                try:
                    source_events: list[dict[str, Any]]
                    source_cursor: str
                    if source.kind == "sec":
                        source_events, source_cursor = fetch_sec_events(source, config, state)
                    elif source.kind == "price":
                        source_events, source_cursor = fetch_price_events(source, config, state)
                    else:
                        source_events, source_cursor = fetch_feed_events(source, config, state)
                    raw_events.extend(source_events)
                    if source_cursor:
                        cursor_updates[source.source_id] = source_cursor
                    source_status_rows.append(
                        _source_status_row(
                            source,
                            status="polled",
                            new_events=len(source_events),
                            cursor=source_cursor,
                        )
                    )
                except SourceFailure as exc:
                    errors.append(str(exc))
                    source_status_rows.append(
                        _source_status_row(
                            source,
                            status="failed",
                            error=str(exc),
                        )
                    )

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

        artifacts_dir.mkdir(parents=True, exist_ok=True)
        source_status_path = artifacts_dir / SOURCE_STATUS_FILENAME
        source_status_payload = {
            "ticker": ticker,
            "sources": source_status_rows,
        }
        if read_json(source_status_path) != source_status_payload:
            write_json(source_status_path, source_status_payload)
            summary["changed_files"].append(str(source_status_path))

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
            "source_status": source_status_rows,
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
        translated_files.extend([_relative_path(current_zh_tw_path), _relative_path(review_summary_zh_tw_path)])

    if PR_BODY_PATH.exists():
        PR_BODY_ZH_TW_PATH.write_text(
            translate_markdown(PR_BODY_PATH.read_text(encoding="utf-8"), context_label="pull request body"),
            encoding="utf-8",
        )
        translated_files.append(_relative_path(PR_BODY_ZH_TW_PATH))

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
    source_status_map = {
        ticker: summary.get("tickers", {}).get(ticker, {}).get("source_status", [])
        for ticker in summary.get("tickers", {})
    }
    draft_summary: dict[str, Any] = {
        "trigger": trigger,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "refreshed_tickers": [],
        "fixture_name": fixture_name,
    }

    for ticker in summary.get("material_tickers", []):
        context_path = CONTEXT_ROOT / f"{ticker}.json"
        context = read_json(context_path)
        if context is None:
            continue
        ticker_dir = research_root / ticker
        current_path = ticker_dir / "current.md"
        state_path = ticker_dir / "state.json"
        state = normalize_state_contract(read_json(state_path))
        current_markdown = current_path.read_text(encoding="utf-8")
        base_version_log = list(state.get("version_log", []))
        refresh = generate_refresh(state, current_markdown, context)
        refresh = post_process_refresh_output(state, refresh, context)
        updated_state = normalize_state_contract(refresh["updated_state"])
        updated_state["last_reviewed_at"] = date.today().isoformat()
        updated_state["next_review_at"] = (
            date.today() + timedelta(days=updated_state["thresholds"]["deep_refresh_days"])
        ).isoformat()
        if "summary_points" in refresh:
            updated_state["latest_delta"] = refresh["summary_points"]
        updated_state["version_log"] = base_version_log
        next_version = f"v{len(updated_state['version_log'])}"
        updated_state["version_log"].append(
            {
                "version": next_version,
                "date": date.today().isoformat(),
                "reason": f"Automated refresh triggered by {trigger}.",
                "impact": refresh["review_summary"],
            }
        )
        updated_state = append_state_change_entry(
            state,
            updated_state,
            summary=refresh["review_summary"],
            change_type="refresh_review",
            changed_at=updated_state["last_reviewed_at"],
        )
        updated_state = record_outcome_marker(
            updated_state,
            kind="material_refresh" if context.get("material_events") else "scheduled_refresh",
            summary=refresh["review_summary"],
            marked_at=updated_state["last_reviewed_at"],
            affected_assumption_ids=[
                item["assumption_id"]
                for item in refresh.get("changed_assumptions", [])
                if item.get("assumption_id")
            ],
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
                "source_status": source_status_map.get(ticker, []),
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
                "digest_path": _relative_path(artifacts_dir / DIGEST_FILENAME),
            }
        )

    digest_payload = build_portfolio_digest(
        research_root,
        tickers=[item["ticker"] for item in draft_summary["refreshed_tickers"]],
        source_status_map=source_status_map,
    )
    draft_summary["canonical_digest_path"] = _relative_path(CANONICAL_DIGEST_PATH)
    write_json(DRAFT_SUMMARY_PATH, draft_summary)
    PR_BODY_PATH.write_text(render_pr_body_from_digest(digest_payload), encoding="utf-8")
    localization_summary = localize_refresh_outputs(
        research_root,
        [item["ticker"] for item in draft_summary["refreshed_tickers"]],
    )
    draft_summary["localization"] = localization_summary
    write_json(DRAFT_SUMMARY_PATH, draft_summary)
    sync_candidate_queue(research_root)
    return draft_summary


def build_dashboard(research_root: Path = RESEARCH_ROOT) -> dict[str, Any]:
    return build_dashboard_bundle(research_root=research_root)


def run_radar_scan(
    research_root: Path = RESEARCH_ROOT,
    universe: list[str] | list[Any] | None = None,
) -> dict[str, Any]:
    from .candidates import upsert_candidate_dossier
    from .config import TickerConfig
    
    universe = universe or list(WATCHLIST.values())
    
    summary = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "scanned_count": 0,
        "flagged_tickers": [],
    }
    
    results = scan_market(universe)
    summary["scanned_count"] = len(results)
    
    for ticker, info in results.items():
        if not info["radar_flags"]:
            continue
            
        company_name = next(
            (t.company_name for t in universe if isinstance(t, TickerConfig) and t.ticker == ticker),
            ticker
        )

        dossier = upsert_candidate_dossier(
            research_root,
            ticker=ticker,
            company_name=company_name,
            research_topic=f"Technically driven candidate via Radar Scanner.",
            candidate_origin="radar_scan",
            research_stage="candidate",
            radar_flags=info["radar_flags"],
            radar_summary=info["radar_summary"],
            radar_risk_level=info["radar_risk_level"],
            note=f"Automatic ingestion from radar scan due to technical flags.",
        )
        summary["flagged_tickers"].append(dossier)

    sync_candidate_queue(research_root)
    write_json(AUTOMATION_ROOT / "radar-summary.json", summary)
    return summary


def sync_research_contracts(research_root: Path = RESEARCH_ROOT) -> dict[str, Any]:
    ensure_observation_system_files(research_root)
    rewritten: list[str] = []
    for state_path in sorted(research_root.glob("*/state.json")):
        state = read_json(state_path)
        if state is None:
            continue
        rewrite_research_artifacts(research_root, state_path.parent.name, state)
        rewritten.append(state_path.parent.name)
    queue = sync_candidate_queue(research_root)
    return {
        "rewritten_tickers": rewritten,
        "candidate_queue_path": str(research_root / "system" / "candidates.json"),
        "candidate_count": len(queue["items"]),
    }
