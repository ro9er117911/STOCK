#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stock_research.pipeline import bootstrap_baselines, draft_refreshes, poll_events


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

    draft_parser = subparsers.add_parser("draft-refresh", help="Create draft thesis refreshes for material updates.")
    draft_parser.add_argument(
        "--trigger",
        choices=("event", "scheduled", "manual"),
        default="event",
        help="Reason for the refresh pipeline.",
    )

    args = parser.parse_args()
    if args.command == "bootstrap-baselines":
        payload = {"created": bootstrap_baselines(force=args.force)}
    elif args.command == "poll":
        payload = poll_events(trigger=args.trigger)
    else:
        payload = draft_refreshes(trigger=args.trigger)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
