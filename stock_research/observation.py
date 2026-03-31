from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from .candidates import upsert_candidate_dossier
from .config import (
    OBSERVATION_EVENTS_PATH,
    OBSERVATION_GRAPH_PATH,
    OBSERVATION_LAKE_PATH,
    WATCHLIST,
)
from .storage import append_jsonl, read_json, read_jsonl, sha1_digest, write_json

OBSERVATION_STATUSES = ("open", "ready_for_candidate", "promoted", "dismissed", "archived")
OBSERVATION_OPENED_FROM = ("company", "peer", "supply_chain", "manual")
OBSERVATION_RELATION_TYPES = ("company", "peer", "supply_chain", "manual")
OBSERVATION_EVENT_FAMILIES = (
    "historical_trauma",
    "capital_allocation",
    "decision_os_lockin",
    "risk_transfer_pricing_power",
    "valuation_regime_shift",
    "peer_readthrough",
    "supply_chain_readthrough",
    "price_exception",
)
SIGNAL_STRENGTH_VALUES = {
    "low": 1.0,
    "medium": 1.6,
    "high": 2.3,
    "critical": 2.9,
}
EVENT_FAMILY_WEIGHTS = {
    "historical_trauma": 2.4,
    "capital_allocation": 2.3,
    "decision_os_lockin": 2.5,
    "risk_transfer_pricing_power": 2.4,
    "valuation_regime_shift": 2.2,
    "peer_readthrough": 1.6,
    "supply_chain_readthrough": 1.4,
    "price_exception": 0.9,
}
RELATION_WEIGHTS = {
    "company": 1.0,
    "peer": 0.8,
    "supply_chain": 0.7,
    "manual": 0.5,
}
READY_FOR_CANDIDATE_THRESHOLD = 7.5
PRICE_EXCEPTION_CAP = 2.2
DEFAULT_INTENDED_HORIZON = "3-12 months"
DEFAULT_OBSERVATION_LAKE = {
    "generated_at": "",
    "items": [],
}
DEFAULT_COMPANY_NAMES = {
    "MSFT": "Microsoft",
    "PLTR": "Palantir Technologies",
    "MAR": "Marriott International",
    "NVDA": "NVIDIA",
    "AMD": "Advanced Micro Devices",
    "AVGO": "Broadcom",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "ORCL": "Oracle",
    "CRM": "Salesforce",
    "NOW": "ServiceNow",
    "SNOW": "Snowflake",
    "CFLT": "Confluent",
    "HLT": "Hilton Worldwide",
    "BKNG": "Booking Holdings",
    "ABNB": "Airbnb",
    "EXPE": "Expedia",
    "SABR": "Sabre",
}
DEFAULT_OBSERVATION_GRAPH = {
    "version": 1,
    "generated_at": "2026-03-31",
    "companies": DEFAULT_COMPANY_NAMES,
    "relations": [
        {
            "ticker": "MSFT",
            "company_name": "Microsoft",
            "theme_id": "ai-platforms",
            "peer_tickers": ["AMZN", "GOOGL", "ORCL"],
            "upstream_tickers": ["NVDA", "AMD", "AVGO"],
            "downstream_tickers": ["PLTR", "CRM", "NOW"],
            "default_horizon": DEFAULT_INTENDED_HORIZON,
            "default_event_weights": {
                "historical_trauma": 2.4,
                "capital_allocation": 2.4,
                "decision_os_lockin": 2.5,
                "risk_transfer_pricing_power": 2.1,
                "valuation_regime_shift": 2.3,
                "peer_readthrough": 1.6,
                "supply_chain_readthrough": 1.5,
                "price_exception": 0.9,
            },
        },
        {
            "ticker": "PLTR",
            "company_name": "Palantir Technologies",
            "theme_id": "decision-os",
            "peer_tickers": ["SNOW", "CFLT", "NOW"],
            "upstream_tickers": ["MSFT", "AMZN", "GOOGL"],
            "downstream_tickers": ["CRM"],
            "default_horizon": DEFAULT_INTENDED_HORIZON,
            "default_event_weights": {
                "historical_trauma": 2.3,
                "capital_allocation": 2.1,
                "decision_os_lockin": 2.7,
                "risk_transfer_pricing_power": 2.4,
                "valuation_regime_shift": 2.2,
                "peer_readthrough": 1.7,
                "supply_chain_readthrough": 1.4,
                "price_exception": 0.9,
            },
        },
        {
            "ticker": "MAR",
            "company_name": "Marriott International",
            "theme_id": "asset-light-travel",
            "peer_tickers": ["HLT", "BKNG", "ABNB"],
            "upstream_tickers": ["SABR", "EXPE"],
            "downstream_tickers": [],
            "default_horizon": DEFAULT_INTENDED_HORIZON,
            "default_event_weights": {
                "historical_trauma": 2.5,
                "capital_allocation": 2.4,
                "decision_os_lockin": 2.1,
                "risk_transfer_pricing_power": 2.6,
                "valuation_regime_shift": 2.1,
                "peer_readthrough": 1.5,
                "supply_chain_readthrough": 1.3,
                "price_exception": 0.8,
            },
        },
    ],
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _today_iso() -> str:
    return date.today().isoformat()


def _company_name_for(ticker: str, graph: dict[str, Any]) -> str:
    ticker = str(ticker or "").upper()
    if ticker in WATCHLIST:
        return WATCHLIST[ticker].company_name
    companies = graph.get("companies", {})
    return companies.get(ticker, DEFAULT_COMPANY_NAMES.get(ticker, ticker))


def ensure_observation_system_files(
    research_root: Path,
    *,
    force: bool = False,
) -> None:
    system_root = research_root / "system"
    system_root.mkdir(parents=True, exist_ok=True)
    lake_path = system_root / OBSERVATION_LAKE_PATH.name
    graph_path = system_root / OBSERVATION_GRAPH_PATH.name
    events_path = system_root / OBSERVATION_EVENTS_PATH.name

    if force or not lake_path.exists():
        write_json(
            lake_path,
            {
                "generated_at": _today_iso(),
                "items": [],
            },
        )
    if force or not graph_path.exists():
        write_json(graph_path, deepcopy(DEFAULT_OBSERVATION_GRAPH))
    if force or not events_path.exists():
        events_path.parent.mkdir(parents=True, exist_ok=True)
        events_path.write_text("", encoding="utf-8")


def load_observation_graph(path: Path = OBSERVATION_GRAPH_PATH) -> dict[str, Any]:
    payload = read_json(path, default=None)
    if payload is None:
        return deepcopy(DEFAULT_OBSERVATION_GRAPH)
    graph = deepcopy(DEFAULT_OBSERVATION_GRAPH)
    graph.update({key: value for key, value in payload.items() if key != "relations"})
    relation_index = {row["ticker"]: row for row in graph["relations"]}
    for row in payload.get("relations", []):
        relation_index[row["ticker"]] = {
            **relation_index.get(row["ticker"], {}),
            **row,
        }
    graph["relations"] = list(relation_index.values())
    graph["companies"] = {
        **DEFAULT_COMPANY_NAMES,
        **payload.get("companies", {}),
    }
    for row in graph["relations"]:
        graph["companies"].setdefault(row["ticker"], row.get("company_name", row["ticker"]))
        for key in ("peer_tickers", "upstream_tickers", "downstream_tickers"):
            row[key] = [str(item).upper() for item in row.get(key, []) if str(item).strip()]
        row["theme_id"] = str(row.get("theme_id", "general")).strip() or "general"
        row["default_horizon"] = str(row.get("default_horizon", DEFAULT_INTENDED_HORIZON)).strip() or DEFAULT_INTENDED_HORIZON
        row["default_event_weights"] = {
            **EVENT_FAMILY_WEIGHTS,
            **row.get("default_event_weights", {}),
        }
    return graph


def _relation_index(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        row["ticker"]: row
        for row in graph.get("relations", [])
    }


def load_observation_lake(path: Path = OBSERVATION_LAKE_PATH) -> dict[str, Any]:
    payload = read_json(path, default=None)
    if payload is None:
        return deepcopy(DEFAULT_OBSERVATION_LAKE)
    return {
        "generated_at": str(payload.get("generated_at", "")),
        "items": list(payload.get("items", [])),
    }


def load_observation_events(path: Path = OBSERVATION_EVENTS_PATH) -> list[dict[str, Any]]:
    return read_jsonl(path)


def _score_label(score: float) -> str:
    if score >= READY_FOR_CANDIDATE_THRESHOLD:
        return "Ready for candidate"
    if score >= 5.0:
        return "High-priority watch"
    if score >= 3.0:
        return "Active watch"
    return "Early watch"


def _promotion_recommendation(
    *,
    score: float,
    structural_count: int,
    recent_confirmation_count: int,
) -> dict[str, Any]:
    eligible = score >= READY_FOR_CANDIDATE_THRESHOLD and structural_count >= 1
    if eligible:
        reason = "結構性事件已成形，且 30 天內有足夠訊號交叉確認，可手動升級成 candidate dossier。"
        label = "建議升級成候選研究"
    elif score >= 5.0:
        reason = "已累積高訊號觀察，但仍需更多 primary-source 或第二事件確認。"
        label = "先維持觀察"
    elif recent_confirmation_count:
        reason = "已有初步事件，但目前尚不足以建立完整 dossier。"
        label = "持續收集事件"
    else:
        reason = "目前仍偏早期線索，先保留在 observation lake。"
        label = "早期觀察"
    return {
        "eligible": eligible,
        "label": label,
        "reason": reason,
        "recommended_origin": "observation_lake",
    }


def _normalize_relation_type(value: str | None, *, default: str = "manual") -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized in {"supply_chain", "supply-chain", "chain"}:
        normalized = "supply_chain"
    if normalized in OBSERVATION_RELATION_TYPES:
        return normalized
    return default


def _normalize_opened_from(value: str | None, *, default: str = "manual") -> str:
    normalized = _normalize_relation_type(value, default=default)
    return normalized if normalized in OBSERVATION_OPENED_FROM else default


def _normalize_event_family(value: str | None, *, default: str = "peer_readthrough") -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in OBSERVATION_EVENT_FAMILIES else default


def _normalize_signal_strength(value: str | None, *, default: str = "medium") -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in SIGNAL_STRENGTH_VALUES else default


def _theme_match_bonus(theme_ids: list[str], graph_row: dict[str, Any] | None) -> float:
    if not graph_row:
        return 0.0
    return 0.6 if graph_row.get("theme_id") in theme_ids else 0.0


def _score_observation(
    item: dict[str, Any],
    events: list[dict[str, Any]],
    *,
    graph_row: dict[str, Any] | None,
) -> tuple[float, dict[str, Any]]:
    total = 0.0
    price_exception_total = 0.0
    structural_count = 0
    recent_confirmation_count = 0
    thirty_days_ago = date.today() - timedelta(days=30)
    for event in events:
        family = event["event_family"]
        relation_weight = RELATION_WEIGHTS.get(event["relation_type"], 0.5)
        family_weight = (graph_row or {}).get("default_event_weights", {}).get(family, EVENT_FAMILY_WEIGHTS[family])
        signal_weight = SIGNAL_STRENGTH_VALUES[event["signal_strength"]]
        contribution = family_weight * relation_weight * signal_weight
        if event["is_primary_source"]:
            contribution += 0.6
        occurred_at = event.get("occurred_at") or _today_iso()
        try:
            if date.fromisoformat(occurred_at) >= thirty_days_ago:
                recent_confirmation_count += 1
                contribution += 0.35
        except ValueError:
            pass
        if family == "price_exception":
            remaining = max(PRICE_EXCEPTION_CAP - price_exception_total, 0.0)
            contribution = min(contribution, remaining)
            price_exception_total += contribution
        else:
            structural_count += 1
        total += contribution

    total += _theme_match_bonus(item["theme_ids"], graph_row)
    if recent_confirmation_count >= 2:
        total += 0.75
    score = round(total, 2)
    return score, {
        "structural_count": structural_count,
        "recent_confirmation_count": recent_confirmation_count,
    }


def _normalize_observation_item(
    item: dict[str, Any],
    *,
    graph: dict[str, Any],
    event_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    ticker = str(item.get("ticker", "")).upper()
    graph_row = _relation_index(graph).get(ticker)
    selected_event_ids = [str(value) for value in item.get("selected_event_ids", []) if str(value).strip()]
    events = [row for row in event_rows if row.get("observation_id") == item.get("observation_id")]
    if selected_event_ids:
        events = [row for row in events if row["event_id"] in selected_event_ids]
    score, metrics = _score_observation(item, events, graph_row=graph_row)
    status = str(item.get("status", "open")).strip() or "open"
    if status not in OBSERVATION_STATUSES:
        status = "open"
    if status == "open" and score >= READY_FOR_CANDIDATE_THRESHOLD:
        status = "ready_for_candidate"
    last_event_at = ""
    if events:
        last_event_at = max(str(event.get("occurred_at", "")) for event in events)
    promotion_recommendation = _promotion_recommendation(
        score=score,
        structural_count=metrics["structural_count"],
        recent_confirmation_count=metrics["recent_confirmation_count"],
    )
    if status in {"dismissed", "archived", "promoted"}:
        promotion_recommendation["eligible"] = False
    return {
        "observation_id": str(item.get("observation_id", "")),
        "ticker": ticker,
        "company_name": str(item.get("company_name") or _company_name_for(ticker, graph)),
        "status": status,
        "intended_horizon": str(item.get("intended_horizon") or (graph_row or {}).get("default_horizon", DEFAULT_INTENDED_HORIZON)),
        "opened_from": _normalize_opened_from(item.get("opened_from"), default="manual"),
        "theme_ids": [str(value) for value in item.get("theme_ids", []) if str(value).strip()],
        "peer_refs": [str(value).upper() for value in item.get("peer_refs", []) if str(value).strip()],
        "chain_refs": [str(value).upper() for value in item.get("chain_refs", []) if str(value).strip()],
        "score": score,
        "score_label": _score_label(score),
        "why_now": str(item.get("why_now", "")).strip(),
        "last_event_at": last_event_at,
        "selected_event_ids": [event["event_id"] for event in events],
        "promotion_recommendation": promotion_recommendation,
        "event_count": len(events),
        "primary_source_event_count": sum(1 for row in events if row.get("is_primary_source")),
        "updated_at": str(item.get("updated_at") or item.get("created_at") or _today_iso()),
        "created_at": str(item.get("created_at") or _today_iso()),
        "notes": str(item.get("notes", "")),
    }


def rebuild_observation_lake(research_root: Path) -> dict[str, Any]:
    ensure_observation_system_files(research_root)
    graph = load_observation_graph(research_root / "system" / OBSERVATION_GRAPH_PATH.name)
    event_rows = load_observation_events(research_root / "system" / OBSERVATION_EVENTS_PATH.name)
    lake = load_observation_lake(research_root / "system" / OBSERVATION_LAKE_PATH.name)
    normalized = [
        _normalize_observation_item(item, graph=graph, event_rows=event_rows)
        for item in lake.get("items", [])
        if str(item.get("observation_id", "")).strip()
    ]
    normalized.sort(
        key=lambda row: (
            row["status"] not in {"ready_for_candidate", "open"},
            -float(row["score"]),
            row["last_event_at"] or "",
            row["ticker"],
        )
    )
    payload = {
        "generated_at": _today_iso(),
        "items": normalized,
    }
    write_json(research_root / "system" / OBSERVATION_LAKE_PATH.name, payload)
    return payload


def _normalize_observation_event(
    observation_id: str,
    ticker: str,
    graph: dict[str, Any],
    raw_event: dict[str, Any],
) -> dict[str, Any]:
    relation_type = _normalize_relation_type(raw_event.get("relation_type"), default="manual")
    event_family = _normalize_event_family(
        raw_event.get("event_family"),
        default="supply_chain_readthrough" if relation_type == "supply_chain" else "peer_readthrough",
    )
    occurred_at = str(raw_event.get("occurred_at") or _today_iso())
    title = str(raw_event.get("title") or "").strip()
    related_ticker = str(raw_event.get("related_ticker") or "").upper()
    event_id = str(raw_event.get("event_id") or "").strip()
    if not event_id:
        event_id = sha1_digest(
            observation_id,
            ticker,
            related_ticker,
            event_family,
            occurred_at,
            title,
        )
    return {
        "event_id": event_id,
        "observation_id": observation_id,
        "ticker": ticker,
        "related_ticker": related_ticker,
        "relation_type": relation_type,
        "event_family": event_family,
        "occurred_at": occurred_at,
        "title": title,
        "summary": str(raw_event.get("summary") or raw_event.get("title") or "").strip(),
        "signal_strength": _normalize_signal_strength(raw_event.get("signal_strength"), default="medium"),
        "source_url": str(raw_event.get("source_url") or ""),
        "is_primary_source": bool(raw_event.get("is_primary_source", False)),
        "selected_for_watch": bool(raw_event.get("selected_for_watch", True)),
        "source_event_id": str(raw_event.get("source_event_id") or ""),
        "source_theme_id": str(raw_event.get("source_theme_id") or ""),
        "related_company_name": _company_name_for(related_ticker, graph) if related_ticker else "",
    }


def _persist_lake_items(research_root: Path, items: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "generated_at": _today_iso(),
        "items": items,
    }
    write_json(research_root / "system" / OBSERVATION_LAKE_PATH.name, payload)
    return rebuild_observation_lake(research_root)


def _lake_items(research_root: Path) -> list[dict[str, Any]]:
    return list(load_observation_lake(research_root / "system" / OBSERVATION_LAKE_PATH.name).get("items", []))


def _open_observation_id(ticker: str, why_now: str) -> str:
    return f"obs-{ticker.lower()}-{sha1_digest(ticker, why_now, _today_iso())[:8]}"


def open_observation(
    research_root: Path,
    *,
    ticker: str,
    company_name: str,
    intended_horizon: str,
    opened_from: str,
    theme_ids: list[str] | None = None,
    peer_refs: list[str] | None = None,
    chain_refs: list[str] | None = None,
    why_now: str,
    selected_events: list[dict[str, Any]] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    ensure_observation_system_files(research_root)
    graph = load_observation_graph(research_root / "system" / OBSERVATION_GRAPH_PATH.name)
    ticker = str(ticker).upper()
    why_now = why_now.strip()
    items = _lake_items(research_root)
    existing = next(
        (
            item
            for item in items
            if item.get("ticker") == ticker and item.get("status") in {"open", "ready_for_candidate"}
        ),
        None,
    )
    if existing is not None:
        return include_events(
            research_root,
            observation_id=existing["observation_id"],
            selected_events=selected_events or [],
            notes=notes or why_now,
        )

    observation_id = _open_observation_id(ticker, why_now)
    created_at = _today_iso()
    item = {
        "observation_id": observation_id,
        "ticker": ticker,
        "company_name": company_name or _company_name_for(ticker, graph),
        "status": "open",
        "intended_horizon": intended_horizon or DEFAULT_INTENDED_HORIZON,
        "opened_from": _normalize_opened_from(opened_from),
        "theme_ids": [str(value) for value in (theme_ids or []) if str(value).strip()],
        "peer_refs": [str(value).upper() for value in (peer_refs or []) if str(value).strip()],
        "chain_refs": [str(value).upper() for value in (chain_refs or []) if str(value).strip()],
        "score": 0.0,
        "score_label": "Early watch",
        "why_now": why_now,
        "last_event_at": "",
        "selected_event_ids": [],
        "promotion_recommendation": {
            "eligible": False,
            "label": "早期觀察",
            "reason": "先建立 observation item，再讓事件累積評分。",
            "recommended_origin": "observation_lake",
        },
        "created_at": created_at,
        "updated_at": created_at,
        "notes": notes,
    }
    items.append(item)
    _persist_lake_items(research_root, items)
    if selected_events:
        return include_events(
            research_root,
            observation_id=observation_id,
            selected_events=selected_events,
            notes=notes or why_now,
        )
    return rebuild_observation_lake(research_root)


def include_events(
    research_root: Path,
    *,
    observation_id: str,
    selected_events: list[dict[str, Any]],
    notes: str = "",
) -> dict[str, Any]:
    ensure_observation_system_files(research_root)
    graph = load_observation_graph(research_root / "system" / OBSERVATION_GRAPH_PATH.name)
    items = _lake_items(research_root)
    target = next((item for item in items if item.get("observation_id") == observation_id), None)
    if target is None:
        raise KeyError(f"Unknown observation_id: {observation_id}")
    rows = [
        _normalize_observation_event(observation_id, target["ticker"], graph, row)
        for row in selected_events
        if str(row.get("title") or "").strip()
    ]
    if rows:
        append_jsonl(research_root / "system" / OBSERVATION_EVENTS_PATH.name, rows)
    for item in items:
        if item.get("observation_id") == observation_id:
            item["updated_at"] = _today_iso()
            if notes:
                item["notes"] = notes
            break
    return _persist_lake_items(research_root, items)


def dismiss_observation(
    research_root: Path,
    *,
    observation_id: str,
    reason: str = "",
) -> dict[str, Any]:
    items = _lake_items(research_root)
    for item in items:
        if item.get("observation_id") == observation_id:
            item["status"] = "dismissed"
            item["updated_at"] = _today_iso()
            if reason:
                item["notes"] = reason
            break
    else:
        raise KeyError(f"Unknown observation_id: {observation_id}")
    return _persist_lake_items(research_root, items)


def promote_observation(
    research_root: Path,
    *,
    observation_id: str,
    stage: str = "candidate",
    note: str = "",
) -> dict[str, Any]:
    graph = load_observation_graph(research_root / "system" / OBSERVATION_GRAPH_PATH.name)
    lake = rebuild_observation_lake(research_root)
    item = next((row for row in lake["items"] if row["observation_id"] == observation_id), None)
    if item is None:
        raise KeyError(f"Unknown observation_id: {observation_id}")
    research_topic = note.strip() or item["why_now"] or f"Observation-lake promotion for {item['ticker']}."
    upsert_candidate_dossier(
        research_root,
        ticker=item["ticker"],
        company_name=item["company_name"] or _company_name_for(item["ticker"], graph),
        research_topic=research_topic,
        candidate_origin="observation_lake",
        research_stage=stage,
        radar_flags=[],
        radar_summary=f"Promoted from Observation Lake. {item['promotion_recommendation']['reason']}",
        radar_risk_level="medium" if item["score"] >= READY_FOR_CANDIDATE_THRESHOLD else "low",
        note=note or "Promoted from observation lake after manual review.",
    )
    items = _lake_items(research_root)
    for row in items:
        if row.get("observation_id") == observation_id:
            row["status"] = "promoted"
            row["updated_at"] = _today_iso()
            row["notes"] = note or row.get("notes", "")
            break
    return _persist_lake_items(research_root, items)


def _event_draft_from_source(
    *,
    source_card: dict[str, Any],
    relation_type: str,
    target_ticker: str,
    target_theme_id: str,
) -> dict[str, Any]:
    seed_event = (source_card.get("key_events") or [None])[0]
    if seed_event:
        title = seed_event.get("title", "")
        occurred_at = seed_event.get("occurred_at", _today_iso())
        summary = f"{source_card['ticker']} 的關鍵事件可延伸到 {target_ticker} 的 {relation_type} 觀察。"
        source_url = seed_event.get("href", "")
        source_event_id = seed_event.get("event_id", "")
    else:
        title = f"{source_card['ticker']} 近期 thesis 進入需要延伸觀察的狀態。"
        occurred_at = _today_iso()
        summary = f"基於 {source_card['ticker']} 的最新研究節奏，延伸建立 {target_ticker} 的 {relation_type} 觀察。"
        source_url = source_card.get("internal_research_path", "")
        source_event_id = ""
    return {
        "related_ticker": source_card["ticker"],
        "relation_type": relation_type,
        "event_family": "supply_chain_readthrough" if relation_type == "supply_chain" else "peer_readthrough",
        "occurred_at": occurred_at,
        "title": title,
        "summary": summary,
        "signal_strength": "high" if source_card.get("priority_score", 0) >= 7 else "medium",
        "source_url": source_url,
        "is_primary_source": True,
        "selected_for_watch": True,
        "source_event_id": source_event_id,
        "source_theme_id": target_theme_id,
    }


def build_observation_workspace(
    research_root: Path,
    *,
    cards: list[dict[str, Any]],
) -> dict[str, Any]:
    ensure_observation_system_files(research_root)
    graph = load_observation_graph(research_root / "system" / OBSERVATION_GRAPH_PATH.name)
    lake = rebuild_observation_lake(research_root)
    relation_index = _relation_index(graph)
    tracked_tickers = {card["ticker"] for card in cards}
    open_items = {
        item["ticker"]: item
        for item in lake["items"]
        if item["status"] in {"open", "ready_for_candidate"}
    }
    recommendations: list[dict[str, Any]] = []
    seen_recommendations: set[tuple[str, str, str]] = set()
    for card in cards:
        row = relation_index.get(card["ticker"])
        if row is None:
            continue
        related_groups = (
            ("peer", row.get("peer_tickers", [])),
            ("supply_chain", row.get("upstream_tickers", [])),
            ("supply_chain", row.get("downstream_tickers", [])),
        )
        for relation_type, tickers in related_groups:
            for related_ticker in tickers:
                if related_ticker in tracked_tickers:
                    continue
                key = (card["ticker"], relation_type, related_ticker)
                if key in seen_recommendations:
                    continue
                seen_recommendations.add(key)
                existing = open_items.get(related_ticker)
                recommendations.append(
                    {
                        "suggestion_id": f"rec-{sha1_digest(*key)[:10]}",
                        "ticker": related_ticker,
                        "company_name": _company_name_for(related_ticker, graph),
                        "relation_type": relation_type,
                        "opened_from": relation_type,
                        "source_ticker": card["ticker"],
                        "source_company_name": card["company_name"],
                        "theme_ids": [row["theme_id"]],
                        "intended_horizon": row.get("default_horizon", DEFAULT_INTENDED_HORIZON),
                        "why_now": f"{card['ticker']} 的關鍵事件與 thesis 節奏，值得延伸觀察 {related_ticker} 的 {relation_type} read-through。",
                        "event_drafts": [
                            _event_draft_from_source(
                                source_card=card,
                                relation_type=relation_type,
                                target_ticker=related_ticker,
                                target_theme_id=row["theme_id"],
                            )
                        ],
                        "existing_observation_id": None if existing is None else existing["observation_id"],
                        "existing_status": None if existing is None else existing["status"],
                    }
                )
    recommendations.sort(
        key=lambda row: (
            row["existing_observation_id"] is not None,
            row["relation_type"] != "peer",
            row["ticker"],
        )
    )
    summary = {
        "total_count": len(lake["items"]),
        "open_count": sum(1 for item in lake["items"] if item["status"] == "open"),
        "ready_count": sum(1 for item in lake["items"] if item["status"] == "ready_for_candidate"),
        "promoted_count": sum(1 for item in lake["items"] if item["status"] == "promoted"),
        "dismissed_count": sum(1 for item in lake["items"] if item["status"] == "dismissed"),
        "average_score": round(
            sum(float(item["score"]) for item in lake["items"]) / len(lake["items"]),
            2,
        ) if lake["items"] else 0.0,
    }
    return {
        "summary": summary,
        "items": lake["items"],
        "watchlist_recommendations": recommendations[:8],
        "graph": graph,
    }


def observation_context_for_ticker(
    ticker: str,
    *,
    graph: dict[str, Any],
) -> dict[str, Any] | None:
    row = _relation_index(graph).get(ticker)
    if row is None:
        return None
    companies = graph.get("companies", {})

    def _items(values: list[str], relation_type: str) -> list[dict[str, str]]:
        return [
            {
                "ticker": value,
                "company_name": companies.get(value, DEFAULT_COMPANY_NAMES.get(value, value)),
                "relation_type": relation_type,
            }
            for value in values
        ]

    return {
        "theme_id": row["theme_id"],
        "default_horizon": row.get("default_horizon", DEFAULT_INTENDED_HORIZON),
        "peers": _items(row.get("peer_tickers", []), "peer"),
        "upstream": _items(row.get("upstream_tickers", []), "supply_chain"),
        "downstream": _items(row.get("downstream_tickers", []), "supply_chain"),
    }
