from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, timedelta
from typing import Any

from .config import DEFAULT_OPENAI_MODEL
from .storage import deep_merge


def _extract_json_blob(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Model response did not contain JSON.")
    return json.loads(match.group(0))


def fallback_refresh(state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    updated_state = json.loads(json.dumps(state))
    new_events = context["new_events"]
    summaries = [event["title"] for event in new_events[:3]]
    if not summaries:
        summaries = ["Scheduled deep refresh without a new material event; state carried forward and review date advanced."]
    changed_assumptions: list[dict[str, Any]] = []
    for event in new_events:
        impact = event["marginal_impact"]
        status = "watch"
        if impact == "+":
            status = "reinforced"
        elif impact == "-":
            status = "pressured"
        for assumption in updated_state["assumptions"]:
            if assumption["assumption_id"] not in event["affected_assumption_ids"]:
                continue
            if assumption["status"] != status:
                changed_assumptions.append(
                    {
                        "assumption_id": assumption["assumption_id"],
                        "summary": f"{assumption['status']} -> {status} because of {event['title']}",
                    }
                )
            assumption["status"] = status
    updated_state["latest_delta"] = summaries
    updated_state["last_reviewed_at"] = date.today().isoformat()
    deep_refresh_days = updated_state["thresholds"]["deep_refresh_days"]
    updated_state["next_review_at"] = (date.today() + timedelta(days=deep_refresh_days)).isoformat()
    review_summary = "Automatic fallback refresh used. Review the generated diff before merging."
    action_rule_delta = [
        {
            "action_rule_id": rule["action_rule_id"],
            "summary": "No rule text changed; review whether the trigger still matches the thesis."
        }
        for rule in updated_state["action_rules"]
        if rule["kind"] in {"add", "trim", "exit"}
    ][:2]
    return {
        "updated_state": updated_state,
        "changed_assumptions": changed_assumptions,
        "action_rule_delta": action_rule_delta,
        "review_summary": review_summary,
    }


def _request_openai(api_key: str, model: str, prompt: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an equity-research state updater. "
                    "Preserve stable ids, update only what the new evidence changes, "
                    "and respond with JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI request failed: {exc}") from exc
    content = body["choices"][0]["message"]["content"]
    return _extract_json_blob(content)


def generate_refresh(state: dict[str, Any], current_markdown: str, context: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback_refresh(state, context)

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    prompt = json.dumps(
        {
            "instructions": {
                "goal": "Update the research state from prior state plus only the new evidence bundle.",
                "rules": [
                    "Keep ticker, thesis_id, assumption_id, and action_rule_id stable.",
                    "Do not rewrite the thesis from scratch if the evidence only changes confidence or status.",
                    "Use summary_points to describe the delta from the previous version.",
                    "Return review_summary, changed_assumptions, action_rule_delta, and updated_state.",
                    "Set last_reviewed_at to today and choose a sensible next_review_at.",
                ],
            },
            "current_markdown": current_markdown,
            "current_state": state,
            "refresh_context": context,
            "output_shape": {
                "review_summary": "string",
                "summary_points": ["string"],
                "changed_assumptions": [{"assumption_id": "string", "summary": "string"}],
                "action_rule_delta": [{"action_rule_id": "string", "summary": "string"}],
                "updated_state": {"copy_all_existing_fields_and_edit_only_needed_ones": True},
            },
        },
        ensure_ascii=False,
    )
    raw = _request_openai(api_key, model, prompt)
    updated_state = deep_merge(state, raw.get("updated_state", {}))
    if "summary_points" in raw:
        updated_state["latest_delta"] = raw["summary_points"]
    return {
        "updated_state": updated_state,
        "changed_assumptions": raw.get("changed_assumptions", []),
        "action_rule_delta": raw.get("action_rule_delta", []),
        "review_summary": raw.get("review_summary", "Manual review required."),
    }
