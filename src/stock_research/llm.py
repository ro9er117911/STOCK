from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, timedelta
from typing import Any

from .config import DEFAULT_OPENAI_MODEL, DEFAULT_TRANSLATION_MODEL
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


def _request_openai_content(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    response_format: dict[str, str] | None = None,
    temperature: float = 0.2,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format is not None:
        payload["response_format"] = response_format
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
    return body["choices"][0]["message"]["content"]


def _request_openai_json(api_key: str, model: str, prompt: str) -> dict[str, Any]:
    content = _request_openai_content(
        api_key,
        model,
        [
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
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return _extract_json_blob(content)


def generate_refresh(state: dict[str, Any], current_markdown: str, context: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback_refresh(state, context)

    model = os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
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
    raw = _request_openai_json(api_key, model, prompt)
    updated_state = deep_merge(state, raw.get("updated_state", {}))
    if "summary_points" in raw:
        updated_state["latest_delta"] = raw["summary_points"]
    return {
        "updated_state": updated_state,
        "changed_assumptions": raw.get("changed_assumptions", []),
        "action_rule_delta": raw.get("action_rule_delta", []),
        "review_summary": raw.get("review_summary", "Manual review required."),
    }


def translate_markdown(markdown_text: str, *, context_label: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return markdown_text

    model = os.getenv("TRANSLATION_MODEL") or DEFAULT_TRANSLATION_MODEL
    content = _request_openai_content(
        api_key,
        model,
        [
            {
                "role": "system",
                "content": (
                    "You translate investment research markdown into colloquial Traditional Chinese for Taiwan. "
                    "Translate section headings, bullet labels, and table headers too, unless they are IDs, tickers, code spans, file paths, or URLs. "
                    "Preserve markdown structure, tables, IDs, tickers, numbers, dates, links, code spans, and file paths exactly. "
                    "Do not summarize or omit content. Use natural, conversational zh-TW wording for investors. "
                    "Preferred glossary: Living Thesis=持續更新研究, Refresh Review Summary=更新檢視摘要, "
                    "Reviewed at=檢視日期, Next review=下次檢查, Current action=目前操作, "
                    "Delta From Previous Version=與前版差異, Assumption Changes=假設變更, Action Rule Delta=操作規則變更."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Translate the following {context_label} into colloquial Traditional Chinese (zh-TW). "
                    "Keep all markdown structure unchanged.\n\n"
                    f"{markdown_text}"
                ),
            },
        ],
        temperature=0.1,
    )
    translated = content.strip()
    return translated if translated else markdown_text


def translate_structured_payload(payload: dict[str, Any], *, context_label: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return payload

    model = os.getenv("TRANSLATION_MODEL") or DEFAULT_TRANSLATION_MODEL
    prompt = json.dumps(
        {
            "task": (
                "Translate only the human-facing string values in this JSON payload into colloquial "
                "Traditional Chinese for Taiwan."
            ),
            "rules": [
                "Preserve every key, nesting shape, array length, boolean, number, date, URL, and ticker exactly.",
                "Do not rename ids or path-like values.",
                "Translate summaries, labels, and descriptive prose into natural zh-TW.",
                "Return JSON only.",
            ],
            "context_label": context_label,
            "payload": payload,
        },
        ensure_ascii=False,
    )
    try:
        translated = _request_openai_json(api_key, model, prompt)
    except (RuntimeError, ValueError):
        return payload
    return translated.get("payload", payload) if "payload" in translated else translated
