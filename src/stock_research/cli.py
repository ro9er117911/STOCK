from __future__ import annotations

import argparse
import json
from pathlib import Path

from .candidates import upsert_candidate_dossier
from .cockpit_api import serve_cockpit_api
from .config import COCKPIT_API_HOST, COCKPIT_API_PORT
from .config import DRAFT_SUMMARY_PATH, RESEARCH_ROOT
from .dashboard import build_dashboard_bundle
from .digest import build_notification_payload, build_portfolio_digest
from .notify import send_resend_email
from .pipeline import bootstrap_baselines, draft_refreshes, poll_events, sync_research_contracts
from .quick_decision import run_quick_decision
from .research_state import sync_candidate_queue
from .storage import read_json, write_json
from .validator import run_all_checks


REPO_ROOT = Path(__file__).parent.parent.parent if "__file__" in globals() else Path(".")


def main() -> int:
    parser = argparse.ArgumentParser(description="Stock research automation CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap_parser = subparsers.add_parser("bootstrap-baselines", help="Generate baseline research files.")
    bootstrap_parser.add_argument("--force", action="store_true", help="Overwrite existing baseline files.")

    poll_parser = subparsers.add_parser("poll", help="Fetch, normalize, and persist new events.")
    poll_parser.add_argument(
        "--trigger",
        choices=("event", "scheduled", "manual"),
        default="event",
        help="Reason for the refresh pipeline.",
    )
    poll_parser.add_argument("--fixture", default="", help="Optional test event fixture name.")

    draft_parser = subparsers.add_parser("draft-refresh", help="Create draft thesis refreshes for material updates.")
    draft_parser.add_argument(
        "--trigger",
        choices=("event", "scheduled", "manual"),
        default="event",
        help="Reason for the refresh pipeline.",
    )
    draft_parser.add_argument("--fixture", default="", help="Optional test event fixture name.")

    quick_parser = subparsers.add_parser("quick-decision", help="Run a light-track one-liner strategy verdict.")
    quick_parser.add_argument("--ticker", default="", help="Ticker symbol, for example 2330.")
    quick_parser.add_argument("--adr-premium-pct", type=float, default=None, help="Manual ADR premium percentage.")
    quick_parser.add_argument("--local-px", type=float, default=None, help="Current local share price.")
    quick_parser.add_argument("--trigger-description", default="", help="One-line trigger or market setup.")
    quick_parser.add_argument(
        "--rsi-state",
        default="neutral",
        choices=("neutral", "overbought", "oversold"),
        help="Manual RSI state for the light-track momentum rule.",
    )
    quick_parser.add_argument("--adr-px", type=float, default=None, help="Manual ADR price for premium calculation.")
    quick_parser.add_argument("--fx-rate", type=float, default=None, help="Manual FX rate for premium calculation.")
    quick_parser.add_argument("--adr-ratio", type=float, default=None, help="ADR ratio override.")
    quick_parser.add_argument("--no-prompt", action="store_true", help="Fail instead of prompting for missing fields.")

    subparsers.add_parser("build-dashboard", help="Generate the static dashboard site.")

    build_analysis_parser = subparsers.add_parser("build-analysis", help="Build price/drawdown/CAGR analysis artifacts.")
    build_analysis_parser.add_argument("--ticker", default="", help="Single ticker to build. Omit to build all.")
    build_analysis_parser.add_argument(
        "--research-root",
        default="",
        help="Path to research root directory. Defaults to configured RESEARCH_ROOT.",
    )

    subparsers.add_parser("verify", help="Validate setup, connectivity, and market support.")
    subparsers.add_parser("sync-research-contracts", help="Normalize all research states and rebuild candidate queue.")
    subparsers.add_parser("sync-candidates", help="Rebuild the candidate queue from research dossiers.")
    api_parser = subparsers.add_parser("serve-cockpit-api", help="Serve the local writeback API for the cockpit.")
    api_parser.add_argument("--host", default=COCKPIT_API_HOST, help="Host to bind the local API.")
    api_parser.add_argument("--port", type=int, default=COCKPIT_API_PORT, help="Port for the local API.")

    candidate_parser = subparsers.add_parser("upsert-candidate", help="Create or update a candidate research dossier.")
    candidate_parser.add_argument("--ticker", required=True, help="Ticker symbol for the candidate.")
    candidate_parser.add_argument("--company-name", required=True, help="Company name for the candidate dossier.")
    candidate_parser.add_argument("--research-topic", required=True, help="Short research topic for the dossier.")
    candidate_parser.add_argument(
        "--origin",
        default="manual_watchlist",
        choices=("manual_watchlist", "ad_hoc_idea", "quant_radar", "observation_lake"),
        help="How the candidate entered the queue.",
    )
    candidate_parser.add_argument(
        "--stage",
        default="candidate",
        choices=("candidate", "in_research", "ready_to_decide", "active", "rejected", "archived"),
        help="Workflow stage for the dossier.",
    )
    candidate_parser.add_argument("--radar-flag", action="append", default=[], help="Optional radar flag; repeatable.")
    candidate_parser.add_argument("--radar-summary", default="", help="Summary of radar findings.")
    candidate_parser.add_argument("--radar-risk-level", default="none", help="Radar risk level label.")
    candidate_parser.add_argument("--note", default="", help="Short note describing why the dossier changed.")
    candidate_parser.add_argument("--current-action", default="", help="Override current_action in the dossier.")
    candidate_parser.add_argument("--invalidation-reason", default=None, help="Reason for reject/archive state.")
    candidate_parser.add_argument("--decision-status", default="", help="Optional explicit decision status.")

    notify_parser = subparsers.add_parser("send-email", help="Send a material-update notification email.")
    notify_parser.add_argument("--run-type", default="event", help="Pipeline run type for the notification payload.")
    notify_parser.add_argument("--pr-url", required=True, help="Pull request URL to include in the email.")
    notify_parser.add_argument("--dashboard-url", required=True, help="Dashboard URL to include in the email.")
    notify_parser.add_argument(
        "--tickers",
        nargs="*",
        default=[],
        help="Optional ticker list. Defaults to material tickers from the latest draft summary.",
    )

    args = parser.parse_args()
    if args.command == "bootstrap-baselines":
        payload = {"created": bootstrap_baselines(force=args.force)}
    elif args.command == "build-analysis":
        from .performance import build_drawdown_artifact, build_strategy_metrics_artifact
        from .market_data import build_price_series_artifact, build_monthly_metrics_artifact
        research_root = Path(args.research_root) if args.research_root else RESEARCH_ROOT
        EXCLUDED = {"system"}
        tickers_to_build = (
            [args.ticker]
            if args.ticker
            else [
                d.name
                for d in sorted(research_root.iterdir())
                if d.is_dir() and d.name not in EXCLUDED
            ]
        )
        results: list[dict] = []
        for t in tickers_to_build:
            yf_ticker = f"{t}.TW" if t.isdigit() else t
            artifacts_dir = research_root / t / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            built: list[str] = []
            errors: list[str] = []
            for artifact_fn, artifact_name in [
                (build_price_series_artifact, "price_series.json"),
                (build_monthly_metrics_artifact, "monthly_metrics.json"),
                (build_drawdown_artifact, "drawdown_analysis.json"),
                (build_strategy_metrics_artifact, "strategy_metrics.json"),
            ]:
                try:
                    data = artifact_fn(yf_ticker)
                    write_json(artifacts_dir / artifact_name, data)
                    built.append(artifact_name)
                except Exception as e:
                    errors.append(f"{artifact_name}: {e}")
            results.append({"ticker": t, "built": built, "errors": errors})
        payload = {"build_analysis": results}
    elif args.command == "verify":
        return run_all_checks()
    elif args.command == "poll":
        payload = poll_events(trigger=args.trigger, fixture_name=args.fixture or None)
    elif args.command == "draft-refresh":
        payload = draft_refreshes(trigger=args.trigger, fixture_name=args.fixture or None)
    elif args.command == "quick-decision":
        payload = run_quick_decision(
            ticker=args.ticker or None,
            adr_premium_pct=args.adr_premium_pct,
            local_px=args.local_px,
            trigger_description=args.trigger_description or None,
            rsi_state=args.rsi_state,
            adr_px=args.adr_px,
            fx_rate=args.fx_rate,
            adr_ratio=args.adr_ratio,
            prompt=not args.no_prompt,
        )
    elif args.command == "build-dashboard":
        payload = build_dashboard_bundle()
    elif args.command == "serve-cockpit-api":
        serve_cockpit_api(host=args.host, port=args.port)
        return 0
    elif args.command == "sync-research-contracts":
        payload = sync_research_contracts()
    elif args.command == "sync-candidates":
        payload = sync_candidate_queue(REPO_ROOT / "research")
    elif args.command == "upsert-candidate":
        payload = upsert_candidate_dossier(
            REPO_ROOT / "research",
            ticker=args.ticker,
            company_name=args.company_name,
            research_topic=args.research_topic,
            candidate_origin=args.origin,
            research_stage=args.stage,
            radar_flags=args.radar_flag,
            radar_summary=args.radar_summary,
            radar_risk_level=args.radar_risk_level,
            note=args.note,
            current_action=args.current_action or None,
            invalidation_reason=args.invalidation_reason,
            decision_status=args.decision_status or None,
        )
    else:
        draft_summary = read_json(DRAFT_SUMMARY_PATH, default={"refreshed_tickers": []})
        tickers = args.tickers or [item["ticker"] for item in draft_summary.get("refreshed_tickers", [])]
        digest_payload = build_portfolio_digest(
            REPO_ROOT / "research",
            tickers=tickers,
        )
        notification_payload = build_notification_payload(
            digest_payload,
            run_type=args.run_type,
            dashboard_url=args.dashboard_url,
            pr_url=args.pr_url,
        )
        payload = {
            "notification": notification_payload,
            "delivery": send_resend_email(notification_payload),
        }

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
