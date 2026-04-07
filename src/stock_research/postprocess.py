from __future__ import annotations

import copy
from typing import Any


STATUS_ORDER = {
    "pressured": 0,
    "watch": 1,
    "reinforced": 2,
}


def _ordered_ids(raw_changes: list[dict[str, Any]], previous_state: dict[str, Any], updated_state: dict[str, Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in raw_changes:
        assumption_id = item.get("assumption_id")
        if assumption_id and assumption_id not in seen:
            ordered.append(assumption_id)
            seen.add(assumption_id)

    previous_map = {item["assumption_id"]: item for item in previous_state["assumptions"]}
    for item in updated_state["assumptions"]:
        assumption_id = item["assumption_id"]
        previous = previous_map.get(assumption_id)
        if previous is None:
            if assumption_id not in seen:
                ordered.append(assumption_id)
                seen.add(assumption_id)
            continue
        status_changed = previous["status"] != item["status"]
        confidence_changed = abs(item["confidence"] - previous["confidence"]) >= 0.02
        if (status_changed or confidence_changed) and assumption_id not in seen:
            ordered.append(assumption_id)
            seen.add(assumption_id)
    return ordered


def _related_events(context: dict[str, Any], assumption_id: str) -> list[dict[str, Any]]:
    material_events = context.get("material_events") or context.get("new_events") or []
    return [
        event
        for event in material_events
        if assumption_id in event.get("affected_assumption_ids", [])
    ]


def _event_reason(events: list[dict[str, Any]]) -> str:
    if not events:
        return "the latest evidence bundle"
    titles = [event["title"].rstrip(".") for event in events[:2]]
    if len(titles) == 1:
        return titles[0]
    return f"{titles[0]} and {titles[1]}"


def _status_rank(status: str) -> int:
    return STATUS_ORDER.get(status, 1)


def _polish_assumption_change(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    events: list[dict[str, Any]],
    raw_summary: str | None,
) -> str:
    reason = _event_reason(events)
    if previous is None:
        return f"Added to the tracked thesis set after {reason}."

    previous_status = previous["status"]
    current_status = current["status"]
    confidence_delta = round(current["confidence"] - previous["confidence"], 2)
    previous_confidence = f"{previous['confidence']:.2f}"
    current_confidence = f"{current['confidence']:.2f}"

    if previous_status == current_status:
        if confidence_delta >= 0.02:
            return (
                f"Status remains {current_status}, but confidence rises from {previous_confidence} "
                f"to {current_confidence} after {reason}."
            )
        if confidence_delta <= -0.02:
            return (
                f"Status remains {current_status}, but confidence slips from {previous_confidence} "
                f"to {current_confidence} because of {reason}."
            )
        if raw_summary and "->" not in raw_summary:
            return raw_summary
        return f"Status remains {current_status}; the latest evidence does not yet justify a re-rating."

    if _status_rank(current_status) > _status_rank(previous_status):
        return (
            f"Status improves from {previous_status} to {current_status}, with confidence moving "
            f"from {previous_confidence} to {current_confidence} after {reason}."
        )
    return (
        f"Status weakens from {previous_status} to {current_status}, with confidence moving "
        f"from {previous_confidence} to {current_confidence} because of {reason}."
    )


def _polish_action_rule_delta(
    raw_delta: list[dict[str, Any]],
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    polished: list[dict[str, Any]] = []
    material_events = context.get("material_events") or context.get("new_events") or []
    event_reason = _event_reason(material_events)
    for item in raw_delta:
        summary = item.get("summary", "").strip()
        if not summary:
            summary = f"Rule text is unchanged; reassess trigger relevance after {event_reason}."
        elif "No rule text changed" in summary:
            summary = f"Rule text is unchanged; keep watching trigger relevance after {event_reason}."
        polished.append(
            {
                "action_rule_id": item["action_rule_id"],
                "summary": summary,
            }
        )
    return polished


def _build_review_summary(
    previous_state: dict[str, Any],
    updated_state: dict[str, Any],
    context: dict[str, Any],
    polished_changes: list[dict[str, Any]],
) -> str:
    material_events = context.get("material_events") or context.get("new_events") or []
    if not material_events:
        return (
            f"No new material event arrived for {updated_state['ticker']}. "
            "The thesis stays in place and the review clock moves forward on schedule."
        )

    upgraded = 0
    weakened = 0
    for item in updated_state["assumptions"]:
        previous = next(
            (row for row in previous_state["assumptions"] if row["assumption_id"] == item["assumption_id"]),
            None,
        )
        if previous is None:
            continue
        if _status_rank(item["status"]) > _status_rank(previous["status"]) or item["confidence"] - previous["confidence"] >= 0.02:
            upgraded += 1
        elif _status_rank(item["status"]) < _status_rank(previous["status"]) or previous["confidence"] - item["confidence"] >= 0.02:
            weakened += 1

    stance = "strengthens"
    if weakened and not upgraded:
        stance = "pressures"
    elif weakened and upgraded:
        stance = "mixed-impact"

    opening = {
        "strengthens": "New evidence strengthens the existing thesis without changing the core setup.",
        "pressures": "New evidence pressures the thesis and requires closer follow-through on the next check-in.",
        "mixed-impact": "New evidence is mixed: some parts of the thesis improve while other parts still need caution.",
    }[stance]
    event_clause = f"Key drivers this cycle were { _event_reason(material_events) }."
    if polished_changes:
        assumption_clause = f"The main assumption shift is: {polished_changes[0]['summary']}"
    else:
        assumption_clause = "The headline thesis remains in place with no assumption re-rating."
    return f"{opening} {event_clause} {assumption_clause}"


def _build_latest_delta(
    previous_state: dict[str, Any],
    updated_state: dict[str, Any],
    context: dict[str, Any],
    polished_changes: list[dict[str, Any]],
) -> list[str]:
    material_events = context.get("material_events") or context.get("new_events") or []
    if not material_events:
        return [
            "No new material event arrived beyond the existing state.",
            "Core thesis and action posture remain intact.",
            "Review timing advanced on the standard cadence.",
        ]

    points = [
        f"Key new input: {_event_reason(material_events)}.",
    ]
    if polished_changes:
        points.extend(item["summary"] for item in polished_changes[:2])
    action_changed = previous_state.get("current_action") != updated_state.get("current_action")
    if action_changed:
        points.append(
            f"Current action shifts from {previous_state['current_action']} to {updated_state['current_action']}."
        )
    else:
        points.append(f"Current action remains {updated_state['current_action']}.")
    return points[:4]


def post_process_refresh_output(
    previous_state: dict[str, Any],
    raw_refresh: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    updated_state = raw_refresh["updated_state"]
    previous_map = {item["assumption_id"]: item for item in previous_state["assumptions"]}
    raw_changes = raw_refresh.get("changed_assumptions", [])
    raw_by_id = {item["assumption_id"]: item.get("summary", "") for item in raw_changes}

    polished_changes: list[dict[str, Any]] = []
    for assumption_id in _ordered_ids(raw_changes, previous_state, updated_state):
        current = next(
            (item for item in updated_state["assumptions"] if item["assumption_id"] == assumption_id),
            None,
        )
        if current is None:
            continue
        polished_changes.append(
            {
                "assumption_id": assumption_id,
                "summary": _polish_assumption_change(
                    previous_map.get(assumption_id),
                    current,
                    _related_events(context, assumption_id),
                    raw_by_id.get(assumption_id),
                ),
            }
        )

    polished = copy.deepcopy(raw_refresh)
    polished["changed_assumptions"] = polished_changes
    polished["action_rule_delta"] = _polish_action_rule_delta(raw_refresh.get("action_rule_delta", []), context)
    polished["review_summary"] = _build_review_summary(previous_state, updated_state, context, polished_changes)
    polished["summary_points"] = _build_latest_delta(previous_state, updated_state, context, polished_changes)
    return polished
