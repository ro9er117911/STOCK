from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_USER_AGENT = "ro9air-stock-research/1.0 ro9er117911@users.noreply.github.com"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_TRANSLATION_MODEL = "gpt-4.1-mini"
BOT_NAME = "stock-research-bot"
BOT_EMAIL = "actions@users.noreply.github.com"

REPO_ROOT = Path(".")
RESEARCH_ROOT = REPO_ROOT / "research"
SYSTEM_ROOT = RESEARCH_ROOT / "system"
OBSERVATION_LAKE_PATH = SYSTEM_ROOT / "observation_lake.json"
OBSERVATION_EVENTS_PATH = SYSTEM_ROOT / "observation_events.jsonl"
OBSERVATION_GRAPH_PATH = SYSTEM_ROOT / "observation_graph.json"
AUTOMATION_ROOT = REPO_ROOT / "automation" / "run"
CONTEXT_ROOT = AUTOMATION_ROOT / "context"
RUN_SUMMARY_PATH = AUTOMATION_ROOT / "poll-summary.json"
DRAFT_SUMMARY_PATH = AUTOMATION_ROOT / "draft-summary.json"
CANONICAL_DIGEST_PATH = AUTOMATION_ROOT / "canonical-digest.json"
NOTIFICATION_PAYLOAD_PATH = AUTOMATION_ROOT / "notification-payload.json"
EMAIL_PREVIEW_HTML_PATH = AUTOMATION_ROOT / "email-preview.html"
EMAIL_PREVIEW_TEXT_PATH = AUTOMATION_ROOT / "email-preview.txt"
PR_BODY_PATH = AUTOMATION_ROOT / "pr-body.md"
PR_BODY_ZH_TW_PATH = AUTOMATION_ROOT / "pr-body.zh-tw.md"
TRANSLATION_SUMMARY_PATH = AUTOMATION_ROOT / "translation-summary.json"
TEST_EVENTS_ROOT = REPO_ROOT / "automation" / "test_events"
SOURCE_REGISTRY_PATH = SYSTEM_ROOT / "source_registry.json"
OPERATOR_GUIDE_PATH = REPO_ROOT / "docs" / "operator-guide.md"
PORTFOLIO_PRIVATE_PATH = SYSTEM_ROOT / "portfolio.private.json"
PORTFOLIO_PRIVATE_EXAMPLE_PATH = SYSTEM_ROOT / "portfolio.private.json.example"
RISK_POLICY_PATH = SYSTEM_ROOT / "risk_policy.json"
SITE_ROOT = REPO_ROOT / "site"
SITE_DATA_ROOT = SITE_ROOT / "data"
SITE_TICKER_DATA_ROOT = SITE_DATA_ROOT / "tickers"
SITE_TICKER_PAGE_ROOT = SITE_ROOT / "tickers"
SITE_RESEARCH_PAGE_ROOT = SITE_ROOT / "research"
LOCAL_DASHBOARD_ROOT = AUTOMATION_ROOT / "dashboard-local"
COCKPIT_API_HOST = "127.0.0.1"
COCKPIT_API_PORT = 8001
SOURCE_STATUS_FILENAME = "source_status.json"
DIGEST_FILENAME = "digest.json"


@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    source_type: str
    kind: str
    url: str
    status: str = "active"
    priority: int = 50
    title_keywords: tuple[str, ...] = ()
    allow_patterns: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class TickerConfig:
    ticker: str
    company_name: str
    cik: str
    yahoo_symbol: str
    price_gap_pct: float
    abnormal_volume_ratio: float
    deep_refresh_days: int = 7
    sources: tuple[SourceConfig, ...] = field(default_factory=tuple)


def _read_source_registry(path: Path = SOURCE_REGISTRY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_source_registry(path: Path = SOURCE_REGISTRY_PATH) -> dict[str, TickerConfig]:
    payload = _read_source_registry(path)
    watchlist: dict[str, TickerConfig] = {}
    for row in payload["tickers"]:
        watchlist[row["ticker"]] = TickerConfig(
            ticker=row["ticker"],
            company_name=row["company_name"],
            cik=row["cik"],
            yahoo_symbol=row["yahoo_symbol"],
            price_gap_pct=row["price_gap_pct"],
            abnormal_volume_ratio=row["abnormal_volume_ratio"],
            deep_refresh_days=row.get("deep_refresh_days", 7),
            sources=tuple(
                SourceConfig(
                    source_id=source["source_id"],
                    source_type=source["source_type"],
                    kind=source["kind"],
                    url=source["url"],
                    status=source.get("status", "active"),
                    priority=source.get("priority", 50),
                    title_keywords=tuple(source.get("title_keywords", ())),
                    allow_patterns=tuple(source.get("allow_patterns", ())),
                    notes=source.get("notes", ""),
                )
                for source in row.get("sources", ())
            ),
        )
    return watchlist


WATCHLIST = load_source_registry()
