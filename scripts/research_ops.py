#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stock_research.config import DRAFT_SUMMARY_PATH
from stock_research.candidates import upsert_candidate_dossier
from stock_research.dashboard import build_dashboard_bundle
from stock_research.digest import build_notification_payload, build_portfolio_digest
from stock_research.notify import send_resend_email
from stock_research.pipeline import bootstrap_baselines, draft_refreshes, poll_events, sync_research_contracts
from stock_research.research_state import sync_candidate_queue
from stock_research.storage import read_json


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

    subparsers.add_parser("build-dashboard", help="Generate the static dashboard site.")
    subparsers.add_parser("sync-research-contracts", help="Normalize all research states and rebuild candidate queue.")
    subparsers.add_parser("sync-candidates", help="Rebuild the candidate queue from research dossiers.")

    candidate_parser = subparsers.add_parser("upsert-candidate", help="Create or update a candidate research dossier.")
    candidate_parser.add_argument("--ticker", required=True, help="Ticker symbol for the candidate.")
    candidate_parser.add_argument("--company-name", required=True, help="Company name for the candidate dossier.")
    candidate_parser.add_argument("--research-topic", required=True, help="Short research topic for the dossier.")
    candidate_parser.add_argument(
        "--origin",
        default="manual_watchlist",
        choices=("manual_watchlist", "ad_hoc_idea", "quant_radar"),
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
    elif args.command == "poll":
        payload = poll_events(trigger=args.trigger, fixture_name=args.fixture or None)
    elif args.command == "draft-refresh":
        payload = draft_refreshes(trigger=args.trigger, fixture_name=args.fixture or None)
    elif args.command == "build-dashboard":
        payload = build_dashboard_bundle()
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


if __name__ == "__main__":
    raise SystemExit(main())
