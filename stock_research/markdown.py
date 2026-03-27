from __future__ import annotations

from typing import Any


def _render_table(headers: list[str], rows: list[list[str]]) -> str:
    header_row = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join([header_row, separator, body]).strip()


def render_current_report(state: dict[str, Any], recent_events: list[dict[str, Any]] | None = None) -> str:
    thesis = state["thesis"]
    assumptions = state["assumptions"]
    scenarios = state["scenarios"]
    action_rules = state["action_rules"]
    risks = state["risks"]
    valuation = state["valuation_regime"]
    version_log = state["version_log"]
    recent_events = recent_events or []

    assumption_rows = [
        [
            item["assumption_id"],
            item["statement"],
            item["status"],
            f'{item["confidence"]:.2f}',
            item["invalidation_condition"],
        ]
        for item in assumptions
    ]
    scenario_rows = [
        [
            item["scenario_id"],
            item["trigger"],
            item["logic"],
            item["action"],
        ]
        for item in scenarios
    ]
    risk_rows = [
        [
            item["risk_id"],
            item["statement"],
            item["tier"],
            item["response"],
        ]
        for item in risks
    ]
    action_rows = [
        [
            item["action_rule_id"],
            item["kind"],
            item["condition"],
            item["action"],
        ]
        for item in action_rules
    ]
    version_rows = [
        [
            item["version"],
            item["date"],
            item["reason"],
            item["impact"],
        ]
        for item in version_log
    ]
    event_rows = [
        [
            item["occurred_at"],
            item["source_type"],
            item["title"],
            item["marginal_impact"],
            item["decision"],
        ]
        for item in recent_events[:8]
    ]

    lines = [
        f"# {state['ticker']} Living Thesis",
        "",
        _render_table(
            ["Field", "Value"],
            [
                ["Company", state["company_name"]],
                ["Research Topic", state["research_topic"]],
                ["Holding Period", state["holding_period"]],
                ["Research Type", state["research_type"]],
                ["Last Reviewed", state["last_reviewed_at"]],
                ["Next Review", state["next_review_at"]],
                ["Current Action", state["current_action"]],
                ["Thesis Confidence", f"{state['confidence']:.2f}"],
            ],
        ),
        "",
        "## Delta From Previous Version",
        "",
        "\n".join(f"- {point}" for point in state["latest_delta"]),
        "",
        "## Core Thesis",
        "",
        f"- `thesis_id`: `{thesis['thesis_id']}`",
        f"- Thesis: {thesis['statement']}",
        f"- Core catalyst: {thesis['core_catalyst']}",
        f"- Market blind spot: {thesis['market_blind_spot']}",
        f"- Verification date: {thesis['verification_date']}",
        f"- Expiry condition: {thesis['expiry_condition']}",
        "",
        "## Observation Framework",
        "",
        f"- Primary variables: {', '.join(state['primary_observation_variables'])}",
        f"- Secondary variables: {', '.join(state['secondary_observation_variables'])}",
        f"- Noise filters: {', '.join(state['noise_filters'])}",
        f"- Thresholds: price gap {state['thresholds']['price_gap_pct']}%, abnormal volume {state['thresholds']['volume_ratio']}x, deep refresh every {state['thresholds']['deep_refresh_days']} days",
        "",
        "## Assumption Status",
        "",
        _render_table(["ID", "Assumption", "Status", "Confidence", "Invalidation"], assumption_rows),
        "",
        "## Risk Register",
        "",
        _render_table(["ID", "Risk", "Tier", "Response"], risk_rows),
        "",
        "## Valuation Regime",
        "",
        f"- Current yardstick: {valuation['current_yardstick']}",
        f"- Better yardstick: {valuation['better_yardstick']}",
        f"- Switch trigger: {valuation['switch_trigger']}",
        f"- Re-rating logic: {valuation['re_rating_logic']}",
        f"- Associated risk: {valuation['associated_risk']}",
        "",
        "## Scenario Actions",
        "",
        _render_table(["ID", "Trigger", "Logic", "Action"], scenario_rows),
        "",
        "## Action Rules",
        "",
        _render_table(["ID", "Kind", "Condition", "Action"], action_rows),
        "",
        "## Follow-Up",
        "",
        f"- Next must-check data: {state['next_must_check_data']}",
        f"- Research debt: {', '.join(state['research_debt'])}",
        "",
        "## Source Manifest",
        "",
        "\n".join(
            f"- `{source['source_id']}` ({source['type']}): {source['label']} - {source['url']}"
            for source in state["source_manifest"]
        ),
        "",
        "## Version Log",
        "",
        _render_table(["Version", "Date", "Reason", "Impact"], version_rows),
    ]

    if event_rows:
        lines.extend(
            [
                "",
                "## Recent Event Log",
                "",
                _render_table(["Date", "Source", "Event", "Impact", "Decision"], event_rows),
            ]
        )

    return "\n".join(lines).strip() + "\n"


def render_review_summary(
    state: dict[str, Any],
    review_summary: str,
    changed_assumptions: list[dict[str, Any]],
    action_rule_delta: list[dict[str, Any]],
) -> str:
    assumption_lines = "\n".join(
        f"- `{item['assumption_id']}`: {item['summary']}" for item in changed_assumptions
    ) or "- None"
    action_lines = "\n".join(
        f"- `{item['action_rule_id']}`: {item['summary']}" for item in action_rule_delta
    ) or "- None"
    return (
        f"# {state['ticker']} Refresh Review Summary\n\n"
        f"- Reviewed at: {state['last_reviewed_at']}\n"
        f"- Next review: {state['next_review_at']}\n"
        f"- Current action: {state['current_action']}\n\n"
        "## Summary\n\n"
        f"{review_summary}\n\n"
        "## Assumption Changes\n\n"
        f"{assumption_lines}\n\n"
        "## Action Rule Delta\n\n"
        f"{action_lines}\n"
    )
